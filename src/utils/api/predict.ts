export interface PredictData {
    source: "image" | "video" | "workflow"
    file: File
    /**
     * 用于推理的图像大小
     */
    imgsz: number
    /**
     * 最小置信度
     */
    conf: number
    /**
     * 非最大抑制的交叉重叠阈值
     */
    iou: number
    /**
     * 启用半精度 FP16 推理
     */
    half: boolean
    /**
     * 推理的批量大小
     */
    batch: number
    /**
     * 每幅图像允许的最大检测次数
     */
    max_det: number
    /**
     * 视频输入的帧间距
     */
    vid_stride?: number
    /**
     * 测试时间增强（TTA）
     */
    augment: boolean
    /**
     * 启用与类别无关的非最大抑制（NMS）
     */
    agnostic_nms: boolean
    /**
     * 类别过滤（留空以检测所有类别）
     */
    classes: string[]
}

export type SavedPredictData = Omit<PredictData, "source" | "file"> & {
    model_id: string
}

export const defaultsPredictData: Partial<PredictData> = {
    imgsz: 640,
    conf: 0.25,
    iou: 0.7,
    half: false,
    batch: 1,
    max_det: 300,
    vid_stride: 1,
    augment: false,
    agnostic_nms: false,
    classes: []
}

interface ImageResponseBox {
    xmin: number
    ymin: number
    xmax: number
    ymax: number
    confidence: number
    class: number
    name: string
}

export type ImageResponse = ImageResponseBox[]

export type VideoResponse = ImageResponseBox[][]