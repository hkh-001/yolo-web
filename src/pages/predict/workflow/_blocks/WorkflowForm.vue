<template>
    <div class="workflow-container">
        <!-- 页面头部 -->
        <div class="page-header">
            <div class="header-main">
                <div class="header-icon workflow-icon">
                    <div class="icon-layer layer-1"></div>
                    <div class="icon-layer layer-2"></div>
                    <div class="icon-layer layer-3"></div>
                    <div class="icon-nodes">
                        <span class="node node-1"></span>
                        <span class="node node-2"></span>
                        <span class="node node-3"></span>
                    </div>
                    <el-icon :size="22" class="main-icon"><Cpu /></el-icon>
                </div>
                <div class="header-content">
                    <h1 class="page-title">智能流程</h1>
                    <p class="page-subtitle">图像识别 → 掩码生成 → 图像增强 一站式处理</p>
                </div>
            </div>
        </div>

        <!-- 顶部流程控制区 -->
        <div class="panel-card control-card">
            <div class="card-header centered-header">
                <div class="card-title-group centered-title">
                    <el-icon class="subtitle-icon" :size="16"><UploadFilled /></el-icon>
                    <span class="card-title">流程控制</span>
                </div>
            </div>
            <div class="card-body">
                <!-- 流程输入区 -->
                <div class="workflow-input-section">
                    <div class="section-subtitle tag-style-subtitle">
                        <div class="subtitle-badge">
                            <el-icon class="subtitle-icon" :size="14"><UploadFilled /></el-icon>
                            <span class="subtitle-text">流程输入</span>
                        </div>
                    </div>
                    <div class="upload-wrapper" @click="debugUploadAreaClick">
                        <input
                            ref="fileInputRef"
                            type="file"
                            accept="image/*"
                            class="native-file-input"
                            @change="onFileSelected"
                            @click="debugInputClick"
                        />
                        <div 
                            class="upload-drop-zone workflow-upload-zone"
                            :class="{ 'has-file': originalImage, 'disabled': isRunning, 'has-preview': originalImage }"
                            @click="triggerFileSelect"
                            @dragover.prevent="onDragOver"
                            @dragleave.prevent="onDragLeave"
                            @drop.prevent="onFileDrop"
                        >
                            <!-- 未上传状态 -->
                            <div v-if="!originalImage" class="upload-content upload-empty-state">
                                <div class="upload-icon-ring">
                                    <div class="upload-icon-bg">
                                        <el-icon class="upload-main-icon" :size="28">
                                            <upload-filled />
                                        </el-icon>
                                    </div>
                                </div>
                                <div class="upload-main-text">
                                    <span class="upload-primary-text">
                                        <span class="workflow-start-hint">流程起点</span>
                                        <span class="upload-action">拖拽图片到此处或 <span class="highlight">点击上传</span></span>
                                    </span>
                                </div>
                                <div class="upload-formats">
                                    <span class="format-label">支持格式</span>
                                    <div class="format-tags">
                                        <el-tag size="small" effect="dark" class="format-tag">JPG</el-tag>
                                        <el-tag size="small" effect="dark" class="format-tag">PNG</el-tag>
                                        <el-tag size="small" effect="dark" class="format-tag">WEBP</el-tag>
                                    </div>
                                </div>
                            </div>
                            
                            <!-- 已上传状态：显示原图预览 -->
                            <div v-else class="upload-preview-state">
                                <div class="preview-image-wrapper">
                                    <img :src="originalImage" alt="已选择的原图" class="preview-image" />
                                </div>
                                <div class="preview-overlay">
                                    <div class="preview-info">
                                        <el-icon :size="16"><DocumentChecked /></el-icon>
                                        <span class="preview-filename">{{ currentFile?.name }}</span>
                                    </div>
                                    <span class="preview-hint">点击或拖拽可更换图片</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- 流程执行区 -->
                <div class="workflow-action-section">
                    <div class="section-subtitle tag-style-subtitle">
                        <div class="subtitle-badge">
                            <el-icon class="subtitle-icon" :size="14"><VideoPlay /></el-icon>
                            <span class="subtitle-text">流程执行</span>
                        </div>
                    </div>
                    <div class="action-buttons">
                        <el-button
                            type="primary"
                            size="large"
                            :disabled="!canStart"
                            :loading="isRunning"
                            @click="startWorkflow"
                            class="action-btn submit-btn"
                        >
                            <el-icon :size="18"><video-play /></el-icon>
                            <span>{{ isRunning ? '执行中...' : '开始智能流程' }}</span>
                        </el-button>
                        <el-button
                            size="large"
                            :disabled="isRunning || (!originalImage && !hasAnyResult)"
                            @click="resetWorkflow"
                            class="action-btn clear-btn"
                        >
                            <el-icon :size="16"><refresh /></el-icon>
                            <span>重置流程</span>
                        </el-button>
                    </div>
                </div>

                <!-- 调试工具区 -->
                <div class="workflow-debug-section">
                    <div class="debug-header" @click="showDebug = !showDebug">
                        <div class="debug-title">
                            <el-icon :size="16"><InfoFilled /></el-icon>
                            <span>调试工具</span>
                        </div>
                        <el-icon class="debug-toggle-icon" :class="{ 'is-active': showDebug }">
                            <ArrowDown v-if="showDebug" />
                            <ArrowRight v-else />
                        </el-icon>
                    </div>
                    <el-collapse-transition>
                        <div v-show="showDebug" class="debug-content">
                            <div class="debug-info-grid">
                                <div class="debug-item">
                                    <span class="debug-label">图片状态</span>
                                    <el-tag size="small" :type="originalImage ? 'success' : 'info'">{{ originalImage ? '已上传' : '未上传' }}</el-tag>
                                </div>
                                <div class="debug-item">
                                    <span class="debug-label">流程状态</span>
                                    <el-tag size="small" :type="isRunning ? 'primary' : workflowStatus === 'completed' ? 'success' : workflowStatus === 'error' ? 'danger' : 'info'">{{ getWorkflowStatusTitle() }}</el-tag>
                                </div>
                                <div class="debug-item">
                                    <span class="debug-label">当前步骤</span>
                                    <el-tag size="small">{{ currentStep > 0 ? '第 ' + currentStep + ' 步' : '未开始' }}</el-tag>
                                </div>
                                <div class="debug-item">
                                    <span class="debug-label">执行条件</span>
                                    <el-tag size="small" :type="canStart ? 'success' : 'warning'">{{ canStart ? '满足' : '不满足' }}</el-tag>
                                </div>
                                <div class="debug-item" v-if="currentFile">
                                    <span class="debug-label">当前文件:</span>
                                    <span class="debug-value">{{ currentFile?.name }}</span>
                                </div>
                            </div>
                        </div>
                    </el-collapse-transition>
                </div>
            </div>
        </div>

        <!-- 工作流结果区：2×2 网格 -->
        <div v-if="originalImage" class="results-section">
            <!-- Workflow 状态总览卡片 -->
            <div class="panel-card workflow-summary-card" :class="{ 'is-running': isRunning, 'is-completed': workflowStatus === 'completed', 'is-error': workflowStatus === 'error' }">
                <div class="summary-main">
                    <div class="summary-status">
                        <div class="status-icon-wrapper" :class="workflowStatus">
                            <el-icon v-if="workflowStatus === 'idle'" :size="24"><Timer /></el-icon>
                            <el-icon v-else-if="workflowStatus === 'running'" :size="24" class="is-loading"><Loading /></el-icon>
                            <el-icon v-else-if="workflowStatus === 'completed'" :size="24"><CircleCheck /></el-icon>
                            <el-icon v-else-if="workflowStatus === 'error'" :size="24"><Warning /></el-icon>
                        </div>
                        <div class="status-info">
                            <div class="status-title">{{ getWorkflowStatusTitle() }}</div>
                            <div class="status-desc">{{ getWorkflowStatusDesc() }}</div>
                        </div>
                    </div>
                    <div v-if="totalDuration > 0" class="summary-duration">
                        <div class="duration-value">{{ formatDuration(totalDuration) }}</div>
                        <div class="duration-label">总耗时</div>
                    </div>
                </div>
                <!-- 步骤进度条 -->
                <div class="summary-progress">
                    <div class="progress-steps">
                        <div class="progress-step" :class="{ active: originalImage, completed: originalImage }">
                            <div class="step-dot"></div>
                            <span class="step-label">原图</span>
                        </div>
                        <div class="progress-line" :class="{ completed: detectStatus === 'success' || detectStatus === 'error' }"></div>
                        <div class="progress-step" :class="{ active: detectStatus !== 'idle', completed: detectStatus === 'success', error: detectStatus === 'error' }">
                            <div class="step-dot"></div>
                            <span class="step-label">识别</span>
                        </div>
                        <div class="progress-line" :class="{ completed: maskStatus === 'success' || maskStatus === 'error' }"></div>
                        <div class="progress-step" :class="{ active: maskStatus !== 'idle', completed: maskStatus === 'success', error: maskStatus === 'error' }">
                            <div class="step-dot"></div>
                            <span class="step-label">掩码</span>
                        </div>
                        <div class="progress-line" :class="{ completed: enhanceStatus === 'success' || enhanceStatus === 'error' }"></div>
                        <div class="progress-step" :class="{ active: enhanceStatus !== 'idle', completed: enhanceStatus === 'success', error: enhanceStatus === 'error' }">
                            <div class="step-dot"></div>
                            <span class="step-label">增强</span>
                        </div>
                    </div>
                </div>
                <!-- 步骤统计 -->
                <div class="summary-stats">
                    <div class="stat-item">
                        <span class="stat-value success">{{ [detectStatus, maskStatus, enhanceStatus].filter(s => s === 'success').length }}</span>
                        <span class="stat-label">完成</span>
                    </div>
                    <div class="stat-divider"></div>
                    <div class="stat-item">
                        <span class="stat-value">{{ [detectStatus, maskStatus, enhanceStatus].filter(s => s === 'running').length }}</span>
                        <span class="stat-label">执行中</span>
                    </div>
                    <div class="stat-divider"></div>
                    <div class="stat-item">
                        <span class="stat-value" :class="{ error: [detectStatus, maskStatus, enhanceStatus].some(s => s === 'error') }">{{ [detectStatus, maskStatus, enhanceStatus].filter(s => s === 'error').length }}</span>
                        <span class="stat-label">失败</span>
                    </div>
                    <div class="stat-divider"></div>
                    <div class="stat-item">
                        <span class="stat-value">{{ [detectStatus, maskStatus, enhanceStatus].filter(s => s === 'idle').length }}</span>
                        <span class="stat-label">待执行</span>
                    </div>
                </div>
            </div>

            <!-- 步骤卡片网格 -->
            <div class="step-cards-header">
                <div class="section-title">
                    <el-icon :size="18"><Grid /></el-icon>
                    <span>流程执行结果</span>
                </div>
                <div class="step-flow-hint">
                    <el-icon :size="14"><ArrowRight /></el-icon>
                    <span>顺序执行</span>
                </div>
            </div>
            <div class="results-grid">
                <!-- Step 1: 原图 -->
                <div class="panel-card step-panel-card">
                    <div class="step-card-header">
                        <div class="step-header-main">
                            <div class="step-badge-wrapper">
                                <span class="step-number step-number-input">01</span>
                            </div>
                            <div class="step-info">
                                <div class="step-name">
                                    <el-icon :size="16"><Picture /></el-icon>
                                    <span>原图</span>
                                </div>
                                <div class="step-desc">流程起点</div>
                            </div>
                        </div>
                        <el-tag type="info" size="small" effect="dark" class="step-status-tag">原始输入</el-tag>
                    </div>
                    <div class="step-card-body">
                        <div class="result-display-box">
                            <img :src="originalImage" alt="原图" class="result-media" />
                        </div>
                    </div>
                </div>

                <!-- Step 2: 图像识别 -->
                <div class="panel-card step-panel-card" :class="{ 'step-active': detectStatus === 'running' }">
                    <div class="step-card-header">
                        <div class="step-header-main">
                            <div class="step-badge-wrapper">
                                <span class="step-number" :class="{ 'step-running': detectStatus === 'running', 'step-success': detectStatus === 'success', 'step-error': detectStatus === 'error' }">02</span>
                                <div v-if="detectStatus === 'running'" class="step-spinner"></div>
                            </div>
                            <div class="step-info">
                                <div class="step-name">
                                    <el-icon :size="16"><Aim /></el-icon>
                                    <span>图像识别</span>
                                </div>
                                <div class="step-meta">
                                    <el-tag :type="getStatusType(detectStatus)" size="small" effect="dark" class="step-status-tag">
                                        {{ getStatusText(detectStatus) }}
                                    </el-tag>
                                    <span v-if="stepDurations.detect > 0" class="step-duration">
                                        {{ formatDuration(stepDurations.detect) }}
                                    </span>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="step-card-body">
                        <div class="result-display-box">
                            <canvas
                                v-if="detectStatus !== 'idle'"
                                ref="detectCanvas"
                                class="result-media"
                            ></canvas>
                            <div v-else class="step-placeholder">
                                <div class="placeholder-icon-wrapper">
                                    <el-icon :size="36"><Aim /></el-icon>
                                </div>
                                <span class="placeholder-text">待执行</span>
                                <span class="placeholder-desc">将对上传图片进行目标检测</span>
                            </div>
                        </div>
                        <div v-if="detectStatus === 'success'" class="step-result-info success">
                            <el-icon :size="16"><CircleCheck /></el-icon>
                            <span>检测完成，共 <strong>{{ detectCount }}</strong> 个目标</span>
                        </div>
                        <div v-if="detectStatus === 'error'" class="step-result-info error">
                            <el-icon :size="16"><Warning /></el-icon>
                            <span>检测失败：{{ errorMessage || '未知错误' }}</span>
                        </div>
                    </div>
                </div>

                <!-- Step 3: 掩码生成 -->
                <div class="panel-card step-panel-card" :class="{ 'step-active': maskStatus === 'running' }">
                    <div class="step-card-header">
                        <div class="step-header-main">
                            <div class="step-badge-wrapper">
                                <span class="step-number" :class="{ 'step-running': maskStatus === 'running', 'step-success': maskStatus === 'success', 'step-error': maskStatus === 'error' }">03</span>
                                <div v-if="maskStatus === 'running'" class="step-spinner"></div>
                            </div>
                            <div class="step-info">
                                <div class="step-name">
                                    <el-icon :size="16"><CopyDocument /></el-icon>
                                    <span>掩码生成</span>
                                </div>
                                <div class="step-meta">
                                    <el-tag :type="getStatusType(maskStatus)" size="small" effect="dark" class="step-status-tag">
                                        {{ getStatusText(maskStatus) }}
                                    </el-tag>
                                    <span v-if="stepDurations.mask > 0" class="step-duration">
                                        {{ formatDuration(stepDurations.mask) }}
                                    </span>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="step-card-body">
                        <div class="result-display-box">
                            <img
                                v-if="maskImage"
                                :src="maskImage"
                                alt="掩码结果"
                                class="result-media"
                            />
                            <div v-else class="step-placeholder">
                                <div class="placeholder-icon-wrapper">
                                    <el-icon :size="36"><CopyDocument /></el-icon>
                                </div>
                                <span class="placeholder-text">{{ maskStatus === 'running' ? '生成中...' : '待执行' }}</span>
                                <span class="placeholder-desc">基于检测结果生成实例掩码</span>
                            </div>
                        </div>
                        <div v-if="maskStatus === 'error' && detectStatus === 'success'" class="step-result-info error">
                            <el-icon :size="16"><Warning /></el-icon>
                            <span>掩码生成失败</span>
                        </div>
                    </div>
                </div>

                <!-- Step 4: 图像增强 -->
                <div class="panel-card step-panel-card" :class="{ 'step-active': enhanceStatus === 'running' }">
                    <div class="step-card-header">
                        <div class="step-header-main">
                            <div class="step-badge-wrapper">
                                <span class="step-number" :class="{ 'step-running': enhanceStatus === 'running', 'step-success': enhanceStatus === 'success', 'step-error': enhanceStatus === 'error' }">04</span>
                                <div v-if="enhanceStatus === 'running'" class="step-spinner"></div>
                            </div>
                            <div class="step-info">
                                <div class="step-name">
                                    <el-icon :size="16"><MagicStick /></el-icon>
                                    <span>图像增强</span>
                                </div>
                                <div class="step-meta">
                                    <el-tag :type="getStatusType(enhanceStatus)" size="small" effect="dark" class="step-status-tag">
                                        {{ getStatusText(enhanceStatus) }}
                                    </el-tag>
                                    <span v-if="stepDurations.enhance > 0" class="step-duration">
                                        {{ formatDuration(stepDurations.enhance) }}
                                    </span>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="step-card-body">
                        <!-- 增强进度提示 -->
                        <div v-if="enhanceStatus === 'running' && enhanceProgress.currentTargetName" class="step-progress-info">
                            <el-icon :size="16" class="is-loading"><Loading /></el-icon>
                            <span>正在增强：<strong>{{ enhanceProgress.currentTargetName }}</strong></span>
                        </div>
                        <!-- 增强结果提示 -->
                        <div v-if="enhanceStatus === 'success'" class="step-progress-info success">
                            <el-icon :size="16"><CircleCheck /></el-icon>
                            <span>{{ maskData.length > 0 ? 'Mask 级精确增强完成' : '图像增强完成' }}</span>
                        </div>
                        <!-- 增强前提示 -->
                        <div v-if="enhanceStatus === 'idle' && detectCount > 0" class="step-progress-info">
                            <el-icon :size="16"><InfoFilled /></el-icon>
                            <span>将对最高置信度目标进行增强<span v-if="maskData.length > 0"> (Mask 精确增强)</span></span>
                        </div>
                        <div class="result-display-box">
                            <img
                                v-if="enhanceImage"
                                :src="enhanceImage"
                                alt="增强结果"
                                class="result-media"
                            />
                            <div v-else class="step-placeholder">
                                <div class="placeholder-icon-wrapper">
                                    <el-icon :size="36"><MagicStick /></el-icon>
                                </div>
                                <span class="placeholder-text">{{ enhanceStatus === 'running' ? '增强中...' : '待执行' }}</span>
                                <span class="placeholder-desc">基于掩码精确增强目标区域</span>
                            </div>
                        </div>
                        <div v-if="enhanceStatus === 'error' && maskStatus === 'success'" class="step-result-info error">
                            <el-icon :size="16"><Warning /></el-icon>
                            <span>增强失败：{{ errorMessage || '未知错误' }}</span>
                        </div>
                    </div>
                </div>
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
    CopyDocument,
    MagicStick,
    DocumentChecked,
    InfoFilled,
    ArrowDown,
    ArrowRight,
    CircleCheck,
    Warning,
    Loading,
    Timer,
    Grid,
    Cpu,
    Operation,
    SwitchButton
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

