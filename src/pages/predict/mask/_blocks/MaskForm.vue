<script lang="ts" setup>
import {
    ElForm, ElSelect, ElUpload, ElIcon, ElSlider, ElSwitch, ElInputNumber, ElInput, ElButton, ElRadioGroup, ElRadio, ElPopconfirm, ElTag,
    type UploadUserFile, type UploadProps, type UploadInstance, type UploadRawFile, genFileId,
} from 'element-plus';
import { UploadFilled, FolderAdd, Refresh, FullScreen, InfoFilled, CircleCheck, Cpu, SwitchButton, Brush, DocumentChecked, View, Download, Delete } from '@element-plus/icons-vue';
import { Message } from '@/utils/message';
import { setURLParams } from '@/utils/url';
import { preventElemmentSSRError } from '@/utils/ssr';
import { computed, onMounted, reactive, ref } from 'vue'
import * as api from "@/utils/api"
import type { ModelInfo } from '@/utils/api';
import type { Task } from '@/utils/api/task';

preventElemmentSSRError()

const props = defineProps<{
    title: string;
    source: "image";
}>();

// Refs
const uploadEl = ref<UploadInstance | null>(null);
const uploadedFileList = ref<UploadUserFile[]>([]);
const originalCanvas = ref<HTMLCanvasElement | null>(null);
const resultCanvas = ref<HTMLCanvasElement | null>(null);
const maskCanvas = ref<HTMLCanvasElement | null>(null);

// State
const submitLoading = ref(false);
const showOriginal = ref(false);
const originalBlob = ref<Blob | null>(null);
const originalUrl = ref<string>("");
const resultData = ref<any>(null);
const resultBlob = ref<Blob | null>(null);
const maskOverlayUrl = ref<string>("");
const hasResult = computed(() => resultData.value !== null || resultBlob.value !== null);
const hasUploaded = computed(() => uploadedFileList.value.length > 0);

// 任务保存状态
const queryTaskName = ref<string>("");
const submitTaskName = ref<string>("");
const saveLoading = ref(false);

// 简化：只保留结果图输出模式（最稳定）
const outputFormat = ref<string>("image/jpeg");

const models = ref<ModelInfo[]>([]);

// Form data - Mask specific parameters
const form = reactive({
    conf: 0.25,
    iou: 0.7,
    imgsz: 640,
    max_det: 300,
    half: false,
    augment: false,
    agnostic_nms: false,
});

// 分割类展示模型映射（展示名称 -> 后端真实模型ID）
const DISPLAY_MODELS = [
    { displayName: "YOLO26-Seg", backendId: "yolo26-seg" },
    { displayName: "SAM 2", backendId: "yolo26-seg" },
    { displayName: "Grounded SAM 2", backendId: "yolo26-seg" },
    { displayName: "Florence-2 + SAM 2", backendId: "yolo26-seg" },
];

// 当前选中的模型（存储 displayName，提交时再映射到 backendId）
const selectedModelId = ref<string>(DISPLAY_MODELS[0].displayName);

