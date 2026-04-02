<script lang="ts" setup>
import {
    ElForm, ElSelect, ElUpload, ElIcon, ElSlider, ElButton, ElInputNumber, ElInput, ElPopconfirm,
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

// 表单参数
const modelId = ref<string>("");
const submitLoading = ref(false);

// 增强参数
const form = reactive({
    scale: 2,           // 放大倍数
    denoise: 0,         // 降噪强度 0-1
});

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

const models = ref<ModelInfo[]>([]);

// 获取模型列表（筛选增强模型）
function updateModels() {
    api.getModels().then((m) => {
        // 筛选增强模型（id 包含 enhance 或特定模型）
        const enhanceModels = m.filter(model => 
            model.id.includes('enhance') || model.id.includes('esrgan') || model.id.includes('super')
        );
        if (enhanceModels.length > 0) {
            modelId.value = enhanceModels[0].id;
            models.value = enhanceModels;
        } else if (m.length > 0) {
            // 如果没有专门的增强模型，显示所有模型
            modelId.value = m[0].id;
            models.value = m;
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
}

// 防止重复提交锁
let isSubmitting = false;

async function onSubmit() {
    if (isSubmitting) {
        Message.warning("任务正在处理中，请稍候...")
        return;
    }
    
    if (!modelId.value) {
        Message.warning("请选择一个模型")
        return;
    }
    if (uploadedFileList.value.length === 0) {
        Message.warning("请上传一张图片")
        return;
    }

    isSubmitting = true;
    submitLoading.value = true;
    
    const uploadedFile: File = uploadedFileList.value[0].raw!;
    
    // 保存原图 URL
    originalUrl.value = URL.createObjectURL(uploadedFile);
    
    const startTime = Date.now();
    
    try {
        // 调用增强模型，期望返回图片 Blob
        const res = await api.callModels<"image">(
            modelId.value, 
            {
                file: uploadedFile,
                source: "image",
                scale: form.scale,
                denoise: form.denoise,
            }, 
            "image/jpeg"  // 直接请求图片输出
        );
        
        if (res instanceof Blob) {
            enhancedBlob.value = res;
            enhancedUrl.value = URL.createObjectURL(res);
            processingTime.value = Date.now() - startTime;
            Message.success(`增强完成，耗时 ${(processingTime.value / 1000).toFixed(2)}s`);
        } else {
            Message.error("返回格式异常");
        }
        
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
    }
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
        // 上传原图
        const uploadedFile: File = uploadedFileList.value[0].raw!;
        const originalBlob = new Blob([uploadedFile], { type: uploadedFile.type });
        const originalId = await api.uploadFile(originalBlob).then(r => r.id);
        
        // 上传增强结果图
        const resultId = await api.uploadFile(enhancedBlob.value).then(r => r.id);
        
        // 保存任务
        const uploadObject: Omit<Task, 'id' | 'timestamp' | 'task_id'> = {
            source: "enhance",
            task_name: submitTaskName.value,
            input_blob: originalId,
            input_args: JSON.stringify({
                model_id: modelId.value,
                scale: form.scale,
                denoise: form.denoise
            }),
            results: JSON.stringify({
                processing_time: processingTime.value,
                original_size: { width: 0, height: 0 },  // Will be filled if available
                enhanced_size: { width: 0, height: 0 }
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
                <!-- 模型选择 -->
                <div class="*:my-2">
                    <span class="text-sm">选择增强模型</span>
                    <ElButton link :icon="Refresh" class="!m-0 !ml-2" @click="updateModels" />
                    <ElSelect v-model="modelId">
                        <ElSelect.Option v-for="model in models" :key="model.id" :label="model.name"
                            :value="model.id" />
                    </ElSelect>
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
                    <span class="text-gray-400">放大倍数:</span> {{ form.scale }}x
                </div>
                <div>
                    <span class="text-gray-400">降噪强度:</span> {{ form.denoise }}
                </div>
                <div>
                    <span class="text-gray-400">处理耗时:</span> {{ (processingTime / 1000).toFixed(2) }}s
                </div>
            </div>
        </div>
    </div>
</template>

<style scoped>
.upload-demo {
    width: 100%;
}
</style>
