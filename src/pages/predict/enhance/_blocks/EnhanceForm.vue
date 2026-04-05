<script lang="ts" setup>
import {
    ElForm, ElSelect, ElUpload, ElIcon, ElSlider, ElButton, ElInputNumber, ElInput, ElPopconfirm, ElRadioGroup, ElRadio, ElTag,
    type UploadUserFile, type UploadProps, type UploadInstance, type UploadRawFile, genFileId,
} from 'element-plus';
import { Delete, Refresh, UploadFilled, FolderAdd, Picture, InfoFilled, CircleCheck, Cpu, MagicStick, Brush, DocumentChecked, View, Download, FullScreen } from '@element-plus/icons-vue';
import * as api from "@/utils/api"
import type { ModelInfo } from '@/utils/api';
import type { Task } from '@/utils/api/task';
import { Message } from '@/utils/message';
import { setURLParams } from '@/utils/url';

import { computed, onMounted, reactive, ref, watch } from 'vue'
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
const hasUploaded = computed(() => uploadedFileList.value.length > 0);

// 任务保存状态
const queryTaskName = ref<string>("");
const submitTaskName = ref<string>("");
const saveLoading = ref(false);

// 增强类展示模型映射（展示名称 -> 后端真实模型ID）
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

// 从历史记录加载任务
async function loadFromTaskQuery() {
    const task_id = new URLSearchParams(window.location.search).get("task")
    if (task_id === null) return;
    if (!task_id) return Message.warning("未给定任务 ID"), false
    
    const task = await api.getTask(task_id).catch((e: Error) => {
        if (e.name === "HTTPError" && e.message.includes("status code 404")) {
            Message.warning("未找到该任务")
            return null
        }
        Message.error(`获取任务失败：${e.name}`)
        console.error(e)
        return null
    })
    if (!task) return false
    
    queryTaskName.value = task.task_name
    
    // 恢复参数
    if (task.input_args) {
        try {
            const inputArgs = JSON.parse(task.input_args)
            // 恢复增强模式
            if (inputArgs.enhance_mode) {
                enhanceMode.value = inputArgs.enhance_mode
            }
            // 恢复模型选择
            if (inputArgs.display_model) {
                selectedDisplayModel.value = inputArgs.display_model
            }
            // 恢复核心参数
            if (inputArgs.scale !== undefined) {
                form.scale = inputArgs.scale
            }
            if (inputArgs.denoise !== undefined) {
                form.denoise = inputArgs.denoise
            }
            // 恢复 ROI 参数（手动模式）
            if (inputArgs.bbox) {
                roiBbox.value = inputArgs.bbox
            }
            // 恢复选中框（自动模式）
            if (inputArgs.detected_box) {
                selectedBox.value = inputArgs.detected_box
            }
        } catch (e) {
            console.error("解析 input_args 失败:", e)
        }
    }
    
    // 恢复结果数据
    if (task.results) {
        try {
            const results = JSON.parse(task.results)
            if (results.processing_time) {
                processingTime.value = results.processing_time
            }
            if (results.selected_box) {
                selectedBox.value = results.selected_box
            }
        } catch (e) {
            console.error("解析 results 失败:", e)
        }
    }
    
    // 获取原图 blob
    const p_originalBlob = api.getFile(task.input_blob).then(blob => {
        if (blob) {
            const file = new File([blob], "image.jpg", { type: blob.type })
            uploadedFileList.value = [{ raw: file, status: "success", name: file.name, size: file.size }] as any
        }
        return blob
    }).catch((e: Error) => {
        Message.error(`获取输入文件失败：${e.name}`)
        console.error(e)
        return null
    })
    
    // 获取结果 blob（增强后的图）
    const p_resultBlob = task.results_blob ? api.getFile(task.results_blob).then(blob => {
        if (blob) {
            enhancedBlob.value = blob
        }
        return blob
    }).catch((e: Error) => {
        Message.error(`获取结果文件失败：${e.name}`)
        console.error(e)
        return null
    }) : Promise.resolve(null)
    
    const [originalBlobData, resultBlobData] = await Promise.all([p_originalBlob, p_resultBlob])
    
    // 设置显示 URL
    if (originalBlobData) {
        originalUrl.value = URL.createObjectURL(originalBlobData)
    }
    if (resultBlobData) {
        enhancedUrl.value = URL.createObjectURL(resultBlobData)
    }
    
    return true
}

