<script lang="ts" setup>
import {
    ElForm, ElSelect, ElUpload, ElIcon, ElSlider, ElSwitch, ElInputNumber, ElInputTag, ElButton,
    type UploadUserFile, type UploadProps, type UploadInstance, type UploadRawFile, genFileId
} from 'element-plus';
import { Delete, UploadFilled } from '@element-plus/icons-vue';
import { defaultsPredictData, type ImageResponse, type PredictData } from '@/utils/api/predict';
import * as api from "@/utils/api"
import { Message } from '@/utils/message';

import { provide, reactive, ref } from 'vue'
import { ID_INJECTION_KEY } from 'element-plus'

provide(ID_INJECTION_KEY, {
    prefix: 100,
    current: 0,
})

const props = defineProps<{
    source: PredictData["source"];
}>();

const uploadEl = ref<UploadInstance | null>(null);
const uploadedFileList = ref<UploadUserFile[]>([]);
const originalCanvas = ref<HTMLCanvasElement | null>(null);
const resultCanvas = ref<HTMLCanvasElement | null>(null);

const modelId = ref<string>("");
const form: Omit<typeof defaultsPredictData, "file"> = reactive(Object.assign({}, defaultsPredictData));
const submitLoading = ref(false);
const showOriginal = ref(false);
const results = ref<ImageResponse | null>(null);

const models = await api.getModels().then((models) => {
    if (models.length > 0) modelId.value = models[0].id
    return models
}).catch((e: Error) => {
    Message.error(`获取模型列表失败：${e.name}`)
    console.error(e)
})

const handleExceed: UploadProps['onExceed'] = (files) => {
    uploadEl.value!.clearFiles()
    const file = files[0] as UploadRawFile
    file.uid = genFileId()
    uploadEl.value!.handleStart(file)
}

async function onSubmit() {
    if (!modelId.value) {
        Message.warning("请选择一个模型")
        return;
    }
    console.log(uploadedFileList.value)
    if (uploadedFileList.value.length === 0) {
        Message.warning("请上传一个文件")
        return;
    }

    submitLoading.value = true;
    const uploadedFile: File = uploadedFileList.value[0].raw!;
    let assignee: Partial<PredictData> = {
        file: uploadedFile,
    }
    if (props.source === "image") assignee.vid_stride = undefined;
    const res = await api.callModels(modelId.value, Object.assign({}, form, assignee)).catch((e: Error) => {
        Message.error(`提交任务失败：${e.name}`)
        console.error(e)
        submitLoading.value = false;
        return null
    })
    if (!res) return;
    results.value = res;
    handleImageResult(URL.createObjectURL(uploadedFile), res);
    submitLoading.value = false;
}

async function handleImageResult(uri: string, data: ImageResponse) {
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
        const boxes = data.map(box => {
            return {
                ...box,
                x: box.xmin,
                y: box.ymin,
                w: box.xmax - box.xmin,
                h: box.ymax - box.ymin
            }
        })
        const colors = ["red", "green", "blue", "yellow"]
        for (let i = 0; i < boxes.length; i++) {
            const box = boxes[i];
            r_ctx.strokeStyle = colors[i % colors.length];
            r_ctx.lineWidth = 4;
            r_ctx.strokeRect(box.x, box.y, box.w, box.h);
            // font weight bold
            r_ctx.font = "24px Arial-Bold";
            r_ctx.fillStyle = colors[i % colors.length];
            r_ctx.fillText(`${box.name} (${box.confidence.toFixed(2)})`, box.x, box.y - 12);
        }
    }
    img.src = uri;
}

</script>

