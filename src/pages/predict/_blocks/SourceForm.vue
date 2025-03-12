<script lang="ts" setup>
import {
    ElForm, ElSelect, ElUpload, ElIcon, ElSlider, ElSwitch, ElInputNumber, ElInputTag, ElButton, ElRadioGroup, ElRadio,
    type UploadUserFile, type UploadProps, type UploadInstance, type UploadRawFile, genFileId
} from 'element-plus';
import { Delete, UploadFilled } from '@element-plus/icons-vue';
import { defaultsPredictData, type ImageResponse, type PredictData } from '@/utils/api/predict';
import * as api from "@/utils/api"
import { Message } from '@/utils/message';

import { computed, provide, reactive, ref } from 'vue'
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
const originalVideo = ref<HTMLVideoElement | null>(null);
const resultVideo = ref<HTMLVideoElement | null>(null);

const modelId = ref<string>("");
const form: Omit<typeof defaultsPredictData, "file"> = reactive(Object.assign({}, defaultsPredictData));
const submitLoading = ref(false);
const showOriginal = ref(false);
const results = ref<ImageResponse | null>(null);
const resultsBlob = ref<Blob | null>(null);
const hasResults = computed(() => results.value !== null || resultsBlob.value !== null);

const models = await api.getModels().then((models) => {
    if (models.length > 0) modelId.value = models[0].id
    return models
}).catch((e: Error) => {
    Message.error(`获取模型列表失败：${e.name}`)
    console.error(e)
})

const acceptOptions = {
    image: [{
        name: "图像输出",
        value: "image/jpeg,image/png"
    }, {
        name: "前端数据渲染",
        value: "application/json"
    }],
    video: [{
        name: "视频输出",
        value: "video/mp4"
    }, {
        name: "前端数据渲染",
        value: "application/json"
    }]
}

const accept = ref<string>(props.source === "image" ? "application/json" : "video/mp4");

function clearResults() {
    results.value = null;
    resultsBlob.value = null;
}

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
        source: props.source,
        file: uploadedFile,
    }
    if (props.source === "image") {
        assignee.vid_stride = undefined;
        const res = await api.callModels(modelId.value, Object.assign({}, form, assignee), accept.value).catch((e: Error) => {
            Message.error(`提交任务失败：${e.name}`)
            console.error(e)
            submitLoading.value = false;
            return null
        })
        if (res && !(res instanceof Blob)) {
            results.value = res;
            handleImageResult(URL.createObjectURL(uploadedFile), res);
        } else if (res) {
            Message.warning("Not implemented yet")
        }
    } else if (props.source === "video") {
        const res = await api.callModels(modelId.value, Object.assign({}, form, assignee), accept.value).catch((e: Error) => {
            Message.error(`提交任务失败：${e.name}`)
            console.error(e)
            submitLoading.value = false;
            return null
        })
        if (res && (res instanceof Blob)) {
            resultsBlob.value = res;
            handleVideoResultBlob(URL.createObjectURL(uploadedFile), URL.createObjectURL(res));
        } else if (res) {
            Message.warning("Not implemented yet")
        }
    }
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
        const colors = ["yellow", "white", "blue", "green", "red",]
        const types: number[] = []
        for (let i = 0; i < boxes.length; i++) {
            const box = boxes[i];
            let colori = 0
            if (types.includes(box.class)) colori = types.indexOf(box.class) % colors.length
            else {
                types.push(box.class)
                colori = (types.length - 1) % colors.length
            }
            r_ctx.strokeStyle = colors[colori];
            r_ctx.lineWidth = 4;
            r_ctx.strokeRect(box.x, box.y, box.w, box.h);
            // font weight bold
            r_ctx.font = "24px Arial-Bold";
            r_ctx.fillStyle = colors[colori];
            r_ctx.fillText(`${box.name} (${box.confidence.toFixed(2)})`, box.x, box.y - 12);
        }
    }
    img.src = uri;
}

async function handleVideoResultBlob(originalUri: string, resultUri: string) {
    const o_video = originalVideo.value!;
    const r_video = resultVideo.value!
    o_video.src = originalUri;
    r_video.src = resultUri;
}

function switchOriginal() {
    showOriginal.value = !showOriginal.value;
    if (props.source === 'video' && resultsBlob.value) {
        const prev = showOriginal.value ? resultVideo.value! : originalVideo.value!;
        const next = showOriginal.value ? originalVideo.value! : resultVideo.value!;
        let state = prev.paused;
        prev.pause();
        let prevTime = prev.currentTime;
        next.currentTime = prevTime;
        if (!state) next.play();
    }
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
                <div class="*:my-2 flex items-center gap-4">
                    <span class="text-sm">输出处理方式</span>
                    <ElRadioGroup v-model="accept" size="small">
                        <ElRadio v-for="option in acceptOptions[props.source]" :key="option.value"
                            :label="option.value">
                            {{ option.name }}
                        </ElRadio>
                    </ElRadioGroup>
                </div>
                <div class="!mt-4 flex">
                    <ElButton type="primary" class="flex-1" @click="onSubmit" :loading="submitLoading">提交任务</ElButton>
                    <ElButton type="warning" plain :icon="Delete" @click="clearResults" v-show="hasResults">
                        清除结果</ElButton>
                </div>
            </ElForm>
        </div>
    </div>

    <!-- Results -->
    <div class="pt-8" v-show="hasResults">
        <div class="flex items-center gap-4">
            <span class="text-xl font-bold">任务结果</span>
            <ElButton text size="small" bg :type="showOriginal ? 'primary' : ''" @click="switchOriginal">
                {{ props.source === "image" ? "查看原图" : "查看原视频" }}
            </ElButton>
        </div>
        <!-- Image -->
        <div class="mt-4" v-if="props?.source === 'image'">
            <canvas ref="originalCanvas" class="max-w-full" v-show="showOriginal"></canvas>
            <canvas ref="resultCanvas" class="max-w-full" v-show="!showOriginal"></canvas>
        </div>
        <!-- Video -->
        <div class="mt-4" v-if="props?.source === 'video'">
            <video ref="originalVideo" class="max-w-full" v-show="showOriginal" controls></video>
            <video ref="resultVideo" class="max-w-full" v-show="!showOriginal" controls></video>
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