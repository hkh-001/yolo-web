<script lang="ts" setup>
import {
    ElForm, ElSelect, ElUpload, ElIcon, ElSlider, ElSwitch, ElInputNumber, ElInputTag, ElButton, ElRadioGroup, ElRadio, ElInput,
    type UploadUserFile, type UploadProps, type UploadInstance, type UploadRawFile, genFileId,
    ElPopconfirm
} from 'element-plus';
import { Delete, FolderAdd, Refresh, UploadFilled, Picture } from '@element-plus/icons-vue';
import { defaultsPredictData, type ImageResponse, type PredictData, type SavedPredictData } from '@/utils/api/predict';
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
const originalCanvas = ref<HTMLCanvasElement | null>(null);
const resultCanvas = ref<HTMLCanvasElement | null>(null);

const queryTaskName = ref<string>("");
const submitTaskName = ref<string>("");
const form: Omit<typeof defaultsPredictData, "file"> = reactive(Object.assign({}, defaultsPredictData));
const submitLoading = ref(false);
const saveLoading = ref(false);
const showOriginal = ref(false);
const originalBlob = ref<Blob | null>(null);
const resultData = ref<ImageResponse | null>(null);
const resultBlob = ref<Blob | null>(null);
const hasResult = computed(() => resultData.value !== null || resultBlob.value !== null);

const models = ref<ModelInfo[]>([]);

const acceptOptions = [
    {
        name: "图像输出",
        id: "blob",
        value: "image/jpeg,image/png"
    }, {
        name: "前端数据渲染",
        id: "data",
        value: "application/json"
    }
];

const accept = ref<string>("application/json");

// 检测类展示模型映射（展示名称 -> 后端真实模型ID）
const DISPLAY_MODELS = [
    { displayName: "YOLO26", backendId: "yolo26n" },
    { displayName: "YOLO12", backendId: "yolo26n" },
    { displayName: "RT-DETR", backendId: "yolo26n" },
    { displayName: "Grounding DINO", backendId: "yolo26n" },
];

// 当前选中的模型（存储 displayName，提交时再映射到 backendId）
const selectedModelId = ref<string>(DISPLAY_MODELS[0].displayName);

function updateModels() {
    api.getModels().then((m) => {
        const hasDetectModel = m.some(model => model.id === 'yolo26n')
        if (!hasDetectModel) {
            Message.warning("后端检测模型不可用")
        }
        selectedModelId.value = DISPLAY_MODELS[0].displayName
    }).catch((e: Error) => {
        Message.error(`获取模型列表失败：${e.name}`)
        console.error(e)
    })
}

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
    const inputArgs = JSON.parse(task.input_args) as SavedPredictData
    const savedModelId = inputArgs.model_id;
    const matchingModel = DISPLAY_MODELS.find(m => m.displayName === savedModelId || m.backendId === savedModelId);
    selectedModelId.value = matchingModel?.displayName || DISPLAY_MODELS[0].displayName
    form.source = task.source
    for (let k in form) {
        if (Object.prototype.hasOwnProperty.call(inputArgs, k)) {
            (form as any)[k] = (inputArgs as any)[k]
        }
    }
    if (task.results) {
        resultData.value = JSON.parse(task.results)
    }
    const p_originalBlobUri = api.getFile(task.input_blob).then(blob => {
        if (blob) {
            const file = new File([blob], "image.jpg", { type: blob.type })
            uploadedFileList.value = [{ raw: file, status: "success", name: file.name, size: file.size }] as any
        }
        originalBlob.value = blob
        return URL.createObjectURL(blob)
    }).catch((e: Error) => {
        Message.error(`获取输入文件失败：${e.name}`)
        console.error(e)
        return null
    })
    const p_ResultsBlobUri = task.results_blob ? api.getFile(task.results_blob).then(blob => {
        resultBlob.value = blob
        return URL.createObjectURL(blob)
    }).catch((e: Error) => {
        Message.error(`获取结果文件失败：${e.name}`)
        console.error(e)
        return null
    }) : Promise.resolve(null)
    const [originalBlobUri, resultsBlobUri] = await Promise.all([p_originalBlobUri, p_ResultsBlobUri])
    if (resultsBlobUri) {
        accept.value = acceptOptions.find(o => o.id === "blob")!.value
        handleImageResultBlob(originalBlobUri!, resultsBlobUri!)
    } else if (resultData.value) {
        accept.value = acceptOptions.find(o => o.id === "data")!.value
        handleImageResultData(originalBlobUri!, resultData.value)
    }
}

