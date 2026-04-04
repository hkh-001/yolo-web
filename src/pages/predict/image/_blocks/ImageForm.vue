<script lang="ts" setup>
import {
    ElForm, ElSelect, ElUpload, ElIcon, ElSlider, ElSwitch, ElInputNumber, ElInputTag, ElButton, ElRadioGroup, ElRadio, ElInput,
    type UploadUserFile, type UploadProps, type UploadInstance, type UploadRawFile, genFileId,
    ElPopconfirm, ElCard, ElDivider, ElTag, ElTooltip, ElEmpty, ElStatistic, ElRow, ElCol, ElIcon as ElIconComponent
} from 'element-plus';
import { Delete, FolderAdd, Refresh, UploadFilled, Picture, DataLine, Cpu, Setting, Aim, Histogram, Download, View, Check } from '@element-plus/icons-vue';
import { defaultsPredictData, type ImageResponse, type VideoResponse, type PredictData, type SavedPredictData } from '@/utils/api/predict';
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
    source: PredictData["source"];
}>();

const uploadEl = ref<UploadInstance | null>(null);
const uploadedFileList = ref<UploadUserFile[]>([]);
const originalCanvas = ref<HTMLCanvasElement | null>(null);
const resultCanvas = ref<HTMLCanvasElement | null>(null);
const originalVideo = ref<HTMLVideoElement | null>(null);
const resultVideo = ref<HTMLVideoElement | null>(null);

const queryTaskName = ref<string>("");
const submitTaskName = ref<string>("");
const form: Omit<typeof defaultsPredictData, "file"> = reactive(Object.assign({}, defaultsPredictData));
const submitLoading = ref(false);
const saveLoading = ref(false);
const showOriginal = ref(false);
const originalBlob = ref<Blob | null>(null);
const resultData = ref<ImageResponse | VideoResponse | null>(null);
const resultBlob = ref<Blob | null>(null);
const hasResult = computed(() => resultData.value !== null || resultBlob.value !== null);

// 检测统计信息
const detectionStats = computed(() => {
    if (!resultData.value) return { count: 0, classes: [], avgConfidence: 0 };
    
    let boxes: any[] = [];
    const data = resultData.value as any;
    if (Array.isArray(data)) {
        boxes = data;
    } else if (data.boxes && Array.isArray(data.boxes)) {
        boxes = data.boxes;
    } else if (data.predictions && Array.isArray(data.predictions)) {
        boxes = data.predictions;
    }
    
    const classes = [...new Set(boxes.map((b: any) => b.name || b.class))];
    const avgConfidence = boxes.length > 0 
        ? boxes.reduce((sum: number, b: any) => sum + (b.conf || b.confidence || 0), 0) / boxes.length 
        : 0;
    
    return { count: boxes.length, classes, avgConfidence };
});

const models = ref<ModelInfo[]>([]);

const acceptOptions = {
    image: [{
        name: "图像输出",
        id: "blob",
        value: "image/jpeg,image/png"
    }, {
        name: "前端数据渲染",
        id: "data",
        value: "application/json"
    }],
    video: [{
        name: "视频输出",
        id: "blob",
        value: "video/mp4"
    }, {
        name: "前端数据渲染",
        id: "data",
        value: "application/json"
    }]
}

const accept = ref<string>(props.source === "image" ? "application/json" : "video/mp4");

// 检测类展示模型映射（展示名称 -> 后端真实模型ID）
const DISPLAY_MODELS = [
    { displayName: "YOLO26", backendId: "yolo26n", description: "高精度检测模型" },
    { displayName: "YOLO12", backendId: "yolo26n", description: "快速检测模型" },
    { displayName: "RT-DETR", backendId: "yolo26n", description: "实时检测模型" },
    { displayName: "Grounding DINO", backendId: "yolo26n", description: "开放词汇检测" },
];

// 当前选中的模型（存储 displayName，提交时再映射到 backendId）
const selectedModelId = ref<string>(DISPLAY_MODELS[0].displayName);

function updateModels() {
    // 前端固定展示模型列表，不再从后端获取后过滤
    // 只验证后端是否有对应的真实模型
    api.getModels().then((m) => {
        const hasDetectModel = m.some(model => model.id === 'yolo26n')
        if (!hasDetectModel) {
            Message.warning("后端检测模型不可用")
        }
        // 默认选中第一个模型的 displayName
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
    // 尝试恢复 displayName，如果保存的是 backendId 则查找对应的 displayName
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
            const file = new File([blob], task.source === "image" ? "image.jpg" : "video.mp4", { type: blob.type })
            uploadedFileList.value = [{ raw: file, status: "success", name: file.name, size: file.size }] as any
        }
        originalBlob.value = blob
        return URL.createObjectURL(blob)
    }).catch((e: Error) => {
        Message.error(`获取输入文件失败：${e.name}`)
        console.error(e)
        return null
    })
    // fill results
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
        if (task.source === "image") {
            accept.value = acceptOptions.image.find(o => o.id === "blob")!.value
            handleImageResultBlob(originalBlobUri!, resultsBlobUri!)
        } else {
            accept.value = acceptOptions.video.find(o => o.id === "blob")!.value
            handleVideoResultBlob(originalBlobUri!, resultsBlobUri!)
        }
    } else if (resultData.value) {
        if (task.source === "image") {
            accept.value = acceptOptions.image.find(o => o.id === "data")!.value
            handleImageResultData(originalBlobUri!, resultData.value as ImageResponse)
        } else {
            accept.value = acceptOptions.video.find(o => o.id === "data")!.value
            handleVideoResultData(originalBlobUri!, resultData.value as VideoResponse)
        }
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
    
    // 清理动态创建的图片元素
    const resultImg = document.getElementById('result-image');
    const originalImg = document.getElementById('original-image');
    if (resultImg) resultImg.remove();
    if (originalImg) originalImg.remove();
    
    // 重置 canvas 显示状态 - 让 v-show 控制显示
    // showOriginal = false 时，根据 v-show：
    // - originalCanvas: v-show="showOriginal" -> false -> display: none
    // - resultCanvas: v-show="!showOriginal" -> true -> display: block
    const o_canvas = originalCanvas.value;
    const r_canvas = resultCanvas.value;
    if (o_canvas) {
        // 移除手动设置的 display，让 v-show 接管
        o_canvas.style.removeProperty('display');
        // 清空 canvas
        const ctx = o_canvas.getContext('2d');
        if (ctx) ctx.clearRect(0, 0, o_canvas.width, o_canvas.height);
        // 重置尺寸
        o_canvas.width = 0;
        o_canvas.height = 0;
    }
    if (r_canvas) {
        // 移除手动设置的 display，让 v-show 接管
        r_canvas.style.removeProperty('display');
        // 清空 canvas
        const ctx = r_canvas.getContext('2d');
        if (ctx) ctx.clearRect(0, 0, r_canvas.width, r_canvas.height);
        // 重置尺寸
        r_canvas.width = 0;
        r_canvas.height = 0;
    }
    
    console.log('[Clear] 结果已清除，canvas 已重置');
}

