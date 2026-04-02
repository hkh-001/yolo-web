<script lang="ts" setup>
import {
    ElForm, ElSelect, ElUpload, ElIcon, ElSlider, ElButton, ElInputNumber, ElInput, ElPopconfirm, ElRadioGroup, ElRadio,
    type UploadUserFile, type UploadProps, type UploadInstance, type UploadRawFile, genFileId,
} from 'element-plus';
import { Delete, Refresh, UploadFilled, FolderAdd } from '@element-plus/icons-vue';
import * as api from "@/utils/api"
import type { ModelInfo } from '@/utils/api';
import type { Task } from '@/utils/api/task';
import { Message } from '@/utils/message';
import { setURLParams } from '@/utils/url';

import { computed, onMounted, reactive, ref } from 'vue'
import { preventElemmentSSRError } from '@/utils/ssr';

preventElemmentSSRError()

const props = defineProps<{
    title: string;
}>();

const uploadEl = ref<UploadInstance | null>(null);
const uploadedFileList = ref<UploadUserFile[]>([]);

// 增强模式：full=整图, auto=自动检测, manual=手动ROI
const enhanceMode = ref<'full' | 'auto' | 'manual'>('full');

// 当前选中的展示模型
const selectedDisplayModel = ref<string>("Real-ESRGAN");

// 表单参数
const submitLoading = ref(false);
const stage = ref<'idle' | 'detecting' | 'enhancing' | 'done'>('idle');
const stageMessage = ref<string>('');

// 增强参数
const form = reactive({
    scale: 2,           // 放大倍数
    denoise: 0,         // 降噪强度 0-1
});

// ROI 参数（手动模式）
const roiBbox = ref<string>("[100, 100, 300, 300]");
const bboxError = ref<string>("");

// 检测结果（自动模式）
const detectedBoxes = ref<any[]>([]);
const selectedBox = ref<any>(null);

// 结果状态
const originalUrl = ref<string>("");
const enhancedUrl = ref<string>("");
const enhancedBlob = ref<Blob | null>(null);
const showOriginal = ref(false);
const processingTime = ref<number>(0);
const hasResult = computed(() => !!enhancedUrl.value);

// 任务保存状态
const queryTaskName = ref<string>("");
const submitTaskName = ref<string>("");
const saveLoading = ref(false);

// 增强类展示模型映射（展示名称 -> 后端真实模型ID）
// 注意：每个展示名称对应一种增强算法，实际后端调用根据 enhanceMode 选择 enhance 或 enhance-roi
const DISPLAY_MODELS = [
    { displayName: "Real-ESRGAN", backendId: "enhance" },
    { displayName: "SwinIR", backendId: "enhance" },
    { displayName: "Swin2SR", backendId: "enhance" },
    { displayName: "BasicSR", backendId: "enhance" },
];

// 获取模型列表（验证后端模型可用性）
function updateModels() {
    api.getModels().then((m) => {
        const hasEnhance = m.some(model => model.id === 'enhance')
        const hasEnhanceRoi = m.some(model => model.id === 'enhance-roi')
        if (!hasEnhance || !hasEnhanceRoi) {
            Message.warning("后端增强模型不可用")
        }
    }).catch((e: Error) => {
        Message.error(`获取模型列表失败：${e.name}`)
        console.error(e)
    })
}

onMounted(() => {
    updateModels()
})

const handleExceed: UploadProps['onExceed'] = (files) => {
    uploadEl.value!.clearFiles()
    const file = files[0] as UploadRawFile
    file.uid = genFileId()
    uploadEl.value!.handleStart(file)
}

function clearResults() {
    enhancedUrl.value = "";
    enhancedBlob.value = null;
    originalUrl.value = "";
    processingTime.value = 0;
    showOriginal.value = false;
    stage.value = 'idle';
    stageMessage.value = '';
    detectedBoxes.value = [];
    selectedBox.value = null;
}