// Workflow 状态文案
function getWorkflowStatusTitle(): string {
    const titles: Record<string, string> = {
        idle: '准备就绪',
        running: '流程执行中',
        completed: '流程完成',
        error: '流程执行失败'
    }
    return titles[workflowStatus.value] || '未知状态'
}

function getWorkflowStatusDesc(): string {
    const descs: Record<string, string> = {
        idle: '点击"开始智能流程"执行四阶段处理',
        running: `正在执行第 ${currentStep.value} 步 / 共 3 步`,
        completed: `四阶段处理已完成，总耗时 ${formatDuration(totalDuration.value)}`,
        error: `流程执行中断，请检查错误信息并重试`
    }
    return descs[workflowStatus.value] || ''
}
</script>

<style scoped>
/* ===== 页面基础容器 ===== */
.workflow-container {
    width: 100%;
    max-width: 1600px;
    margin: 0 auto;
    padding: 0 1rem 1.5rem;
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

/* 智能流程图标 - 产品级模块标识设计 */
.header-icon.workflow-icon {
    position: relative;
    width: 54px;
    height: 54px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 16px;
    overflow: visible;
}

.icon-layer {
    position: absolute;
    border-radius: 16px;
    transition: all 0.3s ease;
}

/* 外层：主渐变背景 + 发光效果 */
.icon-layer.layer-1 {
    inset: 0;
    background: 
        linear-gradient(145deg, rgba(64, 158, 255, 0.4) 0%, rgba(22, 119, 255, 0.35) 50%, rgba(103, 194, 58, 0.25) 100%);
    border: 1.5px solid rgba(64, 158, 255, 0.5);
    box-shadow: 
        0 2px 8px rgba(0, 0, 0, 0.2),
        0 4px 20px rgba(64, 158, 255, 0.3),
        inset 0 1px 1px rgba(255, 255, 255, 0.25),
        inset 0 -1px 1px rgba(0, 0, 0, 0.1);
}

/* 中层：内嵌高光层 */
.icon-layer.layer-2 {
    inset: 2px;
    background: 
        linear-gradient(145deg, rgba(255, 255, 255, 0.15) 0%, rgba(64, 158, 255, 0.1) 40%, transparent 100%);
    border: 1px solid rgba(255, 255, 255, 0.15);
    border-radius: 14px;
}

/* 内层：深色底座 */
.icon-layer.layer-3 {
    inset: 5px;
    background: 
        linear-gradient(145deg, rgba(30, 40, 60, 0.8) 0%, rgba(20, 30, 50, 0.9) 100%);
    border: 1px solid rgba(64, 158, 255, 0.25);
    border-radius: 11px;
    box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.3);
}

