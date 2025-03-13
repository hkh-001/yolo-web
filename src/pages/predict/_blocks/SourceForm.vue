<script lang="ts" setup>
import {
    ElForm, ElSelect, ElUpload, ElIcon, ElSlider, ElSwitch, ElInputNumber, ElInputTag, ElButton, ElRadioGroup, ElRadio, ElInput,
    type UploadUserFile, type UploadProps, type UploadInstance, type UploadRawFile, genFileId,
    ElPopconfirm
} from 'element-plus';
import { Delete, FolderAdd, Refresh, UploadFilled } from '@element-plus/icons-vue';
import { defaultsPredictData, type ImageResponse, type VideoResponse, type PredictData, type SavedPredictData } from '@/utils/api/predict';
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
const modelId = ref<string>("");
const form: Omit<typeof defaultsPredictData, "file"> = reactive(Object.assign({}, defaultsPredictData));
const submitLoading = ref(false);
const saveLoading = ref(false);
const showOriginal = ref(false);
const originalBlob = ref<Blob | null>(null);
const resultData = ref<ImageResponse | VideoResponse | null>(null);
const resultBlob = ref<Blob | null>(null);
const hasResult = computed(() => resultData.value !== null || resultBlob.value !== null);

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

function updateModels() {
    api.getModels().then((m) => {
        if (m.length > 0) modelId.value = m[0].id
        models.value = m
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
    modelId.value = inputArgs.model_id
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
    // queryTaskName.value = "";
    // setURLParams({ task: null }, false)
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
    originalBlob.value = new Blob([uploadedFile], { type: uploadedFile.type });
    if (props.source === "image") {
        assignee.vid_stride = undefined;
        const res = await api.callModels<"image">(modelId.value, Object.assign({}, form, assignee), accept.value).catch((e: Error) => {
            Message.error(`提交任务失败：${e.name}`)
            console.error(e)
            submitLoading.value = false;
            return null
        })
        if (res && (res instanceof Blob)) {
            resultBlob.value = res;
            handleImageResultBlob(URL.createObjectURL(uploadedFile), URL.createObjectURL(res));
        } else if (res && !(res instanceof Blob)) {
            resultData.value = res;
            handleImageResultData(URL.createObjectURL(uploadedFile), res);
        }
    } else if (props.source === "video") {
        const res = await api.callModels<"video">(modelId.value, Object.assign({}, form, assignee), accept.value).catch((e: Error) => {
            Message.error(`提交任务失败：${e.name}`)
            console.error(e)
            submitLoading.value = false;
            return null
        })
        if (res && (res instanceof Blob)) {
            resultBlob.value = res;
            handleVideoResultBlob(URL.createObjectURL(uploadedFile), URL.createObjectURL(res));
        } else if (res) {
            resultData.value = res;
            handleVideoResultData(URL.createObjectURL(uploadedFile), res);
        }
    }
    submitLoading.value = false;
}

async function handleImageResultData(uri: string, data: ImageResponse) {
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

async function handleImageResultBlob(originalUri: string, resultUri: string) {
    Message.warning("Not implemented yet")
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
    showOriginal.value = !showOriginal.value;
    if (props.source === 'video' && resultBlob.value) {
        const prev = showOriginal.value ? resultVideo.value! : originalVideo.value!;
        const next = showOriginal.value ? originalVideo.value! : resultVideo.value!;
        let state = prev.paused;
        prev.pause();
        let prevTime = prev.currentTime;
        next.currentTime = prevTime;
        if (!state) next.play();
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
    const uploadObject: Omit<Task, 'id' | 'timestamp' | 'task_id'> = {
        source: props.source,
        task_name: submitTaskName.value,
        input_blob: originalId,
        input_args: JSON.stringify(<SavedPredictData>{
            model_id: modelId.value,
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
    <div class="mb-4 flex">
        <span class="text-2xl flex-1">
            <span v-if="queryTaskName">
                <span class="font-bold">任务：</span><span>{{ queryTaskName }}</span>
                <ElButton :circle="!hasResult" :link="hasResult" :icon="Refresh" class="!m-0 !ml-2 w-8" @click="loadFromTaskQuery" />
            </span>
        </span>
        <span class="text-2xl font-bold">{{ props.title }}</span>
    </div>
    <!-- Data -->
    <div>
        <div class="flex items-center gap-4">
            <span class="text-xl font-bold">参数设置</span>
        </div>
        <div class="mt-4">
            <ElForm :model="form" class="*:my-2">
                <div class="*:my-2">
                    <span class="text-sm">选择模型</span>
                    <ElButton link :icon="Refresh" class="!m-0 !ml-2" @click="updateModels" />
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
                            :value="option.value">
                            {{ option.name }}
                        </ElRadio>
                    </ElRadioGroup>
                </div>
                <div class="!mt-4 flex">
                    <ElButton type="primary" class="flex-1" @click="onSubmit" :loading="submitLoading">提交任务</ElButton>
                    <ElButton type="warning" plain :icon="Delete" @click="clearResults" v-show="hasResult">
                        清除结果</ElButton>
                </div>
                <div class="!mt-4 flex" v-show="hasResult">
                    <ElInput v-model="submitTaskName" class="flex-1" placeholder="输入任务名称" />
                    <ElPopconfirm width="200" :title="queryTaskName ? '确定保存该任务吗？这将不会覆盖原有任务' : '确定保存该任务吗？'"
                        :hide-icon="true" @confirm="saveResults">
                        <template #reference>
                            <ElButton type="primary" plain :icon="FolderAdd" :loading="saveLoading">
                                保存任务</ElButton>
                        </template>
                    </ElPopconfirm>
                </div>
            </ElForm>
        </div>
    </div>

    <!-- Results -->
    <div class="pt-8" v-show="hasResult">
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