onMounted(() => {
    updateModels()
    loadFromTaskQuery()
})

// 监听上传文件列表变化，自动加载原图
watch(uploadedFileList, (newList, oldList) => {
    // 如果上传了新文件（文件变化），清空上一轮结果
    if (newList.length > 0 && oldList.length > 0 && newList[0].uid !== oldList[0].uid) {
        clearResults()
    }
    if (newList.length > 0) {
        loadOriginalImage()
    }
}, { deep: true })

// 加载原图到上方框
async function loadOriginalImage() {
    if (uploadedFileList.value.length === 0) return;
    
    const file = uploadedFileList.value[0].raw;
    if (!file) return;
    
    originalUrl.value = URL.createObjectURL(file);
}

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
            source: "enhance",
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
    <div class="detection-container">
        <!-- 页面头部 -->
        <div class="page-header">
            <div class="header-main">
                <div class="header-icon">
                    <ElIcon :size="28"><MagicStick /></ElIcon>
                </div>
                <div class="header-content">
                    <h1 class="page-title">{{ props.title }}</h1>
                    <p class="page-subtitle">上传图片并执行超分辨率增强</p>
                </div>
            </div>
        </div>

        <!-- 主内容区 -->
        <div class="main-content">
            <!-- 左侧控制面板 -->
            <div class="control-panel">
                <!-- 模型与输入卡片 -->
                <div class="panel-card">
                    <div class="card-header">
                        <span class="card-title">模型与输入</span>
                    </div>
                    <div class="card-body">
                        <ElForm label-position="top">
                            <!-- 增强算法选择 -->
                            <div class="model-section">
                                <div class="section-label">
                                    <span class="label-text">增强算法</span>
                                    <span class="label-desc">选择用于超分辨率重建的算法模型</span>
                                </div>
                                <ElSelect v-model="selectedDisplayModel" class="model-select" popper-class="dark-select">
                                    <ElSelect.Option 
                                        v-for="model in DISPLAY_MODELS" 
                                        :key="model.displayName" 
                                        :label="model.displayName" 
                                        :value="model.displayName" 
                                    />
                                </ElSelect>
                            </div>
                            
                            <!-- 分隔线 -->
                            <div class="section-divider"></div>
                            
                            <!-- 上传区域 -->
                            <div class="upload-section">
                                <div class="section-label">
                                    <span class="label-text">上传图片</span>
                                    <span class="label-desc">支持拖拽或点击上传</span>
                                </div>
                                <ElUpload 
                                    ref="uploadEl" 
                                    drag 
                                    v-model:file-list="uploadedFileList"
                                    :auto-upload="false" 
                                    :on-exceed="handleExceed" 
                                    :limit="1"
                                    class="upload-area"
                                >
                                    <div class="upload-content">
                                        <div class="upload-icon-wrapper">
                                            <ElIcon class="upload-icon" :size="32">
                                                <UploadFilled />
                                            </ElIcon>
                                        </div>
                                        <div class="upload-text-main">
                                            <span class="upload-primary">拖拽图片至此</span>
                                            <span class="upload-secondary">或点击选择文件</span>
                                        </div>
                                        <div class="upload-meta">
                                            <span class="upload-format">JPG / PNG</span>
                                            <span class="upload-limit">单张图片</span>
                                        </div>
                                    </div>
                                </ElUpload>
                            </div>
                        </ElForm>
                    </div>
                </div>

                <!-- 增强模式与参数卡片 -->
                <div class="panel-card">
                    <div class="card-header">
                        <span class="card-title">增强参数</span>
                    </div>
                    <div class="card-body">
                        <!-- 增强模式选择 -->
                        <div class="param-section">
                            <div class="section-subtitle">
                                <ElIcon class="subtitle-icon" :size="14"><Cpu /></ElIcon>
                                <span class="subtitle-text">增强模式</span>
                            </div>
                            <div class="enhance-mode-group">
                                <ElRadioGroup v-model="enhanceMode">
                                    <ElRadio label="full">整图增强</ElRadio>
                                    <ElRadio label="auto">自动检测增强</ElRadio>
                                    <ElRadio label="manual">手动 ROI 增强</ElRadio>
                                </ElRadioGroup>
                                <div class="mode-hint">
                                    整图=全图超分 | 自动=检测后增强最高置信度目标 | 手动=指定区域增强
                                </div>
                            </div>
                            
                            <!-- 手动模式：ROI 坐标输入 -->
                            <div class="roi-input-section" v-if="enhanceMode === 'manual'">
                                <div class="param-item">
                                    <div class="param-header">
                                        <span class="param-name">ROI 坐标 (x1, y1, x2, y2)</span>
                                    </div>
                                    <ElInput 
                                        v-model="roiBbox" 
                                        placeholder="[100, 100, 300, 300]"
                                        :class="bboxError ? 'input-error' : ''"
                                    />
                                    <div class="param-hint" :class="bboxError ? 'error-text' : ''">
                                        {{ bboxError || "格式: [x1, y1, x2, y2]，例如：[100, 100, 300, 300]" }}
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- 分隔线 -->
                        <div class="param-divider"></div>

                        <!-- 核心参数 -->
                        <div class="param-section">
                            <div class="section-subtitle">
                                <ElIcon class="subtitle-icon" :size="14"><CircleCheck /></ElIcon>
                                <span class="subtitle-text">核心参数</span>
                            </div>
                            
                            <!-- 放大倍数 -->
                            <div class="param-item">
                                <div class="param-header">
                                    <span class="param-name">放大倍数</span>
                                    <span class="param-badge">{{ form.scale }}x</span>
                                </div>
                                <div class="param-hint">1=原尺寸, 2=2倍超分, 4=4倍超分</div>
                                <ElSlider v-model="form.scale" :step="1" :min="1" :max="4" show-stops />
                            </div>
                            
                            <!-- 降噪强度 -->
                            <div class="param-item">
                                <div class="param-header">
                                    <span class="param-name">降噪强度</span>
                                    <span class="param-badge">{{ form.denoise.toFixed(1) }}</span>
                                </div>
                                <div class="param-hint">0=不降噪, 1=强力降噪</div>
                                <ElSlider v-model="form.denoise" :step="0.1" :min="0" :max="1" show-stops />
                            </div>
                        </div>
                    </div>
                </div>

                <!-- 输出与操作卡片 -->
                <div class="panel-card action-card">
                    <div class="card-header">
                        <span class="card-title">操作</span>
                    </div>
                    <div class="card-body">
                        <!-- 阶段提示 -->
                        <div v-if="stage !== 'idle'" class="stage-indicator">
                            <div class="stage-spinner"></div>
                            <span class="stage-text">{{ stageMessage }}</span>
                        </div>
                        
                        <!-- 操作按钮区 -->
                        <div class="action-section">
                            <div class="section-subtitle">
                                <ElIcon class="subtitle-icon" :size="14"><Brush /></ElIcon>
                                <span class="subtitle-text">增强操作</span>
                            </div>
                            
                            <div class="action-buttons">
                                <ElButton 
                                    type="primary" 
                                    size="large" 
                                    @click="onSubmit" 
                                    :loading="submitLoading"
                                    :disabled="uploadedFileList.length === 0"
                                    class="action-btn submit-btn"
                                >
                                    <ElIcon class="btn-icon" :size="18"><FullScreen /></ElIcon>
                                    <span>{{ submitLoading ? '处理中...' : '开始增强' }}</span>
                                </ElButton>
                                
                                <ElButton 
                                    type="info" 
                                    plain 
                                    size="large"
                                    @click="clearAll" 
                                    v-show="hasResult"
                                    class="action-btn clear-btn"
                                >
                                    <ElIcon class="btn-icon" :size="16"><Delete /></ElIcon>
                                    <span>清除结果</span>
                                </ElButton>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- 保存任务卡片 -->
                <div class="panel-card save-card" v-show="hasResult">
                    <div class="card-header">
                        <span class="card-title">保存任务</span>
                    </div>
                    <div class="card-body">
                        <div class="save-task-section">
                            <p class="save-hint">将当前增强结果保存到历史记录</p>
                            <div class="save-task-row">
                                <ElInput 
                                    v-model="submitTaskName" 
                                    placeholder="输入任务名称" 
                                    class="task-name-input"
                                    size="large"
                                    clearable
                                >
                                    <template #prefix>
                                        <ElIcon><DocumentChecked /></ElIcon>
                                    </template>
                                </ElInput>
                                <ElPopconfirm 
                                    width="280" 
                                    :title="queryTaskName ? '确定保存该任务吗？这将不会覆盖原有任务' : '确定保存该任务吗?'"
                                    :hide-icon="true" 
                                    @confirm="saveResults"
                                >
                                    <template #reference>
                                        <ElButton 
                                            type="success" 
                                            size="large"
                                            :icon="FolderAdd" 
                                            :loading="saveLoading"
                                            :disabled="!submitTaskName"
                                            class="save-btn"
                                        >
                                            保存任务
                                        </ElButton>
                                    </template>
                                </ElPopconfirm>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- 右侧结果面板 -->
            <div class="result-panel">
                <!-- 原始图像框（上方，始终显示） -->
                <div class="panel-card original-card top-original">
                    <div class="card-header original-header">
                        <div class="result-title-group">
                            <span class="card-title">原始图像</span>
                        </div>
                    </div>
                    <div class="card-body original-body">
                        <!-- 原始图像空状态 -->
                        <div class="result-placeholder original-placeholder" v-show="!hasUploaded">
                            <div class="placeholder-content">
                                <div class="placeholder-icon-wrapper">
                                    <ElIcon class="placeholder-icon" :size="48">
                                        <Picture />
                                    </ElIcon>
                                </div>
                                <p class="placeholder-title">未上传图片</p>
                                <p class="placeholder-desc">请先上传图片，原始图像将显示在这里</p>
                            </div>
                        </div>
                        
                        <!-- 原始图像展示区 -->
                        <div class="result-display-wrapper unified-display" v-show="hasUploaded">
                            <div class="result-canvas-container unified-container">
                                <img v-if="originalUrl" :src="originalUrl" class="result-image" alt="原始图像" />
                            </div>
                        </div>
                    </div>
                </div>

                <!-- 增强结果框（下方，始终显示） -->
                <div class="panel-card result-card bottom-result">
                    <div class="card-header result-header">
                        <div class="result-title-group">
                            <span class="card-title">增强结果</span>
                            <ElTag v-if="hasResult" type="success" effect="dark" size="small" class="result-status-tag">
                                增强完成
                            </ElTag>
                        </div>
                        <div class="result-actions" v-show="hasResult">
                            <ElButton text size="small" bg :type="showOriginal ? 'primary' : ''" @click="toggleView" class="toggle-btn">
                                {{ showOriginal ? '查看增强图' : '查看原图' }}
                            </ElButton>
                            <ElButton type="success" plain size="small" @click="downloadResult" class="download-btn">
                                <ElIcon class="btn-icon-left" :size="14"><Download /></ElIcon>
                                下载结果
                            </ElButton>
                        </div>
                    </div>
                    <div class="card-body result-body">
                        <!-- 增强结果空状态 -->
                        <div class="result-placeholder result-placeholder-empty" v-show="!hasResult">
                            <div class="placeholder-content">
                                <div class="placeholder-icon-wrapper">
                                    <ElIcon class="placeholder-icon" :size="48">
                                        <Picture />
                                    </ElIcon>
                                </div>
                                <p class="placeholder-title">等待增强</p>
                                <p class="placeholder-desc">上传图片并点击"开始增强"后，增强结果将显示在这里</p>
                            </div>
                        </div>
                        
                        <!-- 增强结果展示区 -->
                        <div class="result-display-wrapper unified-display" v-show="hasResult">
                            <div class="result-canvas-container unified-container">
                                <img 
                                    v-show="!showOriginal" 
                                    :src="enhancedUrl" 
                                    class="result-image" 
                                    alt="增强结果" 
                                />
                                <img 
                                    v-show="showOriginal" 
                                    :src="originalUrl" 
                                    class="result-image" 
                                    alt="原图" 
                                />
                            </div>
                        </div>
                        
                        <!-- 参数信息展示 -->
                        <div class="enhance-info-section" v-if="hasResult">
                            <div class="info-header">
                                <ElIcon class="info-icon" :size="14"><InfoFilled /></ElIcon>
                                <span class="info-title">处理信息</span>
                            </div>
                            <div class="info-grid">
                                <div class="info-item">
                                    <span class="info-label">增强模式:</span>
                                    <span class="info-value">
                                        {{ enhanceMode === 'full' ? '整图' : enhanceMode === 'auto' ? '自动检测' : '手动 ROI' }}
                                    </span>
                                </div>
                                <div class="info-item">
                                    <span class="info-label">放大倍数:</span>
                                    <span class="info-value">{{ form.scale }}x</span>
                                </div>
                                <div class="info-item">
                                    <span class="info-label">处理耗时:</span>
                                    <span class="info-value">{{ (processingTime / 1000).toFixed(2) }}s</span>
                                </div>
                            </div>
                            <div v-if="enhanceMode === 'auto' && selectedBox" class="info-extra">
                                <span class="info-label">检测目标:</span>
                                <span class="info-value">{{ selectedBox.name }} (置信度: {{ (selectedBox.conf || selectedBox.confidence || 0).toFixed(2) }})</span>
                            </div>
                            <div v-if="enhanceMode === 'manual'" class="info-extra">
                                <span class="info-label">ROI 坐标:</span>
                                <span class="info-value">{{ roiBbox }}</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<style scoped>