/* 流程节点装饰 */
.icon-nodes {
    position: absolute;
    inset: 0;
    z-index: 1;
    pointer-events: none;
}

.icon-nodes .node {
    position: absolute;
    width: 5px;
    height: 5px;
    background: rgba(64, 158, 255, 0.8);
    border-radius: 50%;
    box-shadow: 
        0 0 6px rgba(64, 158, 255, 0.6),
        inset 0 1px 1px rgba(255, 255, 255, 0.5);
}

.icon-nodes .node-1 {
    top: 10px;
    left: 10px;
}

.icon-nodes .node-2 {
    top: 10px;
    right: 10px;
}

.icon-nodes .node-3 {
    bottom: 10px;
    left: 50%;
    transform: translateX(-50%);
}

/* 主图标 */
.header-icon.workflow-icon .main-icon {
    position: relative;
    z-index: 2;
    color: #fff;
    filter: 
        drop-shadow(0 1px 2px rgba(0, 0, 0, 0.3))
        drop-shadow(0 0 8px rgba(64, 158, 255, 0.4));
}

/* Hover 时图标动效 */
.page-header:hover .icon-layer.layer-1 {
    box-shadow: 
        0 2px 8px rgba(0, 0, 0, 0.2),
        0 6px 28px rgba(64, 158, 255, 0.4),
        inset 0 1px 1px rgba(255, 255, 255, 0.3),
        inset 0 -1px 1px rgba(0, 0, 0, 0.1);
    border-color: rgba(64, 158, 255, 0.6);
}

