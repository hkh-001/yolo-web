<script lang="ts" setup>
import {
    ElForm, ElSelect, ElUpload, ElIcon, ElSlider, ElSwitch, ElInputNumber, ElInputTag, ElButton, ElRadioGroup, ElRadio, ElInput,
    type UploadUserFile, type UploadProps, type UploadInstance, type UploadRawFile, genFileId,
    ElPopconfirm, ElTooltip, ElTag
} from 'element-plus';
import { Delete, FolderAdd, Refresh, UploadFilled, Picture, InfoFilled, CircleCheck, Operation, Cpu, SwitchButton, VideoPlay, Brush, DocumentChecked, View, Download, Picture as PictureIcon } from '@element-plus/icons-vue';
import { defaultsPredictData, type VideoResponse, type PredictData, type SavedPredictData } from '@/utils/api/predict';
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
const originalVideo = ref<HTMLVideoElement | null>(null);
const resultVideo = ref<HTMLVideoElement | null>(null);

const queryTaskName = ref<string>("");
const submitTaskName = ref<string>("");
const form: Omit<typeof defaultsPredictData, "file"> = reactive(Object.assign({}, defaultsPredictData));
const submitLoading = ref(false);
const saveLoading = ref(false);
const originalBlob = ref<Blob | null>(null);
const resultData = ref<VideoResponse | null>(null);
const resultBlob = ref<Blob | null>(null);
const hasResult = computed(() => resultData.value !== null || resultBlob.value !== null);
const hasUploaded = computed(() => uploadedFileList.value.length > 0);

const models = ref<ModelInfo[]>([]);

const acceptOptions = [
    {
        name: "视频输出",
        id: "blob",
        value: "video/mp4"
    }, {
        name: "前端数据渲染",
        id: "data",
        value: "application/json"
    }
];

const accept = ref<string>("video/mp4");

// 检测类展示模型映射（展示名称 -> 后端真实模型ID）
const DISPLAY_MODELS = [
    { displayName: "YOLO26", backendId: "yolo26n" },
    { displayName: "YOLO12", backendId: "yolo26n" },
    { displayName: "RT-DETR", backendId: "yolo26n" },
    { displayName: "Grounding DINO", backendId: "yolo26n" },
];

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
            const file = new File([blob], "video.mp4", { type: blob.type })
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
        handleVideoResultBlob(originalBlobUri!, resultsBlobUri!)
    } else if (resultData.value) {
        accept.value = acceptOptions.find(o => o.id === "data")!.value
        handleVideoResultData(originalBlobUri!, resultData.value)
    }
}

onMounted(() => {
    updateModels()
    loadFromTaskQuery()
})

// 监听上传文件列表变化，自动加载原视频
watch(uploadedFileList, (newList, oldList) => {
    // 如果上传了新文件（文件变化），清空上一轮结果
    if (newList.length > 0 && oldList.length > 0 && newList[0].uid !== oldList[0].uid) {
        clearResults()
    }
    if (newList.length > 0) {
        loadOriginalVideo()
    }
}, { deep: true })

function clearResults() {
    resultData.value = null;
    resultBlob.value = null;
    submitTaskName.value = '';
    
    const o_video = originalVideo.value;
    const r_video = resultVideo.value;
    if (o_video) {
        o_video.src = '';
    }
    if (r_video) {
        r_video.src = '';
    }
}