/* ===== 基础布局 ===== */
.detection-container {
    width: 100%;
    max-width: 1600px;
    margin: 0 auto;
    padding: 0 1rem;
}

/* ===== 页面头部 ===== */
.page-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 1.5rem;
    padding: 1rem 1.25rem;
    background: rgba(30, 30, 40, 0.6);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    backdrop-filter: blur(10px);
}

.header-main {
    display: flex;
    align-items: center;
    gap: 0.875rem;
}

.header-icon {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 48px;
    height: 48px;
    background: linear-gradient(135deg, rgba(64, 158, 255, 0.2), rgba(103, 194, 58, 0.15));
    border: 1px solid rgba(64, 158, 255, 0.25);
    border-radius: 10px;
    color: #409eff;
}

.header-content {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
}

.page-title {
    font-size: 1.5rem;
    font-weight: 700;
    margin: 0;
    background: linear-gradient(90deg, #409eff, #67c23a);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    line-height: 1.2;
}

.page-subtitle {
    font-size: 0.8125rem;
    color: rgba(255, 255, 255, 0.5);
    margin: 0;
    line-height: 1.4;
}

/* ===== 主内容区 ===== */
.main-content {
    display: grid;
    grid-template-columns: 380px 1fr;
    gap: 1.5rem;
    align-items: start;
}

/* ===== 左侧控制面板 ===== */
.control-panel {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    min-height: 720px;
}

/* ===== 通用卡片样式 ===== */
.panel-card {
    background: rgba(30, 30, 40, 0.5);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    overflow: hidden;
    transition: all 0.3s ease;
}

.panel-card:hover {
    border-color: rgba(255, 255, 255, 0.12);
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
}

.card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.875rem 1.25rem;
    background: rgba(255, 255, 255, 0.03);
    border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.card-title {
    font-size: 0.9375rem;
    font-weight: 600;
    color: rgba(255, 255, 255, 0.9);
}

.card-body {
    padding: 1.25rem;
}

/* ===== 模型选择区 ===== */
.model-section {
    margin-bottom: 0.5rem;
}

.section-label {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
    margin-bottom: 0.75rem;
}

.label-text {
    font-size: 0.875rem;
    font-weight: 500;
    color: rgba(255, 255, 255, 0.9);
}

.label-desc {
    font-size: 0.75rem;
    color: rgba(255, 255, 255, 0.4);
}

.model-select {
    width: 100%;
}

.model-select :deep(.el-input__wrapper) {
    background: rgba(255, 255, 255, 0.05);
    box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.1) inset;
}