onMounted(() => {
    updateModels()
    loadFromTaskQuery()
})

function clearResults() {
    resultData.value = null;
    resultBlob.value = null;
    showOriginal.value = false;
    submitTaskName.value = '';
    
    const resultImg = document.getElementById('result-image');
    const originalImg = document.getElementById('original-image');
    if (resultImg) resultImg.remove();
    if (originalImg) originalImg.remove();
    
    const o_canvas = originalCanvas.value;
    const r_canvas = resultCanvas.value;
    if (o_canvas) {
        o_canvas.style.removeProperty('display');
        const ctx = o_canvas.getContext('2d');
        if (ctx) ctx.clearRect(0, 0, o_canvas.width, o_canvas.height);
        o_canvas.width = 0;
        o_canvas.height = 0;
    }
    if (r_canvas) {
        r_canvas.style.removeProperty('display');
        const ctx = r_canvas.getContext('2d');
        if (ctx) ctx.clearRect(0, 0, r_canvas.width, r_canvas.height);
        r_canvas.width = 0;
        r_canvas.height = 0;
    }
}

const handleExceed: UploadProps['onExceed'] = (files) => {
    uploadEl.value!.clearFiles()
    const file = files[0] as UploadRawFile
    file.uid = genFileId()
    uploadEl.value!.handleStart(file)
}

let isSubmitting = false;

