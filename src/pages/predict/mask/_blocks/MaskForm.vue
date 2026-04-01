<script lang="ts" setup>
import {
    ElForm, ElSelect, ElUpload, ElIcon, ElSlider, ElSwitch, ElInputNumber, ElButton,
    type UploadUserFile, type UploadProps, type UploadInstance, type UploadRawFile, genFileId,
} from 'element-plus';
import { UploadFilled } from '@element-plus/icons-vue';
import { Message } from '@/utils/message';
import { setURLParams } from '@/utils/url';
import { preventElemmentSSRError } from '@/utils/ssr';
import { computed, onMounted, reactive, ref } from 'vue'
import * as api from "@/utils/api"
import type { ModelInfo } from '@/utils/api';

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
const modelId = ref<string>("");
const submitLoading = ref(false);
const showOriginal = ref(false);
const originalBlob = ref<Blob | null>(null);
const resultData = ref<any>(null);
const maskOverlayUrl = ref<string>("");
const hasResult = computed(() => resultData.value !== null || maskOverlayUrl.value !== "");

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

// Load models on mount
onMounted(() => {
    updateModels();
});

function updateModels() {
    api.getModels().then((m) => {
        // Filter only segmentation models
        const segModels = m.filter(model => 
            model.id.includes('seg') || model.name.toLowerCase().includes('seg')
        );
        if (segModels.length > 0) {
            modelId.value = segModels[0].id;
        } else if (m.length > 0) {
            modelId.value = m[0].id;
        }
        models.value = m;
    }).catch((e: Error) => {
        Message.error(`获取模型列表失败：${e.name}`)
        console.error(e)
    })
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
    
    if (!modelId.value) {
        Message.warning("请选择一个模型")
        return;
    }
    if (uploadedFileList.value.length === 0) {
        Message.warning("请上传一个文件")
        return;
    }

    isSubmitting = true;
    submitLoading.value = true;
    
    console.log(`[MaskSubmit] 开始提交掩码任务，模型: ${modelId.value}`);
    const uploadedFile: File = uploadedFileList.value[0].raw!;
    
    // Store original blob
    originalBlob.value = new Blob([uploadedFile], { type: uploadedFile.type });
    
    try {
        // Build form data
        const assignee = {
            source: props.source,
            file: uploadedFile,
            ...form
        };
        
        // Call API - always request JSON for mask data
        const res = await api.callModels<"image">(modelId.value, assignee, "application/json");
        
        console.log('[MaskSubmit] 收到响应:', res);
        
        if (res && !(res instanceof Blob)) {
            resultData.value = res;
            await handleMaskResult(URL.createObjectURL(uploadedFile), res);
            Message.success("掩码生成成功");
        } else {
            Message.error("响应格式错误");
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
    
    // Check data format
    let detections: any[] = [];
    if (data && data.boxes && Array.isArray(data.boxes)) {
        detections = data.boxes;
    } else if (Array.isArray(data)) {
        detections = data;
    }
    
    console.log('[MaskRender] 检测目标数量:', detections.length);
    
    // Draw on canvas
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
        
        // Set canvas sizes
        [o_canvas, r_canvas, m_canvas].forEach(c => {
            c.width = img.width;
            c.height = img.height;
        });
        
        // Draw original
        o_ctx.drawImage(img, 0, 0);
        
        // Draw result with boxes
        r_ctx.drawImage(img, 0, 0);
        
        // Draw masks if available
        m_ctx.clearRect(0, 0, m_canvas.width, m_canvas.height);
        m_ctx.drawImage(img, 0, 0);
        
        // Draw detections
        const colors = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#FFA07A", "#98D8C8"];
        detections.forEach((det: any, index: number) => {
            const color = colors[index % colors.length];
            
            // Get box coordinates
            let x1, y1, x2, y2;
            if (det.box) {
                x1 = det.box.x1; y1 = det.box.y1; x2 = det.box.x2; y2 = det.box.y2;
            } else {
                x1 = det.xmin; y1 = det.ymin; x2 = det.xmax; y2 = det.ymax;
            }
            
            const w = x2 - x1;
            const h = y2 - y1;
            
            // Draw box on result canvas
            r_ctx.strokeStyle = color;
            r_ctx.lineWidth = 3;
            r_ctx.strokeRect(x1, y1, w, h);
            
            // Draw label
            r_ctx.fillStyle = color;
            r_ctx.font = "bold 20px Arial";
            const label = `${det.name || 'unknown'} ${(det.conf || det.confidence || 0).toFixed(2)}`;
            r_ctx.fillText(label, x1, y1 - 5);
            
            // Draw mask overlay if available
            if (det.mask || det.masks) {
                m_ctx.fillStyle = color + '40'; // 25% opacity
                // If mask is available, draw it (simplified)
                m_ctx.fillRect(x1, y1, w, h);
            }
            
            console.log(`[MaskRender] [${index}] ${det.name}: conf=${(det.conf || det.confidence || 0).toFixed(2)}`);
        });
        
        console.log('[MaskRender] ========== 渲染完成 ==========');
    };
    img.src = uri;
}

function switchOriginal() {
    showOriginal.value = !showOriginal.value;
}

function clearResults() {
    resultData.value = null;
    maskOverlayUrl.value = "";
}
</script>

<template>
    <div class="mb-4 flex">
        <span class="text-2xl font-bold">{{ props.title }}</span>
    </div>
    
    <!-- Settings -->
    <div>
        <div class="flex items-center gap-4">
            <span class="text-xl font-bold">参数设置</span>
        </div>
        <div class="mt-4">
            <ElForm :model="form" class="*:my-2">
                <!-- Model Selection -->
                <div class="*:my-2">
                    <span class="text-sm">选择分割模型</span>
                    <ElSelect v-model="modelId" class="w-full">
                        <ElSelect.Option v-for="model in models" :key="model.id" :label="model.name"
                            :value="model.id" />
                    </ElSelect>
                </div>
                
                <!-- File Upload -->
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
                    </ElUpload>
                </div>
                
                <!-- Parameters -->
                <div class="*:my-2">
                    <span class="text-sm">最小置信度 Confidence</span>
                    <ElSlider v-model="form.conf" show-input class="pl-2" :step="0.01" :min="0" :max="1" />
                </div>
                
                <div class="*:my-2">
                    <span class="text-sm">NMS IoU 阈值</span>
                    <ElSlider v-model="form.iou" show-input class="pl-2" :step="0.01" :min="0" :max="1" />
                </div>
                
                <div class="*:my-2">
                    <span class="text-sm">图像大小</span>
                    <ElInputNumber v-model="form.imgsz" :step="10" :min="16" :max="3656" />
                </div>
                
                <div class="*:my-2">
                    <span class="text-sm">最大检测数量</span>
                    <ElInputNumber v-model="form.max_det" :min="1" :max="500" />
                </div>
                
                <!-- Submit Button -->
                <div class="!mt-4 flex">
                    <ElButton type="primary" class="flex-1" @click="onSubmit" :loading="submitLoading">
                        生成掩码
                    </ElButton>
                    <ElButton type="warning" plain @click="clearResults" v-show="hasResult">
                        清除结果
                    </ElButton>
                </div>
            </ElForm>
        </div>
    </div>

    <!-- Results -->
    <div class="pt-8" v-show="hasResult">
        <div class="flex items-center gap-4 mb-4">
            <span class="text-xl font-bold">掩码结果</span>
            <ElButton text size="small" bg :type="showOriginal ? 'primary' : ''" @click="switchOriginal">
                {{ showOriginal ? "查看结果" : "查看原图" }}
            </ElButton>
        </div>
        
        <!-- Canvas Display -->
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <!-- Original -->
            <div class="border rounded-lg p-4">
                <div class="text-sm font-bold mb-2 text-gray-500">原图</div>
                <canvas ref="originalCanvas" class="max-w-full" v-show="showOriginal"></canvas>
                <div v-show="!showOriginal" class="text-gray-400 text-center py-8">
                    点击"查看原图"显示
                </div>
            </div>
            
            <!-- Detection Result -->
            <div class="border rounded-lg p-4">
                <div class="text-sm font-bold mb-2 text-blue-500">检测结果</div>
                <canvas ref="resultCanvas" class="max-w-full" v-show="!showOriginal"></canvas>
                <div v-show="showOriginal" class="text-gray-400 text-center py-8">
                    点击"查看结果"显示
                </div>
            </div>
            
            <!-- Mask Overlay -->
            <div class="border rounded-lg p-4">
                <div class="text-sm font-bold mb-2 text-green-500">掩码叠加</div>
                <canvas ref="maskCanvas" class="max-w-full" v-show="!showOriginal"></canvas>
                <div v-show="showOriginal" class="text-gray-400 text-center py-8">
                    点击"查看结果"显示
                </div>
            </div>
        </div>
        
        <!-- Detection List -->
        <div class="mt-6" v-if="resultData && resultData.boxes">
            <div class="text-lg font-bold mb-3">检测列表 ({{ resultData.boxes.length }}个目标)</div>
            <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div v-for="(box, index) in resultData.boxes" :key="index"
                    class="border rounded p-3 bg-gray-50">
                    <div class="font-bold">{{ box.name || '未知' }}</div>
                    <div class="text-sm text-gray-600">
                        置信度: {{ (box.conf || box.confidence || 0).toFixed(3) }}
                    </div>
                    <div class="text-xs text-gray-400 mt-1">
                        ID: {{ box.cls || box.class || index }}
                    </div>
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