<template>
    <!-- Data -->
    <div>
        <div class="flex items-center gap-4">
            <span class="text-xl font-bold">参数设置</span>
        </div>
        <div class="mt-4">
            <ElForm :model="form" class="*:my-2">
                <div class="*:my-2">
                    <span class="text-sm">选择模型</span>
                    <ElSelect v-model="modelId">
                        <ElSelect.Option v-for="model in models" :key="model.id" :label="model.name"
                            :value="model.id" />
                    </ElSelect>
                </div>
                <div class="*:my-2">
                    <span class="text-sm" v-if="props.source === 'image'">上传图片</span>
                    <span class="text-sm" v-if="props.source === 'video'">上传视频</span>
                    <ElUpload class="upload-demo" ref="uploadEl" drag v-model:file-list="uploadedFileList"
                        :auto-upload="false" :on-exceed="handleExceed" :limit="1" multiple>
                        <ElIcon class="el-icon--upload">
                            <UploadFilled />
                        </ElIcon>
                        <div class="el-upload__text">
                            拖拽文件至此或<em>点击上传</em>
                        </div>
                        <template #tip>
                            <div class="el-upload__tip" v-if="props.source === 'image'">JPG/PNG 图片</div>
                            <div class="el-upload__tip" v-if="props.source === 'video'">MP4 视频</div>
                        </template>
                    </ElUpload>
                </div>
                <div class="*:my-2">
                    <span class="text-sm">最小置信度 Confidence</span>
                    <ElSlider v-model="form.conf" show-input class="pl-2" :step="0.01" :min="0" :max="1" />
                </div>
                <div class="*:my-2">
                    <span class="text-sm">非最大抑制（NMS）的交叉重叠阈值（IoU）</span>
                    <ElSlider v-model="form.iou" show-input class="pl-2" :step="0.01" :min="0" :max="1" />
                </div>
                <div v-if="props.source === 'video'">
                    <span class="text-sm">视频帧间隔</span>
                    <ElSlider v-model="form.vid_stride" show-input class="pl-2 inline-flex" :step="1" :min="1"
                        :max="500" />
                </div>
                <div class="!my-0 *:my-2 *:mr-8 *:last:mr-0">
                    <div class="inline-flex items-center gap-4 w-max">
                        <span class="text-sm">启用半精度 FP16 推理</span>
                        <ElSwitch v-model="form.half" />
                    </div>
                    <div class="inline-flex items-center gap-4 w-max">
                        <span class="text-sm">测试时间增强（TTA）</span>
                        <ElSwitch v-model="form.augment" />
                    </div>
                    <div class="inline-flex items-center gap-4 w-max">
                        <span class="text-sm">启用与类别无关的非最大抑制（NMS）</span>
                        <ElSwitch v-model="form.agnostic_nms" />
                    </div>
                </div>
                <div class="!my-0 *:my-2 *:mr-8 *:last:mr-0">
                    <div class="inline-flex items-center gap-4 w-max">
                        <span class="text-sm">图像大小</span>
                        <ElInputNumber v-model="form.imgsz" :step="10" :min="16" :max="3656" />
                    </div>
                    <div class="inline-flex items-center gap-4 w-max">
                        <span class="text-sm">批量大小</span>
                        <ElInputNumber v-model="form.batch" :min="1" :max="100" />
                    </div>
                    <div class="inline-flex items-center gap-4 w-max">
                        <span class="text-sm">最大检测次数</span>
                        <ElInputNumber v-model="form.max_det" :min="1" :max="500" />
                    </div>
                </div>
                <div class="*:my-2">
                    <span class="text-sm">仅检测以下类别</span>
                    <ElInputTag v-model="form.classes" placeholder="输入并按下 Enter 以添加一个类别，留空表示全部" />
                </div>
                <div class="!mt-4 flex">
                    <ElButton type="primary" class="flex-1" @click="onSubmit" :loading="submitLoading">提交任务</ElButton>
                    <ElButton type="warning" plain :icon="Delete" @click="() => { results = null }" v-show="results">
                        清除结果</ElButton>
                </div>
            </ElForm>
        </div>
    </div>

    <!-- Results -->
    <div class="pt-8" v-show="results">
        <div class="flex items-center gap-4">
            <span class="text-xl font-bold">任务结果</span>
            <ElButton text size="small" bg :type="showOriginal ? 'primary' : ''"
                @click="() => { showOriginal = !showOriginal }">查看原图
            </ElButton>
        </div>
        <div class="mt-4">
            <canvas ref="originalCanvas" class="max-w-full" v-show="showOriginal"></canvas>
            <canvas ref="resultCanvas" class="max-w-full" v-show="!showOriginal"></canvas>
        </div>
    </div>
</template>

<style>
@font-face {
    font-family: 'Arial-Bold';
    font-weight: bold;
    font-style: normal;
    src: local('Arial');
}
</style>