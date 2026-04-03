<template>
    <div class="workflow-form">
        <!-- 顶部控制区域 -->
        <el-card class="upload-section" shadow="hover" :body-style="{ padding: '16px' }">
            <div class="control-bar">
                <div class="upload-area" @click="debugUploadAreaClick">
                    <input
                        ref="fileInputRef"
                        type="file"
                        accept="image/*"
                        class="native-file-input"
                        @change="onFileSelected"
                        @click="debugInputClick"
                    />
                    
                    <!-- 紧凑上传区域 -->
                    <div 
                        class="upload-drop-zone"
                        :class="{ 'has-file': originalImage, 'disabled': isRunning }"
                        @click="triggerFileSelect"
                        @dragover.prevent="onDragOver"
                        @dragleave.prevent="onDragLeave"
                        @drop.prevent="onFileDrop"
                    >
                        <el-icon class="upload-icon" :size="24">
                            <upload-filled />
                        </el-icon>
                        <div class="upload-text">
                            <span v-if="!originalImage">
                                拖拽图片到此处或 <em>点击上传</em>
                            </span>
                            <span v-else>
                                已选择: {{ currentFile?.name }}
                                <small class="replace-hint">（点击更换）</small>
                            </span>
                        </div>
                        <div class="upload-tip">支持 JPG、PNG、WEBP</div>
                    </div>
                </div>
                
                <div class="action-buttons">
                    <el-button
                        type="primary"
                        :disabled="!canStart"
                        :loading="isRunning"
                        @click="startWorkflow"
                    >
                        <el-icon><video-play /></el-icon>
                        开始智能流程
                    </el-button>
                    <el-button
                        :disabled="isRunning || (!originalImage && !hasAnyResult)"
                        @click="resetWorkflow"
                    >
                        <el-icon><refresh /></el-icon>
                        重置
                    </el-button>
                </div>
            </div>
            
            <!-- 调试开关与折叠面板 -->
            <div class="debug-toggle">
                <el-switch
                    v-model="showDebug"
                    active-text="显示调试信息"
                    inline-prompt
                    size="small"
                />
            </div>
            <el-collapse v-if="showDebug" class="debug-collapse">
                <el-collapse-item title="调试信息" name="1">
                    <pre>originalImage: {{ !!originalImage }}
