<template>
    <div class="home-page">
        <!-- ========== 第一部分：Hero 主视觉区 ========== -->
        <section class="hero-section">
            <div class="hero-background">
                <div class="bg-glow glow-1"></div>
                <div class="bg-glow glow-2"></div>
                <div class="bg-grid"></div>
            </div>
            
            <div class="hero-content">
                <div class="hero-badge">
                    <div class="badge-icon">
                        <el-icon :size="14"><Cpu /></el-icon>
                    </div>
                    <span>AI-Powered Vision Platform</span>
                </div>
                
                <h1 class="hero-title">
                    <span class="title-line">
                        <span class="title-highlight">智能视觉</span>工作台
                    </span>
                    <span class="title-line title-secondary">
                        一站式目标检测与图像增强平台
                    </span>
                </h1>
                
                <p class="hero-subtitle">
                    融合 YOLO 检测、实例分割、Real-ESRGAN 增强与智能流程编排<br>
                    从单图识别到全自动流水线，满足多场景视觉智能需求
                </p>
                
                <div class="hero-actions">
                    <button class="hero-cta primary" @click="goTo('/predict/image')">
                        <div class="cta-glow"></div>
                        <el-icon :size="20"><Picture /></el-icon>
                        <span>开始识别</span>
                        <el-icon :size="16" class="cta-arrow"><ArrowRight /></el-icon>
                    </button>
                    <button class="hero-cta secondary" @click="goTo('/predict/workflow')">
                        <el-icon :size="18"><VideoPlay /></el-icon>
                        <span>智能流程</span>
                    </button>
                </div>
                
                <div class="hero-stats">
                    <div class="stat-item">
                        <span class="stat-value">5+</span>
                        <span class="stat-label">核心模块</span>
                    </div>
                    <div class="stat-divider"></div>
                    <div class="stat-item">
                        <span class="stat-value">4</span>
                        <span class="stat-label">流程步骤</span>
                    </div>
                    <div class="stat-divider"></div>
                    <div class="stat-item">
                        <span class="stat-value">端到端</span>
                        <span class="stat-label">全自动处理</span>
                    </div>
                </div>
            </div>
            
            <div class="hero-visual">
                <!-- 主视觉图形：智能工作流示意 -->
                <div class="visual-container">
                    <!-- 中心核心节点 -->
                    <div class="core-node">
                        <div class="core-ring ring-1"></div>
                        <div class="core-ring ring-2"></div>
                        <div class="core-icon">
                            <el-icon :size="32"><Cpu /></el-icon>
                        </div>
                    </div>
                    
                    <!-- 环绕能力节点 -->
                    <div class="orbit-nodes">
                        <div class="orbit-node node-detect">
                            <div class="node-icon"><el-icon :size="18"><Aim /></el-icon></div>
                            <span>检测</span>
                        </div>
                        <div class="orbit-node node-mask">
                            <div class="node-icon"><el-icon :size="18"><CopyDocument /></el-icon></div>
                            <span>掩码</span>
                        </div>
                        <div class="orbit-node node-enhance">
                            <div class="node-icon"><el-icon :size="18"><MagicStick /></el-icon></div>
                            <span>增强</span>
                        </div>
                        <div class="orbit-node node-video">
                            <div class="node-icon"><el-icon :size="18"><VideoPlay /></el-icon></div>
                            <span>视频</span>
                        </div>
                    </div>
                    
                    <!-- 连接线 -->
                    <div class="connection-lines">
                        <div class="conn-line line-to-detect"></div>
                        <div class="conn-line line-to-mask"></div>
                        <div class="conn-line line-to-enhance"></div>
                        <div class="conn-line line-to-video"></div>
                    </div>
                    
                    <!-- 外围装饰网格 -->
                    <div class="decoration-grid">
                        <div class="deco-cell" v-for="n in 16" :key="n"></div>
                    </div>
                </div>
            </div>
        </section>

        <!-- ========== 第二部分：核心功能入口区 ========== -->
        <section class="features-section">
            <div class="section-header">
                <div class="section-tag">
                    <el-icon :size="14"><Grid /></el-icon>
                    <span>核心功能</span>
                </div>
                <h2 class="section-title">全链路视觉智能能力</h2>
            </div>
            <div class="features-grid">
                <div 
                    v-for="feature in features" 
                    :key="feature.id"
                    class="feature-card"
                    :class="`theme-${feature.theme}`"
                    @click="goTo(feature.path)"
                >
                    <!-- 卡片背景层 -->
                    <div class="card-bg-layer"></div>
                    <div class="card-glow-layer"></div>
                    
                    <!-- 图标容器 - 多层精致化设计 -->
                    <div class="feature-icon-wrapper">
                        <div class="icon-layer layer-1"></div>
                        <div class="icon-layer layer-2"></div>
                        <div class="icon-layer layer-3"></div>
                        <div class="icon-glow"></div>
                        <el-icon :size="26" class="feature-icon">
                            <component :is="feature.icon" />
                        </el-icon>
                    </div>
                    
                    <!-- 内容区 -->
                    <div class="feature-content">
                        <h3 class="feature-title">{{ feature.title }}</h3>
                        <p class="feature-desc">{{ feature.desc }}</p>
                        <div class="feature-footer">
                            <div class="feature-tags">
                                <span 
                                    v-for="tag in feature.tags" 
                                    :key="tag" 
                                    class="feature-tag"
                                >
                                    {{ tag }}
                                </span>
                            </div>
                        </div>
                    </div>
                    
                    <!-- 进入指示 -->
                    <div class="feature-action">
                        <div class="action-hint">
                            <span class="hint-text">{{ feature.cta }}</span>
                            <el-icon :size="14" class="hint-arrow"><ArrowRight /></el-icon>
                        </div>
                        <div class="action-arrow">
                            <el-icon :size="18"><ArrowRight /></el-icon>
                        </div>
                    </div>
                </div>
            </div>
        </section>

        <!-- ========== 第三部分：平台能力概览区 ========== -->
        <section class="capabilities-section">
            <div class="section-header">
                <div class="section-tag">
                    <el-icon :size="14"><DataAnalysis /></el-icon>
                    <span>平台能力</span>
                </div>
                <h2 class="section-title">为什么选择 YOLO Web</h2>
            </div>
            <div class="capabilities-grid">
                <div 
                    v-for="cap in capabilities" 
                    :key="cap.id" 
                    class="capability-card"
                    :class="`accent-${cap.accent}`"
                >
                    <!-- 卡片背景与辉光层 -->
                    <div class="capability-bg"></div>
                    <div class="capability-glow"></div>
                    
                    <!-- 顶部：数字与图标 -->
                    <div class="capability-header">
                        <div class="capability-number">
                            <span class="number-digit">{{ cap.number }}</span>
                            <div class="number-glow"></div>
                        </div>
                        <div class="capability-icon-wrap">
                            <el-icon :size="18" class="capability-icon">
                                <component :is="cap.icon" />
                            </el-icon>
                        </div>
                    </div>
                    
                    <!-- 能力标签 -->
                    <div class="capability-label">{{ cap.title }}</div>
                    
                    <!-- 说明 -->
                    <p class="capability-desc">{{ cap.desc }}</p>
                </div>
            </div>
        </section>

        <!-- ========== 第四部分：智能流程亮点区 ========== -->
        <section class="workflow-highlight-section">
            <!-- 区域背景装饰 -->
            <div class="highlight-bg-decoration"></div>
            
            <div class="section-header">
                <div class="section-tag highlight">
                    <el-icon :size="14"><Star /></el-icon>
                    <span>亮点能力</span>
                </div>
                <h2 class="section-title">智能流程：一站式视觉处理</h2>
                <p class="section-subtitle">上传 → 检测 → 掩码 → 增强，全自动流水线</p>
            </div>
            
            <div class="workflow-chain">
                <div 
                    v-for="(step, index) in workflowSteps" 
                    :key="step.id" 
                    class="workflow-step"
                    :class="{ 'is-last': index === workflowSteps.length - 1 }"
                >
                    <div class="step-card">
                        <!-- 卡片背景层 -->
                        <div class="step-card-bg"></div>
                        <div class="step-card-glow"></div>
                        
                        <!-- 步骤指示器 -->
                        <div class="step-indicator">
                            <div class="step-ring"></div>
                            <div class="step-dot"></div>
                            <span class="step-number">0{{ index + 1 }}</span>
                        </div>
                        
                        <!-- 图标 -->
                        <div class="step-icon-wrap">
                            <el-icon :size="22" class="step-icon">
                                <component :is="step.icon" />
                            </el-icon>
                        </div>
                        
                        <!-- 名称 -->
                        <span class="step-name">{{ step.name }}</span>
                        
                        <!-- 微标签 -->
                        <span class="step-hint">{{ step.hint }}</span>
                    </div>
                    
                    <!-- 连接线 -->
                    <div v-if="index < workflowSteps.length - 1" class="step-connector">
                        <div class="connector-track">
                            <div class="connector-progress"></div>
                        </div>
                        <div class="connector-node">
                            <el-icon :size="12" class="node-icon"><ArrowRight /></el-icon>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="workflow-cta">
                <button class="highlight-cta-btn" @click="goTo('/predict/workflow')">
                    <div class="cta-btn-glow"></div>
                    <el-icon :size="18"><VideoPlay /></el-icon>
                    <span>体验智能流程</span>
                    <el-icon :size="14" class="cta-arrow"><ArrowRight /></el-icon>
                </button>
            </div>
        </section>

        <!-- ========== 第五部分：快捷入口区 ========== -->
        <section class="quick-access-section">
            <div class="quick-grid">
                <!-- 历史记录卡片 -->
                <div class="quick-card history-card" @click="goTo('/history')">
                    <div class="quick-card-bg"></div>
                    <div class="quick-card-border"></div>
                    
                    <div class="quick-main">
                        <div class="quick-icon">
                            <div class="icon-bg"></div>
                            <el-icon :size="26"><Timer /></el-icon>
                        </div>
                        <div class="quick-content">
                            <div class="quick-header">
                                <h3>历史记录</h3>
                                <span class="quick-badge">快捷</span>
                            </div>
                            <p>查看和管理已保存的识别任务与结果</p>
                        </div>
                    </div>
                    
                    <div class="quick-action">
                        <span class="action-text">查看全部</span>
                        <el-icon :size="16" class="action-arrow"><ArrowRight /></el-icon>
                    </div>
                </div>
                
                <!-- 快速开始卡片 -->
                <div class="quick-card start-card" @click="goTo('/predict/image')">
                    <div class="quick-card-bg"></div>
                    <div class="quick-card-border"></div>
                    
                    <div class="quick-main">
                        <div class="quick-icon">
                            <div class="icon-bg"></div>
                            <el-icon :size="26"><Plus /></el-icon>
                        </div>
                        <div class="quick-content">
                            <div class="quick-header">
                                <h3>快速开始</h3>
                                <span class="quick-badge hot">推荐</span>
                            </div>
                            <p>立即上传图片，开始目标检测与增强</p>
                        </div>
                    </div>
                    
                    <div class="quick-action primary">
                        <span class="action-text">开始识别</span>
                        <el-icon :size="16" class="action-arrow"><ArrowRight /></el-icon>
                    </div>
                </div>
            </div>
        </section>
    </div>