const handleExceed: UploadProps['onExceed'] = (files) => {
    uploadEl.value!.clearFiles()
    const file = files[0] as UploadRawFile
    file.uid = genFileId()
    uploadEl.value!.handleStart(file)
}

// 防止重复提交锁
let isSubmitting = false;

async function onSubmit() {
    // 防止重复提交
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
    
    // 根据选中的 displayName 查找 backendId
    const selectedModel = DISPLAY_MODELS.find(m => m.displayName === selectedModelId.value);
    const backendModelId = selectedModel?.backendId || 'yolo26n';
    
    console.log(`[Submit] 开始提交任务，展示模型: ${selectedModelId.value}, 后端模型: ${backendModelId}`);
    const uploadedFile: File = uploadedFileList.value[0].raw!;
    let assignee: Partial<PredictData> = {
        source: props.source,
        file: uploadedFile,
    }
    originalBlob.value = new Blob([uploadedFile], { type: uploadedFile.type });
    
    try {
        let res;
        if (props.source === "image") {
            assignee.vid_stride = undefined;
            res = await api.callModels<"image">(backendModelId, Object.assign({}, form, assignee), accept.value);
        } else {
            res = await api.callModels<"video">(backendModelId, Object.assign({}, form, assignee), accept.value);
        }
        
        if (res && (res instanceof Blob)) {
            resultBlob.value = res;
            handleImageResultBlob(URL.createObjectURL(uploadedFile), URL.createObjectURL(res));
        } else if (res && !(res instanceof Blob)) {
            resultData.value = res;
            if (props.source === "image") {
                handleImageResultData(URL.createObjectURL(uploadedFile), res as ImageResponse);
            } else {
                handleVideoResultData(URL.createObjectURL(uploadedFile), res as VideoResponse);
            }
        }
        Message.success("任务提交成功");
        
    } catch (e: any) {
        console.error('[Submit] 提交失败:', e);
        
        // 显示详细错误信息
        let errorMsg = '提交失败';
        if (e.name === 'TimeoutError' || e.message?.includes('timeout')) {
            errorMsg = '请求超时：模型服务响应时间过长';
        } else if (e.message) {
            errorMsg = e.message;
        }
        
        // 如果后端返回了 JSON 错误，尝试解析
        if (e.response) {
            try {
                const errorData = await e.response.json();
                if (errorData.message) {
                    errorMsg = errorData.message;
                }
                if (errorData.detail) {
                    console.error('[Submit] 错误详情:', errorData.detail);
                }
            } catch {
                // 解析失败，使用默认错误消息
            }
        }
        
        Message.error(errorMsg);
    } finally {
        submitLoading.value = false;
        isSubmitting = false;
        console.log('[Submit] 提交流程结束');
    }
}