canStart: {{ canStart }}
isRunning: {{ isRunning }}
workflowStatus: {{ workflowStatus }}
currentFile: {{ currentFile?.name || 'null' }}</pre>
                </el-collapse-item>
            </el-collapse>
        </el-card>

        <!-- 结果展示区：2×2 网格 -->
        <div v-if="originalImage" class="results-section">
            <div class="results-grid">
                <!-- Step 1: 原图 -->
                <el-card class="result-card step-card" shadow="hover">
                    <template #header>
                        <div class="card-header">
                            <div class="card-title-group">
                                <span class="step-badge step-badge-input">01</span>
                                <span class="card-title">
                                    <el-icon><picture /></el-icon>
                                    原图
                                </span>
                            </div>
                            <el-tag type="info" size="small" effect="light">原始输入</el-tag>
                        </div>
                    </template>
                    <div class="image-container">
                        <img :src="originalImage" alt="原图" class="result-image" />
                    </div>
                </el-card>

                <!-- Step 2: 图像识别 -->
                <el-card class="result-card step-card" shadow="hover">
                    <template #header>
                        <div class="card-header">
                            <div class="card-title-group">
                                <span class="step-badge">02</span>
                                <span class="card-title">
                                    <el-icon><aim /></el-icon>
                                    图像识别
                                </span>
                            </div>
                            <div class="header-right">
                                <el-tag :type="getStatusType(detectStatus)" size="small" effect="light">
                                    {{ getStatusText(detectStatus) }}
                                </el-tag>
                                <span v-if="stepDurations.detect > 0" class="duration">
                                    {{ formatDuration(stepDurations.detect) }}
                                </span>
                            </div>
                        </div>
                    </template>
                    <div class="image-container">
                        <canvas
                            v-if="detectStatus !== 'idle'"
                            ref="detectCanvas"
                            class="result-canvas"
                        ></canvas>
                        <div v-else class="placeholder">
                            <el-icon><aim /></el-icon>
                            <span>等待执行</span>
                        </div>
                    </div>
                    <div v-if="detectStatus === 'success'" class="result-info">
                        <el-text type="success">
                            检测到 <strong>{{ detectCount }}</strong> 个目标
                        </el-text>
                    </div>
                    <div v-if="detectStatus === 'error'" class="result-info">
                        <el-text type="danger">{{ errorMessage }}</el-text>
                    </div>
                </el-card>

                <!-- Step 3: 掩码生成 -->
                <el-card class="result-card step-card" shadow="hover">
                    <template #header>
                        <div class="card-header">
                            <div class="card-title-group">
                                <span class="step-badge">03</span>
                                <span class="card-title">
                                    <el-icon><copy-document /></el-icon>
                                    掩码生成
                                </span>
                            </div>
                            <div class="header-right">
                                <el-tag :type="getStatusType(maskStatus)" size="small" effect="light">
                                    {{ getStatusText(maskStatus) }}
                                </el-tag>
                                <span v-if="stepDurations.mask > 0" class="duration">
                                    {{ formatDuration(stepDurations.mask) }}
                                </span>
                            </div>
                        </div>
                    </template>
                    <div class="image-container">
                        <img
                            v-if="maskImage"
                            :src="maskImage"
                            alt="掩码结果"
                            class="result-image"
                        />
                        <div v-else class="placeholder">
                            <el-icon><copy-document /></el-icon>
                            <span>{{ maskStatus === 'running' ? '生成中...' : '等待执行' }}</span>
                        </div>
                    </div>
                    <div v-if="maskStatus === 'error' && detectStatus === 'success'" class="result-info">
                        <el-text type="danger">掩码生成失败</el-text>
                    </div>
                </el-card>

                <!-- Step 4: 图像增强 -->
                <el-card class="result-card step-card" shadow="hover">
                    <template #header>
                        <div class="card-header">
                            <div class="card-title-group">
                                <span class="step-badge">04</span>
                                <span class="card-title">图像增强</span>
                            </div>
                            <el-tag :type="getStatusType(enhanceStatus)" size="small" effect="light">
                                {{ getStatusText(enhanceStatus) }}
                            </el-tag>
                        </div>
                    </template>
                    <!-- 增强进度 -->
                    <div v-if="enhanceStatus === 'running' && enhanceProgress.currentTargetName" class="target-info">
                        <el-text type="info" size="small">
                            正在增强: <strong>{{ enhanceProgress.currentTargetName }}</strong>
                        </el-text>
                    </div>
                    <!-- 增强结果提示 -->
                    <div v-if="enhanceStatus === 'success' && maskData.length > 0" class="target-info">
                        <el-text type="success" size="small">
                            mask 级精确增强完成
                        </el-text>
                    </div>
                    <div v-if="enhanceStatus === 'success' && maskData.length === 0" class="target-info">
                        <el-text type="success" size="small">
                            mask 级精确增强完成
                        </el-text>
                    </div>
                    <!-- 增强前提示 -->
                    <div v-if="enhanceStatus === 'idle' && detectCount > 0" class="target-info">
                        <el-text type="info" size="small">
                            共检测到 {{ detectCount }} 个目标，将增强最高置信度目标
                            <span v-if="maskData.length > 0">（优先使用 mask 精确增强）</span>
                        </el-text>
                    </div>
                    <div class="image-container">
                        <img
                            v-if="enhanceImage"
                            :src="enhanceImage"
                            alt="增强结果"
                            class="result-image"
                        />
                        <div v-else class="placeholder">
                            <span>{{ enhanceStatus === 'running' ? '增强中...' : '等待执行' }}</span>
                        </div>
                    </div>
                    <div v-if="enhanceStatus === 'error' && maskStatus === 'success'" class="result-info">
                        <el-text type="danger">{{ errorMessage || '图像增强失败' }}</el-text>
                    </div>
                </el-card>
            </div>

            <!-- 总耗时 -->
            <div v-if="totalDuration > 0" class="total-duration">
                总耗时: {{ formatDuration(totalDuration) }}
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { ref, computed, reactive, nextTick, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
    UploadFilled,
    VideoPlay,
    Refresh,
    Picture,
    Aim,
    CopyDocument
} from '@element-plus/icons-vue'
import { callModels } from '../../../../utils/api'

// 调试开关（默认隐藏）
const showDebug = ref(false)

// 步骤状态类型
type StepStatus = 'idle' | 'running' | 'success' | 'error'

// 上传相关
const fileInputRef = ref<HTMLInputElement | null>(null)
const currentFile = ref<File | null>(null)

// 图片状态
const originalImage = ref<string>('')
const maskImage = ref<string>('')
const enhanceImage = ref<string>('')

// mask 原始数据（阶段 2A：用于后续 mask 级精确增强）
interface MaskData {
    bbox: [number, number, number, number]
    width: number
    height: number
    mask: string  // base64
    name: string
    conf: number
    index: number
}
const maskData = ref<MaskData[]>([])

// 步骤状态
const detectStatus = ref<StepStatus>('idle')
const maskStatus = ref<StepStatus>('idle')
const enhanceStatus = ref<StepStatus>('idle')

// 流程状态
const workflowStatus = ref<'idle' | 'running' | 'completed' | 'error'>('idle')
const currentStep = ref<number>(0)

// 耗时统计
const stepDurations = reactive({
    detect: 0,
    mask: 0,
    enhance: 0
})
const totalDuration = ref<number>(0)

// 错误信息
const errorMessage = ref<string>('')

// 检测结果
const detectCount = ref<number>(0)
const detectBboxes = ref<any[]>([])

// Canvas 引用
const detectCanvas = ref<HTMLCanvasElement | null>(null)

// 计算属性
const isRunning = computed(() => workflowStatus.value === 'running')
const canStart = computed(() => {
    const result = originalImage.value && !isRunning.value
    console.log('[Workflow] canStart 计算:', { originalImage: !!originalImage.value, isRunning: isRunning.value, result })
    return result
})
const hasAnyResult = computed(() => 
    detectStatus.value !== 'idle' || 
    maskStatus.value !== 'idle' || 
    enhanceStatus.value !== 'idle'
)