.page-header:hover .icon-layer.layer-2 {
    background: 
        linear-gradient(145deg, rgba(255, 255, 255, 0.2) 0%, rgba(64, 158, 255, 0.15) 40%, transparent 100%);
}

.page-header:hover .icon-nodes .node {
    background: rgba(103, 194, 58, 0.9);
    box-shadow: 
        0 0 8px rgba(103, 194, 58, 0.6),
        inset 0 1px 1px rgba(255, 255, 255, 0.5);
}

.page-header:hover .main-icon {
    filter: 
        drop-shadow(0 1px 2px rgba(0, 0, 0, 0.3))
        drop-shadow(0 0 12px rgba(64, 158, 255, 0.5));
}

/* 保留旧 header-icon 样式用于兼容 */
.header-icon {
    width: 48px;
    height: 48px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: linear-gradient(135deg, #409eff 0%, #1677ff 100%);
    border-radius: 12px;
    color: white;
    box-shadow: 0 4px 12px rgba(64, 158, 255, 0.25);
}

.header-content {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
}

.page-title {
    font-size: 1.375rem;
    font-weight: 600;
    color: rgba(255, 255, 255, 0.9);
    margin: 0;
    letter-spacing: 0.5px;
}

.page-subtitle {
    font-size: 0.8125rem;
    color: rgba(255, 255, 255, 0.5);
    margin: 0;
}

/* ===== 统一卡片系统 ===== */
.panel-card {
    background: rgba(30, 30, 40, 0.5);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    overflow: hidden;
    backdrop-filter: blur(10px);
    transition: all 0.3s ease;
}

.panel-card:hover {
    border-color: rgba(255, 255, 255, 0.12);
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
}

.panel-card .card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.875rem 1.25rem;
    background: rgba(255, 255, 255, 0.02);
    border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.panel-card .card-title-group {
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

/* 居中标题组 - 流程控制 */
.card-header.centered-header {
    justify-content: center;
    position: relative;
}

.card-title-group.centered-title {
    justify-content: center;
    padding: 0.375rem 1.25rem;
    background: 
        linear-gradient(135deg, rgba(64, 158, 255, 0.1) 0%, rgba(255, 255, 255, 0.03) 100%);
    border: 1px solid rgba(64, 158, 255, 0.2);
    border-radius: 24px;
    box-shadow: 
        0 2px 8px rgba(0, 0, 0, 0.1),
        inset 0 1px 0 rgba(255, 255, 255, 0.06);
}

.card-title-group.centered-title .subtitle-icon {
    color: #409eff;
}

.card-title-group.centered-title .card-title {
    font-size: 0.9375rem;
    font-weight: 600;
    color: rgba(255, 255, 255, 0.9);
    letter-spacing: 0.5px;
}

.subtitle-icon {
    color: #409eff;
}

.panel-card .card-title {
    font-size: 0.9375rem;
    font-weight: 600;
    color: rgba(255, 255, 255, 0.9);
}

.panel-card .card-body {
    padding: 1.25rem;
}

/* ===== 工作流结果区 ===== */
.results-section {
    margin-top: 1.5rem;
}

/* Workflow 汇总卡片 */
.workflow-summary-card {
    margin-bottom: 1.5rem;
    padding: 1.25rem;
    transition: all 0.3s ease;
}

.workflow-summary-card.is-running {
    border-color: rgba(64, 158, 255, 0.3);
    box-shadow: 0 0 20px rgba(64, 158, 255, 0.1);
}

.workflow-summary-card.is-completed {
    border-color: rgba(103, 194, 58, 0.3);
    box-shadow: 0 0 20px rgba(103, 194, 58, 0.1);
}

.workflow-summary-card.is-error {
    border-color: rgba(245, 108, 108, 0.3);
    box-shadow: 0 0 20px rgba(245, 108, 108, 0.1);
}

.summary-main {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 1.25rem;
}

.summary-status {
    display: flex;
    align-items: center;
    gap: 1rem;
}

.status-icon-wrapper {
    width: 48px;
    height: 48px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 12px;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    color: rgba(255, 255, 255, 0.5);
    transition: all 0.3s ease;
}

.status-icon-wrapper.idle {
    background: rgba(144, 147, 153, 0.1);
    border-color: rgba(144, 147, 153, 0.2);
    color: #909399;
}

.status-icon-wrapper.running {
    background: rgba(64, 158, 255, 0.1);
    border-color: rgba(64, 158, 255, 0.3);
    color: #409eff;
}

.status-icon-wrapper.completed {
    background: rgba(103, 194, 58, 0.1);
    border-color: rgba(103, 194, 58, 0.3);
    color: #67c23a;
}

.status-icon-wrapper.error {
    background: rgba(245, 108, 108, 0.1);
    border-color: rgba(245, 108, 108, 0.3);
    color: #f56c6c;
}

.status-info {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
}

.status-title {
    font-size: 1.125rem;
    font-weight: 600;
    color: rgba(255, 255, 255, 0.9);
}

.status-desc {
    font-size: 0.8125rem;
    color: rgba(255, 255, 255, 0.5);
}

.summary-duration {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 0.25rem;
    padding: 0.5rem 1rem;
    background: rgba(0, 0, 0, 0.2);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 8px;
}

.duration-value {
    font-size: 1.5rem;
    font-weight: 700;
    color: #409eff;
    font-family: monospace;
    line-height: 1;
}

.duration-label {
    font-size: 0.75rem;
    color: rgba(255, 255, 255, 0.4);
}

/* 步骤进度条 */
.summary-progress {
    margin-bottom: 1rem;
    padding: 0.75rem;
    background: rgba(0, 0, 0, 0.2);
    border-radius: 8px;
}

.progress-steps {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
}

.progress-step {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.375rem;
    opacity: 0.4;
    transition: all 0.3s ease;
}

.progress-step.active {
    opacity: 1;
}

.progress-step.completed .step-dot {
    background: #67c23a;
    border-color: #67c23a;
}

.progress-step.error .step-dot {
    background: #f56c6c;
    border-color: #f56c6c;
}

.progress-step.completed .step-label,
.progress-step.active .step-label {
    color: rgba(255, 255, 255, 0.9);
}

.step-dot {
    width: 12px;
    height: 12px;
    border-radius: 50%;
    background: rgba(255, 255, 255, 0.1);
    border: 2px solid rgba(255, 255, 255, 0.2);
    transition: all 0.3s ease;
}

.progress-step.active .step-dot {
    background: #409eff;
    border-color: #409eff;
    box-shadow: 0 0 8px rgba(64, 158, 255, 0.5);
}

.step-label {
    font-size: 0.6875rem;
    color: rgba(255, 255, 255, 0.4);
    white-space: nowrap;
}

.progress-line {
    width: 40px;
    height: 2px;
    background: rgba(255, 255, 255, 0.1);
    transition: all 0.3s ease;
}

.progress-line.completed {
    background: #67c23a;
}

/* 步骤统计 */
.summary-stats {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
    padding-top: 0.75rem;
    border-top: 1px solid rgba(255, 255, 255, 0.06);
}

.stat-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.25rem;
    min-width: 60px;
}

.stat-value {
    font-size: 1.25rem;
    font-weight: 700;
    color: rgba(255, 255, 255, 0.6);
    font-family: monospace;
    line-height: 1;
}

.stat-value.success {
    color: #67c23a;
}

.stat-value.error {
    color: #f56c6c;
}

.stat-label {
    font-size: 0.6875rem;
    color: rgba(255, 255, 255, 0.4);
}

.stat-divider {
    width: 1px;
    height: 24px;
    background: rgba(255, 255, 255, 0.1);
}

/* 步骤卡片区头部 */
.step-cards-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 1rem;
    padding: 0 0.25rem;
}