// 校验 bbox 格式
function validateBbox(bboxStr: string): { valid: boolean; error?: string; value?: number[] } {
    const trimmed = bboxStr.trim();
    
    if (!trimmed.startsWith('[') || !trimmed.endsWith(']')) {
        return { valid: false, error: "格式错误：必须以 [ 开头，] 结尾" };
    }
    
    const content = trimmed.slice(1, -1).trim();
    if (!content) {
        return { valid: false, error: "格式错误：内容不能为空" };
    }
    
    const parts = content.split(',').map(p => p.trim());
    if (parts.length !== 4) {
        return { valid: false, error: `格式错误：需要 4 个数值，实际 ${parts.length} 个` };
    }
    
    const nums: number[] = [];
    for (let i = 0; i < 4; i++) {
        const num = parseInt(parts[i], 10);
        if (isNaN(num)) {
            return { valid: false, error: `格式错误：第 ${i + 1} 个值 "${parts[i]}" 不是有效数字` };
        }
        nums.push(num);
    }
    
    const [x1, y1, x2, y2] = nums;
    if (x2 <= x1) {
        return { valid: false, error: `数值错误：x2 (${x2}) 必须大于 x1 (${x1})` };
    }
    if (y2 <= y1) {
        return { valid: false, error: `数值错误：y2 (${y2}) 必须大于 y1 (${y1})` };
    }
    
    const MIN_SIZE = 32;
    if (x2 - x1 < MIN_SIZE || y2 - y1 < MIN_SIZE) {
        return { valid: false, error: `尺寸错误：ROI 宽高必须至少 ${MIN_SIZE} 像素` };
    }
    
    return { valid: true, value: nums };
}

// 防止重复提交锁
let isSubmitting = false;

async function onSubmit() {
    if (isSubmitting) {
        Message.warning("任务正在处理中，请稍候...")
        return;
    }
    
    if (uploadedFileList.value.length === 0) {
        Message.warning("请上传一张图片")
        return;
    }

    // 手动模式校验
    if (enhanceMode.value === 'manual') {
        bboxError.value = "";
        const validation = validateBbox(roiBbox.value);
        if (!validation.valid) {
            bboxError.value = validation.error || "bbox 格式错误";
            Message.warning(bboxError.value);
            return;
        }
    }

    isSubmitting = true;
    submitLoading.value = true;
    clearResults();
    
    const uploadedFile: File = uploadedFileList.value[0].raw!;
    originalUrl.value = URL.createObjectURL(uploadedFile);
    
    const startTime = Date.now();
    
    try {
        let res: Blob;
        
        switch (enhanceMode.value) {
            case 'full':
                // 整图增强
                res = await runFullEnhance(uploadedFile);
                break;
            case 'auto':
                // 自动检测增强
                res = await runAutoEnhance(uploadedFile);
                break;
            case 'manual':
                // 手动 ROI 增强
                res = await runManualEnhance(uploadedFile);
                break;
            default:
                throw new Error("未知的增强模式");
        }
        
        enhancedBlob.value = res;
        enhancedUrl.value = URL.createObjectURL(res);
        processingTime.value = Date.now() - startTime;
        stage.value = 'done';
        Message.success(`增强完成，耗时 ${(processingTime.value / 1000).toFixed(2)}s`);
        
    } catch (e: any) {
        console.error('[Enhance] 提交失败:', e);
        
        let errorMsg = '增强失败';
        if (e.name === 'TimeoutError' || e.message?.includes('timeout')) {
            errorMsg = '请求超时：模型处理时间过长';
        } else if (e.message) {
            errorMsg = e.message;
        }
        
        if (e.response) {
            try {
                const errorData = await e.response.json();
                if (errorData.message) errorMsg = errorData.message;
            } catch {}
        }
        
        Message.error(errorMsg);
    } finally {
        submitLoading.value = false;
        isSubmitting = false;
        stage.value = 'idle';
        stageMessage.value = '';
    }
}

// 整图增强
async function runFullEnhance(file: File): Promise<Blob> {
    stage.value = 'enhancing';
    stageMessage.value = `${selectedDisplayModel.value} 整图增强中...`;
    
    // 根据展示模型获取后端真实模型ID（整图增强使用 enhance）
    const backendModelId = DISPLAY_MODELS.find(m => m.displayName === selectedDisplayModel.value)?.backendId || 'enhance';
    
    const res = await api.callModels<"image">(
        backendModelId,
        {
            file: file,
            source: "image",
            scale: form.scale,
            denoise: form.denoise,
        },
        "image/jpeg"
    );
    
    if (!(res instanceof Blob)) {
        throw new Error("返回格式异常");
    }
    
    return res;
}