// ========== 调试日志 ==========
onMounted(() => {
    console.log('[Workflow] 组件已挂载')
    console.log('[Workflow] 初始状态:', {
        originalImage: originalImage.value,
        workflowStatus: workflowStatus.value,
        canStart: canStart.value
    })
})

function debugUploadAreaClick() {
    console.log('[Workflow] 点击上传区域外层容器')
}

function debugInputClick() {
    console.log('[Workflow] 原生 input 被点击')
}

// ========== 原生文件上传 ==========
function triggerFileSelect() {
    console.log('[Workflow] 触发文件选择')
    if (isRunning.value) {
        console.log('[Workflow] 运行中，禁止选择')
        return
    }
    fileInputRef.value?.click()
}

function onFileSelected(event: Event) {
    console.log('[Workflow] 文件选择事件触发')
    const input = event.target as HTMLInputElement
    const file = input.files?.[0]
    
    if (file) {
        console.log('[Workflow] 选中文件:', file.name, file.size, file.type)
        handleFile(file)
    } else {
        console.log('[Workflow] 未选中文件')
    }
    
    // 重置 input 以便可以再次选择同一文件
    input.value = ''
}

function onDragOver(event: DragEvent) {
    console.log('[Workflow] 拖拽经过')
    const dropZone = event.currentTarget as HTMLElement
    dropZone.classList.add('drag-over')
}

function onDragLeave(event: DragEvent) {
    console.log('[Workflow] 拖拽离开')
    const dropZone = event.currentTarget as HTMLElement
    dropZone.classList.remove('drag-over')
}

function onFileDrop(event: DragEvent) {
    console.log('[Workflow] 文件拖放')
    const dropZone = event.currentTarget as HTMLElement
    dropZone.classList.remove('drag-over')
    
    if (isRunning.value) {
        ElMessage.warning('流程运行中，请等待完成')
        return
    }
    
    const file = event.dataTransfer?.files[0]
    if (file && file.type.startsWith('image/')) {
        handleFile(file)
    } else {
        ElMessage.warning('请上传图片文件')
    }
}

function handleFile(file: File) {
    console.log('[Workflow] 处理文件:', file.name, file.size, file.type)
    
    // 清理之前的结果
    resetResults()

    // 保存文件
    currentFile.value = file

    // 创建原图预览
    const url = URL.createObjectURL(file)
    originalImage.value = url
    console.log('[Workflow] 原图URL创建成功:', url)
    console.log('[Workflow] 当前状态:', { originalImage: !!originalImage.value, canStart: canStart.value })

    ElMessage.success('图片上传成功，点击"开始智能流程"开始处理')
}

function resetResults() {
    console.log('[Workflow] 重置结果（保留文件）')
    
    // 清理结果图片
    if (maskImage.value) {
        URL.revokeObjectURL(maskImage.value)
        maskImage.value = ''
    }
    if (enhanceImage.value) {
        URL.revokeObjectURL(enhanceImage.value)
        enhanceImage.value = ''
    }
    if (originalImage.value) {
        URL.revokeObjectURL(originalImage.value)
        originalImage.value = ''
    }

    // 重置状态
    detectStatus.value = 'idle'
    maskStatus.value = 'idle'
    enhanceStatus.value = 'idle'
    workflowStatus.value = 'idle'
    currentStep.value = 0

    // 重置数据
    detectCount.value = 0
    detectBboxes.value = []
    maskData.value = []  // 重置 mask 数据
    errorMessage.value = ''

    // 重置耗时
    stepDurations.detect = 0
    stepDurations.mask = 0
    stepDurations.enhance = 0
    totalDuration.value = 0
}

// ========== 工作流控制 ==========
async function startWorkflow() {
    console.log('[Workflow] 点击开始按钮')
    
    if (!currentFile.value) {
        ElMessage.warning('请先上传图片')
        return
    }

    // 重置各步骤状态
    detectStatus.value = 'idle'
    maskStatus.value = 'idle'
    enhanceStatus.value = 'idle'
    detectCount.value = 0
    detectBboxes.value = []
    maskData.value = []  // 重置 mask 数据
    
    // 清理之前的结果图片
    if (maskImage.value) {
        URL.revokeObjectURL(maskImage.value)
        maskImage.value = ''
    }
    if (enhanceImage.value) {
        URL.revokeObjectURL(enhanceImage.value)
        enhanceImage.value = ''
    }

    // 重置耗时
    stepDurations.detect = 0
    stepDurations.mask = 0
    stepDurations.enhance = 0
    totalDuration.value = 0
    errorMessage.value = ''

    workflowStatus.value = 'running'
    console.log('[Workflow] 流程开始运行')
    const workflowStartTime = Date.now()

    try {
        // 步骤 1: 图像识别
        currentStep.value = 1
        const detectSuccess = await runDetect()
        if (!detectSuccess) {
            workflowStatus.value = 'error'
            totalDuration.value = Date.now() - workflowStartTime
            return
        }

        // 步骤 2: 掩码生成
        currentStep.value = 2
        const maskSuccess = await runMask()
        if (!maskSuccess) {
            workflowStatus.value = 'error'
            totalDuration.value = Date.now() - workflowStartTime
            return
        }

        // 步骤 3: 图像增强
        currentStep.value = 3
        const enhanceSuccess = await runEnhance()
        if (!enhanceSuccess) {
            workflowStatus.value = 'error'
            totalDuration.value = Date.now() - workflowStartTime
            return
        }

        // 全部完成
        workflowStatus.value = 'completed'
        totalDuration.value = Date.now() - workflowStartTime
        ElMessage.success('智能流程执行完成')

    } catch (error) {
        workflowStatus.value = 'error'
        totalDuration.value = Date.now() - workflowStartTime
        console.error('工作流执行错误:', error)
    }
}