</template>

<script setup lang="ts">
import {
    Picture,
    VideoPlay,
    CopyDocument,
    MagicStick,
    Cpu,
    Grid,
    DataAnalysis,
    Star,
    ArrowRight,
    Timer,
    Link,
    Aim
} from '@element-plus/icons-vue'

// 核心功能列表
const features = [
    {
        id: 'image',
        title: '图像识别',
        desc: '基于 YOLO 的实时目标检测，支持多种模型切换',
        icon: 'Picture',
        path: '/predict/image',
        tags: ['YOLO', '实时检测'],
        theme: 'blue',
        cta: '开始识别'
    },
    {
        id: 'video',
        title: '视频识别',
        desc: '逐帧检测视频流，支持帧间隔配置与批量导出',
        icon: 'VideoPlay',
        path: '/predict/video',
        tags: ['视频流', '帧检测'],
        theme: 'cyan',
        cta: '视频分析'
    },
    {
        id: 'mask',
        title: '掩码生成',
        desc: '实例分割提取目标轮廓，支持像素级掩码操作',
        icon: 'CopyDocument',
        path: '/predict/mask',
        tags: ['分割', '像素级'],
        theme: 'purple',
        cta: '生成掩码'
    },
    {
        id: 'enhance',
        title: '图像增强',
        desc: 'Real-ESRGAN 超分辨率，整图/ROI/自动检测增强',
        icon: 'MagicStick',
        path: '/predict/enhance',
        tags: ['超分', 'Real-ESRGAN'],
        theme: 'green',
        cta: '增强图像'
    },
    {
        id: 'workflow',
        title: '智能流程',
        desc: '检测→掩码→增强全自动化流水线，一站式处理',
        icon: 'Cpu',
        path: '/predict/workflow',
        tags: ['全自动', 'Pipeline'],
        theme: 'gradient',
        cta: '体验流程'
    }
]

// 平台能力
const capabilities = [
    {
        id: 1,
        number: '01',
        title: '多任务支持',
        desc: '图像、视频、分割、增强全覆盖，满足多样化视觉分析需求',
        icon: 'Grid',
        accent: 'blue'
    },
    {
        id: 2,
        number: '02',
        title: '流程自动化',
        desc: '智能流程串联多阶段处理，一次上传，全自动完成检测与增强',
        icon: 'Connection',
        accent: 'cyan'
    },
    {
        id: 3,
        number: '03',
        title: '历史可追溯',
        desc: '所有任务自动保存，随时查看、下载、复用历史识别结果',
        icon: 'Clock',
        accent: 'purple'
    },
    {
        id: 4,
        number: '04',
        title: '模型可扩展',
        desc: '基于标准化 API 设计，支持灵活接入新模型与新能力',
        icon: 'Plus',
        accent: 'green'
    }
]

// 智能流程步骤
const workflowSteps = [
    { id: 'upload', name: '上传图片', icon: 'Picture', hint: '起点' },
    { id: 'detect', name: '目标检测', icon: 'Aim', hint: 'YOLO' },
    { id: 'mask', name: '掩码生成', icon: 'CopyDocument', hint: '分割' },
    { id: 'enhance', name: '图像增强', icon: 'MagicStick', hint: '输出' }
]

// 导航方法
function goTo(path: string) {
    window.location.href = path
}

function openGithub() {
    window.open('https://github.com', '_blank')
}
</script>

<style scoped>
/* ========== 首页整体容器 ========== */
.home-page {
    width: 100%;
    max-width: 1400px;
    margin: 0 auto;
    padding: 0 1.5rem 3rem;
}

/* ========== 通用 Section 样式 ========== */
/* 统一区块间距节奏：Hero 最重，其余依次递减 */
section {
    margin-bottom: 3.5rem;
}

/* 统一标题区域样式 */
.section-header {
    text-align: center;
    margin-bottom: 2rem;
}

/* 统一标签样式 - 收敛边框 */
.section-tag {
    display: inline-flex;
    align-items: center;
    gap: 0.375rem;
    padding: 0.375rem 0.875rem;
    background: linear-gradient(135deg, rgba(64, 158, 255, 0.08) 0%, rgba(255, 255, 255, 0.02) 100%);
    border: 1px solid rgba(64, 158, 255, 0.15);
    border-radius: 20px;
    margin-bottom: 0.875rem;
}

.section-tag .el-icon {
    color: rgba(64, 158, 255, 0.9);
}

.section-tag span {
    font-size: 0.75rem;
    font-weight: 600;
    color: rgba(255, 255, 255, 0.8);
    letter-spacing: 0.5px;
}

.section-tag.highlight {
    background: linear-gradient(135deg, rgba(103, 194, 58, 0.08) 0%, rgba(255, 255, 255, 0.02) 100%);
    border-color: rgba(103, 194, 58, 0.2);
}

.section-tag.highlight .el-icon {
    color: rgba(103, 194, 58, 0.9);
}

/* 统一标题层级 */
.section-title {
    font-size: 1.625rem;
    font-weight: 700;
    color: rgba(255, 255, 255, 0.92);
    margin: 0 0 0.5rem;
    letter-spacing: -0.01em;
}

.section-subtitle {
    font-size: 0.9375rem;
    color: rgba(255, 255, 255, 0.45);
    margin: 0;
}

/* ========== Hero 主视觉区（强化版） ========== */
.hero-section {
    position: relative;
    display: grid;
    grid-template-columns: 1.1fr 0.9fr;
    gap: 4rem;
    align-items: center;
    min-height: 520px;
    padding: 3rem 0 4rem;
    margin-bottom: 3.5rem;
    overflow: hidden;
}

/* 背景装饰 */
.hero-background {
    position: absolute;
    inset: 0;
    z-index: 0;
    pointer-events: none;
    overflow: hidden;
}

.bg-glow {
    position: absolute;
    border-radius: 50%;
    filter: blur(80px);
    opacity: 0.4;
}

.bg-glow.glow-1 {
    width: 400px;
    height: 400px;
    background: radial-gradient(circle, rgba(64, 158, 255, 0.3) 0%, transparent 70%);
    top: -100px;
    right: 10%;
}

.bg-glow.glow-2 {
    width: 300px;
    height: 300px;
    background: radial-gradient(circle, rgba(103, 194, 58, 0.2) 0%, transparent 70%);
    bottom: -50px;
    left: 20%;
}