.model-select :deep(.el-input__wrapper:hover) {
    box-shadow: 0 0 0 1px rgba(64, 158, 255, 0.3) inset;
}

/* ===== 分隔线 ===== */
.section-divider {
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.1), transparent);
    margin: 1.25rem 0;
}

/* ===== 上传区域 ===== */
.upload-section {
    margin-top: 0.5rem;
}

:deep(.upload-area .el-upload) {
    width: 100%;
}

:deep(.upload-area .el-upload-dragger) {
    width: 100%;
    background: rgba(255, 255, 255, 0.02);
    border: 2px dashed rgba(255, 255, 255, 0.12);
    border-radius: 10px;
    padding: 1.5rem 1rem;
    transition: all 0.25s ease;
}

:deep(.upload-area .el-upload-dragger:hover) {
    background: rgba(64, 158, 255, 0.06);
    border-color: rgba(64, 158, 255, 0.4);
}

:deep(.upload-area .el-upload-dragger.is-dragover) {
    background: rgba(64, 158, 255, 0.1);
    border-color: #409eff;
    border-style: solid;
}

.upload-content {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.75rem;
}

.upload-icon-wrapper {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 56px;
    height: 56px;
    background: rgba(64, 158, 255, 0.1);
    border: 1px solid rgba(64, 158, 255, 0.2);
    border-radius: 50%;
    transition: all 0.25s ease;
}