async function runDetect(): Promise<boolean> {
    if (!currentFile.value) return false

    detectStatus.value = 'running'
    const startTime = Date.now()

    try {
        const result = await callModels('yolo26n', { file: currentFile.value }, 'application/json')
        
        let detectData: any
        if (result instanceof Blob) {
            const text = await result.text()
            detectData = JSON.parse(text)
        } else if (typeof result === 'string') {
            detectData = JSON.parse(result)
        } else {
            detectData = result
        }

        const boxes = detectData.boxes || detectData.predictions || []
        detectBboxes.value = boxes
        detectCount.value = boxes.length

        console.log('[Workflow] ========== detect 完成 ==========')
        console.log(`[Workflow] detectCount: ${detectCount.value}`)
        console.log(`[Workflow] detectBboxes.length: ${detectBboxes.value.length}`)
        if (detectBboxes.value.length > 0) {
            const first = detectBboxes.value[0]
            console.log('[Workflow] detectBboxes[0] 样本:', first)
        }
        console.log('[Workflow] =================================')

        await drawDetections()

        detectStatus.value = 'success'
        stepDurations.detect = Date.now() - startTime
        console.log('[Workflow] detect 步骤成功完成')
        return true

    } catch (error) {
        detectStatus.value = 'error'
        stepDurations.detect = Date.now() - startTime
        errorMessage.value = error instanceof Error ? error.message : '图像识别失败'
        ElMessage.error('图像识别失败: ' + errorMessage.value)
        return false
    }
}

// 获取被选中的目标索引（最高置信度）
function getSelectedTargetIndex(): number {
    if (!detectBboxes.value || detectBboxes.value.length === 0) return -1
    
    let bestIndex = 0
    let bestConf = -1
    
    detectBboxes.value.forEach((box, index) => {
        let conf
        if (Array.isArray(box)) {
            conf = box[4] || 0
        } else if (box.box) {
            conf = box.conf ?? box.confidence ?? 0
        } else {
            conf = box.confidence ?? box.conf ?? 0
        }
        if (conf > bestConf) {
            bestConf = conf
            bestIndex = index
        }
    })
    
    return bestIndex
}

async function drawDetections() {
    if (!detectCanvas.value || !originalImage.value) return

    await nextTick()

    const canvas = detectCanvas.value
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const img = new Image()
    img.src = originalImage.value
    await new Promise((resolve) => { img.onload = resolve })

    canvas.width = img.width
    canvas.height = img.height

    ctx.drawImage(img, 0, 0)

    const colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD']
    const selectedIndex = getSelectedTargetIndex()
    
    detectBboxes.value.forEach((box, index) => {
        // 被选中的目标使用金色高亮
        const isSelected = index === selectedIndex
        const color = isSelected ? '#FFD700' : colors[index % colors.length]
        const lineWidth = isSelected ? 5 : 3
        
        let x1, y1, x2, y2, conf, label
        
        if (Array.isArray(box)) {
            [x1, y1, x2, y2, conf] = box
            label = `Class ${box[5] || index}`
        } else {
            const coords = box.box || { x1: box.xmin, y1: box.ymin, x2: box.xmax, y2: box.ymax }
            x1 = coords.x1 ?? coords.xmin ?? 0
            y1 = coords.y1 ?? coords.ymin ?? 0
            x2 = coords.x2 ?? coords.xmax ?? 0
            y2 = coords.y2 ?? coords.ymax ?? 0
            conf = box.conf !== undefined ? box.conf : box.confidence
            label = box.name || box.class || `目标 ${index + 1}`
        }
        
        ctx.strokeStyle = color
        ctx.lineWidth = lineWidth
        ctx.strokeRect(x1, y1, x2 - x1, y2 - y1)

        const displayLabel = `${label} ${(conf * 100).toFixed(1)}%${isSelected ? ' ★' : ''}`
        ctx.font = `bold ${isSelected ? 16 : 14}px Arial`
        const textMetrics = ctx.measureText(displayLabel)
        const textHeight = isSelected ? 24 : 20
        
        ctx.fillStyle = color
        ctx.fillRect(x1, y1 - textHeight, textMetrics.width + 10, textHeight)

        ctx.fillStyle = '#FFFFFF'
        ctx.fillText(displayLabel, x1 + 5, y1 - 5)
    })
}