// Load models on mount
onMounted(() => {
    updateModels();
    loadFromTaskQuery();
})

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
            if (inputArgs.display_model) {
                selectedModelId.value = inputArgs.display_model
            }
            // 恢复其他参数
            for (let k in form) {
                if (Object.prototype.hasOwnProperty.call(inputArgs, k)) {
                    (form as any)[k] = (inputArgs as any)[k]
                }
            }
        } catch (e) {
            console.error("解析 input_args 失败:", e)
        }
    }
    
    // 恢复结果数据
    if (task.results) {
        try {
            resultData.value = JSON.parse(task.results)
        } catch (e) {
            console.error("解析 results 失败:", e)
        }
    }
    
    // 获取原图 blob
    const p_originalBlob = api.getFile(task.input_blob).then(blob => {
        if (blob) {
            originalBlob.value = blob
            const file = new File([blob], "image.jpg", { type: blob.type })
            uploadedFileList.value = [{ raw: file, status: "success", name: file.name, size: file.size }] as any
        }
        return blob
    }).catch((e: Error) => {
        Message.error(`获取输入文件失败：${e.name}`)
        console.error(e)
        return null
    })
    
    // 获取结果 blob（如果有）
    const p_resultBlob = task.results_blob ? api.getFile(task.results_blob).then(blob => {
        if (blob) {
            resultBlob.value = blob
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
        maskOverlayUrl.value = URL.createObjectURL(resultBlobData)
    }
    
    // 如果有结果数据但没有 blob，需要重新渲染
    if (resultData.value && originalUrl.value) {
        await handleMaskResult(originalUrl.value, resultData.value)
    }
    
    return true
};

function updateModels() {
    api.getModels().then((m) => {
        const hasSegModel = m.some(model => model.id === 'yolo26-seg')
        if (!hasSegModel) {
            Message.warning("后端分割模型不可用")
        }
        selectedModelId.value = DISPLAY_MODELS[0].displayName
    }).catch((e: Error) => {
        Message.error(`获取模型列表失败：${e.name}`)
        console.error(e)
    })
}

// 处理文件变化（上传新文件时触发）
const handleUploadChange: UploadProps['onChange'] = (uploadFile) => {
    if (!uploadFile.raw) return;
    
    console.log('[Upload] 新文件上传:', uploadFile.name);
    
    // 清空上一轮结果状态
    clearResults();
    
    // 设置新的原图显示
    const file = uploadFile.raw;
    originalBlob.value = new Blob([file], { type: file.type });
    originalUrl.value = URL.createObjectURL(originalBlob.value);
    
    console.log('[Upload] 原图已设置:', originalUrl.value.substring(0, 50) + '...');
}

const handleExceed: UploadProps['onExceed'] = (files) => {
    uploadEl.value!.clearFiles()
    const file = files[0] as UploadRawFile
    file.uid = genFileId()
    uploadEl.value!.handleStart(file)
}

// Prevent duplicate submission
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
    const backendModelId = selectedModel?.backendId || 'yolo26-seg';
    
    console.log(`[MaskSubmit] 开始提交掩码任务，展示模型: ${selectedModelId.value}, 后端模型: ${backendModelId}`);
    const uploadedFile: File = uploadedFileList.value[0].raw!;
    
    originalBlob.value = new Blob([uploadedFile], { type: uploadedFile.type });
    originalUrl.value = URL.createObjectURL(originalBlob.value);
    console.log('[MaskSubmit] 原图已缓存，URL:', originalUrl.value.substring(0, 50) + '...');
    
    try {
        const assignee = {
            source: props.source,
            file: uploadedFile,
            ...form
        };
        
        console.log(`[MaskSubmit] 请求格式: ${outputFormat.value}`);
        const res = await api.callModels<"image">(backendModelId, assignee, outputFormat.value);
        
        console.log('[MaskSubmit] 收到响应类型:', res instanceof Blob ? 'Blob(图片)' : 'JSON');
        
        if (res instanceof Blob) {
            resultBlob.value = res;
            maskOverlayUrl.value = URL.createObjectURL(res);
            Message.success("掩码生成成功（结果图）");
        } else {
            resultData.value = res;
            await handleMaskResult(URL.createObjectURL(uploadedFile), res);
            Message.success("掩码生成成功（数据渲染）");
        }
        
    } catch (e: any) {
        console.error('[MaskSubmit] 提交失败:', e);
        let errorMsg = '提交失败';
        if (e.message) errorMsg = e.message;
        Message.error(errorMsg);
    } finally {
        submitLoading.value = false;
        isSubmitting = false;
    }
}