:deep(.upload-area .el-upload-dragger:hover) .upload-icon-wrapper {
    background: rgba(64, 158, 255, 0.15);
    border-color: rgba(64, 158, 255, 0.35);
    transform: scale(1.02);
}

.upload-icon {
    color: #409eff;
}

.upload-text-main {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.25rem;
}

.upload-primary {
    font-size: 0.9375rem;
    font-weight: 500;
    color: rgba(255, 255, 255, 0.9);
}

.upload-secondary {
    font-size: 0.8125rem;
    color: rgba(255, 255, 255, 0.5);
}

.upload-meta {
    display: flex;
    gap: 0.5rem;
    margin-top: 0.25rem;
}

.upload-format,
.upload-limit {
    font-size: 0.6875rem;
    color: rgba(255, 255, 255, 0.4);
    padding: 0.125rem 0.5rem;
    background: rgba(255, 255, 255, 0.05);
    border-radius: 4px;
    border: 1px solid rgba(255, 255, 255, 0.08);
}

/* ===== 上传文件列表样式优化 ===== */
:deep(.upload-area .el-upload-list) {
    margin-top: 0.75rem;
}

:deep(.upload-area .el-upload-list__item) {
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 6px;
    margin-top: 0.5rem;
    transition: all 0.2s ease;
}