.bg-grid {
    position: absolute;
    inset: 0;
    background-image: 
        linear-gradient(rgba(64, 158, 255, 0.03) 1px, transparent 1px),
        linear-gradient(90deg, rgba(64, 158, 255, 0.03) 1px, transparent 1px);
    background-size: 60px 60px;
    mask-image: linear-gradient(to bottom, transparent 0%, black 20%, black 80%, transparent 100%);
}

.hero-content {
    position: relative;
    z-index: 1;
    display: flex;
    flex-direction: column;
    gap: 1.75rem;
}

/* 徽章优化 */
.hero-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.625rem;
    width: fit-content;
    padding: 0.5rem 1.125rem;
    background: 
        linear-gradient(135deg, rgba(64, 158, 255, 0.12) 0%, rgba(103, 194, 58, 0.08) 100%);
    border: 1px solid rgba(64, 158, 255, 0.25);
    border-radius: 24px;
    box-shadow: 
        0 2px 8px rgba(0, 0, 0, 0.1),
        inset 0 1px 0 rgba(255, 255, 255, 0.08);
}

.badge-icon {
    width: 24px;
    height: 24px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: linear-gradient(135deg, rgba(64, 158, 255, 0.3) 0%, rgba(64, 158, 255, 0.1) 100%);
    border-radius: 50%;
}

.badge-icon .el-icon {
    color: #409eff;
}

.hero-badge span {
    font-size: 0.8125rem;
    font-weight: 600;
    color: rgba(255, 255, 255, 0.85);
    letter-spacing: 0.5px;
}

/* 标题层级强化 */
.hero-title {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    margin: 0;
}

.title-line {
    display: block;
    font-size: 3.25rem;
    font-weight: 800;
    color: rgba(255, 255, 255, 0.95);
    line-height: 1.15;
    letter-spacing: -0.02em;
}