async function handleImageResultData(uri: string, data: any) {
    console.log('[Render] ========== 开始绘制结果 ==========');
    console.log('[Render] 原图URI:', uri.substring(0, 50) + '...');
    console.log('[Render] 收到的数据类型:', typeof data);
    console.log('[Render] 收到的数据结构:', JSON.stringify(data, null, 2).substring(0, 500));
    
    // 检查数据格式
    let boxes: any[] = [];
    if (Array.isArray(data)) {
        console.log('[Render] 数据是数组，长度:', data.length);
        boxes = data;
    } else if (data && data.boxes && Array.isArray(data.boxes)) {
        console.log('[Render] 数据包含 boxes 字段，数量:', data.boxes.length);
        boxes = data.boxes;
    } else if (data && data.predictions && Array.isArray(data.predictions)) {
        console.log('[Render] 数据包含 predictions 字段，数量:', data.predictions.length);
        boxes = data.predictions;
    } else {
        console.error('[Render] ❌ 无法识别的数据格式:', data);
        return;
    }
    
    console.log('[Render] 检测框数量:', boxes.length);
    if (boxes.length === 0) {
        console.warn('[Render] ⚠️ 没有检测到任何目标');
    } else {
        console.log('[Render] 第一个检测框:', JSON.stringify(boxes[0]));
    }
    
    const o_canvas = originalCanvas.value;
    const r_canvas = resultCanvas.value;
    
    if (!o_canvas || !r_canvas) {
        console.error('[Render] ❌ Canvas 元素未找到');
        return;
    }
    
    const o_ctx = o_canvas.getContext('2d');
    const r_ctx = r_canvas.getContext('2d');
    
    if (!o_ctx || !r_ctx) {
        console.error('[Render] ❌ 无法获取 canvas context');
        return;
    }
    
    // 注意：不手动设置 display，完全依赖 v-show 控制
    // v-show="showOriginal" 控制 originalCanvas
    // v-show="!showOriginal" 控制 resultCanvas
    // showOriginal 默认为 false，所以 resultCanvas 会显示
    
    const img = new Image();
    img.crossOrigin = 'anonymous';
    
    img.onload = () => {
        console.log('[Render] 图片加载成功:', img.width, 'x', img.height);
        
        // 设置 canvas 尺寸
        o_canvas.width = img.width;
        o_canvas.height = img.height;
        r_canvas.width = img.width;
        r_canvas.height = img.height;
        
        // 绘制原图
        o_ctx.drawImage(img, 0, 0);
        console.log('[Render] 原图绘制完成');

        // 绘制结果图（先画原图再画框）
        r_ctx.drawImage(img, 0, 0);
        console.log('[Render] 准备绘制', boxes.length, '个检测框');
        
        // 兼容两种字段命名：box.x1/y1/x2/y2 或 xmin/ymin/xmax/ymax
        const normalizedBoxes = boxes.map((box: any, index: number) => {
            let x, y, w, h, name, confidence, cls;
            
            if (box.box) {
                // Python 返回格式: {box: {x1, y1, x2, y2}, name, conf, cls}
                x = box.box.x1;
                y = box.box.y1;
                w = box.box.x2 - box.box.x1;
                h = box.box.y2 - box.box.y1;
                name = box.name;
                confidence = box.conf;
                cls = box.cls;
            } else {
                // 原始格式: {xmin, ymin, xmax, ymax, name, confidence, class}
                x = box.xmin;
                y = box.ymin;
                w = box.xmax - box.xmin;
                h = box.ymax - box.ymin;
                name = box.name;
                confidence = box.confidence;
                cls = box.class;
            }
            
            if (index < 3) { // 只打印前3个框的日志
                console.log(`[Render] 框[${index}]: ${name} (${confidence?.toFixed(2)}) at [${x?.toFixed(0)}, ${y?.toFixed(0)}]`);
            }
            
            return { x, y, w, h, name, confidence, class: cls };
        });
        
        // 绘制检测框
        const colors = ["#67C23A", "#409EFF", "#E6A23C", "#F56C6C", "#909399", "#00CED1", "#FF69B4", "#32CD32"];
        const types: number[] = [];
        
        for (let i = 0; i < normalizedBoxes.length; i++) {
            const box = normalizedBoxes[i];
            let colori = 0;
            if (types.includes(box.class)) {
                colori = types.indexOf(box.class) % colors.length;
            } else {
                types.push(box.class);
                colori = (types.length - 1) % colors.length;
            }
            
            // 绘制矩形框
            r_ctx.strokeStyle = colors[colori];
            r_ctx.lineWidth = Math.max(2, Math.min(img.width, img.height) / 200); // 根据图片大小调整线宽
            r_ctx.strokeRect(box.x, box.y, box.w, box.h);
            
            // 绘制标签背景
            const label = `${box.name} ${(box.confidence * 100).toFixed(0)}%`;
            r_ctx.font = `bold ${Math.max(12, Math.min(img.width, img.height) / 50)}px Inter, sans-serif`;
            const textMetrics = r_ctx.measureText(label);
            const textHeight = 20;
            
            r_ctx.fillStyle = colors[colori];
            r_ctx.fillRect(box.x, box.y - textHeight - 4, textMetrics.width + 8, textHeight + 4);
            
            // 绘制标签文字
            r_ctx.fillStyle = '#FFFFFF';
            r_ctx.fillText(label, box.x + 4, box.y - 6);
        }
        
        console.log('[Render] ========== 绘制完成 ==========');
    };
    
    img.onerror = (err) => {
        console.error('[Render] ❌ 图片加载失败:', err);
        Message.error('图片加载失败，无法显示结果');
    };
    
    img.src = uri;
}

async function handleImageResultBlob(originalUri: string, resultUri: string) {
    console.log('[BlobRender] 显示图片输出模式');
    console.log('[BlobRender] 原图URI:', originalUri.substring(0, 50) + '...');
    console.log('[BlobRender] 结果图URI:', resultUri.substring(0, 50) + '...');
    
    // 获取 canvas 容器
    const canvasWrapper = document.querySelector('.canvas-wrapper');
    if (!canvasWrapper) {
        console.error('[BlobRender] 找不到 canvas-wrapper 容器');
        return;
    }
    
    // 隐藏 canvas（Blob 模式使用 img 元素显示）
    const o_canvas = originalCanvas.value;
    const r_canvas = resultCanvas.value;
    if (o_canvas) o_canvas.style.display = 'none';
    if (r_canvas) r_canvas.style.display = 'none';
    
    // 移除旧的 img 元素（如果存在）
    const oldResultImg = document.getElementById('result-image');
    const oldOriginalImg = document.getElementById('original-image');
    if (oldResultImg) oldResultImg.remove();
    if (oldOriginalImg) oldOriginalImg.remove();
    
    // 创建结果图片元素
    const resultImg = document.createElement('img');
    resultImg.id = 'result-image';
    resultImg.className = 'result-image';
    resultImg.src = resultUri;
    resultImg.style.maxWidth = '100%';
    resultImg.style.height = 'auto';
    resultImg.style.display = showOriginal.value ? 'none' : 'block';
    resultImg.style.boxShadow = '0 4px 16px rgba(0, 0, 0, 0.3)';
    resultImg.style.borderRadius = '4px';
    
    // 等待图片加载完成后再添加到 DOM
    resultImg.onload = () => {
        console.log('[BlobRender] 结果图片加载完成');
    };
    resultImg.onerror = (err) => {
        console.error('[BlobRender] 结果图片加载失败:', err);
    };
    canvasWrapper.appendChild(resultImg);
    
    // 创建原图图片元素
    const originalImg = document.createElement('img');
    originalImg.id = 'original-image';
    originalImg.className = 'result-image';
    originalImg.src = originalUri;
    originalImg.style.maxWidth = '100%';
    originalImg.style.height = 'auto';
    originalImg.style.display = showOriginal.value ? 'block' : 'none';
    originalImg.style.boxShadow = '0 4px 16px rgba(0, 0, 0, 0.3)';
    originalImg.style.borderRadius = '4px';
    
    originalImg.onload = () => {
        console.log('[BlobRender] 原图加载完成');
    };
    canvasWrapper.appendChild(originalImg);
    
    console.log('[BlobRender] 图片元素已创建并添加到 DOM');
}