// 自动检测增强
async function runAutoEnhance(file: File): Promise<Blob> {
    // 阶段1：检测
    stage.value = 'detecting';
    stageMessage.value = '目标检测中...';
    
    const detectRes = await api.callModels<"image">(
        'yolo26n',
        {
            file: file,
            source: "image",
            conf: 0.25,
            iou: 0.7,
            imgsz: 640,
        },
        "application/json"
    );
    
    if (detectRes instanceof Blob) {
        throw new Error("检测返回格式异常，期望 JSON");
    }
    
    const detectData = detectRes as any;
    const boxes = detectData.boxes || detectData.predictions || [];
    
    // 过滤低置信度
    const validBoxes = boxes.filter((box: any) => {
        const conf = box.conf !== undefined ? box.conf : box.confidence;
        return conf >= 0.25;
    });
    
    if (validBoxes.length === 0) {
        throw new Error("未检测到目标（置信度>=0.25），请改用手动 ROI 模式");
    }
    
    // 取最高置信度
    validBoxes.sort((a: any, b: any) => {
        const confA = a.conf !== undefined ? a.conf : a.confidence;
        const confB = b.conf !== undefined ? b.conf : b.confidence;
        return confB - confA;
    });
    
    const bestBox = validBoxes[0];
    const boxCoords = bestBox.box || { x1: bestBox.xmin, y1: bestBox.ymin, x2: bestBox.xmax, y2: bestBox.ymax };
    const bbox = [boxCoords.x1, boxCoords.y1, boxCoords.x2, boxCoords.y2];
    
    console.log('[AutoEnhance] 检测到目标:', bestBox.name, 'conf:', bestBox.conf || bestBox.confidence);
    console.log('[AutoEnhance] 使用 bbox:', bbox);
    
    detectedBoxes.value = validBoxes;
    selectedBox.value = bestBox;
    
    // 阶段2：增强
    stage.value = 'enhancing';
    stageMessage.value = `${selectedDisplayModel.value} 增强目标: ${bestBox.name}...`;
    
    // ROI 增强使用 enhance-roi 后端
    const enhanceRes = await api.callModels<"image">(
        'enhance-roi',
        {
            file: file,
            bbox: JSON.stringify(bbox),
            source: "image",
            scale: form.scale,
            denoise: form.denoise,
        },
        "image/jpeg"
    );
    
    if (!(enhanceRes instanceof Blob)) {
        throw new Error("增强返回格式异常");
    }
    
    return enhanceRes;
}

// 手动 ROI 增强
async function runManualEnhance(file: File): Promise<Blob> {
    stage.value = 'enhancing';
    stageMessage.value = `${selectedDisplayModel.value} ROI 增强中...`;
    
    const validation = validateBbox(roiBbox.value);
    if (!validation.valid || !validation.value) {
        throw new Error(validation.error || "bbox 校验失败");
    }
    
    // ROI 增强使用 enhance-roi 后端
    const res = await api.callModels<"image">(
        'enhance-roi',
        {
            file: file,
            bbox: roiBbox.value.trim(),
            source: "image",
            scale: form.scale,
            denoise: form.denoise,
        },
        "image/jpeg"
    );
    
    if (!(res instanceof Blob)) {
        throw new Error("返回格式异常");
    }
    
    return res;
}

function toggleView() {
    showOriginal.value = !showOriginal.value;
}

function downloadResult() {
    if (!enhancedBlob.value) return;
    const link = document.createElement('a');
    link.href = enhancedUrl.value;
    link.download = `enhanced_${Date.now()}.jpg`;
    link.click();
}

function clearAll() {
    clearResults();
    submitTaskName.value = "";
}

async function saveResults() {
    if (!submitTaskName.value) {
        Message.warning("请输入任务名称");
        return;
    }
    if (!enhancedBlob.value) {
        Message.warning("没有可保存的结果");
        return;
    }
    
    saveLoading.value = true;
    
    try {
        const uploadedFile: File = uploadedFileList.value[0].raw!;
        const originalBlob = new Blob([uploadedFile], { type: uploadedFile.type });
        const originalId = await api.uploadFile(originalBlob).then(r => r.id);
        const resultId = await api.uploadFile(enhancedBlob.value).then(r => r.id);
        
        const inputArgs: any = {
            mode: enhanceMode.value,
            scale: form.scale,
            denoise: form.denoise
        };
        
        if (enhanceMode.value === 'manual') {
            inputArgs.bbox = roiBbox.value.trim();
        } else if (enhanceMode.value === 'auto' && selectedBox.value) {
            inputArgs.detected_box = selectedBox.value;
        }
        
        // 添加展示模型和后端模型映射
        const backendModelId = DISPLAY_MODELS.find(m => m.displayName === selectedDisplayModel.value)?.backendId || 'enhance';
        inputArgs.display_model = selectedDisplayModel.value;
        inputArgs.backend_model_id = backendModelId;
        
        const uploadObject: Omit<Task, 'id' | 'timestamp' | 'task_id'> = {
            source: enhanceMode.value === 'full' ? 'enhance' : `enhance-${enhanceMode.value}`,
            task_name: submitTaskName.value,
            input_blob: originalId,
            input_args: JSON.stringify(inputArgs),
            results: JSON.stringify({
                processing_time: processingTime.value,
                detected_boxes: detectedBoxes.value.length,
                selected_box: selectedBox.value
            }),
            results_blob: resultId,
        };
        
        const task_id = await api.saveTask(uploadObject).then(r => r.task_id);
        
        if (task_id) {
            setURLParams({ task: task_id }, true);
            Message.success("任务保存成功");
        }
    } catch (e: any) {
        console.error('[Enhance] 保存失败:', e);
        Message.error(`保存失败: ${e.message || '未知错误'}`);
    } finally {
        saveLoading.value = false;
    }
}
</script>