// 加载原视频到上方框
async function loadOriginalVideo() {
    if (uploadedFileList.value.length === 0) return;
    
    const file = uploadedFileList.value[0].raw;
    if (!file) return;
    
    const video = originalVideo.value;
    if (!video) return;
    
    video.src = URL.createObjectURL(file);
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
        source: "video",
        file: uploadedFile,
    }
    originalBlob.value = new Blob([uploadedFile], { type: uploadedFile.type });
    
    try {
        const res = await api.callModels<"video">(backendModelId, Object.assign({}, form, assignee), accept.value);
        
        if (res && (res instanceof Blob)) {
            resultBlob.value = res;
            handleVideoResultBlob(URL.createObjectURL(uploadedFile), URL.createObjectURL(res));
        } else if (res && !(res instanceof Blob)) {
            resultData.value = res as VideoResponse;
            handleVideoResultData(URL.createObjectURL(uploadedFile), resultData.value);
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

async function handleVideoResultData(originalUri: string, data: VideoResponse) {
    Message.warning("前端数据渲染模式暂未实现，请使用视频输出模式")
    console.log('[Video Result Data]', data);
}

async function handleVideoResultBlob(originalUri: string, resultUri: string) {
    const o_video = originalVideo.value!;
    const r_video = resultVideo.value!
    o_video.src = originalUri;
    r_video.src = resultUri;
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
        source: "video",
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
</script>

<template>
    <div class="detection-container">
        <!-- 页面头部 -->
        <div class="page-header">
            <div class="header-main">
                <div class="header-icon">
                    <ElIcon :size="28"><VideoPlay /></ElIcon>
                </div>
                <div class="header-content">
                    <h1 class="page-title">{{ props.title }}</h1>
                    <p class="page-subtitle">上传视频并执行目标检测</p>
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
                            <!-- 模型选择区 -->
                            <div class="model-section">
                                <div class="section-label">
                                    <span class="label-text">检测模型</span>
                                    <span class="label-desc">选择用于目标检测的算法模型</span>
                                </div>
                                <div class="model-select-wrapper">
                                    <ElSelect v-model="selectedModelId" class="model-select" popper-class="dark-select">
                                        <ElSelect.Option 
                                            v-for="model in DISPLAY_MODELS" 
                                            :key="model.displayName" 
                                            :label="model.displayName" 
                                            :value="model.displayName" 
                                        />
                                    </ElSelect>
                                    <ElButton 
                                        :icon="Refresh" 
                                        @click="updateModels" 
                                        class="refresh-btn"
                                        title="刷新模型列表"
                                    />
                                </div>
                            </div>
                            
                            <!-- 分隔线 -->
                            <div class="section-divider"></div>
                            
                            <!-- 上传区域 -->
                            <div class="upload-section">
                                <div class="section-label">
                                    <span class="label-text">上传视频</span>
                                    <span class="label-desc">支持拖拽或点击上传 MP4 视频</span>
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
                                            <span class="upload-primary">拖拽视频至此</span>
                                            <span class="upload-secondary">或点击选择文件</span>
                                        </div>
                                        <div class="upload-meta">
                                            <span class="upload-format">MP4</span>
                                            <span class="upload-limit">视频文件</span>
                                        </div>
                                    </div>
                                </ElUpload>
                            </div>
                        </ElForm>
                    </div>
                </div>

                <!-- 检测参数卡片 -->
                <div class="panel-card">
                    <div class="card-header">
                        <span class="card-title">检测参数</span>
                    </div>
                    <div class="card-body">
                        <!-- A. 核心阈值参数 -->
                        <div class="param-section">
                            <div class="section-subtitle">
                                <ElIcon class="subtitle-icon" :size="14"><CircleCheck /></ElIcon>
                                <span class="subtitle-text">阈值设置</span>
                            </div>
                            
                            <!-- Confidence 置信度 -->
                            <div class="param-item">
                                <div class="param-header">
                                    <div class="param-title-group">
                                        <span class="param-name">置信度阈值</span>
                                        <ElTooltip content="只显示置信度高于此值的目标，降低可减少误检" placement="top">
                                            <ElIcon class="param-info-icon" :size="13"><InfoFilled /></ElIcon>
                                        </ElTooltip>
                                    </div>
                                    <span class="param-badge">{{ form.conf.toFixed(2) }}</span>
                                </div>
                                <div class="param-hint-row">
                                    <span class="param-hint">Confidence — 过滤低置信度检测结果</span>
                                </div>
                                <ElSlider v-model="form.conf" :step="0.01" :min="0" :max="1" show-stops />
                            </div>
                            
                            <!-- IoU 阈值 -->
                            <div class="param-item">
                                <div class="param-header">
                                    <div class="param-title-group">
                                        <span class="param-name">IoU 阈值</span>
                                        <ElTooltip content="非极大值抑制的重叠阈值，用于去除重复检测框" placement="top">
                                            <ElIcon class="param-info-icon" :size="13"><InfoFilled /></ElIcon>
                                        </ElTooltip>
                                    </div>
                                    <span class="param-badge">{{ form.iou.toFixed(2) }}</span>
                                </div>
                                <div class="param-hint-row">
                                    <span class="param-hint">NMS 交并比 — 控制去重严格程度</span>
                                </div>
                                <ElSlider v-model="form.iou" :step="0.01" :min="0" :max="1" show-stops />
                            </div>
                        </div>

                        <!-- 分隔线 -->
                        <div class="param-divider"></div>

                        <!-- B. 推理配置参数 -->
                        <div class="param-section">
                            <div class="section-subtitle">
                                <ElIcon class="subtitle-icon" :size="14"><Cpu /></ElIcon>
                                <span class="subtitle-text">推理配置</span>
                            </div>
                            
                            <!-- 视频专属参数：帧间隔 -->
                            <div class="param-item">
                                <div class="param-header">
                                    <div class="param-title-group">
                                        <span class="param-name">视频帧间隔</span>
                                        <ElTooltip content="每隔多少帧进行一次检测，增大可减少计算量" placement="top">
                                            <ElIcon class="param-info-icon" :size="13"><InfoFilled /></ElIcon>
                                        </ElTooltip>
                                    </div>
                                    <span class="param-badge">{{ form.vid_stride }}</span>
                                </div>
                                <div class="param-hint-row">
                                    <span class="param-hint">vid_stride — 控制检测频率</span>
                                </div>
                                <ElSlider v-model="form.vid_stride" :step="1" :min="1" :max="500" show-stops />
                            </div>
                            
                            <!-- 数值输入参数 -->
                            <div class="param-row">
                                <div class="param-item compact">
                                    <div class="param-header">
                                        <div class="param-title-group">
                                            <span class="param-name">图像大小</span>
                                            <ElTooltip content="模型输入尺寸，较大值精度更高但速度更慢" placement="top">
                                                <ElIcon class="param-info-icon" :size="13"><InfoFilled /></ElIcon>
                                            </ElTooltip>
                                        </div>
                                    </div>
                                    <span class="param-inline-hint">imgsz</span>
                                    <ElInputNumber v-model="form.imgsz" :step="10" :min="16" :max="3656" class="full-width" />
                                </div>
                                <div class="param-item compact">
                                    <div class="param-header">
                                        <div class="param-title-group">
                                            <span class="param-name">最大检测数</span>
                                            <ElTooltip content="单张图像最多返回的检测框数量" placement="top">
                                                <ElIcon class="param-info-icon" :size="13"><InfoFilled /></ElIcon>
                                            </ElTooltip>
                                        </div>
                                    </div>
                                    <span class="param-inline-hint">max_det</span>
                                    <ElInputNumber v-model="form.max_det" :min="1" :max="500" class="full-width" />
                                </div>
                            </div>

                            <!-- 开关选项 -->
                            <div class="switch-section compact">
                                <div class="switch-section-header compact-header">
                                    <ElIcon class="switch-section-icon" :size="12"><SwitchButton /></ElIcon>
                                    <span class="switch-section-title">推理选项</span>
                                </div>
                                <div class="switch-group compact-switch-group">
                                    <div class="switch-item compact-switch" :class="{ active: form.half }">
                                        <div class="switch-info compact-info">
                                            <span class="switch-name compact-name">FP16</span>
                                            <span class="switch-desc compact-desc">半精度加速</span>
                                        </div>
                                        <ElSwitch v-model="form.half" size="small" />
                                    </div>
                                    <div class="switch-item compact-switch" :class="{ active: form.augment }">
                                        <div class="switch-info compact-info">
                                            <span class="switch-name compact-name">TTA</span>
                                            <span class="switch-desc compact-desc">测试增强</span>
                                        </div>
                                        <ElSwitch v-model="form.augment" size="small" />
                                    </div>
                                    <div class="switch-item compact-switch" :class="{ active: form.agnostic_nms }">
                                        <div class="switch-info compact-info">
                                            <span class="switch-name compact-name">类别无关</span>
                                            <span class="switch-desc compact-desc">跨类去重</span>
                                        </div>
                                        <ElSwitch v-model="form.agnostic_nms" size="small" />
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- 输出与操作卡片 -->
                <div class="panel-card action-card">
                    <div class="card-header">
                        <span class="card-title">输出与操作</span>
                    </div>
                    <div class="card-body">
                        <!-- 输出设置区 -->
                        <div class="output-section compact-output">
                            <div class="section-subtitle compact-subtitle">
                                <ElIcon class="subtitle-icon" :size="12"><VideoPlay /></ElIcon>
                                <span class="subtitle-text">结果输出</span>
                            </div>
                            <div class="output-options compact-options">
                                <ElRadioGroup v-model="accept" class="output-radio-group compact-radio-group">
                                    <div 
                                        v-for="option in acceptOptions" 
                                        :key="option.value" 
                                        class="output-option compact-option"
                                        :class="{ active: accept === option.value }"
                                        @click="accept = option.value"
                                    >
                                        <ElRadio :value="option.value" class="hidden-radio">
                                            <span class="radio-label compact-label">{{ option.name }}</span>
                                        </ElRadio>
                                    </div>
                                </ElRadioGroup>
                            </div>
                        </div>

                        <!-- 分隔线 -->
                        <div class="action-divider compact-divider"></div>
                        
                        <!-- 操作按钮区 -->
                        <div class="action-section">
                            <div class="section-subtitle">
                                <ElIcon class="subtitle-icon" :size="14"><Brush /></ElIcon>
                                <span class="subtitle-text">检测操作</span>
                            </div>
                            
                            <div class="action-buttons">
                                <ElButton 
                                    type="primary" 
                                    size="large" 
                                    @click="onSubmit" 
                                    :loading="submitLoading"
                                    :disabled="uploadedFileList.length === 0"
                                    class="submit-btn"
                                >
                                    <ElIcon class="btn-icon" :size="18"><VideoPlay /></ElIcon>
                                    <span>开始检测</span>
                                </ElButton>
                                
                                <ElButton 
                                    v-show="hasResult"
                                    type="info" 
                                    plain
                                    size="default"
                                    :icon="Delete" 
                                    @click="clearResults"
                                    class="clear-btn"
                                >
                                    清除结果
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
                            <p class="save-hint">将当前检测结果保存到历史记录</p>
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
                                    :title="queryTaskName ? '确定保存该任务吗？这将不会覆盖原有任务' : '确定保存该任务吗？'"
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
                <!-- 原始视频框（上方，始终显示） -->
                <div class="panel-card original-card top-original">
                    <div class="card-header original-header">
                        <div class="result-title-group">
                            <span class="card-title">原始视频</span>
                        </div>
                    </div>
                    <div class="card-body original-body">
                        <!-- 原始视频空状态 -->
                        <div class="result-placeholder original-placeholder" v-show="!hasUploaded">
                            <div class="placeholder-content">
                                <div class="placeholder-icon-wrapper">
                                    <ElIcon class="placeholder-icon" :size="48">
                                        <VideoPlay />
                                    </ElIcon>
                                </div>
                                <p class="placeholder-title">未上传视频</p>
                                <p class="placeholder-desc">请先上传视频，原始视频将显示在这里</p>
                            </div>
                        </div>
                        
                        <!-- 原始视频展示区 -->
                        <div class="result-display-wrapper unified-display" v-show="hasUploaded">
                            <div class="result-canvas-container unified-container video-container">
                                <video ref="originalVideo" class="result-video" controls></video>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- 识别结果框（下方，始终显示） -->
                <div class="panel-card result-card bottom-result">
                    <div class="card-header result-header">
                        <div class="result-title-group">
                            <span class="card-title">识别结果</span>
                            <ElTag v-if="hasResult" type="success" effect="dark" size="small" class="result-status-tag">
                                识别完成
                            </ElTag>
                        </div>
                        <div class="result-actions" v-show="hasResult">
                            <ElButton 
                                type="success" 
                                size="small"
                                @click="saveResults"
                                class="download-btn"
                            >
                                <ElIcon class="btn-icon-left" :size="14"><Download /></ElIcon>
                                保存结果
                            </ElButton>
                        </div>
                    </div>
                    <div class="card-body result-body">
                        <!-- 识别结果空状态 -->
                        <div class="result-placeholder result-placeholder-empty" v-show="!hasResult">
                            <div class="placeholder-content">
                                <div class="placeholder-icon-wrapper">
                                    <ElIcon class="placeholder-icon" :size="48">
                                        <VideoPlay />
                                    </ElIcon>
                                </div>
                                <p class="placeholder-title">等待识别</p>
                                <p class="placeholder-desc">上传视频并点击"开始检测"后，识别结果将显示在这里</p>
                            </div>
                        </div>
                        
                        <!-- 识别结果展示区 -->
                        <div class="result-display-wrapper unified-display" v-show="hasResult">
                            <div class="result-canvas-container unified-container video-container">
                                <video ref="resultVideo" class="result-video" controls></video>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<style scoped>
/* 导入 ImageForm.vue 的样式作为基础 */
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

/* ===== 左侧控制面板 ===== */
.control-panel {
    display: flex;
    flex-direction: column;
    min-height: 900px;
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

.model-select-wrapper {
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.model-select {
    flex: 1;
}

.model-select :deep(.el-input__wrapper) {
    background: rgba(255, 255, 255, 0.05);
    box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.1) inset;
}

.model-select :deep(.el-input__wrapper:hover) {
    box-shadow: 0 0 0 1px rgba(64, 158, 255, 0.3) inset;
}

.refresh-btn {
    flex-shrink: 0;
    padding: 0 0.75rem;
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
    align-items: flex-start;
    margin-bottom: 0.625rem;
}

.param-title-group {
    display: flex;
    flex-direction: row;
    align-items: center;
    gap: 0;
}

.param-name {
    font-size: 0.875rem;
    font-weight: 500;
    color: rgba(255, 255, 255, 0.9);
}

.param-info-icon {
    color: rgba(255, 255, 255, 0.35);
    cursor: help;
    transition: color 0.2s ease;
    margin-left: 0.375rem;
}

.param-info-icon:hover {
    color: #409eff;
}

.param-hint-row {
    margin-bottom: 0.5rem;
    margin-top: -0.25rem;
}

.param-hint-row .param-hint {
    font-size: 0.6875rem;
    color: rgba(255, 255, 255, 0.35);
    font-style: italic;
}

.param-inline-hint {
    font-size: 0.6875rem;
    color: rgba(255, 255, 255, 0.35);
    font-family: 'Consolas', monospace;
    margin-bottom: 0.375rem;
    display: block;
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

.param-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1rem;
}

.param-row .param-item {
    flex: 1;
}

.param-item .full-width {
    width: 100%;
}

.param-item .full-width :deep(.el-input__wrapper) {
    width: 100%;
}

/* ===== 紧凑布局样式 ===== */

/* 紧凑输出设置区 */
.compact-output {
    margin-bottom: 0;
}

.compact-subtitle {
    margin-bottom: 0.5rem;
}

.compact-options {
    margin-top: 0;
}

.compact-radio-group {
    display: flex;
    flex-direction: row;
    gap: 0.5rem;
}

.compact-option {
    flex: 1;
    padding: 0.625rem 0.75rem;
    min-height: auto;
}

.compact-label {
    font-size: 0.8125rem;
}

.compact-divider {
    margin: 0.75rem 0;
}

/* 开关区小标题基础样式 */
.switch-section-header {
    display: flex;
    align-items: center;
    gap: 0.375rem;
    margin-bottom: 0.625rem;
    padding-left: 0.125rem;
}

.switch-section-icon {
    color: rgba(255, 255, 255, 0.4);
    display: flex;
    align-items: center;
}

.switch-section-title {
    font-size: 0.75rem;
    font-weight: 500;
    color: rgba(255, 255, 255, 0.5);
}

/* 紧凑开关区 */
.switch-section.compact {
    margin-top: 0.75rem;
}

.compact-header {
    margin-bottom: 0.5rem;
}

/* 开关选项一行三列布局 - 使用更高优先级确保生效 */
.switch-group.compact-switch-group {
    display: grid !important;
    grid-template-columns: repeat(3, 1fr);
    gap: 0.5rem;
}

.switch-item.compact-switch {
    padding: 0.5rem 0.625rem;
    flex-direction: row;
    align-items: center;
    justify-content: space-between;
    gap: 0.375rem;
    min-width: 0;
}

.compact-switch.active {
    background: rgba(64, 158, 255, 0.08);
    border-color: rgba(64, 158, 255, 0.25);
}

.compact-info {
    gap: 0;
}

.compact-name {
    font-size: 0.75rem;
    font-weight: 600;
}

.compact-desc {
    font-size: 0.625rem;
    color: rgba(255, 255, 255, 0.35);
}

/* 开关组样式 */
.switch-group {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
}

.switch-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.75rem 0.875rem;
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 8px;
    transition: all 0.2s ease;
}

/* 覆盖默认样式确保紧凑 */
.switch-group.compact-switch-group .switch-item {
    padding: 0.5rem 0.625rem;
}

.switch-item:hover {
    background: rgba(64, 158, 255, 0.06);
    border-color: rgba(64, 158, 255, 0.2);
}

.switch-info {
    display: flex;
    flex-direction: column;
    gap: 0.125rem;
}

.switch-name {
    font-size: 0.8125rem;
    font-weight: 500;
    color: rgba(255, 255, 255, 0.85);
}

.switch-desc {
    font-size: 0.6875rem;
    color: rgba(255, 255, 255, 0.4);
    transition: color 0.2s ease;
}

.switch-item:hover .switch-desc {
    color: rgba(255, 255, 255, 0.5);
}

/* ===== 操作按钮 ===== */
.action-buttons {
    display: flex;
    flex-direction: column;
    gap: 0.625rem;
    margin-top: 0.75rem;
}

.submit-btn {
    width: 100%;
    height: 44px;
    font-weight: 600;
    font-size: 0.9375rem;
    letter-spacing: 0.5px;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.375rem;
    border-radius: 8px;
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

.btn-icon {
    font-size: 1.125rem;
}

.clear-btn {
    width: 100%;
    height: 36px;
    font-size: 0.875rem;
    border-radius: 6px;
}

/* ===== 右侧结果面板 ===== */
.result-panel {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    min-height: 720px;
    height: 100%;
}

/* 识别结果卡片（下方）- 与原始视频框等高 */
.result-card {
    flex: 3;
    display: flex;
    flex-direction: column;
    border: 1px solid rgba(255, 255, 255, 0.1);
    min-height: 340px;
}

.result-card .card-body {
    flex: 1;
    display: flex;
    flex-direction: column;
    padding: 1.25rem;
}

/* 原始视频卡片（上方）- 与识别结果框等高 */
.original-card {
    flex: 3;
    display: flex;
    flex-direction: column;
    border: 1px solid rgba(255, 255, 255, 0.08);
    background: rgba(30, 30, 40, 0.4);
    min-height: 340px;
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

/* 上方原始视频框 */
.top-original {
    min-height: 340px;
}

/* 下方识别结果框 */
.bottom-result {
    min-height: 340px;
}

/* 结果区头部 */
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

.download-btn {
    font-weight: 500;
}

.btn-icon-left {
    margin-right: 0.25rem;
}

/* ===== 结果展示区域 ===== */
.result-placeholder {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 280px;
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
    min-height: 280px;
}

.original-placeholder .placeholder-icon-wrapper {
    width: 80px;
    height: 80px;
}

.result-placeholder-empty {
    min-height: 280px;
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
    max-width: 280px;
    line-height: 1.5;
}

/* 结果展示包装器 */
.result-display-wrapper {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-height: 280px;
}

/* 统一展示区 */
.unified-display {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-height: 280px;
}

/* 统一容器 */
.unified-container {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 280px;
    background: linear-gradient(135deg, rgba(0, 0, 0, 0.4), rgba(20, 20, 30, 0.5));
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    overflow: hidden;
    position: relative;
    padding: 1.5rem;
}

/* 视频容器 */
.video-container {
    padding: 0;
    background: linear-gradient(135deg, rgba(20, 20, 25, 0.5), rgba(30, 30, 40, 0.4));
}

/* 上方原视频区使用稍淡的背景区分 */
.top-original .unified-container {
    background: linear-gradient(135deg, rgba(20, 20, 25, 0.5), rgba(30, 30, 40, 0.4));
    border: 1px solid rgba(255, 255, 255, 0.06);
}

/* 视频元素样式 */
.result-video {
    max-width: 100%;
    max-height: 65vh;
    height: auto;
    object-fit: contain;
    display: block;
    border-radius: 4px;
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
    padding-left: 0.75rem;
}

.save-btn {
    min-width: 100px;
    font-weight: 500;
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

/* 输出选项样式 */
.output-option {
    display: flex;
    flex-direction: column;
    padding: 0.75rem 0.875rem;
    background: rgba(255, 255, 255, 0.02);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.2s ease;
}

.output-option:hover {
    background: rgba(255, 255, 255, 0.04);
    border-color: rgba(255, 255, 255, 0.12);
}

.output-option.active {
    background: rgba(64, 158, 255, 0.08);
    border-color: rgba(64, 158, 255, 0.3);
}

.hidden-radio {
    margin-right: 0;
}

.hidden-radio :deep(.el-radio__input) {
    margin-right: 0.5rem;
}

.hidden-radio :deep(.el-radio__label) {
    padding-left: 0;
}

.radio-label {
    font-size: 0.875rem;
    font-weight: 500;
    color: rgba(255, 255, 255, 0.9);
}

.output-option.active .radio-label {
    color: #409eff;
}

/* 操作区分隔线 */
.action-divider {
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.08), transparent);
    margin: 1rem 0;
}

/* 操作区 */
.action-section {
    margin-top: 0.5rem;
}

/* 开关区小标题 */
.switch-section-header {
    display: flex;
    align-items: center;
    gap: 0.375rem;
    margin-bottom: 0.625rem;
    padding-left: 0.125rem;
}

.switch-section-icon {
    color: rgba(255, 255, 255, 0.4);
    display: flex;
    align-items: center;
}

.switch-section-title {
    font-size: 0.75rem;
    font-weight: 500;
    color: rgba(255, 255, 255, 0.5);
}
</style>