async function handleVideoResultData(originalUri: string, data: VideoResponse) {
    Message.warning("Not implemented yet")
}

async function handleVideoResultBlob(originalUri: string, resultUri: string) {
    const o_video = originalVideo.value!;
    const r_video = resultVideo.value!
    o_video.src = originalUri;
    r_video.src = resultUri;
}

function switchOriginal() {
    const newValue = !showOriginal.value;
    console.log('[ViewOriginal] 切换显示模式:', showOriginal.value, '->', newValue);
    
    // 先更新状态
    showOriginal.value = newValue;
    
    // 获取相关元素
    const originalImg = document.getElementById('original-image') as HTMLImageElement;
    const resultImg = document.getElementById('result-image') as HTMLImageElement;
    
    // 优先处理 Blob 图片模式（动态创建的 img 元素）
    if (originalImg && resultImg) {
        if (newValue) {
            originalImg.style.display = 'block';
            resultImg.style.display = 'none';
        } else {
            originalImg.style.display = 'none';
            resultImg.style.display = 'block';
        }
        console.log('[ViewOriginal] Blob 模式 - 显示:', newValue ? '原图' : '结果图');
        return;
    }
    
    // Canvas 模式由 v-show 自动处理，无需手动设置 display
    // v-show="showOriginal" 控制 originalCanvas
    // v-show="!showOriginal" 控制 resultCanvas
    console.log('[ViewOriginal] Canvas 模式 - v-show 自动处理');
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
    
    // 查找 backendModelId
    const selectedModel = DISPLAY_MODELS.find(m => m.displayName === selectedModelId.value);
    const backendModelId = selectedModel?.backendId || 'yolo26n';
    
    const uploadObject: Omit<Task, 'id' | 'timestamp' | 'task_id'> = {
        source: props.source,
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

// 下载结果图片
function downloadResult() {
    const resultImg = document.getElementById('result-image') as HTMLImageElement;
    const originalImg = document.getElementById('original-image') as HTMLImageElement;
    const r_canvas = resultCanvas.value;
    const o_canvas = originalCanvas.value;
    
    let dataUrl: string | null = null;
    let filename = 'detection-result';
    
    // 判断当前显示的是原图还是结果图
    const isShowingOriginal = showOriginal.value;
    
    console.log(`[Download] 当前显示模式: ${isShowingOriginal ? '原图' : '结果图'}`);
    
    if (isShowingOriginal) {
        // 下载原图
        if (originalImg && originalImg.style.display !== 'none') {
            // Blob 模式：直接从 img 元素的 src 创建下载链接
            // 如果 src 是 blob URL，可以直接使用
            if (originalImg.src.startsWith('blob:')) {
                // 使用 fetch 获取 blob 然后下载
                fetch(originalImg.src)
                    .then(res => res.blob())
                    .then(blob => {
                        const url = URL.createObjectURL(blob);
                        const link = document.createElement('a');
                        link.download = `original-image-${Date.now()}.png`;
                        link.href = url;
                        document.body.appendChild(link);
                        link.click();
                        document.body.removeChild(link);
                        URL.revokeObjectURL(url);
                        console.log('[Download] 原图下载完成 (Blob 模式)');
                    })
                    .catch(err => {
                        console.error('[Download] 下载失败:', err);
                        Message.error('下载失败');
                    });
                return;
            }
        } else if (o_canvas && o_canvas.style.display !== 'none' && o_canvas.width > 0) {
            // Canvas 模式
            dataUrl = o_canvas.toDataURL('image/png');
        }
        filename = 'original-image';
    } else {
        // 下载结果图
        if (resultImg && resultImg.style.display !== 'none') {
            if (resultImg.src.startsWith('blob:')) {
                fetch(resultImg.src)
                    .then(res => res.blob())
                    .then(blob => {
                        const url = URL.createObjectURL(blob);
                        const link = document.createElement('a');
                        link.download = `detection-result-${Date.now()}.png`;
                        link.href = url;
                        document.body.appendChild(link);
                        link.click();
                        document.body.removeChild(link);
                        URL.revokeObjectURL(url);
                        console.log('[Download] 结果图下载完成 (Blob 模式)');
                    })
                    .catch(err => {
                        console.error('[Download] 下载失败:', err);
                        Message.error('下载失败');
                    });
                return;
            }
        } else if (r_canvas && r_canvas.style.display !== 'none' && r_canvas.width > 0) {
            // Canvas 模式
            dataUrl = r_canvas.toDataURL('image/png');
        }
        filename = 'detection-result';
    }
    
    if (dataUrl) {
        const link = document.createElement('a');
        link.download = `${filename}-${Date.now()}.png`;
        link.href = dataUrl;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        console.log(`[Download] 已下载: ${filename} (Canvas 模式)`);
    } else {
        Message.warning('暂无结果可下载');
        console.error('[Download] 无法获取图片数据');
    }
}

// 格式化文件大小
function formatFileSize(bytes: number): string {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// 当前选中文件信息
const currentFile = computed(() => {
    if (uploadedFileList.value.length === 0) return null;
    const file = uploadedFileList.value[0];
    return {
        name: file.name,
        size: file.raw?.size || 0
    };
});
</script>

<template>
    <div class="image-detection-container">
        <!-- 页面标题区 -->
        <div class="page-header">
            <div class="header-left">
                <h1 class="page-title">
                    <ElIconComponent class="title-icon"><Aim /></ElIconComponent>
                    {{ props.title }}
                </h1>
                <p class="page-subtitle">上传图片，AI 自动识别图像中的目标对象</p>
            </div>
            <div class="header-right" v-if="queryTaskName">
                <ElTag type="info" size="large" effect="dark">
                    <ElIconComponent class="mr-1"><Check /></ElIconComponent>
                    任务：{{ queryTaskName }}
                </ElTag>
                <ElButton circle :icon="Refresh" @click="loadFromTaskQuery" title="刷新任务" />
            </div>
        </div>

        <!-- 主内容区：左右双栏 -->
        <div class="main-content">
            <!-- 左侧：控制面板 -->
            <div class="control-panel">
                <!-- 上传区域卡片 -->
                <ElCard class="panel-card upload-card" shadow="hover">
                    <template #header>
                        <div class="card-header">
                            <ElIconComponent class="header-icon"><Picture /></ElIconComponent>
                            <span>图片上传</span>
                        </div>
                    </template>
                    
                    <ElUpload
                        ref="uploadEl"
                        v-model:file-list="uploadedFileList"
                        class="upload-area"
                        drag
                        :auto-upload="false"
                        :on-exceed="handleExceed"
                        :limit="1"
                        accept="image/jpeg,image/png"
                    >
                        <div class="upload-content" v-if="!currentFile">
                            <ElIcon class="upload-icon" :size="48">
                                <UploadFilled />
                            </ElIcon>
                            <div class="upload-text">
                                <p class="primary-text">拖拽图片到此处</p>
                                <p class="secondary-text">或 <em>点击上传</em></p>
                            </div>
                            <div class="upload-hint">
                                <ElTag size="small" type="info">JPG</ElTag>
                                <ElTag size="small" type="info">PNG</ElTag>
                                <span class="hint-text">支持格式</span>
                            </div>
                        </div>
                        <div class="upload-file-info" v-else>
                            <ElIcon class="file-icon" :size="32"><Picture /></ElIcon>
                            <div class="file-details">
                                <p class="file-name">{{ currentFile.name }}</p>
                                <p class="file-size">{{ formatFileSize(currentFile.size) }}</p>
                            </div>
                            <ElTag type="success" effect="dark" size="small">已上传</ElTag>
                        </div>
                    </ElUpload>
                </ElCard>

                <!-- 模型设置卡片 -->
                <ElCard class="panel-card" shadow="hover">
                    <template #header>
                        <div class="card-header">
                            <ElIconComponent class="header-icon"><Cpu /></ElIconComponent>
                            <span>模型设置</span>
                            <ElButton link :icon="Refresh" class="refresh-btn" @click="updateModels" title="刷新模型列表" />
                        </div>
                    </template>
                    
                    <div class="form-item">
                        <label class="form-label">选择检测模型</label>
                        <ElSelect v-model="selectedModelId" class="w-full">
                            <ElOption 
                                v-for="model in DISPLAY_MODELS" 
                                :key="model.displayName" 
                                :label="model.displayName" 
                                :value="model.displayName"
                            >
                                <div class="model-option">
                                    <span>{{ model.displayName }}</span>
                                    <ElTag size="small" type="info">{{ model.description }}</ElTag>
                                </div>
                            </ElOption>
                        </ElSelect>
                        <p class="form-hint">{{ DISPLAY_MODELS.find(m => m.displayName === selectedModelId)?.description }}</p>
                    </div>

                    <div class="form-item">
                        <label class="form-label">输出处理方式</label>
                        <ElRadioGroup v-model="accept" size="small">
                            <ElRadioButton 
                                v-for="option in acceptOptions[props.source]" 
                                :key="option.value"
                                :value="option.value"
                            >
                                {{ option.name }}
                            </ElRadioButton>
                        </ElRadioGroup>
                        <p class="form-hint">图像输出：直接下载结果图片；前端渲染：在页面中显示检测框</p>
                    </div>
                </ElCard>

                <!-- 检测参数卡片 -->
                <ElCard class="panel-card" shadow="hover">
                    <template #header>
                        <div class="card-header">
                            <ElIconComponent class="header-icon"><Setting /></ElIconComponent>
                            <span>检测参数</span>
                        </div>
                    </template>
                    
                    <div class="form-item slider-item">
                        <div class="slider-header">
                            <label class="form-label">
                                置信度阈值
                                <ElTooltip content="只显示置信度高于此值的目标" placement="top">
                                    <ElIconComponent class="info-icon"><DataLine /></ElIconComponent>
                                </ElTooltip>
                            </label>
                            <span class="slider-value">{{ (form.conf * 100).toFixed(0) }}%</span>
                        </div>
                        <ElSlider v-model="form.conf" :step="0.01" :min="0" :max="1" show-input show-stops />
                    </div>

                    <ElDivider />

                    <div class="form-item slider-item">
                        <div class="slider-header">
                            <label class="form-label">
                                IoU 阈值
                                <ElTooltip content="非极大值抑制的重叠阈值，用于去除重复检测框" placement="top">
                                    <ElIconComponent class="info-icon"><DataLine /></ElIconComponent>
                                </ElTooltip>
                            </label>
                            <span class="slider-value">{{ (form.iou * 100).toFixed(0) }}%</span>
                        </div>
                        <ElSlider v-model="form.iou" :step="0.01" :min="0" :max="1" show-input show-stops />
                    </div>

                    <ElDivider />

                    <div class="form-row">
                        <div class="form-item compact">
                            <label class="form-label">图像尺寸</label>
                            <ElInputNumber v-model="form.imgsz" :step="10" :min="16" :max="3656" controls-position="right" />
                        </div>
                        <div class="form-item compact">
                            <label class="form-label">最大检测数</label>
                            <ElInputNumber v-model="form.max_det" :step="1" :min="1" :max="500" controls-position="right" />
                        </div>
                    </div>
                </ElCard>

                <!-- 高级选项卡片 -->
                <ElCard class="panel-card advanced-card" shadow="hover">
                    <template #header>
                        <div class="card-header">
                            <ElIconComponent class="header-icon"><Histogram /></ElIconComponent>
                            <span>高级选项</span>
                        </div>
                    </template>
                    
                    <div class="switch-list">
                        <div class="switch-item">
                            <div class="switch-label">
                                <span>半精度推理 (FP16)</span>
                                <ElTooltip content="使用 FP16 半精度推理可加速处理，但需要 GPU 支持" placement="top">
                                    <ElIconComponent class="info-icon"><DataLine /></ElIconComponent>
                                </ElTooltip>
                            </div>
                            <ElSwitch v-model="form.half" />
                        </div>
                        
                        <div class="switch-item">
                            <div class="switch-label">
                                <span>测试时增强 (TTA)</span>
                                <ElTooltip content="Test Time Augmentation，可提升检测精度但速度更慢" placement="top">
                                    <ElIconComponent class="info-icon"><DataLine /></ElIconComponent>
                                </ElTooltip>
                            </div>
                            <ElSwitch v-model="form.augment" />
                        </div>
                        
                        <div class="switch-item">
                            <div class="switch-label">
                                <span>类别无关 NMS</span>
                                <ElTooltip content="不同类别之间也进行非极大值抑制" placement="top">
                                    <ElIconComponent class="info-icon"><DataLine /></ElIconComponent>
                                </ElTooltip>
                            </div>
                            <ElSwitch v-model="form.agnostic_nms" />
                        </div>
                    </div>
                </ElCard>

                <!-- 操作按钮区 -->
                <div class="action-buttons">
                    <ElButton 
                        type="primary" 
                        size="large" 
                        class="submit-btn"
                        :loading="submitLoading"
                        :disabled="uploadedFileList.length === 0"
                        @click="onSubmit"
                    >
                        <ElIconComponent class="btn-icon"><Aim /></ElIconComponent>
                        开始检测
                    </ElButton>
                    
                    <ElButton 
                        v-show="hasResult"
                        type="danger" 
                        plain
                        size="large"
                        class="clear-btn"
                        :icon="Delete"
                        @click="clearResults"
                    >
                        清除结果
                    </ElButton>
                </div>

                <!-- 保存任务区 -->
                <div class="save-task-section" v-show="hasResult">
                    <ElDivider>保存检测结果</ElDivider>
                    <div class="save-task-form">
                        <ElInput 
                            v-model="submitTaskName" 
                            placeholder="输入任务名称以便保存"
                            size="large"
                        >
                            <template #prefix>
                                <ElIconComponent><FolderAdd /></ElIconComponent>
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
                                    :loading="saveLoading"
                                    :disabled="!submitTaskName"
                                >
                                    保存任务
                                </ElButton>
                            </template>
                        </ElPopconfirm>
                    </div>
                </div>
            </div>

            <!-- 右侧：结果展示区 -->
            <div class="result-panel">
                <!-- 检测结果主卡片 -->
                <ElCard class="result-card" shadow="always">
                    <template #header>
                        <div class="result-header">
                            <div class="result-title">
                                <ElIconComponent class="header-icon"><View /></ElIconComponent>
                                <span>检测结果</span>
                                <ElTag v-if="hasResult" type="success" effect="dark" size="small">
                                    检测完成
                                </ElTag>
                            </div>
                            <div class="result-actions" v-if="hasResult">
                                <ElButton 
                                    :type="showOriginal ? '' : 'primary'" 
                                    :plain="showOriginal"
                                    size="small"
                                    @click="switchOriginal"
                                >
                                    {{ showOriginal ? '查看结果' : '查看原图' }}
                                </ElButton>
                                <ElButton 
                                    type="success" 
                                    size="small"
                                    :icon="Download"
                                    @click="downloadResult"
                                >
                                    下载结果
                                </ElButton>
                            </div>
                        </div>
                    </template>
                    
                    <!-- 空状态 -->
                    <div v-if="!hasResult" class="empty-state">
                        <ElEmpty description="暂无检测结果">
                            <template #image>
                                <div class="empty-icon-wrapper">
                                    <ElIcon :size="80" color="var(--el-text-color-secondary)">
                                        <Picture />
                                    </ElIcon>
                                </div>
                            </template>
                            <template #description>
                                <div class="empty-description">
                                    <p class="empty-title">准备开始检测</p>
                                    <p class="empty-hint">上传图片并设置参数后，点击"开始检测"按钮</p>
                                </div>
                            </template>
                        </ElEmpty>
                    </div>

                    <!-- 图片展示区 -->
                    <div v-else class="image-display">
                        <div class="canvas-wrapper">
                            <canvas ref="originalCanvas" v-show="showOriginal"></canvas>
                            <canvas ref="resultCanvas" v-show="!showOriginal"></canvas>
                        </div>
                    </div>
                </ElCard>

                <!-- 检测统计卡片 -->
                <ElCard v-if="hasResult" class="stats-card" shadow="hover">
                    <template #header>
                        <div class="card-header">
                            <ElIconComponent class="header-icon"><Histogram /></ElIconComponent>
                            <span>检测统计</span>
                        </div>
                    </template>
                    
                    <ElRow :gutter="20">
                        <ElCol :span="8">
                            <div class="stat-item">
                                <div class="stat-value">{{ detectionStats.count }}</div>
                                <div class="stat-label">检测到目标</div>
                            </div>
                        </ElCol>
                        <ElCol :span="8">
                            <div class="stat-item">
                                <div class="stat-value">{{ detectionStats.classes.length }}</div>
                                <div class="stat-label">目标类别</div>
                            </div>
                        </ElCol>
                        <ElCol :span="8">
                            <div class="stat-item">
                                <div class="stat-value">{{ (detectionStats.avgConfidence * 100).toFixed(1) }}%</div>
                                <div class="stat-label">平均置信度</div>
                            </div>
                        </ElCol>
                    </ElRow>

                    <!-- 类别分布 -->
                    <div v-if="detectionStats.classes.length > 0" class="class-distribution">
                        <ElDivider />
                        <p class="distribution-title">检测类别</p>
                        <div class="class-tags">
                            <ElTag 
                                v-for="cls in detectionStats.classes" 
                                :key="cls"
                                type="primary"
                                effect="light"
                                size="large"
                            >
                                {{ cls }}
                            </ElTag>
                        </div>
                    </div>
                </ElCard>
            </div>
        </div>
    </div>
</template>

<style scoped>
/* ========== 容器与布局 ========== */
.image-detection-container {
    height: 100%;
    display: flex;
    flex-direction: column;
    gap: 20px;
}

/* 页面头部 */
.page-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    padding-bottom: 16px;
    border-bottom: 1px solid var(--el-border-color-lighter);
}

.header-left {
    display: flex;
    flex-direction: column;
    gap: 4px;
}

.page-title {
    font-size: 24px;
    font-weight: 600;
    color: var(--el-text-color-primary);
    margin: 0;
    display: flex;
    align-items: center;
    gap: 10px;
}

.title-icon {
    color: var(--el-color-primary);
    font-size: 28px;
}

.page-subtitle {
    font-size: 14px;
    color: var(--el-text-color-secondary);
    margin: 0;
}

.header-right {
    display: flex;
    align-items: center;
    gap: 12px;
}

/* 主内容区：左右双栏 */
.main-content {
    display: flex;
    gap: 24px;
    flex: 1;
    min-height: 0;
    overflow: hidden;
}

/* 左侧控制面板 */
.control-panel {
    width: 400px;
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    gap: 16px;
    overflow-y: auto;
    padding-right: 4px;
    max-height: calc(100vh - 180px);
}

/* 右侧结果面板 */
.result-panel {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 16px;
    overflow-y: auto;
    max-height: calc(100vh - 180px);
    padding-right: 4px;
}

/* ========== 卡片样式 ========== */
.panel-card {
    border-radius: 12px;
    transition: all 0.3s ease;
}

.panel-card:hover {
    transform: translateY(-2px);
}

:deep(.el-card__header) {
    padding: 14px 18px;
    border-bottom: 1px solid var(--el-border-color-lighter);
}

:deep(.el-card__body) {
    padding: 18px;
}

.card-header {
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 16px;
    font-weight: 600;
    color: var(--el-text-color-primary);
}

.header-icon {
    color: var(--el-color-primary);
    font-size: 18px;
}

.refresh-btn {
    margin-left: auto;
}

/* ========== 上传区域 ========== */
.upload-card :deep(.el-card__body) {
    padding: 0;
}

.upload-area {
    width: 100%;
}

.upload-area :deep(.el-upload) {
    width: 100%;
}

.upload-area :deep(.el-upload-dragger) {
    width: 100%;
    height: auto;
    min-height: 280px;
    padding: 40px 20px;
    border: 2px dashed var(--el-border-color);
    border-radius: 8px;
    background: var(--el-fill-color-lighter);
    transition: all 0.3s ease;
}

.upload-area :deep(.el-upload-dragger:hover) {
    border-color: var(--el-color-primary);
    background: var(--el-fill-color);
}

.upload-content {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 16px;
}

.upload-icon {
    color: var(--el-color-primary);
    opacity: 0.8;
}

.upload-text {
    text-align: center;
}

.primary-text {
    font-size: 16px;
    font-weight: 500;
    color: var(--el-text-color-primary);
    margin: 0;
}

.secondary-text {
    font-size: 14px;
    color: var(--el-text-color-secondary);
    margin: 4px 0 0;
}

.secondary-text em {
    color: var(--el-color-primary);
    font-style: normal;
    font-weight: 500;
}

.upload-hint {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-top: 8px;
}

.hint-text {
    font-size: 12px;
    color: var(--el-text-color-placeholder);
    margin-left: 4px;
}

/* 已上传文件信息 */
.upload-file-info {
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 20px;
}

.file-icon {
    color: var(--el-color-success);
}

.file-details {
    flex: 1;
    text-align: left;
}

.file-name {
    font-size: 14px;
    font-weight: 500;
    color: var(--el-text-color-primary);
    margin: 0;
    word-break: break-all;
}

.file-size {
    font-size: 12px;
    color: var(--el-text-color-secondary);
    margin: 4px 0 0;
}

/* ========== 表单样式 ========== */
.form-item {
    margin-bottom: 20px;
}

.form-item:last-child {
    margin-bottom: 0;
}

.form-label {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 14px;
    font-weight: 500;
    color: var(--el-text-color-primary);
    margin-bottom: 10px;
}

.form-hint {
    font-size: 12px;
    color: var(--el-text-color-secondary);
    margin: 8px 0 0;
    line-height: 1.5;
}

.info-icon {
    font-size: 14px;
    color: var(--el-text-color-secondary);
    cursor: help;
}

/* 滑块样式 */
.slider-item {
    margin-bottom: 16px;
}

/* 滑块输入框样式 */
.slider-item :deep(.el-slider__input) {
    width: 80px;
}

.slider-item :deep(.el-slider__runway.show-input) {
    margin-right: 90px;
}

.slider-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 10px;
}

.slider-header .form-label {
    margin-bottom: 0;
}

.slider-value {
    font-size: 14px;
    font-weight: 600;
    color: var(--el-color-primary);
    background: var(--el-color-primary-light-9);
    padding: 2px 10px;
    border-radius: 12px;
}

/* 双列表单 */
.form-row {
    display: flex;
    gap: 20px;
}

.form-row .form-item {
    flex: 1;
}

.form-item.compact :deep(.el-input-number) {
    width: 100%;
}

/* 模型选项 */
.model-option {
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.w-full {
    width: 100%;
}

/* ========== 高级选项开关列表 ========== */
.switch-list {
    display: flex;
    flex-direction: column;
    gap: 16px;
}

.switch-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 0;
    border-bottom: 1px solid var(--el-border-color-lighter);
}

.switch-item:last-child {
    border-bottom: none;
    padding-bottom: 0;
}

.switch-label {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 14px;
    color: var(--el-text-color-primary);
}

/* ========== 操作按钮区 ========== */
.action-buttons {
    display: flex;
    flex-direction: column;
    gap: 12px;
    margin-top: 8px;
}

.submit-btn {
    width: 100%;
    height: 48px;
    font-size: 16px;
    font-weight: 600;
}

.btn-icon {
    margin-right: 6px;
    font-size: 18px;
}

.clear-btn {
    width: 100%;
}

/* 保存任务区 */
.save-task-section {
    margin-top: 8px;
}

.save-task-form {
    display: flex;
    gap: 12px;
    margin-top: 12px;
}

.save-task-form .el-input {
    flex: 1;
}

/* ========== 结果展示区 ========== */
.result-card {
    flex: 1;
    min-height: 400px;
    border-radius: 12px;
}

.result-card :deep(.el-card__body) {
    height: calc(100% - 55px);
    display: flex;
    flex-direction: column;
}

.result-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.result-title {
    display: flex;
    align-items: center;
    gap: 10px;
}

.result-actions {
    display: flex;
    gap: 8px;
}

/* 空状态 */
.empty-state {
    flex: 1;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    min-height: 400px;
}

.empty-icon-wrapper {
    padding: 30px;
    border-radius: 50%;
    background: var(--el-fill-color-lighter);
    margin-bottom: 20px;
}

.empty-description {
    text-align: center;
}

.empty-title {
    font-size: 16px;
    font-weight: 500;
    color: var(--el-text-color-primary);
    margin: 0 0 8px;
}

.empty-hint {
    font-size: 14px;
    color: var(--el-text-color-secondary);
    margin: 0;
}

/* 图片展示区 */
.image-display {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-height: 0;
}

.canvas-wrapper {
    flex: 1;
    display: flex;
    justify-content: center;
    align-items: flex-start;
    background: var(--el-fill-color-darker);
    border-radius: 8px;
    padding: 20px;
    overflow: auto;
    min-height: 300px;
}

.canvas-wrapper canvas {
    max-width: 100%;
    max-height: 70vh;
    height: auto;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
    border-radius: 4px;
    display: block;
}

:deep(.result-image) {
    max-width: 100%;
    height: auto;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
    border-radius: 4px;
}

/* 统计卡片 */
.stats-card {
    border-radius: 12px;
}

.stat-item {
    text-align: center;
    padding: 16px;
    background: var(--el-fill-color-lighter);
    border-radius: 8px;
    transition: all 0.3s ease;
}

.stat-item:hover {
    background: var(--el-fill-color);
}

.stat-value {
    font-size: 32px;
    font-weight: 700;
    color: var(--el-color-primary);
    line-height: 1.2;
}

.stat-label {
    font-size: 13px;
    color: var(--el-text-color-secondary);
    margin-top: 6px;
}

/* 类别分布 */
.class-distribution {
    margin-top: 16px;
}

.distribution-title {
    font-size: 14px;
    font-weight: 500;
    color: var(--el-text-color-primary);
    margin: 0 0 12px;
}

.class-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
}

/* ========== 滚动条美化 ========== */
.control-panel::-webkit-scrollbar,
.result-panel::-webkit-scrollbar {
    width: 6px;
}

.control-panel::-webkit-scrollbar-thumb,
.result-panel::-webkit-scrollbar-thumb {
    background: var(--el-border-color);
    border-radius: 3px;
}

.control-panel::-webkit-scrollbar-thumb:hover,
.result-panel::-webkit-scrollbar-thumb:hover {
    background: var(--el-text-color-disabled);
}

.control-panel::-webkit-scrollbar-track,
.result-panel::-webkit-scrollbar-track {
    background: transparent;
}

/* ========== 响应式适配 ========== */
@media (max-width: 1200px) {
    .main-content {
        flex-direction: column;
    }

    .control-panel {
        width: 100%;
        max-height: none;
    }

    .result-panel {
        max-height: none;
    }
}

/* ========== 自定义字体 ========== */
@font-face {
    font-family: 'Arial-Bold';
    font-weight: bold;
    font-style: normal;
    src: local('Arial');
}
</style>