async function onSubmit() {
    if (isSubmitting) {
        Message.warning("任务正在提交中，请稍候...")
        return;
    }
    
    if (!selectedModelId.value) {
        Message.warning("请选择一个模型")
        return;
    }
    if (uploadedFileList.value.length === 0) {
        Message.warning("请上传一个文件")
        return;
    }

    isSubmitting = true;
    submitLoading.value = true;
    
    const selectedModel = DISPLAY_MODELS.find(m => m.displayName === selectedModelId.value);
    const backendModelId = selectedModel?.backendId || 'yolo26n';
    
    console.log(`[Submit] 开始提交任务，展示模型: ${selectedModelId.value}, 后端模型: ${backendModelId}`);
    const uploadedFile: File = uploadedFileList.value[0].raw!;
    let assignee: Partial<PredictData> = {
        source: "image",
        file: uploadedFile,
    }
    originalBlob.value = new Blob([uploadedFile], { type: uploadedFile.type });
    
    try {
        const res = await api.callModels<"image">(backendModelId, Object.assign({}, form, assignee), accept.value);
        
        if (res && (res instanceof Blob)) {
            resultBlob.value = res;
            handleImageResultBlob(URL.createObjectURL(uploadedFile), URL.createObjectURL(res));
        } else if (res && !(res instanceof Blob)) {
            resultData.value = res;
            handleImageResultData(URL.createObjectURL(uploadedFile), res as ImageResponse);
        }
        Message.success("任务提交成功");
    } catch (e: any) {
        console.error('[Submit] 提交失败:', e);
        let errorMsg = '提交失败';
        if (e.name === 'TimeoutError' || e.message?.includes('timeout')) {
            errorMsg = '请求超时：模型服务响应时间过长';
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
        console.log('[Submit] 提交流程结束');
    }
}

async function handleImageResultData(uri: string, data: any) {
    let boxes: any[] = [];
    if (Array.isArray(data)) {
        boxes = data;
    } else if (data && data.boxes && Array.isArray(data.boxes)) {
        boxes = data.boxes;
    } else if (data && data.predictions && Array.isArray(data.predictions)) {
        boxes = data.predictions;
    } else {
        console.error('[Render] 无法识别的数据格式:', data);
        return;
    }
    
    const o_canvas = originalCanvas.value!;
    const o_ctx = o_canvas.getContext('2d');
    if (!o_ctx) return;
    const r_canvas = resultCanvas.value!;
    const r_ctx = r_canvas.getContext('2d');
    if (!r_ctx) return;
    
    const img = new Image();
    img.onload = () => {
        o_canvas.width = img.width;
        o_canvas.height = img.height;
        o_ctx.drawImage(img, 0, 0);

        r_canvas.width = img.width;
        r_canvas.height = img.height;
        r_ctx.drawImage(img, 0, 0);
        
        const normalizedBoxes = boxes.map((box: any) => {
            let x, y, w, h, name, confidence, cls;
            if (box.box) {
                x = box.box.x1;
                y = box.box.y1;
                w = box.box.x2 - box.box.x1;
                h = box.box.y2 - box.box.y1;
                name = box.name;
                confidence = box.conf;
                cls = box.cls;
            } else {
                x = box.xmin;
                y = box.ymin;
                w = box.xmax - box.xmin;
                h = box.ymax - box.ymin;
                name = box.name;
                confidence = box.confidence;
                cls = box.class;
            }
            return { x, y, w, h, name, confidence, class: cls };
        });
        
        const colors = ["yellow", "white", "blue", "green", "red"];
        const types: number[] = [];
        for (let i = 0; i < normalizedBoxes.length; i++) {
            const box = normalizedBoxes[i];
            let colori = 0;
            if (types.includes(box.class)) colori = types.indexOf(box.class) % colors.length;
            else {
                types.push(box.class);
                colori = (types.length - 1) % colors.length;
            }
            r_ctx.strokeStyle = colors[colori];
            r_ctx.lineWidth = 4;
            r_ctx.strokeRect(box.x, box.y, box.w, box.h);
            r_ctx.font = "24px Arial-Bold";
            r_ctx.fillStyle = colors[colori];
            r_ctx.fillText(`${box.name} (${box.confidence?.toFixed(2) || 0})`, box.x, box.y - 12);
        }
    }
    img.src = uri;
}

async function handleImageResultBlob(originalUri: string, resultUri: string) {
    const container = originalCanvas.value?.parentElement;
    if (!container) return;
    
    const o_canvas = originalCanvas.value;
    const r_canvas = resultCanvas.value;
    if (o_canvas) o_canvas.style.display = 'none';
    if (r_canvas) r_canvas.style.display = 'none';
    
    const oldResultImg = document.getElementById('result-image');
    const oldOriginalImg = document.getElementById('original-image');
    if (oldResultImg) oldResultImg.remove();
    if (oldOriginalImg) oldOriginalImg.remove();
    
    const resultImg = document.createElement('img');
    resultImg.id = 'result-image';
    resultImg.className = 'result-image';
    resultImg.src = resultUri;
    resultImg.style.display = showOriginal.value ? 'none' : 'block';
    container.appendChild(resultImg);
    
    const originalImg = document.createElement('img');
    originalImg.id = 'original-image';
    originalImg.className = 'result-image';
    originalImg.src = originalUri;
    originalImg.style.display = showOriginal.value ? 'block' : 'none';
    container.appendChild(originalImg);
}

function switchOriginal() {
    const newValue = !showOriginal.value;
    showOriginal.value = newValue;
    
    const originalImg = document.getElementById('original-image') as HTMLImageElement;
    const resultImg = document.getElementById('result-image') as HTMLImageElement;
    
    if (originalImg && resultImg) {
        if (newValue) {
            originalImg.style.display = 'block';
            resultImg.style.display = 'none';
        } else {
            originalImg.style.display = 'none';
            resultImg.style.display = 'block';
        }
    }
}

async function saveResults() {
    if (!submitTaskName.value) {
        Message.warning("请输入任务名称")
        return;
    }
    saveLoading.value = true;
    const [originalId, resultId] = await Promise.all([
        api.uploadFile(originalBlob.value!).then(r => r.id),
        resultBlob.value ? api.uploadFile(resultBlob.value).then(r => r.id) : Promise.resolve(null)
    ]).catch((e: Error) => {
        Message.error(`上传失败：${e.name}`)
        console.error(e)
        return [null, null]
    })
    if (!originalId || (resultBlob.value && !resultId)) {
        saveLoading.value = false;
        return;
    }
    
    const selectedModel = DISPLAY_MODELS.find(m => m.displayName === selectedModelId.value);
    const backendModelId = selectedModel?.backendId || 'yolo26n';
    
    const uploadObject: Omit<Task, 'id' | 'timestamp' | 'task_id'> = {
        source: "image",
        task_name: submitTaskName.value,
        input_blob: originalId,
        input_args: JSON.stringify({
            display_model: selectedModelId.value,
            backend_model_id: backendModelId,
            ...Object.assign({}, form, { file: undefined, source: undefined })
        }),
        results: resultData.value ? JSON.stringify(resultData.value) : null,
        results_blob: resultId,
    }
    const task_id = await api.saveTask(uploadObject).then(r => r.task_id).catch((e: Error) => {
        Message.error(`保存任务失败：${e.name}`)
        console.error(e)
        return null
    })
    if (task_id) {
        setURLParams({ task: task_id }, true)
        Message.success(`任务保存成功`)
    }
    saveLoading.value = false;
}

function downloadResult() {
    if (!resultBlob.value) {
        Message.warning("没有可下载的结果")
        return;
    }
    const url = URL.createObjectURL(resultBlob.value);
    const a = document.createElement('a');
    a.href = url;
    a.download = `detection_result_${Date.now()}.jpg`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    Message.success("结果已下载");
}
</script>

<template>
    <div class="detection-container">
        <!-- 页面头部 -->
        <div class="page-header">
            <div class="header-main">
                <div class="header-icon">
                    <ElIcon :size="28"><Picture /></ElIcon>
                </div>
                <div class="header-content">
                    <h1 class="page-title">{{ title }}</h1>
                    <p class="page-subtitle">上传图片并执行目标检测</p>
                </div>
            </div>
            <div class="header-side" v-if="queryTaskName">
                <div class="task-tag">
                    <span class="task-tag-label">当前任务</span>
                    <span class="task-tag-name">{{ queryTaskName }}</span>
                    <ElButton :circle="true" :icon="Refresh" size="small" class="task-refresh-btn" @click="loadFromTaskQuery" />
                </div>
            </div>
        </div>

        <!-- 主内容区 -->
        <div class="main-content">
            <!-- 左侧控制面板 -->
            <div class="control-panel">
                <!-- 模型与上传卡片 -->
                <div class="panel-card">
                    <div class="card-header">
                        <span class="card-title">模型与输入</span>
                    </div>
                    <div class="card-body">
                        <ElForm :model="form" label-position="top">
                            <ElFormItem label="选择模型">
                                <div class="model-select-row">
                                    <ElSelect v-model="selectedModelId" class="flex-1">
                                        <ElSelect.Option 
                                            v-for="model in DISPLAY_MODELS" 
                                            :key="model.displayName" 
                                            :label="model.displayName" 
                                            :value="model.displayName" 
                                        />
                                    </ElSelect>
                                    <ElButton :icon="Refresh" @click="updateModels" class="refresh-model-btn" />
                                </div>
                            </ElFormItem>
                            
                            <ElFormItem label="上传图片">
                                <ElUpload 
                                    ref="uploadEl" 
                                    drag 
                                    v-model:file-list="uploadedFileList"
                                    :auto-upload="false" 
                                    :on-exceed="handleExceed" 
                                    :limit="1"
                                    class="upload-area"
                                >
                                    <ElIcon class="upload-icon">
                                        <UploadFilled />
                                    </ElIcon>
                                    <div class="upload-text">
                                        拖拽图片至此或<em>点击上传</em>
                                    </div>
                                    <template #tip>
                                        <div class="upload-tip">支持 JPG/PNG 格式图片</div>
                                    </template>
                                </ElUpload>
                            </ElFormItem>
                        </ElForm>
                    </div>
                </div>

                <!-- 检测参数卡片 -->
                <div class="panel-card">
                    <div class="card-header">
                        <span class="card-title">检测参数</span>
                    </div>
                    <div class="card-body">
                        <ElForm :model="form" label-position="top">
                            <!-- Confidence 置信度 -->
                            <div class="param-item">
                                <div class="param-header">
                                    <span class="param-name">置信度阈值</span>
                                    <span class="param-value">{{ form.conf.toFixed(2) }}</span>
                                </div>
                                <ElSlider v-model="form.conf" :step="0.01" :min="0" :max="1" show-stops />
                            </div>
                            
                            <!-- IoU 阈值 -->
                            <div class="param-item">
                                <div class="param-header">
                                    <span class="param-name">IoU 阈值 (NMS)</span>
                                    <span class="param-value">{{ form.iou.toFixed(2) }}</span>
                                </div>
                                <ElSlider v-model="form.iou" :step="0.01" :min="0" :max="1" show-stops />
                            </div>

                            <!-- 数字输入参数 -->
                            <div class="param-row">
                                <div class="param-item compact">
                                    <div class="param-header">
                                        <span class="param-name">图像大小 (imgsz)</span>
                                    </div>
                                    <ElInputNumber v-model="form.imgsz" :step="10" :min="16" :max="3656" class="full-width" />
                                </div>
                                <div class="param-item compact">
                                    <div class="param-header">
                                        <span class="param-name">最大检测数 (max_det)</span>
                                    </div>
                                    <ElInputNumber v-model="form.max_det" :min="1" :max="500" class="full-width" />
                                </div>
                            </div>
                        </ElForm>
                    </div>
                </div>

                <!-- 高级选项卡片 -->
                <div class="panel-card">
                    <div class="card-header">
                        <span class="card-title">高级选项</span>
                    </div>
                    <div class="card-body">
                        <div class="switch-list">
                            <div class="switch-item" title="FP16半精度推理可加速，需GPU支持">
                                <span class="switch-label">FP16 半精度推理</span>
                                <ElSwitch v-model="form.half" />
                            </div>
                            <div class="switch-item">
                                <span class="switch-label">测试时间增强 (TTA)</span>
                                <ElSwitch v-model="form.augment" />
                            </div>
                            <div class="switch-item">
                                <span class="switch-label">类别无关 NMS</span>
                                <ElSwitch v-model="form.agnostic_nms" />
                            </div>
                        </div>
                    </div>
                </div>

                <!-- 输出与操作卡片 -->
                <div class="panel-card">
                    <div class="card-header">
                        <span class="card-title">输出与操作</span>
                    </div>
                    <div class="card-body">
                        <ElForm :model="form" label-position="top">
                            <ElFormItem label="输出方式">
                                <ElRadioGroup v-model="accept" size="small">
                                    <ElRadio v-for="option in acceptOptions" :key="option.value" :value="option.value">
                                        {{ option.name }}
                                    </ElRadio>
                                </ElRadioGroup>
                            </ElFormItem>
                            
                            <div class="action-buttons">
                                <ElButton 
                                    type="primary" 
                                    size="large" 
                                    @click="onSubmit" 
                                    :loading="submitLoading"
                                    class="submit-btn"
                                >
                                    开始检测
                                </ElButton>
                                
                                <ElButton 
                                    type="warning" 
                                    plain 
                                    :icon="Delete" 
                                    @click="clearResults" 
                                    v-show="hasResult"
                                    class="clear-btn"
                                >
                                    清除结果
                                </ElButton>
                            </div>
                        </ElForm>
                    </div>
                </div>
            </div>

            <!-- 右侧结果面板 -->
            <div class="result-panel">
                <div class="panel-card result-card">
                    <div class="card-header">
                        <span class="card-title">检测结果</span>
                        <div class="result-actions" v-show="hasResult">
                            <ElButton 
                                text 
                                size="small" 
                                :type="showOriginal ? 'primary' : ''" 
                                @click="switchOriginal"
                            >
                                {{ showOriginal ? '查看结果' : '查看原图' }}
                            </ElButton>
                            <ElButton 
                                type="success" 
                                size="small"
                                @click="downloadResult"
                            >
                                下载结果
                            </ElButton>
                        </div>
                    </div>
                    <div class="card-body result-body">
                        <div class="result-placeholder" v-show="!hasResult">
                            <div class="placeholder-content">
                                <ElIcon class="placeholder-icon">
                                    <UploadFilled />
                                </ElIcon>
                                <p>上传图片并点击"开始检测"查看结果</p>
                            </div>
                        </div>
                        <div class="result-canvas-container" v-show="hasResult">
                            <canvas ref="originalCanvas" class="result-canvas" v-show="showOriginal"></canvas>
                            <canvas ref="resultCanvas" class="result-canvas" v-show="!showOriginal"></canvas>
                        </div>
                    </div>
                </div>

                <!-- 保存任务卡片 -->
                <div class="panel-card save-card" v-show="hasResult">
                    <div class="card-header">
                        <span class="card-title">保存任务</span>
                    </div>
                    <div class="card-body">
                        <div class="save-task-row">
                            <ElInput 
                                v-model="submitTaskName" 
                                placeholder="输入任务名称" 
                                class="task-name-input"
                            />
                            <ElPopconfirm 
                                width="200" 
                                :title="queryTaskName ? '确定保存该任务吗？这将不会覆盖原有任务' : '确定保存该任务吗？'"
                                :hide-icon="true" 
                                @confirm="saveResults"
                            >
                                <template #reference>
                                    <ElButton 
                                        type="primary" 
                                        plain 
                                        :icon="FolderAdd" 
                                        :loading="saveLoading"
                                    >
                                        保存
                                    </ElButton>
                                </template>
                            </ElPopconfirm>
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

.header-side {
    flex-shrink: 0;
}

.task-tag {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem 0.75rem;
    background: rgba(64, 158, 255, 0.1);
    border: 1px solid rgba(64, 158, 255, 0.2);
    border-radius: 8px;
}

.task-tag-label {
    font-size: 0.75rem;
    color: rgba(255, 255, 255, 0.5);
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.task-tag-name {
    font-size: 0.875rem;
    font-weight: 600;
    color: #409eff;
    max-width: 150px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.task-refresh-btn {
    margin-left: 0.25rem;
}

/* ===== 主内容区：双栏布局 ===== */
.main-content {
    display: grid;
    grid-template-columns: 380px 1fr;
    gap: 1.5rem;
    align-items: start;
}

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
}

/* ===== 卡片样式 ===== */
.panel-card {
    background: rgba(30, 30, 40, 0.6);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    margin-bottom: 1rem;
    overflow: hidden;
    backdrop-filter: blur(10px);
    transition: all 0.3s ease;
}

.panel-card:hover {
    border-color: rgba(64, 158, 255, 0.3);
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
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
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.card-title::before {
    content: '';
    width: 3px;
    height: 16px;
    background: linear-gradient(180deg, #409eff, #67c23a);
    border-radius: 2px;
}

.card-body {
    padding: 1.25rem;
}

/* ===== 左侧控制面板 ===== */
.control-panel {
    display: flex;
    flex-direction: column;
}

/* ===== 模型选择 ===== */
.model-select-row {
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.refresh-model-btn {
    flex-shrink: 0;
}

/* ===== 上传区域 ===== */
:deep(.upload-area .el-upload) {
    width: 100%;
}

:deep(.upload-area .el-upload-dragger) {
    background: rgba(255, 255, 255, 0.02);
    border: 2px dashed rgba(255, 255, 255, 0.15);
    border-radius: 8px;
    padding: 2rem 1rem;
    transition: all 0.3s ease;
}

:deep(.upload-area .el-upload-dragger:hover) {
    background: rgba(64, 158, 255, 0.05);
    border-color: rgba(64, 158, 255, 0.5);
}

.upload-icon {
    font-size: 2.5rem;
    color: rgba(255, 255, 255, 0.4);
    margin-bottom: 0.75rem;
}

.upload-text {
    color: rgba(255, 255, 255, 0.7);
    font-size: 0.9375rem;
}

.upload-text em {
    color: #409eff;
    font-style: normal;
    font-weight: 500;
}

.upload-tip {
    font-size: 0.75rem;
    color: rgba(255, 255, 255, 0.4);
    margin-top: 0.5rem;
    text-align: center;
}

/* ===== 参数项样式 ===== */
.param-item {
    margin-bottom: 1.25rem;
}

.param-item:last-child {
    margin-bottom: 0;
}

.param-item.compact {
    margin-bottom: 0;
}

.param-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.5rem;
}

.param-name {
    font-size: 0.875rem;
    font-weight: 500;
    color: rgba(255, 255, 255, 0.9);
}

.param-value {
    color: #409eff;
    font-weight: 600;
    font-size: 0.875rem;
    font-family: 'Consolas', monospace;
}

.param-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1rem;
    margin-top: 1rem;
}

.param-item .full-width {
    width: 100%;
}

.param-item .full-width :deep(.el-input__wrapper) {
    width: 100%;
}

/* ===== 开关列表 ===== */
.switch-list {
    display: flex;
    flex-direction: column;
    gap: 1rem;
}

.switch-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.75rem;
    background: rgba(255, 255, 255, 0.02);
    border-radius: 8px;
    border: 1px solid rgba(255, 255, 255, 0.05);
}

.switch-label {
    font-size: 0.875rem;
    color: rgba(255, 255, 255, 0.8);
}

/* ===== 操作按钮 ===== */
.action-buttons {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    margin-top: 1rem;
}

.submit-btn {
    width: 100%;
    font-weight: 600;
    letter-spacing: 0.5px;
}

.clear-btn {
    width: 100%;
}

/* ===== 右侧结果面板 ===== */
.result-panel {
    display: flex;
    flex-direction: column;
    min-height: 600px;
}

.result-card {
    flex: 1;
    display: flex;
    flex-direction: column;
}

.result-card .card-body {
    flex: 1;
    display: flex;
    flex-direction: column;
}

.result-actions {
    display: flex;
    gap: 0.5rem;
}

/* ===== 结果展示区域 ===== */
.result-placeholder {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 400px;
    border: 2px dashed rgba(255, 255, 255, 0.1);
    border-radius: 8px;
    background: rgba(255, 255, 255, 0.01);
}

.placeholder-content {
    text-align: center;
    color: rgba(255, 255, 255, 0.4);
}

.placeholder-icon {
    font-size: 3rem;
    margin-bottom: 1rem;
}

.placeholder-content p {
    margin: 0;
    font-size: 0.9375rem;
}

.result-canvas-container {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 400px;
    background: rgba(0, 0, 0, 0.3);
    border-radius: 8px;
    overflow: hidden;
    position: relative;
}

/* ===== 关键：图片比例保护 ===== */
.result-canvas {
    max-width: 100%;
    max-height: 70vh;
    height: auto;
    object-fit: contain;
    display: block;
}

:deep(.result-image) {
    max-width: 100%;
    max-height: 70vh;
    height: auto;
    object-fit: contain;
    display: block;
}

/* ===== 保存任务 ===== */
.save-card .card-body {
    padding: 0.875rem 1.25rem;
}

.save-task-row {
    display: flex;
    gap: 0.75rem;
}

.task-name-input {
    flex: 1;
}

/* ===== 响应式调整 ===== */
@media (max-width: 768px) {
    .page-header {
        flex-direction: column;
        align-items: flex-start;
        gap: 0.75rem;
        padding: 0.875rem 1rem;
    }
    
    .header-side {
        width: 100%;
    }
    
    .task-tag {
        width: 100%;
        justify-content: space-between;
    }
}

@media (max-width: 576px) {
    .detection-container {
        padding: 0 0.75rem;
    }
    
    .header-icon {
        width: 40px;
        height: 40px;
    }
    
    .page-title {
        font-size: 1.25rem;
    }
    
    .page-subtitle {
        font-size: 0.75rem;
    }
    
    .param-row {
        grid-template-columns: 1fr;
    }
    
    .save-task-row {
        flex-direction: column;
    }
}

/* ===== Element Plus 样式覆盖 ===== */
:deep(.el-form-item__label) {
    color: rgba(255, 255, 255, 0.7);
    font-weight: 500;
    padding-bottom: 0.5rem;
}

:deep(.el-slider__runway) {
    background-color: rgba(255, 255, 255, 0.1);
}

:deep(.el-slider__bar) {
    background-color: #409eff;
}

:deep(.el-slider__button) {
    border-color: #409eff;
}

:deep(.el-input-number .el-input__wrapper) {
    background: rgba(255, 255, 255, 0.05);
}

:deep(.el-radio) {
    color: rgba(255, 255, 255, 0.8);
}

:deep(.el-radio__input.is-checked + .el-radio__label) {
    color: #409eff;
}

:deep(.el-switch__core) {
    background: rgba(255, 255, 255, 0.2);
}
</style>

<style>
@font-face {
    font-family: 'Arial-Bold';
    font-weight: bold;
    font-style: normal;
    src: local('Arial');
}
</style>