:deep(.upload-area .el-upload-list__item:hover) {
    background: rgba(255, 255, 255, 0.05);
    border-color: rgba(64, 158, 255, 0.2);
}

:deep(.upload-area .el-upload-list__item-name) {
    color: rgba(255, 255, 255, 0.8);
    font-size: 0.8125rem;
}

:deep(.upload-area .el-upload-list__item-file-name) {
    color: rgba(255, 255, 255, 0.6);
}

:deep(.upload-area .el-upload-list__item-status-label) {
    color: #67c23a;
}

:deep(.upload-area .el-upload-list__item .el-icon--close) {
    color: rgba(255, 255, 255, 0.5);
}

:deep(.upload-area .el-upload-list__item .el-icon--close:hover) {
    color: rgba(255, 255, 255, 0.8);
}

/* ===== 参数区域分组 ===== */
.param-section {
    margin-bottom: 1rem;
}

.param-section:last-child {
    margin-bottom: 0;
}

.section-subtitle {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 1rem;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.subtitle-icon {
    color: #409eff;
    display: flex;
    align-items: center;
}

.subtitle-text {
    font-size: 0.8125rem;
    font-weight: 600;
    color: rgba(255, 255, 255, 0.6);
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.param-divider {
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.08), transparent);
    margin: 1.25rem 0;
}

/* ===== 增强模式选择 ===== */
.enhance-mode-group {
    margin-bottom: 1rem;
}

.enhance-mode-group :deep(.el-radio-group) {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
}

.enhance-mode-group :deep(.el-radio) {
    color: rgba(255, 255, 255, 0.85);
    margin-right: 0;
}

.mode-hint {
    font-size: 0.75rem;
    color: rgba(255, 255, 255, 0.4);
    margin-top: 0.5rem;
}

/* ROI 输入区 */
.roi-input-section {
    margin-top: 1rem;
    padding-top: 1rem;
    border-top: 1px solid rgba(255, 255, 255, 0.06);
}

/* ===== 参数项样式 ===== */
.param-item {
    margin-bottom: 1.25rem;
}

.param-item:last-child {
    margin-bottom: 0;
}

.param-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 0.5rem;
}

.param-name {
    font-size: 0.875rem;
    font-weight: 500;
    color: rgba(255, 255, 255, 0.9);
}

.param-badge {
    background: rgba(64, 158, 255, 0.15);
    border: 1px solid rgba(64, 158, 255, 0.25);
    border-radius: 4px;
    padding: 0.125rem 0.5rem;
    color: #409eff;
    font-weight: 600;
    font-size: 0.8125rem;
    font-family: 'Consolas', monospace;
    min-width: 2.5rem;
    text-align: center;
}