async function handleMaskResult(uri: string, data: any) {
    console.log('[MaskRender] ========== 开始渲染掩码结果 ==========');
    console.log('[MaskRender] 数据结构:', JSON.stringify(data, null, 2).substring(0, 500));
    
    let detections: any[] = [];
    if (data && data.boxes && Array.isArray(data.boxes)) {
        detections = data.boxes;
    } else if (Array.isArray(data)) {
        detections = data;
    }
    
    console.log('[MaskRender] 检测目标数量:', detections.length);
    
    const o_canvas = originalCanvas.value!;
    const o_ctx = o_canvas.getContext('2d');
    if (!o_ctx) return;
    
    const r_canvas = resultCanvas.value!;
    const r_ctx = r_canvas.getContext('2d');
    if (!r_ctx) return;
    
    const m_canvas = maskCanvas.value!;
    const m_ctx = m_canvas.getContext('2d');
    if (!m_ctx) return;
    
    const img = new Image();
    img.onload = () => {
        console.log('[MaskRender] 图片加载成功:', img.width, 'x', img.height);
        
        [o_canvas, r_canvas, m_canvas].forEach(c => {
            c.width = img.width;
            c.height = img.height;
        });
        
        o_ctx.drawImage(img, 0, 0);
        r_ctx.drawImage(img, 0, 0);
        m_ctx.drawImage(img, 0, 0);
        
        const colors = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#FFA07A", "#98D8C8", "#FFD93D", "#6BCB77"];
        
        detections.forEach((det: any, index: number) => {
            const color = colors[index % colors.length];
            
            let x1, y1, x2, y2;
            if (det.box) {
                x1 = det.box.x1; y1 = det.box.y1; x2 = det.box.x2; y2 = det.box.y2;
            } else {
                x1 = det.xmin; y1 = det.ymin; x2 = det.xmax; y2 = det.ymax;
            }
            
            const w = x2 - x1;
            const h = y2 - y1;
            
            r_ctx.strokeStyle = color;
            r_ctx.lineWidth = 3;
            r_ctx.strokeRect(x1, y1, w, h);
            
            const label = `${det.name || 'unknown'} ${(det.conf || det.confidence || 0).toFixed(2)}`;
            r_ctx.font = "bold 18px Arial";
            const textMetrics = r_ctx.measureText(label);
            r_ctx.fillStyle = color + 'CC';
            r_ctx.fillRect(x1, y1 - 25, textMetrics.width + 10, 25);
            
            r_ctx.fillStyle = '#FFFFFF';
            r_ctx.fillText(label, x1 + 5, y1 - 7);
            
            if (det.has_mask || det.mask || det.masks) {
                m_ctx.fillStyle = color + '60';
                m_ctx.fillRect(x1, y1, w, h);
                
                m_ctx.strokeStyle = color;
                m_ctx.lineWidth = 4;
                m_ctx.strokeRect(x1, y1, w, h);
                
                m_ctx.fillStyle = color;
                m_ctx.font = "bold 14px Arial";
                m_ctx.fillText("🎭 MASK", x1 + 5, y1 + h - 5);
            } else {
                m_ctx.strokeStyle = color;
                m_ctx.lineWidth = 3;
                m_ctx.strokeRect(x1, y1, w, h);
            }
            
            m_ctx.fillStyle = color + 'CC';
            m_ctx.fillRect(x1, y1 - 25, textMetrics.width + 10, 25);
            m_ctx.fillStyle = '#FFFFFF';
            m_ctx.font = "bold 18px Arial";
            m_ctx.fillText(label, x1 + 5, y1 - 7);
            
            console.log(`[MaskRender] [${index}] ${det.name}: conf=${(det.conf || det.confidence || 0).toFixed(2)}, has_mask=${det.has_mask || false}`);
        });
        
        console.log('[MaskRender] ========== 渲染完成 ==========');
    };
    img.src = uri;
}

function refreshResult() {
    console.log('[MaskRender] 手动刷新显示');
    if (resultData.value && originalBlob.value) {
        const url = URL.createObjectURL(originalBlob.value);
        handleMaskResult(url, resultData.value);
    }
}

function switchOriginal() {
    showOriginal.value = !showOriginal.value;
}

function toggleOriginal() {
    showOriginal.value = !showOriginal.value;
    console.log('[MaskView] 切换到:', showOriginal.value ? '原图' : '结果图');
}