<template>
    <div class="mb-4 flex">
        <span class="text-2xl font-bold">{{ props.title }}</span>
    </div>
    
    <!-- 参数设置 -->
    <div>
        <div class="flex items-center gap-4">
            <span class="text-xl font-bold">参数设置</span>
        </div>
        <div class="mt-4">
            <ElForm class="*:my-2">
                <!-- 增强算法选择 -->
                <div class="*:my-2">
                    <span class="text-sm">增强算法</span>
                    <ElSelect v-model="selectedDisplayModel" class="mt-2">
                        <ElSelect.Option v-for="model in DISPLAY_MODELS" :key="model.displayName" 
                            :label="model.displayName" :value="model.displayName" />
                    </ElSelect>
                    <div class="text-xs text-gray-400 mt-1">
                        当前使用后端模型: {{ DISPLAY_MODELS.find(m => m.displayName === selectedDisplayModel)?.backendId }}
                    </div>
                </div>
                
                <!-- 增强模式选择 -->
                <div class="*:my-2">
                    <span class="text-sm">增强模式</span>
                    <ElRadioGroup v-model="enhanceMode" class="mt-2 ml-6">
                        <ElRadio label="full">整图增强</ElRadio>
                        <ElRadio label="auto">自动检测增强</ElRadio>
                        <ElRadio label="manual">手动 ROI 增强</ElRadio>
                    </ElRadioGroup>
                    <div class="text-xs text-gray-400 mt-1">
                        整图=全图超分 | 自动=检测后增强最高置信度目标 | 手动=指定区域增强
                    </div>
                </div>
                
                <!-- 手动模式：ROI 坐标输入 -->
                <div class="*:my-2" v-if="enhanceMode === 'manual'">
                    <span class="text-sm">ROI 坐标 (x1, y1, x2, y2)</span>
                    <ElInput 
                        v-model="roiBbox" 
                        placeholder="[100, 100, 300, 300]"
                        :class="bboxError ? 'border-red-500' : ''"
                    />
                    <div class="text-xs" :class="bboxError ? 'text-red-500' : 'text-gray-400'">
                        {{ bboxError || "格式: [x1, y1, x2, y2]，例如：[100, 100, 300, 300]" }}
                    </div>
                </div>
                
                <!-- 图片上传 -->
                <div class="*:my-2">
                    <span class="text-sm">上传图片</span>
                    <ElUpload class="upload-demo" ref="uploadEl" drag v-model:file-list="uploadedFileList"
                        :auto-upload="false" :on-exceed="handleExceed" :limit="1" multiple accept="image/*">
                        <ElIcon class="el-icon--upload">
                            <UploadFilled />
                        </ElIcon>
                        <div class="el-upload__text">
                            拖拽文件至此或<em>点击上传</em>
                        </div>
                        <template #tip>
                            <div class="el-upload__tip">支持 JPG/PNG 格式</div>
                        </template>
                    </ElUpload>
                </div>
                
                <!-- 放大倍数 -->
                <div class="*:my-2">
                    <span class="text-sm">放大倍数</span>
                    <ElSlider v-model="form.scale" show-input class="pl-2" :step="1" :min="1" :max="4" />
                    <div class="text-xs text-gray-400">1=原尺寸, 2=2倍超分, 4=4倍超分</div>
                </div>
                
                <!-- 降噪强度 -->
                <div class="*:my-2">
                    <span class="text-sm">降噪强度</span>
                    <ElSlider v-model="form.denoise" show-input class="pl-2" :step="0.1" :min="0" :max="1" />
                    <div class="text-xs text-gray-400">0=不降噪, 1=强力降噪</div>
                </div>
                
                <!-- 阶段提示 -->
                <div v-if="stage !== 'idle'" class="p-3 bg-blue-50 rounded-lg">
                    <div class="flex items-center gap-2">
                        <div class="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
                        <span class="text-sm text-blue-600">{{ stageMessage }}</span>
                    </div>
                </div>
                
                <!-- 提交按钮 -->
                <div class="!mt-4 flex gap-2">
                    <ElButton type="primary" class="flex-1" @click="onSubmit" :loading="submitLoading">
                        {{ submitLoading ? '处理中...' : '开始增强' }}
                    </ElButton>
                    <ElButton type="warning" plain :icon="Delete" @click="clearAll" v-show="hasResult">
                        清除结果
                    </ElButton>
                </div>
                
                <!-- 保存任务 -->
                <div class="!mt-4 flex gap-2" v-show="hasResult">
                    <ElInput v-model="submitTaskName" class="flex-1" placeholder="输入任务名称" />
                    <ElPopconfirm 
                        width="200" 
                        :title="queryTaskName ? '确定保存该任务吗？这将不会覆盖原有任务' : '确定保存该任务吗?'"
                        :hide-icon="true" 
                        @confirm="saveResults">
                        <template #reference>
                            <ElButton type="primary" plain :icon="FolderAdd" :loading="saveLoading">
                                保存任务
                            </ElButton>
                        </template>
                    </ElPopconfirm>
                </div>
            </ElForm>
        </div>
    </div>

    <!-- 结果展示 -->
    <div class="pt-8" v-show="hasResult">
        <div class="flex items-center justify-between mb-4">
            <div class="flex items-center gap-4">
                <span class="text-xl font-bold">增强结果</span>
                <ElButton text size="small" bg :type="showOriginal ? 'primary' : ''" @click="toggleView">
                    {{ showOriginal ? '查看增强图' : '查看原图' }}
                </ElButton>
            </div>
            <div class="flex items-center gap-2">
                <span class="text-sm text-gray-500">
                    处理耗时: {{ (processingTime / 1000).toFixed(2) }}s
                </span>
                <ElButton type="success" plain size="small" @click="downloadResult">
                    下载结果
                </ElButton>
            </div>
        </div>
        
        <!-- 图片对比区 -->
        <div class="border rounded-lg p-4">
            <div class="text-sm font-bold mb-2" :class="showOriginal ? 'text-gray-600' : 'text-green-600'">
                {{ showOriginal ? '原图' : '增强结果' }}
            </div>
            <img v-show="!showOriginal" :src="enhancedUrl" class="max-w-full rounded" alt="增强结果" />
            <img v-show="showOriginal" :src="originalUrl" class="max-w-full rounded" alt="原图" />
        </div>
        
        <!-- 参数信息 -->
        <div class="mt-4 p-4 bg-gray-50 rounded-lg text-sm text-gray-600">
            <div class="grid grid-cols-3 gap-4">
                <div>
                    <span class="text-gray-400">增强模式:</span> 
                    {{ enhanceMode === 'full' ? '整图' : enhanceMode === 'auto' ? '自动检测' : '手动 ROI' }}
                </div>
                <div>
                    <span class="text-gray-400">放大倍数:</span> {{ form.scale }}x
                </div>
                <div>
                    <span class="text-gray-400">处理耗时:</span> {{ (processingTime / 1000).toFixed(2) }}s
                </div>
            </div>
            <div v-if="enhanceMode === 'auto' && selectedBox" class="mt-2 pt-2 border-t border-gray-200">
                <span class="text-gray-400">检测目标:</span> 
                {{ selectedBox.name }} (置信度: {{ (selectedBox.conf || selectedBox.confidence || 0).toFixed(2) }})
            </div>
            <div v-if="enhanceMode === 'manual'" class="mt-2 pt-2 border-t border-gray-200">
                <span class="text-gray-400">ROI 坐标:</span> {{ roiBbox }}
            </div>
        </div>
    </div>
</template>

<style scoped>
.upload-demo {
    width: 100%;
}

@keyframes spin {
    to {
        transform: rotate(360deg);
    }
}

.animate-spin {
    animation: spin 1s linear infinite;
}
</style>