.param-hint {
    font-size: 0.75rem;
    color: rgba(255, 255, 255, 0.4);
    margin-bottom: 0.5rem;
}

.param-hint.error-text {
    color: #f56c6c;
}

.input-error :deep(.el-input__wrapper) {
    box-shadow: 0 0 0 1px #f56c6c inset;
}

/* ===== 阶段指示器 ===== */
.stage-indicator {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.75rem 1rem;
    background: rgba(64, 158, 255, 0.1);
    border: 1px solid rgba(64, 158, 255, 0.2);
    border-radius: 8px;
    margin-bottom: 1rem;
}

.stage-spinner {
    width: 16px;
    height: 16px;
    border: 2px solid rgba(64, 158, 255, 0.3);
    border-top-color: #409eff;
    border-radius: 50%;
    animation: spin 1s linear infinite;
}

@keyframes spin {
    to {
        transform: rotate(360deg);
    }
}

.stage-text {
    font-size: 0.875rem;
    color: #409eff;
    font-weight: 500;
}

/* ===== 操作按钮 ===== */
.action-buttons {
    display: flex;
    flex-direction: column;
    gap: 0.625rem;
    margin-top: 0.75rem;
    width: 100%;
}

/* 按钮组统一基础样式 */
.action-btn {
    width: 100% !important;
    height: 44px !important;
    min-height: 44px;
    font-size: 0.9375rem;
    border-radius: 8px;
    display: inline-flex !important;
    align-items: center;
    justify-content: center;
    gap: 0.375rem;
    box-sizing: border-box;
    padding: 0 1rem;
    margin: 0;
}

/* 主按钮特殊样式 */
.submit-btn {
    font-weight: 600;
    letter-spacing: 0.5px;
    transition: all 0.25s ease;
}

.submit-btn:hover:not(:disabled) {
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(64, 158, 255, 0.35);
}

.submit-btn:disabled {
    opacity: 0.6;
    cursor: not-allowed;
}

/* 清除按钮特殊样式 */
.clear-btn {
    font-weight: 500;
}

/* 按钮图标统一 */
.btn-icon {
    font-size: 1.125rem;
    display: inline-flex;
    align-items: center;
    justify-content: center;
}

/* ===== 保存任务 ===== */
.save-card .card-body {
    padding: 1rem 1.25rem;
}

.save-task-section {
    display: flex;
    flex-direction: column;
    gap: 0.625rem;
}

.save-hint {
    font-size: 0.75rem;
    color: rgba(255, 255, 255, 0.45);
    margin: 0 0 0.25rem 0;
}

.save-task-row {
    display: flex;
    gap: 0.75rem;
    align-items: stretch;
}

.task-name-input {
    flex: 1;
}

.task-name-input :deep(.el-input__wrapper) {
    background: rgba(255, 255, 255, 0.05);
    padding-left: 0.75rem;
}

.save-btn {
    flex-shrink: 0;
    padding: 0 1.25rem;
}

/* ===== 右侧结果面板 ===== */
.result-panel {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    min-height: 900px;
    height: 100%;
}

/* 原始图像卡片（上方） */
.original-card {
    flex: 3;
    display: flex;
    flex-direction: column;
    border: 1px solid rgba(255, 255, 255, 0.08);
    background: rgba(30, 30, 40, 0.4);
    min-height: 420px;
}

.original-card .card-body {
    flex: 1;
    display: flex;
    flex-direction: column;
    padding: 1.25rem;
}

.original-header {
    padding: 0.875rem 1.25rem;
    background: rgba(255, 255, 255, 0.02);
    border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.original-header .card-title {
    font-size: 0.9375rem;
    color: rgba(255, 255, 255, 0.9);
}

.top-original {
    min-height: 420px;
}

/* 增强结果卡片（下方） */
.result-card {
    flex: 3;
    display: flex;
    flex-direction: column;
    border: 1px solid rgba(255, 255, 255, 0.1);
    min-height: 420px;
}

.result-card .card-body {
    flex: 1;
    display: flex;
    flex-direction: column;
    padding: 1.25rem;
}

.result-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
}

.result-title-group {
    display: flex;
    align-items: center;
    gap: 0.75rem;
}

.result-status-tag {
    font-weight: 500;
}

.result-actions {
    display: flex;
    align-items: center;
    gap: 0.625rem;
}