function clearResults() {
    resultData.value = null;
    resultBlob.value = null;
    maskOverlayUrl.value = "";
    originalUrl.value = "";
    showOriginal.value = false;
    submitTaskName.value = "";
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
        return [null, null] as [null, null]
    })
    if (!originalId || (resultBlob.value && !resultId)) {
        saveLoading.value = false;
        return;
    }
    
    const selectedModel = DISPLAY_MODELS.find(m => m.displayName === selectedModelId.value);
    const backendModelId = selectedModel?.backendId || 'yolo26-seg';
    
    const uploadObject: Omit<Task, 'id' | 'timestamp' | 'task_id'> = {
        source: "mask",
        task_name: submitTaskName.value,
        input_blob: originalId,
        input_args: JSON.stringify({
            display_model: selectedModelId.value,
            backend_model_id: backendModelId,
            ...form,
            task: "segmentation"
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
                    <ElIcon :size="28"><FullScreen /></ElIcon>
                </div>
                <div class="header-content">
                    <h1 class="page-title">{{ props.title }}</h1>
                    <p class="page-subtitle">上传图片并生成分割掩码</p>
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
                                    <span class="label-text">分割模型</span>
                                    <span class="label-desc">选择用于实例分割的算法模型</span>
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
                                    <span class="label-text">上传图片</span>
                                    <span class="label-desc">支持拖拽或点击上传</span>
                                </div>
                                <ElUpload 
                                    ref="uploadEl" 
                                    drag 
                                    v-model:file-list="uploadedFileList"
                                    :auto-upload="false"
                                    :on-change="handleUploadChange"
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

                <!-- 分割参数卡片 -->
                <div class="panel-card">
                    <div class="card-header">
                        <span class="card-title">分割参数</span>
                    </div>
                    <div class="card-body">
                        <!-- 核心阈值参数 -->
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

                        <!-- 推理配置参数 -->
                        <div class="param-section">
                            <div class="section-subtitle">
                                <ElIcon class="subtitle-icon" :size="14"><Cpu /></ElIcon>
                                <span class="subtitle-text">推理配置</span>
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
                        <!-- 操作按钮区 -->
                        <div class="action-section">
                            <div class="section-subtitle">
                                <ElIcon class="subtitle-icon" :size="14"><Brush /></ElIcon>
                                <span class="subtitle-text">掩码操作</span>
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
                                    <ElIcon class="btn-icon" :size="18"><Picture /></ElIcon>
                                    <span>生成掩码</span>
                                </ElButton>
                                
                                <ElButton 
                                    type="info" 
                                    plain 
                                    size="default"
                                    :icon="Delete"
                                    @click="clearResults" 
                                    v-show="hasResult"
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
                            <p class="save-hint">将当前掩码生成结果保存到历史记录</p>
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

                <!-- 掩码结果框（下方，始终显示） -->
                <div class="panel-card result-card bottom-result">
                    <div class="card-header result-header">
                        <div class="result-title-group">
                            <span class="card-title">掩码结果</span>
                            <ElTag v-if="hasResult" type="success" effect="dark" size="small" class="result-status-tag">
                                生成完成
                            </ElTag>
                        </div>
                        <div class="result-actions" v-show="hasResult">
                            <ElButton 
                                v-if="resultBlob"
                                text 
                                size="small" 
                                bg 
                                @click="toggleOriginal"
                                class="toggle-btn"
                            >
                                {{ showOriginal ? "显示结果图" : "显示原图" }}
                            </ElButton>
                        </div>
                    </div>
                    <div class="card-body result-body">
                        <!-- 掩码结果空状态 -->
                        <div class="result-placeholder result-placeholder-empty" v-show="!hasResult">
                            <div class="placeholder-content">
                                <div class="placeholder-icon-wrapper">
                                    <ElIcon class="placeholder-icon" :size="48">
                                        <Picture />
                                    </ElIcon>
                                </div>
                                <p class="placeholder-title">等待生成</p>
                                <p class="placeholder-desc">上传图片并点击"生成掩码"后，掩码结果将显示在这里</p>
                            </div>
                        </div>
                        
                        <!-- 掩码结果展示区 -->
                        <div class="result-display-wrapper unified-display" v-show="hasResult">
                            <div class="result-canvas-container unified-container">
                                <!-- Blob 结果图 -->
                                <img 
                                    v-if="resultBlob && !showOriginal" 
                                    :src="maskOverlayUrl" 
                                    class="result-image" 
                                    alt="掩码结果" 
                                />
                                <img 
                                    v-if="resultBlob && showOriginal" 
                                    :src="originalUrl" 
                                    class="result-image" 
                                    alt="原图" 
                                />
                                <!-- JSON 数据渲染 -->
                                <canvas 
                                    v-if="resultData && !resultBlob" 
                                    ref="resultCanvas" 
                                    class="result-canvas"
                                ></canvas>
                            </div>
                        </div>
                        
                        <!-- 检测列表 -->
                        <div class="detection-list-section" v-if="resultData && resultData.boxes">
                            <div class="detection-list-header">
                                <ElIcon class="list-icon" :size="14"><View /></ElIcon>
                                <span class="list-title">检测目标 ({{ resultData.boxes.length }})</span>
                            </div>
                            <div class="detection-list-grid">
                                <div 
                                    v-for="(box, index) in resultData.boxes" 
                                    :key="index"
                                    class="detection-item"
                                >
                                    <div class="item-name">{{ box.name || '未知' }}</div>
                                    <div class="item-confidence">
                                        置信度: {{ (box.conf || box.confidence || 0).toFixed(3) }}
                                    </div>
                                    <div class="item-id">
                                        ID: {{ box.cls || box.class || index }}
                                    </div>
                                </div>
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

.header-side {
    flex-shrink: 0;
}

.task-tag {
    display: flex;
    align-items: center;
    gap: 0.625rem;
    padding: 0.5rem 0.875rem;
    background: rgba(64, 158, 255, 0.1);
    border: 1px solid rgba(64, 158, 255, 0.2);
    border-radius: 8px;
}

.task-tag-label {
    font-size: 0.6875rem;
    color: rgba(255, 255, 255, 0.5);
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.task-tag-name {
    font-size: 0.8125rem;
    font-weight: 600;
    color: #409eff;
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

.param-item .full-width {
    width: 100%;
}

.param-item .full-width :deep(.el-input__wrapper) {
    width: 100%;
}

/* ===== 开关区 ===== */
.switch-section.compact {
    margin-top: 0.75rem;
}

.switch-section-header {
    display: flex;
    align-items: center;
    gap: 0.375rem;
    margin-bottom: 0.5rem;
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

/* 开关选项一行三列布局 */
.switch-group.compact-switch-group {
    display: grid !important;
    grid-template-columns: repeat(3, 1fr);
    gap: 0.5rem;
}

.switch-item.compact-switch {
    padding: 0.5rem 0.5rem;
    flex-direction: row;
    align-items: center;
    justify-content: space-between;
    gap: 0.375rem;
    min-width: 0;
}

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

.switch-item:hover {
    background: rgba(64, 158, 255, 0.06);
    border-color: rgba(64, 158, 255, 0.2);
}

.switch-item.active {
    background: rgba(64, 158, 255, 0.08);
    border-color: rgba(64, 158, 255, 0.25);
}

.switch-info {
    display: flex;
    flex-direction: column;
    gap: 0.125rem;
}

.switch-info.compact-info {
    gap: 0;
}

.switch-name {
    font-size: 0.8125rem;
    font-weight: 500;
    color: rgba(255, 255, 255, 0.85);
}

.switch-name.compact-name {
    font-size: 0.75rem;
    font-weight: 600;
}

.switch-desc {
    font-size: 0.6875rem;
    color: rgba(255, 255, 255, 0.4);
    transition: color 0.2s ease;
}

.switch-desc.compact-desc {
    font-size: 0.625rem;
    color: rgba(255, 255, 255, 0.35);
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
    min-height: 720px;
    height: 100%;
}

/* 原始图像卡片（上方） */
.original-card {
    flex: 1;
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

.top-original {
    min-height: 340px;
}

/* 掩码结果卡片（下方） */
.result-card {
    flex: 1;
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

.bottom-result {
    min-height: 340px;
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

/* 结果画布样式 */
.result-canvas {
    max-width: 100%;
    max-height: 65vh;
    height: auto;
    object-fit: contain;
    display: block;
    border-radius: 4px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
}

/* ===== 检测列表 ===== */
.detection-list-section {
    margin-top: 1.25rem;
    padding-top: 1.25rem;
    border-top: 1px solid rgba(255, 255, 255, 0.06);
}

.detection-list-header {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.75rem;
}

.list-icon {
    color: #409eff;
}

.list-title {
    font-size: 0.875rem;
    font-weight: 600;
    color: rgba(255, 255, 255, 0.8);
}

.detection-list-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 0.75rem;
}

.detection-item {
    padding: 0.75rem;
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 8px;
    transition: all 0.2s ease;
}

.detection-item:hover {
    background: rgba(64, 158, 255, 0.06);
    border-color: rgba(64, 158, 255, 0.2);
}

.item-name {
    font-size: 0.8125rem;
    font-weight: 600;
    color: rgba(255, 255, 255, 0.9);
    margin-bottom: 0.25rem;
}

.item-confidence {
    font-size: 0.75rem;
    color: rgba(255, 255, 255, 0.6);
    margin-bottom: 0.125rem;
}

.item-id {
    font-size: 0.6875rem;
    color: rgba(255, 255, 255, 0.4);
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
    
    .task-tag {
        width: 100%;
        justify-content: space-between;
    }
}
</style>