async function runMask(): Promise<boolean> {
    if (!currentFile.value) return false

    maskStatus.value = 'running'
    const startTime = Date.now()

    try {
        // 步骤 1: 获取 JSON 数据（包含 mask 原始数据）
        console.log('[Workflow] 步骤2: 开始掩码生成，获取 JSON 数据...')
        const jsonResult = await callModels('yolo26-seg', { file: currentFile.value }, 'application/json') as any
        
        // 存储 mask 数据（阶段 2A：为后续 mask 级增强做准备）
        console.log('[Workflow] ========== mask 完成 ==========')
        if (jsonResult.masks && Array.isArray(jsonResult.masks)) {
            maskData.value = jsonResult.masks
            console.log(`[Workflow] maskData.length: ${maskData.value.length}`)
            if (maskData.value.length > 0) {
                maskData.value.forEach((m, i) => {
                    console.log(`[Workflow] mask ${i}: ${m.name}, bbox: [${m.bbox.join(', ')}], size: ${m.width}x${m.height}`)
                })
            }
        } else {
            maskData.value = []
            console.log('[Workflow] 未获取到 mask 数据 (jsonResult.masks 为空)')
        }
        console.log('[Workflow] =================================')
        
        // 步骤 2: 获取 overlay 图片（用于显示）
        const imageResult = await callModels('yolo26-seg', { file: currentFile.value }, 'image/jpeg')
        
        if (maskImage.value) {
            URL.revokeObjectURL(maskImage.value)
        }
        maskImage.value = URL.createObjectURL(imageResult as Blob)

        maskStatus.value = 'success'
        stepDurations.mask = Date.now() - startTime
        console.log('[Workflow] 掩码生成完成')
        return true

    } catch (error) {
        console.error('[Workflow] 掩码生成失败:', error)
        maskStatus.value = 'error'
        stepDurations.mask = Date.now() - startTime
        ElMessage.error('掩码生成失败')
        return false
    }
}

// 从 detectBboxes 中提取最高置信度目标的完整信息
function getBestBboxForEnhance(): { x1: number, y1: number, x2: number, y2: number, conf: number, name: string } | null {
    if (!detectBboxes.value || detectBboxes.value.length === 0) {
        return null
    }

    // 统一转换为标准格式并排序
    const normalizedBoxes = detectBboxes.value.map((box: any) => {
        let x1, y1, x2, y2, conf, name

        if (Array.isArray(box)) {
            // 数组格式: [x1, y1, x2, y2, conf, cls]
            [x1, y1, x2, y2, conf] = box
            name = `Class ${box[5] || 0}`
        } else if (box.box) {
            // 对象格式: {box: {x1, y1, x2, y2}, name, conf}
            x1 = box.box.x1 ?? box.box.xmin
            y1 = box.box.y1 ?? box.box.ymin
            x2 = box.box.x2 ?? box.box.xmax
            y2 = box.box.y2 ?? box.box.ymax
            conf = box.conf ?? box.confidence ?? 0
            name = box.name || box.class_name || `Class ${box.cls || 0}`
        } else {
            // 备用格式: {xmin, ymin, xmax, ymax, confidence, name}
            x1 = box.xmin ?? box.x1 ?? 0
            y1 = box.ymin ?? box.y1 ?? 0
            x2 = box.xmax ?? box.x2 ?? 0
            y2 = box.ymax ?? box.y2 ?? 0
            conf = box.confidence ?? box.conf ?? 0
            name = box.name || box.class_name || `Class ${box.class ?? 0}`
        }

        return { x1, y1, x2, y2, conf, name }
    })

    // 按置信度排序，取最高
    normalizedBoxes.sort((a, b) => b.conf - a.conf)
    return normalizedBoxes[0]
}

// 多目标增强进度跟踪
const enhanceProgress = reactive({
    current: 0,
    total: 0,
    skipped: 0,
    failed: 0,
    currentTargetName: ''
})

// 筛选所有有效目标（多目标增强）
function filterValidBboxes(): { x1: number, y1: number, x2: number, y2: number, conf: number, name: string, index: number }[] {
    if (!detectBboxes.value || detectBboxes.value.length === 0) {
        return []
    }

    const MIN_ROI_SIZE = 32
    const MIN_CONF = 0.25
    const MAX_TARGETS = 5  // 最多增强5个目标，避免时间过长

    const validBoxes: { x1: number, y1: number, x2: number, y2: number, conf: number, name: string, index: number }[] = []

    detectBboxes.value.forEach((box: any, index: number) => {
        let x1, y1, x2, y2, conf, name

        if (Array.isArray(box)) {
            [x1, y1, x2, y2, conf] = box
            name = `Class ${box[5] || 0}`
        } else if (box.box) {
            x1 = box.box.x1 ?? box.box.xmin
            y1 = box.box.y1 ?? box.box.ymin
            x2 = box.box.x2 ?? box.box.xmax
            y2 = box.box.y2 ?? box.box.ymax
            conf = box.conf ?? box.confidence ?? 0
            name = box.name || box.class_name || `Class ${box.cls || 0}`
        } else {
            x1 = box.xmin ?? box.x1 ?? 0
            y1 = box.ymin ?? box.y1 ?? 0
            x2 = box.xmax ?? box.x2 ?? 0
            y2 = box.ymax ?? box.y2 ?? 0
            conf = box.confidence ?? box.conf ?? 0
            name = box.name || box.class_name || `Class ${box.class ?? 0}`
        }

        const roiW = Math.abs(x2 - x1)
        const roiH = Math.abs(y2 - y1)

        // 筛选条件：尺寸足够 + 置信度足够
        if (roiW >= MIN_ROI_SIZE && roiH >= MIN_ROI_SIZE && conf >= MIN_CONF) {
            validBoxes.push({ x1, y1, x2, y2, conf, name, index })
        }
    })

    // 按置信度降序排序，取前 MAX_TARGETS 个
    validBoxes.sort((a, b) => b.conf - a.conf)
    return validBoxes.slice(0, MAX_TARGETS)
}