.toggle-btn {
    font-weight: 500;
}

.download-btn {
    font-weight: 500;
}

.btn-icon-left {
    margin-right: 0.25rem;
}

.bottom-result {
    min-height: 420px;
}

/* ===== 结果展示区域 ===== */
.result-placeholder {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 400px;
    border: 2px dashed rgba(255, 255, 255, 0.12);
    border-radius: 12px;
    background: rgba(255, 255, 255, 0.02);
    transition: all 0.3s ease;
}

.result-placeholder:hover {
    border-color: rgba(64, 158, 255, 0.25);
    background: rgba(64, 158, 255, 0.03);
}

.original-placeholder {
    min-height: 400px;
}

.result-placeholder-empty {
    min-height: 400px;
}

.placeholder-content {
    text-align: center;
    color: rgba(255, 255, 255, 0.5);
}

.placeholder-icon-wrapper {
    width: 100px;
    height: 100px;
    margin: 0 auto 1.25rem;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 50%;
    transition: all 0.3s ease;
}

.result-placeholder:hover .placeholder-icon-wrapper {
    background: rgba(64, 158, 255, 0.06);
    border-color: rgba(64, 158, 255, 0.2);
    transform: scale(1.02);
}

.placeholder-icon {
    color: rgba(255, 255, 255, 0.25);
    transition: color 0.3s ease;
}

.result-placeholder:hover .placeholder-icon {
    color: rgba(64, 158, 255, 0.5);
}

.placeholder-title {
    font-size: 1rem;
    font-weight: 600;
    color: rgba(255, 255, 255, 0.7);
    margin: 0 0 0.5rem;
}

.placeholder-desc {
    font-size: 0.8125rem;
    color: rgba(255, 255, 255, 0.4);
    margin: 0;
    line-height: 1.5;
}

/* 结果展示包装器 */
.result-display-wrapper {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-height: 360px;
}

/* 统一展示区 */
.unified-display {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-height: 360px;
}

/* 统一容器 */
.unified-container {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 360px;
    background: linear-gradient(135deg, rgba(0, 0, 0, 0.4), rgba(20, 20, 30, 0.5));
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    overflow: hidden;
    position: relative;
    padding: 1.5rem;
}

/* 原始图像容器特殊背景 */
.top-original .unified-container {
    background: linear-gradient(135deg, rgba(20, 20, 25, 0.5), rgba(30, 30, 40, 0.4));
    border: 1px solid rgba(255, 255, 255, 0.06);
}

/* 结果图片样式 */
.result-image {
    max-width: 100%;
    max-height: 65vh;
    height: auto;
    object-fit: contain;
    display: block;
    border-radius: 4px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
}

/* ===== 增强信息展示区 ===== */
.enhance-info-section {
    margin-top: 1.25rem;
    padding: 1rem;
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 8px;
}

.info-header {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.75rem;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.info-icon {
    color: #409eff;
}

.info-title {
    font-size: 0.8125rem;
    font-weight: 600;
    color: rgba(255, 255, 255, 0.7);
}

.info-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 0.75rem;
}

.info-item {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
}

.info-label {
    font-size: 0.6875rem;
    color: rgba(255, 255, 255, 0.5);
}

.info-value {
    font-size: 0.8125rem;
    color: rgba(255, 255, 255, 0.85);
    font-weight: 500;
}

.info-extra {
    margin-top: 0.75rem;
    padding-top: 0.75rem;
    border-top: 1px solid rgba(255, 255, 255, 0.06);
    font-size: 0.8125rem;
}

/* ===== 响应式适配 ===== */
@media (max-width: 1200px) {
    .main-content {
        grid-template-columns: 340px 1fr;
        gap: 1rem;
    }
}

@media (max-width: 992px) {
    .main-content {
        grid-template-columns: 1fr;
    }
    
    .control-panel {
        min-height: auto;
    }
    
    .result-panel {
        min-height: auto;
    }
    
    .info-grid {
        grid-template-columns: 1fr;
    }
    
    .save-task-row {
        flex-direction: column;
    }
}

@media (max-width: 576px) {
    .page-header {
        flex-direction: column;
        gap: 1rem;
        align-items: flex-start;
    }
    
    .header-main {
        width: 100%;
    }
    
    .result-actions {
        flex-wrap: wrap;
    }
}
</style>