.title-highlight {
    background: linear-gradient(135deg, #409eff 0%, #67c23a 60%, #409eff 100%);
    background-size: 200% auto;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

.title-secondary {
    font-size: 1.5rem;
    font-weight: 500;
    color: rgba(255, 255, 255, 0.6);
}

.hero-subtitle {
    font-size: 1.0625rem;
    color: rgba(255, 255, 255, 0.5);
    margin: 0;
    line-height: 1.7;
    max-width: 520px;
}

/* CTA 按钮区优化 */
.hero-actions {
    display: flex;
    gap: 1rem;
    margin-top: 0.5rem;
}

.hero-cta {
    position: relative;
    display: inline-flex;
    align-items: center;
    gap: 0.625rem;
    height: 52px;
    padding: 0 1.75rem;
    font-size: 1rem;
    font-weight: 600;
    border: none;
    border-radius: 12px;
    cursor: pointer;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    overflow: hidden;
}

.hero-cta.primary {
    background: linear-gradient(135deg, #409eff 0%, #1677ff 50%, #409eff 100%);
    background-size: 200% auto;
    color: white;
    box-shadow: 
        0 4px 20px rgba(64, 158, 255, 0.35),
        0 2px 8px rgba(0, 0, 0, 0.2),
        inset 0 1px 0 rgba(255, 255, 255, 0.2);
}

.hero-cta.primary:hover {
    background-position: right center;
    transform: translateY(-2px);
    box-shadow: 
        0 8px 28px rgba(64, 158, 255, 0.45),
        0 4px 12px rgba(0, 0, 0, 0.25),
        inset 0 1px 0 rgba(255, 255, 255, 0.25);
}

.hero-cta.primary:active {
    transform: translateY(0);
    box-shadow: 
        0 2px 12px rgba(64, 158, 255, 0.3),
        inset 0 2px 4px rgba(0, 0, 0, 0.2);
}

.cta-glow {
    position: absolute;
    inset: 0;
    background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
    transform: translateX(-100%);
    transition: transform 0.6s ease;
}

.hero-cta.primary:hover .cta-glow {
    transform: translateX(100%);
}

.cta-arrow {
    margin-left: 0.25rem;
    transition: transform 0.3s ease;
}

.hero-cta.primary:hover .cta-arrow {
    transform: translateX(4px);
}

.hero-cta.secondary {
    background: rgba(255, 255, 255, 0.04);
    border: 1.5px solid rgba(255, 255, 255, 0.12);
    color: rgba(255, 255, 255, 0.85);
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.hero-cta.secondary:hover {
    background: rgba(255, 255, 255, 0.08);
    border-color: rgba(64, 158, 255, 0.3);
    color: rgba(255, 255, 255, 0.95);
    transform: translateY(-2px);
    box-shadow: 0 4px 16px rgba(64, 158, 255, 0.15);
}

/* 统计数据 */
.hero-stats {
    display: flex;
    align-items: center;
    gap: 1.5rem;
    margin-top: 1rem;
    padding-top: 1.5rem;
    border-top: 1px solid rgba(255, 255, 255, 0.06);
}

.stat-item {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
}

.stat-value {
    font-size: 1.25rem;
    font-weight: 700;
    color: rgba(255, 255, 255, 0.9);
}

.stat-label {
    font-size: 0.75rem;
    color: rgba(255, 255, 255, 0.4);
    letter-spacing: 0.5px;
}

.stat-divider {
    width: 1px;
    height: 32px;
    background: rgba(255, 255, 255, 0.08);
}

/* ========== Hero 右侧视觉区（全新设计） ========== */
.hero-visual {
    position: relative;
    z-index: 1;
    height: 420px;
    display: flex;
    align-items: center;
    justify-content: center;
}

.visual-container {
    position: relative;
    width: 360px;
    height: 360px;
}

/* 中心核心节点 */
.core-node {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    width: 100px;
    height: 100px;
}

.core-ring {
    position: absolute;
    inset: 0;
    border-radius: 50%;
    border: 2px solid transparent;
}

.core-ring.ring-1 {
    background: linear-gradient(135deg, rgba(64, 158, 255, 0.2), rgba(103, 194, 58, 0.15));
    border: 2px solid rgba(64, 158, 255, 0.25);
    animation: pulse-ring 3s ease-in-out infinite;
}

.core-ring.ring-2 {
    inset: 8px;
    border-color: rgba(64, 158, 255, 0.15);
    animation: pulse-ring 3s ease-in-out infinite 0.5s;
}

@keyframes pulse-ring {
    0%, 100% { transform: scale(1); opacity: 0.6; }
    50% { transform: scale(1.05); opacity: 1; }
}

.core-icon {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    width: 56px;
    height: 56px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: linear-gradient(135deg, rgba(64, 158, 255, 0.25) 0%, rgba(22, 119, 255, 0.15) 100%);
    border: 1px solid rgba(64, 158, 255, 0.35);
    border-radius: 50%;
    box-shadow: 
        0 0 30px rgba(64, 158, 255, 0.3),
        inset 0 1px 0 rgba(255, 255, 255, 0.1);
}

.core-icon .el-icon {
    color: #fff;
    filter: drop-shadow(0 1px 2px rgba(0, 0, 0, 0.3));
}

/* 环绕节点 */
.orbit-nodes {
    position: absolute;
    inset: 0;
}

.orbit-node {
    position: absolute;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.375rem;
    padding: 0.75rem 1rem;
    background: rgba(30, 35, 45, 0.8);
    border: 1px solid rgba(64, 158, 255, 0.2);
    border-radius: 12px;
    backdrop-filter: blur(10px);
    transition: all 0.3s ease;
}

.orbit-node:hover {
    transform: scale(1.05);
    border-color: rgba(64, 158, 255, 0.4);
    box-shadow: 0 4px 20px rgba(64, 158, 255, 0.2);
}

.orbit-node .node-icon {
    width: 36px;
    height: 36px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: linear-gradient(135deg, rgba(64, 158, 255, 0.15) 0%, rgba(64, 158, 255, 0.05) 100%);
    border-radius: 8px;
}

.orbit-node .node-icon .el-icon {
    color: #409eff;
}

.orbit-node span {
    font-size: 0.6875rem;
    font-weight: 500;
    color: rgba(255, 255, 255, 0.6);
}

.orbit-node.node-detect { top: 5%; left: 50%; transform: translateX(-50%); }
.orbit-node.node-mask { top: 50%; right: 0; transform: translateY(-50%); }
.orbit-node.node-enhance { bottom: 5%; left: 50%; transform: translateX(-50%); }
.orbit-node.node-video { top: 50%; left: 0; transform: translateY(-50%); }

/* 连接线 */
.connection-lines {
    position: absolute;
    inset: 0;
    pointer-events: none;
}

.conn-line {
    position: absolute;
    height: 1px;
    background: linear-gradient(90deg, 
        transparent, 
        rgba(64, 158, 255, 0.3) 20%, 
        rgba(64, 158, 255, 0.3) 80%, 
        transparent
    );
}

.line-to-detect { top: 18%; left: 40%; width: 20%; transform: rotate(-90deg); transform-origin: left; }
.line-to-mask { top: 40%; right: 18%; width: 20%; }
.line-to-enhance { bottom: 18%; left: 40%; width: 20%; transform: rotate(90deg); transform-origin: left; }
.line-to-video { top: 40%; left: 18%; width: 20%; }

/* 外围装饰网格 */
.decoration-grid {
    position: absolute;
    inset: -40px;
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 1rem;
    opacity: 0.3;
    pointer-events: none;
}

.deco-cell {
    border: 1px solid rgba(64, 158, 255, 0.1);
    border-radius: 8px;
}

.deco-cell:nth-child(3n) {
    border-color: rgba(103, 194, 58, 0.15);
}

/* ========== 核心功能入口区 ========== */
/* 核心功能入口区 - 保持主视觉地位 */
.features-section {
    margin-bottom: 4rem;
}

.features-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 1rem;
}

/* 功能卡片 - 统一边框透明度为 0.06 */
.feature-card {
    position: relative;
    display: flex;
    align-items: flex-start;
    gap: 1rem;
    padding: 1.25rem;
    background: rgba(30, 30, 40, 0.4);
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 14px;
    cursor: pointer;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    overflow: hidden;
}

/* 卡片背景层 */
.card-bg-layer {
    position: absolute;
    inset: 0;
    background: linear-gradient(145deg, rgba(40, 44, 60, 0.3) 0%, rgba(30, 30, 40, 0.2) 100%);
    opacity: 0;
    transition: opacity 0.35s ease;
}

/* 卡片发光层 */
.card-glow-layer {
    position: absolute;
    inset: -1px;
    background: radial-gradient(ellipse at 50% 0%, rgba(64, 158, 255, 0.15) 0%, transparent 60%);
    opacity: 0;
    transition: opacity 0.35s ease;
    pointer-events: none;
}

/* Hover 状态 - 统一上浮 2px，收敛发光 */
.feature-card:hover {
    transform: translateY(-2px);
    border-color: rgba(64, 158, 255, 0.18);
    box-shadow: 
        0 10px 32px rgba(0, 0, 0, 0.25),
        0 2px 8px rgba(64, 158, 255, 0.08);
}

.feature-card:hover .card-bg-layer {
    opacity: 1;
}

.feature-card:hover .card-glow-layer {
    opacity: 1;
}

/* Active/Pressed 状态 */
.feature-card:active {
    transform: translateY(-1px) scale(0.995);
    transition-duration: 0.1s;
}

/* 主题色差异化 - 各模块主色调 */
.feature-card.theme-cyan:hover {
    border-color: rgba(0, 200, 200, 0.25);
    box-shadow: 
        0 12px 40px rgba(0, 0, 0, 0.3),
        0 4px 12px rgba(0, 200, 200, 0.08);
}
.feature-card.theme-cyan:hover .card-glow-layer {
    background: radial-gradient(ellipse at 50% 0%, rgba(0, 200, 200, 0.12) 0%, transparent 60%);
}

.feature-card.theme-purple:hover {
    border-color: rgba(150, 100, 255, 0.25);
    box-shadow: 
        0 12px 40px rgba(0, 0, 0, 0.3),
        0 4px 12px rgba(150, 100, 255, 0.08);
}
.feature-card.theme-purple:hover .card-glow-layer {
    background: radial-gradient(ellipse at 50% 0%, rgba(150, 100, 255, 0.12) 0%, transparent 60%);
}

.feature-card.theme-green:hover {
    border-color: rgba(103, 194, 58, 0.25);
    box-shadow: 
        0 12px 40px rgba(0, 0, 0, 0.3),
        0 4px 12px rgba(103, 194, 58, 0.08);
}
.feature-card.theme-green:hover .card-glow-layer {
    background: radial-gradient(ellipse at 50% 0%, rgba(103, 194, 58, 0.12) 0%, transparent 60%);
}

.feature-card.theme-gradient:hover {
    border-color: rgba(103, 194, 58, 0.25);
    box-shadow: 
        0 12px 40px rgba(0, 0, 0, 0.3),
        0 4px 16px rgba(64, 158, 255, 0.12),
        0 4px 16px rgba(103, 194, 58, 0.08);
}

/* 图标容器 - 统一 48px，更克制 */
.feature-icon-wrapper {
    position: relative;
    width: 48px;
    height: 48px;
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: center;
}

/* 图标层1 - 外发光底座 */
/* 图标层统一 12px 圆角，收敛发光 */
.icon-layer {
    position: absolute;
    border-radius: 12px;
    transition: all 0.3s ease;
}

.icon-layer.layer-1 {
    inset: 0;
    background: linear-gradient(135deg, rgba(64, 158, 255, 0.15) 0%, rgba(22, 119, 255, 0.1) 100%);
    border: 1px solid rgba(64, 158, 255, 0.25);
    box-shadow: 
        0 2px 6px rgba(0, 0, 0, 0.15),
        0 2px 8px rgba(64, 158, 255, 0.1);
}

.icon-layer.layer-2 {
    inset: 2px;
    background: linear-gradient(145deg, rgba(255, 255, 255, 0.06) 0%, rgba(64, 158, 255, 0.03) 50%, transparent 100%);
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 10px;
}

.icon-layer.layer-3 {
    inset: 5px;
    background: linear-gradient(145deg, rgba(30, 40, 60, 0.5) 0%, rgba(20, 30, 50, 0.7) 100%);
    border: 1px solid rgba(64, 158, 255, 0.12);
    border-radius: 7px;
    box-shadow: inset 0 1px 2px rgba(0, 0, 0, 0.15);
}

/* 图标辉光 */
.icon-glow {
    position: absolute;
    inset: -2px;
    background: radial-gradient(circle at center, rgba(64, 158, 255, 0.4) 0%, transparent 70%);
    opacity: 0;
    transition: opacity 0.35s ease;
    pointer-events: none;
}

/* 图标本身 */
.feature-icon {
    position: relative;
    z-index: 2;
    color: rgba(255, 255, 255, 0.9);
    filter: drop-shadow(0 1px 2px rgba(0, 0, 0, 0.3));
    transition: all 0.35s ease;
}

/* Hover 时图标容器效果 */
.feature-card:hover .icon-layer.layer-1 {
    background: linear-gradient(135deg, rgba(64, 158, 255, 0.35) 0%, rgba(22, 119, 255, 0.25) 100%);
    border-color: rgba(64, 158, 255, 0.5);
    box-shadow: 
        0 2px 8px rgba(0, 0, 0, 0.2),
        0 6px 20px rgba(64, 158, 255, 0.35),
        inset 0 1px 1px rgba(255, 255, 255, 0.25);
}

.feature-card:hover .icon-layer.layer-2 {
    background: linear-gradient(145deg, rgba(255, 255, 255, 0.15) 0%, rgba(64, 158, 255, 0.1) 50%, transparent 100%);
}

.feature-card:hover .icon-glow {
    opacity: 1;
}

.feature-card:hover .feature-icon {
    transform: scale(1.05);
    filter: drop-shadow(0 1px 2px rgba(0, 0, 0, 0.3)) drop-shadow(0 0 8px rgba(64, 158, 255, 0.4));
}

/* 主题差异化 - 图标容器 */
.feature-card.theme-cyan .icon-layer.layer-1 {
    background: linear-gradient(135deg, rgba(0, 200, 200, 0.2) 0%, rgba(0, 150, 180, 0.15) 100%);
    border-color: rgba(0, 200, 200, 0.3);
    box-shadow: 
        0 2px 8px rgba(0, 0, 0, 0.2),
        0 4px 16px rgba(0, 200, 200, 0.15),
        inset 0 1px 1px rgba(255, 255, 255, 0.15);
}
.feature-card.theme-cyan:hover .icon-layer.layer-1 {
    background: linear-gradient(135deg, rgba(0, 200, 200, 0.35) 0%, rgba(0, 150, 180, 0.25) 100%);
    border-color: rgba(0, 200, 200, 0.5);
    box-shadow: 
        0 2px 8px rgba(0, 0, 0, 0.2),
        0 6px 20px rgba(0, 200, 200, 0.3),
        inset 0 1px 1px rgba(255, 255, 255, 0.25);
}
.feature-card.theme-cyan .icon-glow {
    background: radial-gradient(circle at center, rgba(0, 200, 200, 0.4) 0%, transparent 70%);
}

.feature-card.theme-purple .icon-layer.layer-1 {
    background: linear-gradient(135deg, rgba(150, 100, 255, 0.2) 0%, rgba(120, 80, 220, 0.15) 100%);
    border-color: rgba(150, 100, 255, 0.3);
    box-shadow: 
        0 2px 8px rgba(0, 0, 0, 0.2),
        0 4px 16px rgba(150, 100, 255, 0.15),
        inset 0 1px 1px rgba(255, 255, 255, 0.15);
}
.feature-card.theme-purple:hover .icon-layer.layer-1 {
    background: linear-gradient(135deg, rgba(150, 100, 255, 0.35) 0%, rgba(120, 80, 220, 0.25) 100%);
    border-color: rgba(150, 100, 255, 0.5);
    box-shadow: 
        0 2px 8px rgba(0, 0, 0, 0.2),
        0 6px 20px rgba(150, 100, 255, 0.3),
        inset 0 1px 1px rgba(255, 255, 255, 0.25);
}
.feature-card.theme-purple .icon-glow {
    background: radial-gradient(circle at center, rgba(150, 100, 255, 0.4) 0%, transparent 70%);
}

.feature-card.theme-green .icon-layer.layer-1 {
    background: linear-gradient(135deg, rgba(103, 194, 58, 0.2) 0%, rgba(80, 160, 40, 0.15) 100%);
    border-color: rgba(103, 194, 58, 0.3);
    box-shadow: 
        0 2px 8px rgba(0, 0, 0, 0.2),
        0 4px 16px rgba(103, 194, 58, 0.15),
        inset 0 1px 1px rgba(255, 255, 255, 0.15);
}
.feature-card.theme-green:hover .icon-layer.layer-1 {
    background: linear-gradient(135deg, rgba(103, 194, 58, 0.35) 0%, rgba(80, 160, 40, 0.25) 100%);
    border-color: rgba(103, 194, 58, 0.5);
    box-shadow: 
        0 2px 8px rgba(0, 0, 0, 0.2),
        0 6px 20px rgba(103, 194, 58, 0.3),
        inset 0 1px 1px rgba(255, 255, 255, 0.25);
}
.feature-card.theme-green .icon-glow {
    background: radial-gradient(circle at center, rgba(103, 194, 58, 0.4) 0%, transparent 70%);
}

.feature-card.theme-gradient .icon-layer.layer-1 {
    background: linear-gradient(135deg, rgba(64, 158, 255, 0.25) 0%, rgba(103, 194, 58, 0.2) 100%);
    border-color: rgba(64, 158, 255, 0.35);
    box-shadow: 
        0 2px 8px rgba(0, 0, 0, 0.2),
        0 4px 20px rgba(64, 158, 255, 0.2),
        0 4px 20px rgba(103, 194, 58, 0.1),
        inset 0 1px 1px rgba(255, 255, 255, 0.15);
}
.feature-card.theme-gradient:hover .icon-layer.layer-1 {
    background: linear-gradient(135deg, rgba(64, 158, 255, 0.4) 0%, rgba(103, 194, 58, 0.3) 100%);
    border-color: rgba(103, 194, 58, 0.5);
    box-shadow: 
        0 2px 8px rgba(0, 0, 0, 0.2),
        0 6px 24px rgba(64, 158, 255, 0.3),
        0 6px 24px rgba(103, 194, 58, 0.2),
        inset 0 1px 1px rgba(255, 255, 255, 0.25);
}
.feature-card.theme-gradient .icon-glow {
    background: radial-gradient(circle at center, rgba(103, 194, 58, 0.4) 0%, transparent 70%);
}

/* 内容区 */
.feature-content {
    flex: 1;
    min-width: 0;
    position: relative;
    z-index: 1;
}

.feature-title {
    font-size: 1.1rem;
    font-weight: 600;
    color: rgba(255, 255, 255, 0.95);
    margin: 0 0 0.375rem;
    letter-spacing: -0.01em;
}

.feature-desc {
    font-size: 0.8125rem;
    color: rgba(255, 255, 255, 0.5);
    margin: 0 0 0.75rem;
    line-height: 1.5;
}

/* 卡片底部 - 标签和CTA */
.feature-footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.75rem;
}

.feature-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 0.375rem;
}

.feature-tag {
    display: inline-flex;
    align-items: center;
    padding: 0.25rem 0.5rem;
    font-size: 0.6875rem;
    font-weight: 500;
    color: rgba(255, 255, 255, 0.6);
    background: rgba(64, 158, 255, 0.1);
    border: 1px solid rgba(64, 158, 255, 0.15);
    border-radius: 4px;
    transition: all 0.3s ease;
}

.feature-card:hover .feature-tag {
    background: rgba(64, 158, 255, 0.15);
    border-color: rgba(64, 158, 255, 0.25);
    color: rgba(255, 255, 255, 0.75);
}

/* 主题标签色 */
.feature-card.theme-cyan .feature-tag {
    background: rgba(0, 200, 200, 0.1);
    border-color: rgba(0, 200, 200, 0.15);
}
.feature-card.theme-cyan:hover .feature-tag {
    background: rgba(0, 200, 200, 0.15);
    border-color: rgba(0, 200, 200, 0.25);
}

.feature-card.theme-purple .feature-tag {
    background: rgba(150, 100, 255, 0.1);
    border-color: rgba(150, 100, 255, 0.15);
}
.feature-card.theme-purple:hover .feature-tag {
    background: rgba(150, 100, 255, 0.15);
    border-color: rgba(150, 100, 255, 0.25);
}

.feature-card.theme-green .feature-tag {
    background: rgba(103, 194, 58, 0.1);
    border-color: rgba(103, 194, 58, 0.15);
}
.feature-card.theme-green:hover .feature-tag {
    background: rgba(103, 194, 58, 0.15);
    border-color: rgba(103, 194, 58, 0.25);
}

.feature-card.theme-gradient .feature-tag {
    background: rgba(103, 194, 58, 0.1);
    border-color: rgba(103, 194, 58, 0.15);
}
.feature-card.theme-gradient:hover .feature-tag {
    background: rgba(103, 194, 58, 0.15);
    border-color: rgba(103, 194, 58, 0.25);
}

/* 进入指示区 */
.feature-action {
    position: absolute;
    right: 1.25rem;
    bottom: 1.25rem;
    z-index: 2;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.action-hint {
    display: flex;
    align-items: center;
    gap: 0.25rem;
    font-size: 0.75rem;
    color: rgba(255, 255, 255, 0.35);
    opacity: 0;
    transform: translateX(-8px);
    transition: all 0.3s ease;
}

.hint-text {
    font-weight: 500;
}

.hint-arrow {
    transition: transform 0.3s ease;
}

.action-arrow {
    width: 32px;
    height: 32px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: rgba(255, 255, 255, 0.25);
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 8px;
    transition: all 0.35s cubic-bezier(0.4, 0, 0.2, 1);
}

/* Hover 时进入指示效果 */
.feature-card:hover .action-hint {
    opacity: 1;
    transform: translateX(0);
    color: rgba(64, 158, 255, 0.8);
}

.feature-card:hover .action-arrow {
    color: #409eff;
    background: rgba(64, 158, 255, 0.1);
    border-color: rgba(64, 158, 255, 0.25);
    transform: translateX(2px);
}

.feature-card:hover .hint-arrow {
    transform: translateX(2px);
}

/* 主题色进入指示 */
.feature-card.theme-cyan:hover .action-hint { color: rgba(0, 200, 200, 0.8); }
.feature-card.theme-cyan:hover .action-arrow { 
    color: #00c8c8; 
    background: rgba(0, 200, 200, 0.1);
    border-color: rgba(0, 200, 200, 0.25);
}

.feature-card.theme-purple:hover .action-hint { color: rgba(150, 100, 255, 0.8); }
.feature-card.theme-purple:hover .action-arrow { 
    color: #9678ff; 
    background: rgba(150, 100, 255, 0.1);
    border-color: rgba(150, 100, 255, 0.25);
}

.feature-card.theme-green:hover .action-hint { color: rgba(103, 194, 58, 0.8); }
.feature-card.theme-green:hover .action-arrow { 
    color: #67c23a; 
    background: rgba(103, 194, 58, 0.1);
    border-color: rgba(103, 194, 58, 0.25);
}

.feature-card.theme-gradient:hover .action-hint { color: rgba(103, 194, 58, 0.9); }
.feature-card.theme-gradient:hover .action-arrow { 
    color: #67c23a; 
    background: rgba(103, 194, 58, 0.12);
    border-color: rgba(103, 194, 58, 0.3);
}

/* ========== 平台能力概览区 - 轻度呈现 ========== */
.capabilities-section {
    margin-bottom: 3rem;
}

.capabilities-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 1rem;
}

/* 能力卡片 - 统一边框透明度 0.05，更收敛 */
.capability-card {
    position: relative;
    padding: 1.25rem;
    background: rgba(30, 30, 40, 0.35);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 12px;
    text-align: left;
    transition: all 0.3s ease;
    overflow: hidden;
}

/* 卡片背景层 */
.capability-bg {
    position: absolute;
    inset: 0;
    background: linear-gradient(145deg, rgba(40, 44, 60, 0.2) 0%, transparent 60%);
    opacity: 0;
    transition: opacity 0.3s ease;
}

/* 卡片辉光层 - 顶部微光 */
.capability-glow {
    position: absolute;
    inset: 0;
    background: radial-gradient(ellipse at 50% 0%, rgba(64, 158, 255, 0.08) 0%, transparent 50%);
    opacity: 0;
    transition: opacity 0.3s ease;
    pointer-events: none;
}

/* Hover 状态 - 统一上浮 2px */
.capability-card:hover {
    transform: translateY(-2px);
    border-color: rgba(64, 158, 255, 0.1);
    box-shadow: 0 8px 20px rgba(0, 0, 0, 0.2);
}

.capability-card:hover .capability-bg {
    opacity: 1;
}

.capability-card:hover .capability-glow {
    opacity: 1;
}

/* Active 状态 */
.capability-card:active {
    transform: translateY(-1px);
    transition-duration: 0.1s;
}

/* 主题色差异化 - 比功能入口区更收敛 */
.capability-card.accent-cyan:hover {
    border-color: rgba(0, 200, 200, 0.12);
}
.capability-card.accent-cyan .capability-glow {
    background: radial-gradient(ellipse at 50% 0%, rgba(0, 200, 200, 0.06) 0%, transparent 50%);
}

.capability-card.accent-purple:hover {
    border-color: rgba(150, 100, 255, 0.12);
}
.capability-card.accent-purple .capability-glow {
    background: radial-gradient(ellipse at 50% 0%, rgba(150, 100, 255, 0.06) 0%, transparent 50%);
}

.capability-card.accent-green:hover {
    border-color: rgba(103, 194, 58, 0.12);
}
.capability-card.accent-green .capability-glow {
    background: radial-gradient(ellipse at 50% 0%, rgba(103, 194, 58, 0.06) 0%, transparent 50%);
}

/* 顶部区域：数字 + 图标 */
.capability-header {
    position: relative;
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    margin-bottom: 0.875rem;
    z-index: 1;
}

/* 数字展示 - 强化视觉层级 */
.capability-number {
    position: relative;
    display: inline-block;
}

.number-digit {
    font-size: 2.25rem;
    font-weight: 800;
    line-height: 1;
    background: linear-gradient(135deg, 
        rgba(100, 180, 255, 0.9) 0%, 
        rgba(64, 158, 255, 0.7) 50%,
        rgba(103, 194, 58, 0.6) 100%
    );
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    filter: drop-shadow(0 2px 4px rgba(64, 158, 255, 0.15));
    transition: all 0.3s ease;
}

/* 数字辉光效果 */
.number-glow {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    width: 60px;
    height: 40px;
    background: radial-gradient(ellipse at center, rgba(64, 158, 255, 0.2) 0%, transparent 70%);
    opacity: 0;
    transition: opacity 0.3s ease;
    pointer-events: none;
}

.capability-card:hover .number-digit {
    filter: drop-shadow(0 2px 6px rgba(64, 158, 255, 0.25));
}

.capability-card:hover .number-glow {
    opacity: 1;
}

/* 主题色数字差异化 */
.capability-card.accent-cyan .number-digit {
    background: linear-gradient(135deg, rgba(0, 220, 220, 0.9) 0%, rgba(0, 180, 200, 0.7) 100%);
    filter: drop-shadow(0 2px 4px rgba(0, 200, 200, 0.15));
}
.capability-card.accent-cyan .number-glow {
    background: radial-gradient(ellipse at center, rgba(0, 200, 200, 0.2) 0%, transparent 70%);
}

.capability-card.accent-purple .number-digit {
    background: linear-gradient(135deg, rgba(170, 120, 255, 0.9) 0%, rgba(130, 90, 220, 0.7) 100%);
    filter: drop-shadow(0 2px 4px rgba(150, 100, 255, 0.15));
}
.capability-card.accent-purple .number-glow {
    background: radial-gradient(ellipse at center, rgba(150, 100, 255, 0.2) 0%, transparent 70%);
}

.capability-card.accent-green .number-digit {
    background: linear-gradient(135deg, rgba(123, 214, 78, 0.9) 0%, rgba(83, 174, 48, 0.7) 100%);
    filter: drop-shadow(0 2px 4px rgba(103, 194, 58, 0.15));
}
.capability-card.accent-green .number-glow {
    background: radial-gradient(ellipse at center, rgba(103, 194, 58, 0.2) 0%, transparent 70%);
}

/* 图标容器 - 克制简洁 */
.capability-icon-wrap {
    position: relative;
    width: 34px;
    height: 34px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(64, 158, 255, 0.08);
    border: 1px solid rgba(64, 158, 255, 0.15);
    border-radius: 9px;
    transition: all 0.3s ease;
}

.capability-icon {
    color: rgba(64, 158, 255, 0.7);
    transition: all 0.3s ease;
}

.capability-card:hover .capability-icon-wrap {
    background: rgba(64, 158, 255, 0.12);
    border-color: rgba(64, 158, 255, 0.25);
    transform: translateY(-1px);
}

.capability-card:hover .capability-icon {
    color: rgba(64, 158, 255, 0.9);
}

/* 图标主题色差异化 */
.capability-card.accent-cyan .capability-icon-wrap {
    background: rgba(0, 200, 200, 0.08);
    border-color: rgba(0, 200, 200, 0.15);
}
.capability-card.accent-cyan .capability-icon {
    color: rgba(0, 200, 200, 0.7);
}
.capability-card.accent-cyan:hover .capability-icon-wrap {
    background: rgba(0, 200, 200, 0.12);
    border-color: rgba(0, 200, 200, 0.25);
}
.capability-card.accent-cyan:hover .capability-icon {
    color: rgba(0, 200, 200, 0.9);
}

.capability-card.accent-purple .capability-icon-wrap {
    background: rgba(150, 100, 255, 0.08);
    border-color: rgba(150, 100, 255, 0.15);
}
.capability-card.accent-purple .capability-icon {
    color: rgba(150, 100, 255, 0.7);
}
.capability-card.accent-purple:hover .capability-icon-wrap {
    background: rgba(150, 100, 255, 0.12);
    border-color: rgba(150, 100, 255, 0.25);
}
.capability-card.accent-purple:hover .capability-icon {
    color: rgba(150, 100, 255, 0.9);
}

.capability-card.accent-green .capability-icon-wrap {
    background: rgba(103, 194, 58, 0.08);
    border-color: rgba(103, 194, 58, 0.15);
}
.capability-card.accent-green .capability-icon {
    color: rgba(103, 194, 58, 0.7);
}
.capability-card.accent-green:hover .capability-icon-wrap {
    background: rgba(103, 194, 58, 0.12);
    border-color: rgba(103, 194, 58, 0.25);
}
.capability-card.accent-green:hover .capability-icon {
    color: rgba(103, 194, 58, 0.9);
}

/* 能力标签 - 醒目但克制 */
.capability-label {
    position: relative;
    font-size: 1rem;
    font-weight: 600;
    color: rgba(255, 255, 255, 0.92);
    margin-bottom: 0.5rem;
    z-index: 1;
}

/* 说明文字 */
.capability-desc {
    position: relative;
    font-size: 0.8125rem;
    color: rgba(255, 255, 255, 0.45);
    margin: 0;
    line-height: 1.55;
    z-index: 1;
}

/* 响应式适配 */
@media (max-width: 1024px) {
    .capabilities-grid {
        grid-template-columns: repeat(2, 1fr);
    }
}

@media (max-width: 640px) {
    .capabilities-grid {
        grid-template-columns: 1fr;
        gap: 1rem;
    }
    
    .capability-card {
        padding: 1.25rem;
    }
    
    .number-digit {
        font-size: 2rem;
    }
}

/* ========== 智能流程亮点区 ========== */
.workflow-highlight-section {
    position: relative;
    padding: 2.5rem 0;
    background: 
        linear-gradient(135deg, rgba(64, 158, 255, 0.03) 0%, rgba(103, 194, 58, 0.02) 100%),
        rgba(25, 28, 38, 0.4);
    border: 1px solid rgba(64, 158, 255, 0.1);
    border-radius: 20px;
    margin-bottom: 2.5rem;
    overflow: hidden;
}

/* 区域背景装饰 */
.highlight-bg-decoration {
    position: absolute;
    inset: 0;
    pointer-events: none;
    background: 
        radial-gradient(ellipse at 20% 0%, rgba(64, 158, 255, 0.06) 0%, transparent 50%),
        radial-gradient(ellipse at 80% 100%, rgba(103, 194, 58, 0.04) 0%, transparent 40%);
}

/* 流程链容器 */
.workflow-chain {
    position: relative;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0;
    padding: 2rem;
    flex-wrap: wrap;
}

.workflow-step {
    display: flex;
    align-items: center;
}

/* 步骤卡片 - 统一边框 0.06，圆角 14px */
.step-card {
    position: relative;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.5rem;
    padding: 1.25rem 1.5rem;
    background: rgba(30, 33, 45, 0.5);
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 14px;
    min-width: 120px;
    transition: all 0.3s ease;
}

.step-card-bg {
    position: absolute;
    inset: 0;
    border-radius: 18px;
    background: linear-gradient(145deg, rgba(40, 45, 60, 0.3) 0%, transparent 60%);
    opacity: 0;
    transition: opacity 0.35s ease;
}

.step-card-glow {
    position: absolute;
    inset: -1px;
    border-radius: 19px;
    background: radial-gradient(ellipse at 50% 0%, rgba(64, 158, 255, 0.15) 0%, transparent 60%);
    opacity: 0;
    transition: opacity 0.35s ease;
    pointer-events: none;
}

/* 步骤卡片 hover - 统一上浮 2px */
.step-card:hover {
    transform: translateY(-2px);
    border-color: rgba(64, 158, 255, 0.15);
    box-shadow: 
        0 10px 24px rgba(0, 0, 0, 0.25),
        0 2px 8px rgba(64, 158, 255, 0.06);
}

.step-card:hover .step-card-bg {
    opacity: 1;
}

.step-card:hover .step-card-glow {
    opacity: 1;
}

/* 最后一步特殊样式 */
.workflow-step.is-last .step-card {
    border-color: rgba(103, 194, 58, 0.12);
}

.workflow-step.is-last .step-card:hover {
    border-color: rgba(103, 194, 58, 0.22);
    box-shadow: 
        0 12px 32px rgba(0, 0, 0, 0.3),
        0 4px 16px rgba(103, 194, 58, 0.1);
}

.workflow-step.is-last .step-card-glow {
    background: radial-gradient(ellipse at 50% 0%, rgba(103, 194, 58, 0.15) 0%, transparent 60%);
}

/* 步骤指示器（数字 + 状态环） */
.step-indicator {
    position: relative;
    display: flex;
    align-items: center;
    justify-content: center;
    width: 36px;
    height: 36px;
    margin-bottom: 0.25rem;
}

.step-ring {
    position: absolute;
    inset: 0;
    border: 2px solid rgba(64, 158, 255, 0.2);
    border-radius: 50%;
    transition: all 0.35s ease;
}

.step-dot {
    position: absolute;
    width: 8px;
    height: 8px;
    background: rgba(64, 158, 255, 0.6);
    border-radius: 50%;
    transition: all 0.35s ease;
}

.step-number {
    position: relative;
    font-size: 0.6875rem;
    font-weight: 700;
    color: rgba(255, 255, 255, 0.7);
    letter-spacing: 0.5px;
    z-index: 1;
}

.step-card:hover .step-ring {
    border-color: rgba(64, 158, 255, 0.4);
    transform: scale(1.1);
}

.step-card:hover .step-dot {
    background: rgba(64, 158, 255, 0.9);
    box-shadow: 0 0 12px rgba(64, 158, 255, 0.5);
}

/* 最后一步指示器 */
.workflow-step.is-last .step-ring {
    border-color: rgba(103, 194, 58, 0.25);
}

.workflow-step.is-last .step-dot {
    background: rgba(103, 194, 58, 0.7);
}

.workflow-step.is-last .step-card:hover .step-ring {
    border-color: rgba(103, 194, 58, 0.45);
}

.workflow-step.is-last .step-card:hover .step-dot {
    background: rgba(103, 194, 58, 0.9);
    box-shadow: 0 0 12px rgba(103, 194, 58, 0.5);
}

/* 图标容器 */
.step-icon-wrap {
    position: relative;
    display: flex;
    align-items: center;
    justify-content: center;
    width: 44px;
    height: 44px;
    background: linear-gradient(135deg, rgba(64, 158, 255, 0.1) 0%, rgba(22, 119, 255, 0.08) 100%);
    border: 1px solid rgba(64, 158, 255, 0.15);
    border-radius: 12px;
    transition: all 0.35s ease;
}

.step-icon {
    color: rgba(100, 180, 255, 0.9);
    transition: all 0.35s ease;
}

.step-card:hover .step-icon-wrap {
    background: linear-gradient(135deg, rgba(64, 158, 255, 0.18) 0%, rgba(22, 119, 255, 0.12) 100%);
    border-color: rgba(64, 158, 255, 0.28);
    transform: scale(1.05);
}

.step-card:hover .step-icon {
    color: #409eff;
    filter: drop-shadow(0 0 8px rgba(64, 158, 255, 0.4));
}

/* 最后一步图标 */
.workflow-step.is-last .step-icon-wrap {
    background: linear-gradient(135deg, rgba(103, 194, 58, 0.1) 0%, rgba(80, 160, 40, 0.08) 100%);
    border-color: rgba(103, 194, 58, 0.18);
}

.workflow-step.is-last .step-icon {
    color: rgba(123, 214, 78, 0.9);
}

.workflow-step.is-last .step-card:hover .step-icon-wrap {
    background: linear-gradient(135deg, rgba(103, 194, 58, 0.18) 0%, rgba(80, 160, 40, 0.12) 100%);
    border-color: rgba(103, 194, 58, 0.3);
}

.workflow-step.is-last .step-card:hover .step-icon {
    color: #67c23a;
    filter: drop-shadow(0 0 8px rgba(103, 194, 58, 0.4));
}

/* 步骤名称 */
.step-name {
    font-size: 0.9375rem;
    font-weight: 600;
    color: rgba(255, 255, 255, 0.9);
    letter-spacing: -0.01em;
}

/* 微标签 */
.step-hint {
    font-size: 0.6875rem;
    font-weight: 500;
    color: rgba(255, 255, 255, 0.4);
    padding: 0.125rem 0.5rem;
    background: rgba(255, 255, 255, 0.05);
    border-radius: 4px;
    letter-spacing: 0.5px;
}

.workflow-step.is-last .step-hint {
    color: rgba(103, 194, 58, 0.6);
    background: rgba(103, 194, 58, 0.08);
}

/* 步骤连接线 - 更有流程推进感 */
.step-connector {
    display: flex;
    align-items: center;
    padding: 0 0.75rem;
    position: relative;
}

.connector-track {
    position: relative;
    width: 48px;
    height: 2px;
    background: rgba(255, 255, 255, 0.06);
    border-radius: 1px;
    overflow: hidden;
}

.connector-progress {
    position: absolute;
    inset: 0;
    background: linear-gradient(90deg, rgba(64, 158, 255, 0.4), rgba(103, 194, 58, 0.5));
    transform: scaleX(0);
    transform-origin: left;
    transition: transform 0.6s cubic-bezier(0.4, 0, 0.2, 1);
}

.workflow-highlight-section:hover .connector-progress {
    transform: scaleX(1);
}

/* 连接节点 */
.connector-node {
    position: absolute;
    left: 50%;
    transform: translateX(-50%);
    width: 20px;
    height: 20px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(30, 33, 45, 0.8);
    border: 1px solid rgba(64, 158, 255, 0.25);
    border-radius: 50%;
    transition: all 0.35s ease;
}

.node-icon {
    color: rgba(64, 158, 255, 0.7);
    transition: all 0.35s ease;
}

.workflow-highlight-section:hover .connector-node {
    border-color: rgba(103, 194, 58, 0.4);
    background: rgba(30, 33, 45, 0.95);
}

.workflow-highlight-section:hover .node-icon {
    color: rgba(103, 194, 58, 0.9);
    transform: translateX(1px);
}

/* CTA 按钮 - 精致化 */
.workflow-cta {
    text-align: center;
    margin-top: 2rem;
    position: relative;
    z-index: 1;
}

.highlight-cta-btn {
    position: relative;
    display: inline-flex;
    align-items: center;
    gap: 0.625rem;
    padding: 0.875rem 1.75rem;
    font-size: 0.9375rem;
    font-weight: 500;
    color: rgba(255, 255, 255, 0.95);
    background: linear-gradient(135deg, rgba(64, 158, 255, 0.15) 0%, rgba(22, 119, 255, 0.1) 100%);
    border: 1px solid rgba(64, 158, 255, 0.25);
    border-radius: 10px;
    cursor: pointer;
    overflow: hidden;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.cta-btn-glow {
    position: absolute;
    inset: 0;
    background: linear-gradient(90deg, transparent, rgba(64, 158, 255, 0.2), transparent);
    transform: translateX(-100%);
    transition: transform 0.6s ease;
}

.highlight-cta-btn:hover {
    background: linear-gradient(135deg, rgba(64, 158, 255, 0.25) 0%, rgba(22, 119, 255, 0.15) 100%);
    border-color: rgba(64, 158, 255, 0.4);
    box-shadow: 
        0 4px 20px rgba(64, 158, 255, 0.2),
        0 2px 8px rgba(0, 0, 0, 0.2);
    transform: translateY(-1px);
}

.highlight-cta-btn:hover .cta-btn-glow {
    transform: translateX(100%);
}

.highlight-cta-btn:hover .cta-arrow {
    transform: translateX(3px);
}

.highlight-cta-btn:active {
    transform: translateY(0);
    transition-duration: 0.1s;
}

.cta-arrow {
    transition: transform 0.3s ease;
}

/* ========== 快捷入口区 - 轻度收敛 ========== */
.quick-access-section {
    padding: 0 0 2rem;
}

.quick-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 1rem;
}

/* 快捷卡片 - 更轻量，不抢眼 */
.quick-card {
    position: relative;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    padding: 1rem 1.25rem;
    background: rgba(30, 30, 40, 0.25);
    border-radius: 12px;
    cursor: pointer;
    transition: all 0.3s ease;
    overflow: hidden;
}

/* 卡片背景层 */
.quick-card-bg {
    position: absolute;
    inset: 0;
    background: linear-gradient(145deg, rgba(35, 38, 50, 0.4) 0%, rgba(30, 30, 40, 0.2) 100%);
    opacity: 0;
    transition: opacity 0.3s ease;
}

/* 卡片边框层 - 统一 0.05 透明度 */
.quick-card-border {
    position: absolute;
    inset: 0;
    border-radius: 12px;
    border: 1px solid rgba(255, 255, 255, 0.05);
    transition: all 0.3s ease;
    pointer-events: none;
}

/* 快捷卡片 hover - 仅上浮 1px，更克制 */
.quick-card:hover {
    transform: translateY(-1px);
}

.quick-card:hover .quick-card-bg {
    opacity: 0.5;
}

.quick-card:hover .quick-card-border {
    border-color: rgba(64, 158, 255, 0.1);
}

/* 卡片主体内容 */
.quick-main {
    position: relative;
    display: flex;
    align-items: center;
    gap: 1rem;
    z-index: 1;
}

/* 图标容器 - 更克制 */
.quick-icon {
    position: relative;
    width: 44px;
    height: 44px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: rgba(100, 180, 255, 0.9);
    transition: all 0.3s ease;
}

.icon-bg {
    position: absolute;
    inset: 0;
    background: linear-gradient(135deg, rgba(64, 158, 255, 0.08) 0%, rgba(22, 119, 255, 0.05) 100%);
    border: 1px solid rgba(64, 158, 255, 0.12);
    border-radius: 11px;
    transition: all 0.3s ease;
}

.quick-icon .el-icon {
    position: relative;
    z-index: 1;
}

.quick-card:hover .icon-bg {
    background: linear-gradient(135deg, rgba(64, 158, 255, 0.12) 0%, rgba(22, 119, 255, 0.08) 100%);
    border-color: rgba(64, 158, 255, 0.2);
    transform: scale(1.05);
}

/* 历史记录卡片 - 绿色主题 */
.quick-card.history-card .quick-icon {
    color: rgba(123, 214, 78, 0.9);
}

.quick-card.history-card .icon-bg {
    background: linear-gradient(135deg, rgba(103, 194, 58, 0.08) 0%, rgba(80, 160, 40, 0.05) 100%);
    border-color: rgba(103, 194, 58, 0.12);
}

.quick-card.history-card:hover .icon-bg {
    background: linear-gradient(135deg, rgba(103, 194, 58, 0.12) 0%, rgba(80, 160, 40, 0.08) 100%);
    border-color: rgba(103, 194, 58, 0.2);
}

.quick-card.history-card:hover .quick-card-border {
    border-color: rgba(103, 194, 58, 0.15);
}

/* 快速开始卡片 - 强调感 */
.quick-card.start-card .quick-icon {
    color: rgba(255, 255, 255, 0.95);
}

.quick-card.start-card .icon-bg {
    background: linear-gradient(135deg, rgba(64, 158, 255, 0.25) 0%, rgba(22, 119, 255, 0.15) 100%);
    border-color: rgba(64, 158, 255, 0.35);
}

.quick-card.start-card:hover .icon-bg {
    background: linear-gradient(135deg, rgba(64, 158, 255, 0.35) 0%, rgba(22, 119, 255, 0.2) 100%);
    border-color: rgba(64, 158, 255, 0.45);
    box-shadow: 0 4px 12px rgba(64, 158, 255, 0.2);
}

.quick-card.start-card:hover .quick-card-border {
    border-color: rgba(64, 158, 255, 0.25);
}

/* 内容区 */
.quick-content {
    flex: 1;
    min-width: 0;
}

.quick-header {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.25rem;
}

.quick-content h3 {
    font-size: 1rem;
    font-weight: 600;
    color: rgba(255, 255, 255, 0.9);
    margin: 0;
    letter-spacing: -0.01em;
}

.quick-badge {
    display: inline-flex;
    align-items: center;
    padding: 0.125rem 0.375rem;
    font-size: 0.625rem;
    font-weight: 600;
    color: rgba(255, 255, 255, 0.6);
    background: rgba(255, 255, 255, 0.08);
    border-radius: 4px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.quick-badge.hot {
    color: rgba(64, 158, 255, 0.9);
    background: rgba(64, 158, 255, 0.12);
}

.quick-content p {
    font-size: 0.8125rem;
    color: rgba(255, 255, 255, 0.45);
    margin: 0;
    line-height: 1.5;
}

/* 快捷操作区 */
.quick-action {
    position: relative;
    display: flex;
    align-items: center;
    gap: 0.375rem;
    padding: 0.375rem 0.75rem;
    font-size: 0.8125rem;
    font-weight: 500;
    color: rgba(255, 255, 255, 0.5);
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 8px;
    transition: all 0.3s ease;
    z-index: 1;
}

.action-text {
    white-space: nowrap;
}

.action-arrow {
    transition: transform 0.3s ease;
}

.quick-card:hover .quick-action {
    color: rgba(255, 255, 255, 0.7);
    background: rgba(255, 255, 255, 0.06);
    border-color: rgba(255, 255, 255, 0.1);
}

.quick-card:hover .action-arrow {
    transform: translateX(2px);
}

/* 主要操作按钮样式 */
.quick-action.primary {
    color: rgba(64, 158, 255, 0.8);
    background: rgba(64, 158, 255, 0.08);
    border-color: rgba(64, 158, 255, 0.15);
}

.quick-card:hover .quick-action.primary {
    color: #409eff;
    background: rgba(64, 158, 255, 0.12);
    border-color: rgba(64, 158, 255, 0.25);
}

/* 历史记录操作按钮 */
.quick-card.history-card .quick-action {
    color: rgba(103, 194, 58, 0.7);
    background: rgba(103, 194, 58, 0.06);
    border-color: rgba(103, 194, 58, 0.12);
}

.quick-card.history-card:hover .quick-action {
    color: #67c23a;
    background: rgba(103, 194, 58, 0.1);
    border-color: rgba(103, 194, 58, 0.2);
}

/* ========== 响应式适配 ========== */
/* ========== 响应式适配 ========== */
@media (max-width: 1200px) {
    .hero-section {
        grid-template-columns: 1fr;
        text-align: center;
        gap: 3rem;
        min-height: auto;
        padding: 3rem 0 4rem;
    }
    
    .hero-content {
        align-items: center;
    }
    
    .hero-title {
        align-items: center;
    }
    
    .title-line {
        font-size: 2.75rem;
    }
    
    .title-secondary {
        font-size: 1.25rem;
    }
    
    .hero-subtitle {
        max-width: 100%;
    }
    
    .hero-stats {
        justify-content: center;
    }
    
    .hero-visual {
        height: 320px;
        order: -1;
    }
    
    .visual-container {
        width: 300px;
        height: 300px;
    }
    
    .capabilities-grid {
        grid-template-columns: repeat(2, 1fr);
    }
}

@media (max-width: 768px) {
    .home-page {
        padding: 0 1rem 2rem;
    }
    
    .hero-section {
        padding: 2rem 0 3rem;
    }
    
    .title-line {
        font-size: 2rem;
    }
    
    .title-secondary {
        font-size: 1rem;
    }
    
    .hero-subtitle {
        font-size: 0.9375rem;
    }
    
    .hero-actions {
        flex-direction: column;
        width: 100%;
    }
    
    .hero-cta {
        width: 100%;
        justify-content: center;
    }
    
    .hero-stats {
        flex-wrap: wrap;
        justify-content: center;
        gap: 1rem;
    }
    
    .stat-divider {
        display: none;
    }
    
    .hero-visual {
        height: 280px;
    }
    
    .visual-container {
        width: 260px;
        height: 260px;
    }
    
    .orbit-node {
        padding: 0.5rem 0.75rem;
    }
    
    .orbit-node .node-icon {
        width: 28px;
        height: 28px;
    }
    
    .features-grid {
        grid-template-columns: 1fr;
    }
    
    .capabilities-grid {
        grid-template-columns: 1fr;
    }
    
    .workflow-chain {
        flex-direction: column;
        gap: 1rem;
    }
    
    .step-connector {
        transform: rotate(90deg);
        padding: 0.5rem 0;
    }
    
    .quick-grid {
        grid-template-columns: 1fr;
    }
}
</style>