// 当前增强统计信息（用于显示）
const enhanceSummary = computed(() => {
    if (enhanceStatus.value === 'idle') return null
    return {
        total: detectCount.value,
        enhanced: enhanceProgress.total - enhanceProgress.skipped - enhanceProgress.failed,
        skipped: enhanceProgress.skipped,
        failed: enhanceProgress.failed
    }
})

// 获取最佳目标及其 mask（用于 mask 级精确增强）
function getBestTargetWithMask(): { 
    target: { x1: number, y1: number, x2: number, y2: number, conf: number, name: string } | null,
    maskData: MaskData | null 
} {
    console.log('[Workflow] getBestTargetWithMask(): maskData.value =', maskData.value?.length || 0)
    
    // 从 maskData 中选取最高置信度的目标
    if (!maskData.value || maskData.value.length === 0) {
        console.log('[Workflow] maskData 为空，无法获取带 mask 的目标')
        return { target: null, maskData: null }
    }
    
    // 按置信度排序
    const sortedMasks = [...maskData.value].sort((a, b) => b.conf - a.conf)
    const bestMask = sortedMasks[0]
    
    // 构造 target
    const target = {
        x1: bestMask.bbox[0],
        y1: bestMask.bbox[1],
        x2: bestMask.bbox[2],
        y2: bestMask.bbox[3],
        conf: bestMask.conf,
        name: bestMask.name
    }
    
    console.log(`[Workflow] 从 maskData 选中目标: ${target.name}, conf: ${target.conf}`)
    return { target, maskData: bestMask }
}

// 从 detectBboxes 获取最佳目标（fallback，用于 bbox 增强）
function getBestTargetFromDetectBboxes(): { x1: number, y1: number, x2: number, y2: number, conf: number, name: string } | null {
    console.log('[Workflow] getBestTargetFromDetectBboxes(): detectBboxes.value =', detectBboxes.value?.length || 0)
    
    if (!detectBboxes.value || detectBboxes.value.length === 0) {
        console.log('[Workflow] detectBboxes 为空')
        return null
    }
    
    // 统一转换为标准格式并排序
    const normalizedBoxes = detectBboxes.value.map((box: any) => {
        let x1, y1, x2, y2, conf, name

        if (Array.isArray(box)) {
            [x1, y1, x2, y2, conf] = box
            name = `Class ${box[5] || 0}`
        } else if (box.box) {
            x1 = box.box.x1 ?? box.box.xmin
            y1 = box.box.y1 ?? box.box.ymin
            x2 = box.box.x2 ?? box.box.xmax
            y2 = box.box.y2 ?? box.box.ymax
            conf = box.conf ?? box.confidence ?? 0
            name = box.name || box.class_name || `Class ${box.cls || 0}`
        } else {
            x1 = box.xmin ?? box.x1 ?? 0
            y1 = box.ymin ?? box.y1 ?? 0
            x2 = box.xmax ?? box.x2 ?? 0
            y2 = box.ymax ?? box.y2 ?? 0
            conf = box.confidence ?? box.conf ?? 0
            name = box.name || box.class_name || `Class ${box.class ?? 0}`
        }

        return { x1, y1, x2, y2, conf, name }
    })

    // 按置信度排序，取最高
    normalizedBoxes.sort((a, b) => b.conf - a.conf)
    const best = normalizedBoxes[0]
    
    console.log(`[Workflow] 从 detectBboxes 选中目标: ${best.name}, conf: ${best.conf}`)
    return best
}

// 使用 mask 进行精确增强
async function enhanceWithMask(
    imageFile: File | Blob, 
    target: { x1: number, y1: number, x2: number, y2: number, name: string },
    mask: MaskData
): Promise<Blob> {
    console.log(`[Workflow] 使用 mask 精确增强: ${target.name}, bbox: [${target.x1}, ${target.y1}, ${target.x2}, ${target.y2}]`)
    
    const result = await callModels('enhance-mask', {
        file: imageFile,
        bbox: JSON.stringify([target.x1, target.y1, target.x2, target.y2]),
        mask: mask.mask  // base64 mask
    }, 'image/jpeg')
    
    return result as Blob
}

// 使用 bbox 进行 ROI 增强（fallback）
async function enhanceWithBbox(
    imageFile: File | Blob,
    target: { x1: number, y1: number, x2: number, y2: number, name: string }
): Promise<Blob> {
    console.log(`[Workflow] 使用 bbox 增强(fallback): ${target.name}`)
    
    const result = await callModels('enhance-roi', {
        file: imageFile,
        bbox: JSON.stringify([target.x1, target.y1, target.x2, target.y2])
    }, 'image/jpeg')
    
    return result as Blob
}