.section-title {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.9375rem;
    font-weight: 600;
    color: rgba(255, 255, 255, 0.7);
}

.step-flow-hint {
    display: flex;
    align-items: center;
    gap: 0.25rem;
    font-size: 0.75rem;
    color: rgba(255, 255, 255, 0.4);
}

.results-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1rem;
    align-items: stretch;
}

/* 步骤卡片 */
.step-panel-card {
    display: flex;
    flex-direction: column;
    height: 100%;
    transition: all 0.3s ease;
}

.step-panel-card.step-active {
    border-color: rgba(64, 158, 255, 0.3);
    box-shadow: 0 0 20px rgba(64, 158, 255, 0.1);
}

/* 步骤卡片头部 */
.step-card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.875rem 1rem;
    background: rgba(255, 255, 255, 0.02);
    border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.step-header-main {
    display: flex;
    align-items: center;
    gap: 0.75rem;
}

/* 步骤编号 */
.step-badge-wrapper {
    position: relative;
    display: flex;
    align-items: center;
    justify-content: center;
}

.step-number {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 28px;
    height: 28px;
    border-radius: 8px;
    background: linear-gradient(135deg, #409eff 0%, #1677ff 100%);
    color: #fff;
    font-size: 12px;
    font-weight: 700;
    box-shadow: 0 2px 8px rgba(64, 158, 255, 0.25);
    transition: all 0.3s ease;
}

.step-number-input {
    background: linear-gradient(135deg, #909399 0%, #606266 100%);
    box-shadow: 0 2px 8px rgba(144, 147, 153, 0.25);
}

.step-number.step-running {
    background: linear-gradient(135deg, #409eff 0%, #1677ff 100%);
    animation: step-pulse 2s ease-in-out infinite;
}

.step-number.step-success {
    background: linear-gradient(135deg, #67c23a 0%, #529b2e 100%);
    box-shadow: 0 2px 8px rgba(103, 194, 58, 0.25);
}

.step-number.step-error {
    background: linear-gradient(135deg, #f56c6c 0%, #c45656 100%);
    box-shadow: 0 2px 8px rgba(245, 108, 108, 0.25);
}

@keyframes step-pulse {
    0%, 100% { box-shadow: 0 2px 8px rgba(64, 158, 255, 0.25); }
    50% { box-shadow: 0 2px 16px rgba(64, 158, 255, 0.5); }
}

/* 旋转动画 */
.step-spinner {
    position: absolute;
    width: 36px;
    height: 36px;
    border: 2px solid transparent;
    border-top-color: #409eff;
    border-right-color: #409eff;
    border-radius: 50%;
    animation: step-spin 1s linear infinite;
}

@keyframes step-spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
}

/* 步骤信息 */
.step-info {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
}

.step-name {
    display: flex;
    align-items: center;
    gap: 0.375rem;
    font-weight: 600;
    font-size: 0.9375rem;
    color: rgba(255, 255, 255, 0.9);
}

.step-desc {
    font-size: 0.75rem;
    color: rgba(255, 255, 255, 0.4);
}

.step-meta {
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.step-status-tag {
    font-weight: 500;
}

.step-duration {
    font-size: 0.75rem;
    color: rgba(255, 255, 255, 0.4);
    font-family: monospace;
}

/* 步骤卡片内容区 */
.step-card-body {
    flex: 1;
    padding: 1rem;
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
}

/* 结果展示区 */
.result-display-box {
    flex: 1;
    min-height: 240px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: linear-gradient(135deg, rgba(0, 0, 0, 0.3), rgba(20, 20, 30, 0.4));
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 8px;
    overflow: hidden;
    position: relative;
}

.result-media {
    max-width: 100%;
    max-height: 280px;
    object-fit: contain;
    display: block;
}

/* 空状态/占位符 */
.step-placeholder {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 0.75rem;
    padding: 2rem;
    text-align: center;
    color: rgba(255, 255, 255, 0.4);
}

.placeholder-icon-wrapper {
    width: 72px;
    height: 72px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 50%;
    transition: all 0.3s ease;
}

.step-placeholder:hover .placeholder-icon-wrapper {
    background: rgba(64, 158, 255, 0.06);
    border-color: rgba(64, 158, 255, 0.2);
}

.placeholder-text {
    font-size: 0.9375rem;
    font-weight: 500;
    color: rgba(255, 255, 255, 0.6);
}

.placeholder-desc {
    font-size: 0.75rem;
    color: rgba(255, 255, 255, 0.35);
    max-width: 200px;
    line-height: 1.4;
}

/* 步骤进度/结果信息 */
.step-progress-info {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.375rem;
    padding: 0.5rem 0.75rem;
    background: rgba(64, 158, 255, 0.08);
    border: 1px solid rgba(64, 158, 255, 0.15);
    border-radius: 6px;
    font-size: 0.8125rem;
    color: rgba(255, 255, 255, 0.7);
}

.step-progress-info.success {
    background: rgba(103, 194, 58, 0.08);
    border-color: rgba(103, 194, 58, 0.15);
    color: #67c23a;
}

.step-progress-info :deep(.el-icon.is-loading) {
    animation: rotate 1s linear infinite;
}

@keyframes rotate {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
}

.step-result-info {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.375rem;
    padding: 0.5rem 0.75rem;
    border-radius: 6px;
    font-size: 0.8125rem;
}

.step-result-info.success {
    background: rgba(103, 194, 58, 0.1);
    border: 1px solid rgba(103, 194, 58, 0.2);
    color: #67c23a;
}

.step-result-info.error {
    background: rgba(245, 108, 108, 0.1);
    border: 1px solid rgba(245, 108, 108, 0.2);
    color: #f56c6c;
}

/* ===== 流程控制区 ===== */
.control-card {
    margin-bottom: 1.5rem;
}

.control-card .card-body {
    display: flex;
    flex-direction: column;
    gap: 1.25rem;
}

/* 小标题统一样式 */
.section-subtitle {
    display: flex;
    align-items: center;
    gap: 0.375rem;
    margin-bottom: 0.75rem;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

/* 居中小标题 */
.section-subtitle.centered-subtitle {
    justify-content: center;
}

/* 标签式小标题 - 带框感/卡片感 */
.section-subtitle.tag-style-subtitle {
    display: flex;
    justify-content: center;
    margin-bottom: 1rem;
    padding-bottom: 0;
    border-bottom: none;
}

.subtitle-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem 1rem;
    background: 
        linear-gradient(135deg, rgba(64, 158, 255, 0.08) 0%, rgba(255, 255, 255, 0.03) 100%);
    border: 1px solid rgba(64, 158, 255, 0.2);
    border-radius: 20px;
    box-shadow: 
        0 2px 8px rgba(0, 0, 0, 0.1),
        inset 0 1px 0 rgba(255, 255, 255, 0.05);
    transition: all 0.25s ease;
}

.subtitle-badge:hover {
    background: 
        linear-gradient(135deg, rgba(64, 158, 255, 0.12) 0%, rgba(255, 255, 255, 0.05) 100%);
    border-color: rgba(64, 158, 255, 0.3);
    box-shadow: 
        0 4px 12px rgba(64, 158, 255, 0.15),
        inset 0 1px 0 rgba(255, 255, 255, 0.08);
}

.subtitle-badge .subtitle-icon {
    color: #409eff;
    font-size: 14px;
}

.subtitle-badge .subtitle-text {
    font-size: 0.8125rem;
    font-weight: 600;
    color: rgba(255, 255, 255, 0.85);
    letter-spacing: 0.5px;
}

.section-subtitle .subtitle-icon {
    color: #409eff;
}

.section-subtitle .subtitle-text {
    font-size: 0.8125rem;
    font-weight: 600;
    color: rgba(255, 255, 255, 0.7);
}

/* ===== 流程输入区 ===== */
.workflow-input-section {
    width: 100%;
}

.upload-wrapper {
    position: relative;
}

/* 彻底隐藏原生文件输入框及其默认提示 */
.native-file-input {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    opacity: 0;
    cursor: pointer;
    z-index: 10;
    font-size: 0;
    color: transparent;
}

.native-file-input::-webkit-file-upload-button {
    visibility: hidden;
    display: none;
}

.native-file-input::file-selector-button {
    visibility: hidden;
    display: none;
}

/* 智能流程专用上传区 - 更精致的设计 */
.upload-drop-zone.workflow-upload-zone {
    position: relative;
    border: 2px dashed rgba(255, 255, 255, 0.1);
    border-radius: 14px;
    padding: 2rem 1.5rem;
    cursor: pointer;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    background: 
        linear-gradient(135deg, rgba(64, 158, 255, 0.03) 0%, rgba(103, 194, 58, 0.02) 100%),
        rgba(255, 255, 255, 0.02);
    box-shadow: 
        inset 0 1px 0 rgba(255, 255, 255, 0.05),
        0 2px 8px rgba(0, 0, 0, 0.1);
}

.upload-drop-zone.workflow-upload-zone:hover {
    border-color: rgba(64, 158, 255, 0.5);
    background: 
        linear-gradient(135deg, rgba(64, 158, 255, 0.08) 0%, rgba(103, 194, 58, 0.04) 100%),
        rgba(255, 255, 255, 0.03);
    box-shadow: 
        inset 0 1px 0 rgba(255, 255, 255, 0.08),
        0 4px 16px rgba(64, 158, 255, 0.15);
    transform: translateY(-1px);
}

.upload-drop-zone.workflow-upload-zone.drag-over {
    border-color: #409eff;
    border-style: solid;
    background: 
        linear-gradient(135deg, rgba(64, 158, 255, 0.12) 0%, rgba(103, 194, 58, 0.06) 100%),
        rgba(255, 255, 255, 0.04);
    box-shadow: 
        inset 0 1px 0 rgba(255, 255, 255, 0.1),
        0 0 0 3px rgba(64, 158, 255, 0.1),
        0 8px 24px rgba(64, 158, 255, 0.2);
    transform: translateY(-2px);
}

.upload-drop-zone.workflow-upload-zone.has-file {
    border-color: rgba(103, 194, 58, 0.4);
    border-style: solid;
    background: 
        linear-gradient(135deg, rgba(103, 194, 58, 0.06) 0%, rgba(64, 158, 255, 0.03) 100%),
        rgba(255, 255, 255, 0.02);
}

.upload-drop-zone.workflow-upload-zone.disabled {
    cursor: not-allowed;
    opacity: 0.5;
    transform: none;
}

/* 上传内容层次优化 - 完全居中 */
.upload-drop-zone.workflow-upload-zone .upload-content,
.upload-drop-zone.workflow-upload-zone .upload-empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 1rem;
    text-align: center;
    width: 100%;
}

/* 空状态文字层级居中 */
.upload-empty-state .upload-main-text {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    width: 100%;
}

.upload-empty-state .upload-primary-text {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
    text-align: center;
}

.upload-empty-state .upload-formats {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
    text-align: center;
    width: 100%;
}

/* ===== 上传后原图预览状态 ===== */
.upload-preview-state {
    position: relative;
    width: 100%;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 0.75rem;
}

.preview-image-wrapper {
    width: 100%;
    max-height: 200px;
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;
    border-radius: 10px;
    background: rgba(0, 0, 0, 0.2);
}

.preview-image {
    max-width: 100%;
    max-height: 200px;
    height: auto;
    object-fit: contain;
    display: block;
}

.preview-overlay {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 0.375rem;
    text-align: center;
}

.preview-info {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
    color: #67c23a;
    font-size: 0.875rem;
    font-weight: 500;
}

.preview-filename {
    max-width: 200px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    color: rgba(255, 255, 255, 0.9);
}

.preview-hint {
    font-size: 0.75rem;
    color: rgba(255, 255, 255, 0.5);
    transition: color 0.2s ease;
}

.upload-drop-zone.workflow-upload-zone:hover .preview-hint {
    color: #409eff;
}

/* has-preview 状态的样式调整 */
.upload-drop-zone.workflow-upload-zone.has-preview {
    padding: 1rem;
    background: 
        linear-gradient(135deg, rgba(103, 194, 58, 0.08) 0%, rgba(64, 158, 255, 0.04) 100%),
        rgba(255, 255, 255, 0.02);
}

/* 图标环形设计 */
.upload-icon-ring {
    position: relative;
    width: 64px;
    height: 64px;
    display: flex;
    align-items: center;
    justify-content: center;
}

.upload-icon-ring::before {
    content: '';
    position: absolute;
    inset: 0;
    border-radius: 50%;
    border: 2px dashed rgba(64, 158, 255, 0.2);
    animation: ring-rotate 20s linear infinite;
}

@keyframes ring-rotate {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
}

.upload-drop-zone.workflow-upload-zone:hover .upload-icon-ring::before {
    border-color: rgba(64, 158, 255, 0.4);
}

.upload-icon-bg {
    width: 52px;
    height: 52px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: linear-gradient(135deg, rgba(64, 158, 255, 0.15) 0%, rgba(22, 119, 255, 0.1) 100%);
    border: 1px solid rgba(64, 158, 255, 0.25);
    border-radius: 50%;
    transition: all 0.3s ease;
}

.upload-drop-zone.workflow-upload-zone:hover .upload-icon-bg {
    background: linear-gradient(135deg, rgba(64, 158, 255, 0.25) 0%, rgba(22, 119, 255, 0.15) 100%);
    border-color: rgba(64, 158, 255, 0.4);
    transform: scale(1.05);
}

.upload-drop-zone.workflow-upload-zone .upload-main-icon {
    color: rgba(64, 158, 255, 0.8);
    transition: all 0.3s ease;
}

.upload-drop-zone.workflow-upload-zone:hover .upload-main-icon {
    color: #409eff;
}

/* 上传文案层次 */
.upload-drop-zone.workflow-upload-zone .upload-main-text {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.375rem;
}

.upload-primary-text {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.25rem;
}

.workflow-start-hint {
    font-size: 0.75rem;
    font-weight: 600;
    color: rgba(64, 158, 255, 0.9);
    text-transform: uppercase;
    letter-spacing: 1px;
    padding: 0.25rem 0.75rem;
    background: rgba(64, 158, 255, 0.1);
    border: 1px solid rgba(64, 158, 255, 0.2);
    border-radius: 20px;
}

.upload-action {
    font-size: 0.9375rem;
    color: rgba(255, 255, 255, 0.8);
    line-height: 1.5;
}

.upload-action .highlight {
    color: #409eff;
    font-weight: 600;
}

/* 已上传文件展示 */
.file-selected {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.5rem;
}

.file-badge {
    width: 40px;
    height: 40px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: linear-gradient(135deg, rgba(103, 194, 58, 0.2) 0%, rgba(103, 194, 58, 0.1) 100%);
    border: 1px solid rgba(103, 194, 58, 0.3);
    border-radius: 50%;
    color: #67c23a;
}

.file-selected .filename {
    font-size: 0.9375rem;
    font-weight: 500;
    color: rgba(255, 255, 255, 0.9);
    max-width: 280px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.file-selected .replace-hint {
    font-size: 0.8125rem;
    color: rgba(255, 255, 255, 0.5);
    transition: color 0.2s ease;
}

.upload-drop-zone.workflow-upload-zone:hover .file-selected .replace-hint {
    color: #409eff;
}

/* 格式标签优化 */
.upload-drop-zone.workflow-upload-zone .upload-formats {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.5rem;
    margin-top: 0.5rem;
}

.format-label {
    font-size: 0.6875rem;
    color: rgba(255, 255, 255, 0.35);
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.format-tags {
    display: flex;
    gap: 0.5rem;
}

.format-tag {
    background: rgba(255, 255, 255, 0.05) !important;
    border-color: rgba(255, 255, 255, 0.1) !important;
    color: rgba(255, 255, 255, 0.6) !important;
}

/* 保留旧样式用于兼容 */
.upload-drop-zone {
    border: 2px dashed rgba(255, 255, 255, 0.12);
    border-radius: 12px;
    padding: 1.5rem;
    cursor: pointer;
    transition: all 0.3s ease;
    background: rgba(255, 255, 255, 0.02);
}

.upload-drop-zone:hover {
    border-color: rgba(64, 158, 255, 0.4);
    background: rgba(64, 158, 255, 0.04);
}

.upload-drop-zone.drag-over {
    border-color: #409eff;
    background: rgba(64, 158, 255, 0.08);
}

.upload-drop-zone.has-file {
    border-color: rgba(103, 194, 58, 0.4);
    background: rgba(103, 194, 58, 0.04);
}

.upload-drop-zone.disabled {
    cursor: not-allowed;
    opacity: 0.5;
}

.upload-content {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 0.75rem;
    text-align: center;
}

.upload-main-icon {
    color: rgba(255, 255, 255, 0.3);
    transition: color 0.3s ease;
}

.upload-drop-zone:hover .upload-main-icon {
    color: #409eff;
}

.upload-main-text {
    font-size: 0.9375rem;
    color: rgba(255, 255, 255, 0.7);
    line-height: 1.5;
}

.upload-main-text .highlight {
    color: #409eff;
    font-weight: 500;
}

.upload-main-text .file-selected {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
    color: rgba(255, 255, 255, 0.85);
}

.upload-main-text .filename {
    font-weight: 500;
}

.upload-main-text .replace-hint {
    font-size: 0.75rem;
    color: rgba(255, 255, 255, 0.4);
    margin-left: 0.25rem;
}

.upload-formats {
    display: flex;
    gap: 0.5rem;
    margin-top: 0.25rem;
}

/* ===== 流程执行区 ===== */
.workflow-action-section {
    width: 100%;
}

.action-buttons {
    display: flex;
    flex-direction: column;
    gap: 0.625rem;
    width: 100%;
}

/* ===== 按钮交互反馈优化 ===== */
.action-btn {
    width: 100% !important;
    height: 46px !important;
    display: inline-flex !important;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
    border-radius: 10px;
    font-weight: 500;
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    position: relative;
    overflow: hidden;
}

/* 主按钮 - 开始智能流程 */
.action-btn.submit-btn {
    font-weight: 600;
    font-size: 0.9375rem;
    letter-spacing: 0.5px;
    background: linear-gradient(135deg, #409eff 0%, #1677ff 100%);
    border: none;
    box-shadow: 
        0 2px 8px rgba(64, 158, 255, 0.3),
        0 4px 16px rgba(64, 158, 255, 0.2),
        inset 0 1px 0 rgba(255, 255, 255, 0.2);
}

.action-btn.submit-btn::before {
    content: '';
    position: absolute;
    inset: 0;
    background: linear-gradient(135deg, rgba(255, 255, 255, 0.2) 0%, transparent 100%);
    opacity: 0;
    transition: opacity 0.2s ease;
}

/* Hover 状态 */
.action-btn.submit-btn:not(:disabled):hover {
    transform: translateY(-2px);
    box-shadow: 
        0 4px 12px rgba(64, 158, 255, 0.4),
        0 8px 24px rgba(64, 158, 255, 0.25),
        inset 0 1px 0 rgba(255, 255, 255, 0.25);
}

.action-btn.submit-btn:not(:disabled):hover::before {
    opacity: 1;
}

/* Active / Pressed 状态 */
.action-btn.submit-btn:not(:disabled):active {
    transform: translateY(0);
    box-shadow: 
        0 1px 4px rgba(64, 158, 255, 0.3),
        inset 0 2px 4px rgba(0, 0, 0, 0.1);
}

/* Focus 状态 */
.action-btn.submit-btn:focus-visible {
    outline: none;
    box-shadow: 
        0 0 0 3px rgba(64, 158, 255, 0.3),
        0 4px 12px rgba(64, 158, 255, 0.4);
}

/* Disabled 状态 */
.action-btn.submit-btn:disabled {
    background: linear-gradient(135deg, rgba(64, 158, 255, 0.3) 0%, rgba(22, 119, 255, 0.3) 100%);
    box-shadow: none;
    cursor: not-allowed;
}

/* Loading 状态 */
.action-btn.submit-btn.is-loading {
    background: linear-gradient(135deg, rgba(64, 158, 255, 0.6) 0%, rgba(22, 119, 255, 0.6) 100%);
}

/* 次按钮 - 重置流程 */
.action-btn.clear-btn {
    font-size: 0.875rem;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.12);
    color: rgba(255, 255, 255, 0.7);
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
}

.action-btn.clear-btn::before {
    content: '';
    position: absolute;
    inset: 0;
    background: rgba(255, 255, 255, 0.05);
    opacity: 0;
    transition: opacity 0.2s ease;
}

/* Hover 状态 */
.action-btn.clear-btn:not(:disabled):hover {
    background: rgba(255, 255, 255, 0.08);
    border-color: rgba(255, 255, 255, 0.2);
    color: rgba(255, 255, 255, 0.9);
    transform: translateY(-1px);
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}

.action-btn.clear-btn:not(:disabled):hover::before {
    opacity: 1;
}

/* Active / Pressed 状态 */
.action-btn.clear-btn:not(:disabled):active {
    transform: translateY(0);
    background: rgba(255, 255, 255, 0.05);
    border-color: rgba(255, 255, 255, 0.15);
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
}

/* Focus 状态 */
.action-btn.clear-btn:focus-visible {
    outline: none;
    box-shadow: 
        0 0 0 2px rgba(255, 255, 255, 0.1),
        0 2px 8px rgba(0, 0, 0, 0.15);
}

/* Disabled 状态 */
.action-btn.clear-btn:disabled {
    background: rgba(255, 255, 255, 0.02);
    border-color: rgba(255, 255, 255, 0.06);
    color: rgba(255, 255, 255, 0.3);
    cursor: not-allowed;
}

/* ===== 调试工具区 ===== */
.workflow-debug-section {
    margin-top: 0.5rem;
    padding-top: 1rem;
    border-top: 1px dashed rgba(255, 255, 255, 0.08);
}

.debug-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.5rem 0.75rem;
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 6px;
    cursor: pointer;
    transition: all 0.25s ease;
}

.debug-header:hover {
    background: rgba(255, 255, 255, 0.05);
    border-color: rgba(255, 255, 255, 0.1);
}

.debug-title {
    display: flex;
    align-items: center;
    gap: 0.375rem;
    font-size: 0.8125rem;
    color: rgba(255, 255, 255, 0.6);
}

.debug-toggle-icon {
    color: rgba(255, 255, 255, 0.4);
    transition: transform 0.25s ease;
}

.debug-toggle-icon.is-active {
    transform: rotate(180deg);
}

.debug-content {
    margin-top: 0.75rem;
    padding: 0.75rem;
    background: rgba(0, 0, 0, 0.2);
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 6px;
}

.debug-info-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: 0.5rem;
}

.debug-item {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.75rem;
}

.debug-label {
    color: rgba(255, 255, 255, 0.4);
    flex-shrink: 0;
}

.debug-value {
    color: rgba(255, 255, 255, 0.7);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.upload-section {
    margin-bottom: 16px;
}

/* 控制栏：响应式 Flex */
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

/* 响应式 */
@media (max-width: 992px) {
    .results-grid {
        grid-template-columns: 1fr;
    }
    
    .page-header {
        flex-direction: column;
        gap: 1rem;
        align-items: flex-start;
    }
    
    .summary-main {
        flex-direction: column;
        gap: 1rem;
        align-items: flex-start;
    }
    
    .summary-duration {
        align-items: flex-start;
        width: 100%;
    }
}

@media (max-width: 768px) {
    .workflow-container {
        padding: 0 0.75rem 1rem;
    }

    .action-buttons {
        width: 100%;
    }
    
    .workflow-summary-card {
        padding: 1rem;
    }
    
    .status-icon-wrapper {
        width: 40px;
        height: 40px;
    }
    
    .status-title {
        font-size: 1rem;
    }
    
    .progress-line {
        width: 24px;
    }
    
    .step-label {
        font-size: 0.625rem;
    }
    
    .summary-stats {
        flex-wrap: wrap;
        gap: 0.75rem;
    }
    
    .stat-divider {
        display: none;
    }
    
    .result-display-box {
        min-height: 200px;
    }
    
    .result-media {
        max-height: 240px;
    }
    
    .step-card-header {
        padding: 0.75rem;
    }
    
    .step-number {
        width: 24px;
        height: 24px;
        font-size: 11px;
    }
    
    .step-name {
        font-size: 0.875rem;
    }
}
</style>