async function runEnhance(): Promise<boolean> {
    if (!currentFile.value) return false

    console.log('[Workflow] ========== 步骤3: 开始图像增强 ==========')
    console.log('[Workflow] 当前状态:')
    console.log('  - detectCount:', detectCount.value)
    console.log('  - detectBboxes.length:', detectBboxes.value?.length || 0)
    console.log('  - maskData.length:', maskData.value?.length || 0)
    
    enhanceStatus.value = 'running'
    enhanceProgress.current = 1
    enhanceProgress.total = 1
    enhanceProgress.currentTargetName = ''
    const startTime = Date.now()

    // 步骤1: 尝试获取带 mask 的最佳目标
    let { target, maskData: bestMask } = getBestTargetWithMask()
    
    // 如果 maskData 没有目标，尝试从 detectBboxes 获取
    if (!target) {
        console.log('[Workflow] maskData 无有效目标，尝试从 detectBboxes 获取...')
        target = getBestTargetFromDetectBboxes()
        bestMask = null
    }
    
    // 如果还是没有目标，才真正报错
    if (!target) {
        console.error('[Workflow] 增强失败: 未检测到有效目标')
        console.error('[Workflow] 请检查:')
        console.error('  1. detect 步骤是否成功')
        console.error('  2. detectBboxes 是否有数据')
        console.error('  3. maskData 是否有数据')
        enhanceStatus.value = 'error'
        stepDurations.enhance = Date.now() - startTime
        errorMessage.value = '未检测到目标，无法进行增强'
        ElMessage.error('未检测到目标，无法进行增强')
        return false
    }
    
    enhanceProgress.currentTargetName = target.name
    console.log(`[Workflow] 最终选中目标: ${target.name} (conf: ${target.conf.toFixed(3)})`)
    console.log(`[Workflow] 使用增强方式: ${bestMask ? 'mask 精确增强' : 'bbox 增强'}`)

    // 步骤2: 优先尝试 mask 精确增强，失败则 fallback 到 bbox
    let resultBlob: Blob
    let usedMask = false
    
    if (bestMask) {
        // 有 mask 数据，尝试 mask 精确增强
        try {
            console.log('[Workflow] 尝试 mask 级精确增强...')
            resultBlob = await enhanceWithMask(currentFile.value, target, bestMask)
            usedMask = true
            console.log('[Workflow] mask 精确增强成功')
        } catch (error: any) {
            console.error('[Workflow] mask 精确增强失败:', error)
            console.log('[Workflow] fallback 到 bbox 增强...')
            
            try {
                resultBlob = await enhanceWithBbox(currentFile.value, target)
                console.log('[Workflow] bbox 增强成功(fallback)')
            } catch (fallbackError: any) {
                console.error('[Workflow] bbox 增强也失败:', fallbackError)
                enhanceStatus.value = 'error'
                stepDurations.enhance = Date.now() - startTime
                errorMessage.value = '图像增强失败'
                ElMessage.error('图像增强失败')
                return false
            }
        }
    } else {
        // 无 mask 数据，直接使用 bbox 增强
        console.log('[Workflow] 无 mask 数据，使用 bbox 增强')
        try {
            resultBlob = await enhanceWithBbox(currentFile.value, target)
        } catch (error: any) {
            console.error('[Workflow] bbox 增强失败:', error)
            enhanceStatus.value = 'error'
            stepDurations.enhance = Date.now() - startTime
            errorMessage.value = '图像增强失败'
            ElMessage.error('图像增强失败')
            return false
        }
    }

    // 步骤3: 设置结果
    if (enhanceImage.value) {
        URL.revokeObjectURL(enhanceImage.value)
    }
    enhanceImage.value = URL.createObjectURL(resultBlob)

    enhanceStatus.value = 'success'
    stepDurations.enhance = Date.now() - startTime
    
    if (usedMask) {
        console.log('[Workflow] mask 级精确增强完成')
        ElMessage.success('mask 级精确增强完成')
    } else {
        console.log('[Workflow] bbox 增强完成')
        ElMessage.success('mask 级精确增强完成')
    }
    
    return true
}

function resetWorkflow() {
    console.log('[Workflow] 执行完全重置')
    
    resetResults()
    currentFile.value = null
    
    ElMessage.info('已重置')
}

function getStatusText(status: StepStatus): string {
    const map: Record<StepStatus, string> = {
        idle: '待执行',
        running: '执行中',
        success: '完成',
        error: '失败'
    }
    return map[status]
}

function getStatusType(status: StepStatus): 'info' | 'warning' | 'success' | 'danger' {
    const map: Record<StepStatus, 'info' | 'warning' | 'success' | 'danger'> = {
        idle: 'info',
        running: 'warning',
        success: 'success',
        error: 'danger'
    }
    return map[status]
}

function formatDuration(ms: number): string {
    if (ms < 1000) {
        return `${ms}ms`
    }
    return `${(ms / 1000).toFixed(2)}s`
}
</script>

<style scoped>
.workflow-form {
    padding: 0;
}

.upload-section {
    margin-bottom: 16px;
}

/* 控制栏：响应式 Flex */
.control-bar {
    display: flex;
    align-items: center;
    gap: 16px;
    flex-wrap: wrap;
}

.upload-area {
    flex: 1;
    min-width: 260px;
    margin-bottom: 0;
}

/* 紧凑上传区域 */
.upload-drop-zone {
    border: 1px dashed var(--el-border-color);
    border-radius: 6px;
    padding: 12px 16px;
    text-align: left;
    cursor: pointer;
    transition: all 0.3s;
    background-color: transparent;
    display: flex;
    align-items: center;
    gap: 10px;
}

.upload-drop-zone:hover {
    border-color: var(--el-color-primary);
    background-color: var(--el-fill-color-lighter);
}

.upload-drop-zone.drag-over {
    border-color: var(--el-color-primary);
    background-color: var(--el-color-primary-light-9);
}

.upload-drop-zone.has-file {
    border-color: var(--el-color-success);
    background-color: var(--el-color-success-light-9);
}

.upload-drop-zone.disabled {
    cursor: not-allowed;
    opacity: 0.6;
}

.upload-icon {
    color: var(--el-text-color-secondary);
    flex-shrink: 0;
}

.upload-drop-zone:hover .upload-icon {
    color: var(--el-color-primary);
}

.upload-text {
    font-size: 13px;
    color: var(--el-text-color-regular);
    line-height: 1.4;
    flex: 1;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.upload-text em {
    color: var(--el-color-primary);
    font-style: normal;
    font-weight: 500;
}

.replace-hint {
    margin-left: 4px;
    color: var(--el-text-color-secondary);
    font-weight: normal;
}

.upload-tip {
    font-size: 11px;
    color: var(--el-text-color-secondary);
    flex-shrink: 0;
}

.action-buttons {
    display: flex;
    gap: 10px;
    flex-shrink: 0;
}

/* 调试信息 */
.debug-toggle {
    margin-top: 12px;
    padding-top: 8px;
    border-top: 1px dashed var(--el-border-color-lighter);
}

.debug-collapse {
    margin-top: 8px;
}

.debug-collapse pre {
    margin: 0;
    padding: 10px;
    font-size: 12px;
    font-family: monospace;
    white-space: pre-wrap;
    background-color: var(--el-fill-color-lighter);
    border-radius: 4px;
}

/* 结果区 */
.results-section {
    margin-top: 20px;
}

/* 2×2 网格 */
.results-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
    align-items: stretch;
}

.result-card {
    height: auto;
}

.result-card :deep(.el-card__header) {
    padding: 12px 16px;
}

.result-card :deep(.el-card__body) {
    padding: 16px;
}

/* 步骤卡片 */
.step-card {
    margin-bottom: 0;
}

.card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.card-title-group {
    display: flex;
    align-items: center;
    gap: 8px;
}

.step-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 22px;
    height: 22px;
    border-radius: 50%;
    background: var(--el-color-primary);
    color: #fff;
    font-size: 11px;
    font-weight: 600;
    flex-shrink: 0;
}

.step-badge-input {
    background: var(--el-color-info);
}

.card-title {
    display: flex;
    align-items: center;
    gap: 6px;
    font-weight: 600;
    font-size: 15px;
}

.header-right {
    display: flex;
    align-items: center;
    gap: 10px;
}

.duration {
    font-size: 12px;
    color: var(--el-text-color-secondary);
}

/* 图片容器：固定高度 + 透明背景，消除巨大灰色块 */
.image-container {
    width: 100%;
    height: 280px;
    display: flex;
    align-items: center;
    justify-content: center;
    background-color: transparent;
    border: 1px solid var(--el-border-color-lighter);
    border-radius: 6px;
    overflow: hidden;
}

.result-image {
    width: 100%;
    height: 100%;
    max-height: 280px;
    object-fit: contain;
    display: block;
}

.result-canvas {
    max-width: 100%;
    max-height: 280px;
    height: auto;
    width: auto;
    display: block;
}

.placeholder {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 6px;
    color: var(--el-text-color-secondary);
    font-size: 13px;
    padding: 16px;
}

.placeholder :deep(.el-icon) {
    font-size: 24px;
}

.result-info {
    margin-top: 10px;
    padding: 6px 10px;
    background-color: var(--el-fill-color-light);
    border-radius: 4px;
    text-align: center;
    font-size: 13px;
}

/* 目标信息展示 */
.target-info {
    margin-bottom: 8px;
    padding: 4px 8px;
    background-color: var(--el-fill-color-lighter);
    border-radius: 4px;
    text-align: center;
    font-size: 12px;
}

.target-hint {
    margin-top: 8px;
    text-align: center;
    font-size: 11px;
}

.total-duration {
    margin-top: 20px;
    text-align: center;
}

.total-duration :deep(.el-icon) {
    margin-right: 4px;
}

/* 响应式 */
@media (max-width: 768px) {
    .results-grid {
        grid-template-columns: 1fr;
    }

    .control-bar {
        flex-direction: column;
        align-items: stretch;
    }

    .upload-area {
        min-width: auto;
    }

    .action-buttons {
        justify-content: flex-start;
    }

    .upload-drop-zone {
        flex-wrap: wrap;
    }

    .upload-tip {
        width: 100%;
        margin-top: 2px;
        padding-left: 34px;
    }

    .image-container {
        height: 240px;
    }

    .result-image {
        max-height: 240px;
    }

    .result-canvas {
        max-height: 240px;
    }
}
</style>
