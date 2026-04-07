<script setup lang="ts">
import { ref, reactive } from 'vue';
import { ElMessage, ElSelect, ElOption, ElInput, ElInputNumber } from 'element-plus';

const API_BASE = import.meta.env.DEV ? 'http://localhost:5000' : '';

// 7个核心参数
const config = reactive({
  model: 'yolo26s.pt',
  data: 'coco128.yaml',
  epochs: 1,
  imgsz: 320,
  device: 'cpu',
  amp: false,
  name: '',
});

const isRunning = ref(false);
const taskId = ref('');
const status = ref<'idle' | 'running' | 'completed' | 'error'>('idle');
const statusText = ref('准备就绪');

// 训练进度
const progress = ref(0);
const currentEpoch = ref(0);
const totalEpochs = ref(0);

// TensorBoard 状态
const tbStatus = ref<{ running: boolean; url: string | null }>({ running: false, url: null });
const tbChecking = ref(false);

// 检测 TensorBoard 状态
async function checkTensorBoard() {
  tbChecking.value = true;
  try {
    const res = await fetch(`${API_BASE}/api/train/tensorboard/status`);
    const data = await res.json();
    tbStatus.value = {
      running: data.running,
      url: data.url,
    };
  } catch (e) {
    tbStatus.value = { running: false, url: null };
  } finally {
    tbChecking.value = false;
  }
}

// 启动 TensorBoard
async function startTensorBoard() {
  try {
    const res = await fetch(`${API_BASE}/api/train/tensorboard/start`, { method: 'POST' });
    const data = await res.json();
    if (data.success) {
      ElMessage.success(data.message);
      tbStatus.value = { running: true, url: data.url };
      // 延迟一下再打开，确保服务已启动
      setTimeout(() => {
        if (data.url) window.open(data.url, '_blank');
      }, 1500);
    } else {
      ElMessage.error(data.message || '启动失败');
    }
  } catch (e) {
    ElMessage.error('启动 TensorBoard 失败');
  }
}

async function startTraining() {
  try {
    isRunning.value = true;
    status.value = 'running';
    statusText.value = '正在启动训练...';
    
    const response = await fetch(`${API_BASE}/api/train/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config),
    });
    
    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.detail || '启动失败');
    }
    
    const data = await response.json();
    taskId.value = data.task_id;
    statusText.value = `训练运行中: ${data.task_id}`;
    ElMessage.success('训练已启动');
    
    pollStatus();
  } catch (error: any) {
    isRunning.value = false;
    status.value = 'error';
    statusText.value = error.message === 'Failed to fetch' 
      ? '连接后端失败，请检查后端是否启动 (port 5000)' 
      : '错误: ' + error.message;
    ElMessage.error(statusText.value);
  }
}

async function pollStatus() {
  if (!taskId.value) return;
  
  const interval = setInterval(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/train/status/${taskId.value}`);
      const data = await res.json();
      
      // 更新进度信息（即使字段缺失也不会报错）
      progress.value = data.progress ?? 0;
      currentEpoch.value = data.current_epoch ?? 0;
      totalEpochs.value = data.total_epochs ?? config.epochs;
      
      if (data.status === 'completed') {
        clearInterval(interval);
        isRunning.value = false;
        status.value = 'completed';
        progress.value = 100;
        currentEpoch.value = totalEpochs.value;
        statusText.value = '训练完成！';
        ElMessage.success('训练完成！');
      } else if (data.status === 'error') {
        clearInterval(interval);
        isRunning.value = false;
        status.value = 'error';
        statusText.value = '训练出错';
      } else if (data.status === 'running') {
        statusText.value = `训练中... Epoch ${currentEpoch.value}/${totalEpochs.value}`;
      }
    } catch (e) {
      console.error('Polling error:', e);
    }
  }, 3000);
}

const modelOptions = [
  { value: 'yolo26n.pt', label: 'YOLO26-Nano', desc: '轻量版，适合边缘设备' },
  { value: 'yolo26s.pt', label: 'YOLO26-Small', desc: '推荐，速度与精度平衡' },
  { value: 'yolo26m.pt', label: 'YOLO26-Medium', desc: '中等精度' },
  { value: 'yolo26l.pt', label: 'YOLO26-Large', desc: '高精度' },
  { value: 'yolo26x.pt', label: 'YOLO26-XLarge', desc: '最高精度' },
];

const dataOptions = [
  { value: 'coco128.yaml', label: 'COCO128', desc: '128张图片，适合快速测试' },
  { value: 'coco8.yaml', label: 'COCO8', desc: '8张图片，极简验证' },
];
</script>

<template>
  <div class="train-wrapper">
    <!-- 页面标题区 -->
    <header class="page-header">
      <h1 class="page-title">模型训练</h1>
      <p class="page-subtitle">使用自定义数据集训练 YOLO 检测模型</p>
    </header>

    <div class="content-grid">
      <!-- 左侧：训练配置 -->
      <section class="main-card">
        <div class="card-header">
          <span class="header-icon">⚙️</span>
          <h2 class="header-title">训练配置</h2>
        </div>
        
        <div class="card-body">
          <!-- 核心参数组 -->
          <div class="form-section">
            <h3 class="section-title">核心训练参数</h3>
            
            <div class="form-row">
              <!-- 模型选择 -->
              <div class="form-field">
                <label class="field-label">
                  预训练模型
                  <span class="label-required">*</span>
                </label>
                <el-select 
                  v-model="config.model" 
                  class="field-select"
                  popper-class="train-select-dropdown"
                  placeholder="选择模型"
                >
                  <el-option
                    v-for="opt in modelOptions"
                    :key="opt.value"
                    :label="opt.label"
                    :value="opt.value"
                  >
                    <div class="select-option">
                      <span class="option-name">{{ opt.label }}</span>
                      <span class="option-desc">{{ opt.desc }}</span>
                    </div>
                  </el-option>
                </el-select>
              </div>

              <!-- 数据集选择 -->
              <div class="form-field">
                <label class="field-label">
                  数据集
                  <span class="label-required">*</span>
                </label>
                <el-select 
                  v-model="config.data" 
                  class="field-select"
                  popper-class="train-select-dropdown"
                  placeholder="选择数据集"
                >
                  <el-option
                    v-for="opt in dataOptions"
                    :key="opt.value"
                    :label="opt.label"
                    :value="opt.value"
                  >
                    <div class="select-option">
                      <span class="option-name">{{ opt.label }}</span>
                      <span class="option-desc">{{ opt.desc }}</span>
                    </div>
                  </el-option>
                </el-select>
              </div>
            </div>

            <div class="form-row">
              <!-- Epochs -->
              <div class="form-field">
                <label class="field-label">训练轮数</label>
                <el-input-number 
                  v-model="config.epochs" 
                  :min="1" 
                  :max="1000" 
                  class="field-number"
                  controls-position="right"
                />
                <span class="field-hint">推荐 50-300 轮</span>
              </div>

              <!-- Image Size -->
              <div class="form-field">
                <label class="field-label">输入尺寸</label>
                <el-select v-model="config.imgsz" class="field-select">
                  <el-option :value="320" label="320 × 320" />
                  <el-option :value="640" label="640 × 640（推荐）" />
                  <el-option :value="1280" label="1280 × 1280" />
                </el-select>
              </div>
            </div>
          </div>

          <div class="divider"></div>

          <!-- 任务设置组 -->
          <div class="form-section">
            <h3 class="section-title">任务设置</h3>
            
            <div class="form-row">
              <!-- Device -->
              <div class="form-field">
                <label class="field-label">计算设备</label>
                <div class="device-options">
                  <label class="device-option" :class="{ active: config.device === 'cpu' }">
                    <input v-model="config.device" type="radio" value="cpu" />
                    <span class="device-icon">💻</span>
                    <span class="device-name">CPU</span>
                  </label>
                  <label class="device-option" :class="{ active: config.device === '0' }">
                    <input v-model="config.device" type="radio" value="0" />
                    <span class="device-icon">🎮</span>
                    <span class="device-name">GPU</span>
                  </label>
                </div>
              </div>

              <!-- Task Name -->
              <div class="form-field">
                <label class="field-label">任务名称</label>
                <el-input 
                  v-model="config.name" 
                  placeholder="留空将自动生成"
                  class="field-input"
                />
                <span class="field-hint">用于标识本次训练</span>
              </div>
            </div>

            <!-- AMP -->
            <div class="form-row">
              <div class="form-field full-width">
                <label class="amp-option">
                  <input v-model="config.amp" type="checkbox" class="amp-checkbox" />
                  <span class="amp-box">
                    <span class="amp-icon">⚡</span>
                    <span class="amp-text">
                      <span class="amp-title">启用混合精度训练 (AMP)</span>
                      <span class="amp-desc">可加速训练并减少显存占用约 40%</span>
                    </span>
                  </span>
                </label>
              </div>
            </div>
          </div>
        </div>

        <!-- 按钮区 -->
        <div class="card-footer">
          <button 
            class="train-button"
            :class="{ loading: isRunning }"
            :disabled="isRunning"
            @click="startTraining"
          >
            <span v-if="isRunning" class="btn-spinner"></span>
            <span class="btn-text">{{ isRunning ? '训练中' : '开始训练' }}</span>
          </button>
        </div>
      </section>

      <!-- 右侧：状态面板 -->
      <aside class="side-panel">
        <div class="status-card" :class="status">
          <div class="status-header">
            <span class="status-icon">
              {{ status === 'idle' ? '⏸️' : status === 'running' ? '🔄' : status === 'completed' ? '✅' : '❌' }}
            </span>
            <div class="status-info">
              <h3 class="status-title">训练状态</h3>
              <span class="status-badge" :class="status">
                {{ status === 'idle' ? '准备就绪' : status === 'running' ? '训练进行中' : status === 'completed' ? '训练完成' : '训练失败' }}
              </span>
            </div>
          </div>
          
          <div class="status-body">
            <p class="status-message">{{ statusText }}</p>
            
            <!-- 训练进度 -->
            <div v-if="status === 'running' || status === 'completed'" class="progress-section">
              <div class="progress-header">
                <span class="progress-epoch">Epoch {{ currentEpoch }} / {{ totalEpochs }}</span>
                <span class="progress-percent">{{ progress }}%</span>
              </div>
              <div class="progress-bar">
                <div class="progress-fill" :style="{ width: progress + '%' }"></div>
              </div>
            </div>
            
            <!-- TensorBoard 入口 -->
            <div v-if="status === 'running' || status === 'completed'" class="tensorboard-section">
              <!-- 检测状态按钮 -->
              <button 
                v-if="!tbStatus.running && !tbChecking" 
                class="tb-check-button"
                @click="checkTensorBoard"
              >
                <span class="tb-icon">🔍</span>
                <span class="tb-text">检测 TensorBoard</span>
              </button>
              
              <!-- 启动或打开按钮 -->
              <button 
                v-else-if="tbStatus.running" 
                class="tb-button"
                @click="() => tbStatus.url && window.open(tbStatus.url, '_blank')"
              >
                <span class="tb-icon">📊</span>
                <span class="tb-text">打开 TensorBoard</span>
              </button>
              
              <button 
                v-else-if="tbChecking" 
                class="tb-check-button"
                disabled
              >
                <span class="tb-icon">⏳</span>
                <span class="tb-text">检测中...</span>
              </button>
              
              <!-- 未运行时显示启动按钮 -->
              <button 
                v-if="!tbStatus.running && !tbChecking" 
                class="tb-start-button"
                @click="startTensorBoard"
              >
                <span class="tb-icon">🚀</span>
                <span class="tb-text">启动 TensorBoard</span>
              </button>
              
              <p class="tb-hint">
                {{ tbStatus.running ? 'TensorBoard 已运行，点击打开查看训练可视化' : '点击检测或启动 TensorBoard 服务' }}
              </p>
            </div>
            
            <div v-if="taskId" class="task-id">
              <span class="id-label">任务 ID</span>
              <code class="id-value">{{ taskId }}</code>
            </div>
          </div>

          <div v-if="status === 'completed'" class="status-footer">
            <div class="success-notice">
              <span class="notice-icon">🎉</span>
              <span class="notice-text">训练成功完成，可查看结果</span>
            </div>
          </div>
        </div>

        <!-- 提示卡片 -->
        <div class="tips-card">
          <h4 class="tips-title">💡 训练提示</h4>
          <ul class="tips-list">
            <li>首次训练建议使用 COCO8 快速验证</li>
            <li>GPU 训练速度通常比 CPU 快 5-10 倍</li>
            <li>训练过程中请勿关闭页面</li>
            <li>结果将保存在 ~/ultralytics/runs/detect/</li>
          </ul>
        </div>
      </aside>
    </div>
  </div>
</template>

<style scoped>
/* ========== 页面整体布局 ========== */
.train-wrapper {
  max-width: 1200px;
  margin: 0 auto;
  padding: 32px 24px;
}

.page-header {
  margin-bottom: 32px;
  text-align: center;
}

.page-title {
  font-size: 32px;
  font-weight: 700;
  color: #ffffff;
  margin: 0 0 8px 0;
  letter-spacing: -0.5px;
}

.page-subtitle {
  font-size: 15px;
  color: #8b92a8;
  margin: 0;
}

.content-grid {
  display: grid;
  grid-template-columns: 1fr 360px;
  gap: 24px;
  align-items: start;
}

@media (max-width: 960px) {
  .content-grid {
    grid-template-columns: 1fr;
  }
}

/* ========== 主卡片 ========== */
.main-card {
  background: #1a1f2e;
  border: 1px solid #2a3142;
  border-radius: 16px;
  overflow: hidden;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 20px 24px;
  background: linear-gradient(135deg, #242b3d 0%, #1e2333 100%);
  border-bottom: 1px solid #2a3142;
}

.header-icon {
  font-size: 20px;
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(64, 158, 255, 0.15);
  border-radius: 10px;
}

.header-title {
  font-size: 18px;
  font-weight: 600;
  color: #ffffff;
  margin: 0;
}

.card-body {
  padding: 24px;
}

.card-footer {
  padding: 20px 24px;
  background: #151922;
  border-top: 1px solid #2a3142;
  display: flex;
  justify-content: center;
}

/* ========== 表单分区 ========== */
.form-section {
  margin-bottom: 24px;
}

.form-section:last-child {
  margin-bottom: 0;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: #8b92a8;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin: 0 0 16px 0;
}

.divider {
  height: 1px;
  background: linear-gradient(90deg, transparent, #2a3142, transparent);
  margin: 24px 0;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  margin-bottom: 16px;
}

.form-row:last-child {
  margin-bottom: 0;
}

@media (max-width: 640px) {
  .form-row {
    grid-template-columns: 1fr;
  }
}

/* ========== 表单字段 ========== */
.form-field {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-field.full-width {
  grid-column: 1 / -1;
}

.field-label {
  font-size: 14px;
  font-weight: 500;
  color: #c5cbe0;
  display: flex;
  align-items: center;
  gap: 4px;
}

.label-required {
  color: #f56c6c;
}

.field-hint {
  font-size: 12px;
  color: #5c6275;
  margin-top: 2px;
}

/* ========== Element Plus 样式覆盖 ========== */
:deep(.field-select) {
  width: 100%;
}

:deep(.field-select .el-input__wrapper) {
  background: #0d1117;
  border: 1px solid #30363d;
  border-radius: 8px;
  box-shadow: none !important;
  padding: 10px 14px;
  transition: all 0.2s;
  cursor: pointer;
}

:deep(.field-select .el-input__wrapper:hover) {
  border-color: #409eff;
  background: #141820;
}

:deep(.field-select .el-input__wrapper.is-focus) {
  border-color: #409eff;
  box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.2) !important;
}

:deep(.field-select .el-input__inner) {
  color: #ffffff;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
}

:deep(.field-select .el-input__inner::placeholder) {
  color: #5c6275;
}

/* 下拉箭头 */
:deep(.field-select .el-select__caret) {
  color: #8b92a8;
  font-size: 16px;
  font-weight: bold;
}

:deep(.field-select .el-input__wrapper:hover .el-select__caret) {
  color: #409eff;
}

/* 选中值的样式 */
:deep(.field-select .el-input__prefix) {
  color: #409eff;
}

:deep(.field-number) {
  width: 100%;
}

:deep(.field-number .el-input__wrapper) {
  background: #0d1117;
  border: 1px solid #30363d;
  border-radius: 8px;
  box-shadow: none !important;
}

:deep(.field-number .el-input__inner) {
  color: #ffffff;
  text-align: left;
  padding-left: 12px;
}

:deep(.field-input .el-input__wrapper) {
  background: #0d1117;
  border: 1px solid #30363d;
  border-radius: 8px;
  box-shadow: none !important;
}

:deep(.field-input .el-input__inner) {
  color: #ffffff;
}

/* ========== 下拉选项样式 ========== */
.select-option {
  display: flex;
  flex-direction: column;
  padding: 4px 0;
}

.option-name {
  font-size: 14px;
  font-weight: 500;
  color: #ffffff;
}

.option-desc {
  font-size: 12px;
  color: #8b92a8;
  margin-top: 2px;
}

:deep(.train-select-dropdown) {
  background: #1a1f2e !important;
  border: 1px solid #2a3142 !important;
  border-radius: 8px !important;
}

:deep(.train-select-dropdown .el-select-dropdown__item) {
  padding: 12px 16px;
  border-bottom: 1px solid #242b3d;
}

:deep(.train-select-dropdown .el-select-dropdown__item:last-child) {
  border-bottom: none;
}

:deep(.train-select-dropdown .el-select-dropdown__item:hover) {
  background: #242b3d;
}

:deep(.train-select-dropdown .el-select-dropdown__item.selected) {
  background: rgba(64, 158, 255, 0.15);
}

/* ========== 设备选择 ========== */
.device-options {
  display: flex;
  gap: 12px;
}

.device-option {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 16px;
  background: #0d1117;
  border: 2px solid #30363d;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s;
}

.device-option:hover {
  border-color: #409eff;
}

.device-option.active {
  border-color: #409eff;
  background: rgba(64, 158, 255, 0.1);
}

.device-option input {
  display: none;
}

.device-icon {
  font-size: 24px;
}

.device-name {
  font-size: 14px;
  font-weight: 500;
  color: #c5cbe0;
}

/* ========== AMP 选项 ========== */
.amp-option {
  display: flex;
  cursor: pointer;
}

.amp-checkbox {
  display: none;
}

.amp-box {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 20px;
  background: #0d1117;
  border: 2px solid #30363d;
  border-radius: 10px;
  width: 100%;
  transition: all 0.2s;
}

.amp-option:hover .amp-box {
  border-color: #409eff;
}

.amp-checkbox:checked + .amp-box {
  border-color: #409eff;
  background: rgba(64, 158, 255, 0.1);
}

.amp-icon {
  font-size: 24px;
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(64, 158, 255, 0.15);
  border-radius: 10px;
}

.amp-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.amp-title {
  font-size: 14px;
  font-weight: 500;
  color: #ffffff;
}

.amp-desc {
  font-size: 12px;
  color: #8b92a8;
}

/* ========== 训练按钮 ========== */
.train-button {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  min-width: 200px;
  padding: 14px 32px;
  background: linear-gradient(135deg, #409eff 0%, #2b7fd1 100%);
  border: none;
  border-radius: 10px;
  color: #ffffff;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: 0 4px 14px rgba(64, 158, 255, 0.3);
}

.train-button:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 6px 20px rgba(64, 158, 255, 0.4);
}

.train-button:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.btn-spinner {
  width: 18px;
  height: 18px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #ffffff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* ========== 右侧面板 ========== */
.side-panel {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* ========== 状态卡片 ========== */
.status-card {
  background: #1a1f2e;
  border: 1px solid #2a3142;
  border-radius: 16px;
  padding: 20px;
  transition: all 0.3s;
}

.status-card.running {
  border-color: #e6a23c;
  box-shadow: 0 0 0 1px rgba(230, 162, 60, 0.3);
}

.status-card.completed {
  border-color: #67c23a;
  box-shadow: 0 0 0 1px rgba(103, 194, 58, 0.3);
}

.status-card.error {
  border-color: #f56c6c;
  box-shadow: 0 0 0 1px rgba(245, 108, 108, 0.3);
}

.status-header {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 16px;
}

.status-icon {
  font-size: 28px;
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #242b3d;
  border-radius: 12px;
}

.status-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.status-title {
  font-size: 14px;
  font-weight: 500;
  color: #8b92a8;
  margin: 0;
}

.status-badge {
  display: inline-flex;
  align-items: center;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 13px;
  font-weight: 600;
  width: fit-content;
}

.status-badge.idle {
  background: rgba(144, 147, 153, 0.15);
  color: #909399;
}

.status-badge.running {
  background: rgba(230, 162, 60, 0.15);
  color: #e6a23c;
}

.status-badge.completed {
  background: rgba(103, 194, 58, 0.15);
  color: #67c23a;
}

.status-badge.error {
  background: rgba(245, 108, 108, 0.15);
  color: #f56c6c;
}

.status-body {
  padding-top: 16px;
  border-top: 1px solid #2a3142;
}

.status-message {
  font-size: 14px;
  color: #c5cbe0;
  margin: 0 0 12px 0;
  line-height: 1.5;
}

/* ========== TensorBoard 入口 ========== */
.tensorboard-section {
  margin: 16px 0;
  padding-top: 16px;
  border-top: 1px solid #2a3142;
}

.tb-button {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  background: rgba(114, 46, 209, 0.15);
  border: 1px solid rgba(114, 46, 209, 0.3);
  border-radius: 8px;
  color: #a855f7;
  font-size: 14px;
  font-weight: 500;
  text-decoration: none;
  transition: all 0.2s;
  cursor: pointer;
}

.tb-button:hover {
  background: rgba(114, 46, 209, 0.25);
  border-color: rgba(114, 46, 209, 0.5);
}

.tb-check-button {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  background: rgba(64, 158, 255, 0.15);
  border: 1px solid rgba(64, 158, 255, 0.3);
  border-radius: 8px;
  color: #409eff;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.tb-check-button:hover {
  background: rgba(64, 158, 255, 0.25);
  border-color: rgba(64, 158, 255, 0.5);
}

.tb-check-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.tb-start-button {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  background: rgba(103, 194, 58, 0.15);
  border: 1px solid rgba(103, 194, 58, 0.3);
  border-radius: 8px;
  color: #67c23a;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  margin-left: 8px;
}

.tb-start-button:hover {
  background: rgba(103, 194, 58, 0.25);
  border-color: rgba(103, 194, 58, 0.5);
}

.tb-icon {
  font-size: 16px;
}

.tb-hint {
  margin: 8px 0 0 0;
  font-size: 11px;
  color: #5c6275;
}

/* ========== 训练进度 ========== */
.progress-section {
  margin-bottom: 16px;
}

.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.progress-epoch {
  font-size: 13px;
  color: #8b92a8;
  font-weight: 500;
}

.progress-percent {
  font-size: 14px;
  font-weight: 600;
  color: #409eff;
}

.progress-bar {
  height: 8px;
  background: #0d1117;
  border-radius: 4px;
  overflow: hidden;
  border: 1px solid #30363d;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #409eff, #2b7fd1);
  border-radius: 4px;
  transition: width 0.3s ease;
}

.task-id {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.id-label {
  font-size: 11px;
  color: #5c6275;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.id-value {
  font-family: 'Monaco', 'Consolas', monospace;
  font-size: 12px;
  color: #8b92a8;
  background: #0d1117;
  padding: 6px 10px;
  border-radius: 6px;
  border: 1px solid #30363d;
}

.status-footer {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #2a3142;
}

.success-notice {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px;
  background: rgba(103, 194, 58, 0.1);
  border-radius: 8px;
}

.notice-icon {
  font-size: 18px;
}

.notice-text {
  font-size: 13px;
  color: #67c23a;
  font-weight: 500;
}

/* ========== 提示卡片 ========== */
.tips-card {
  background: #1a1f2e;
  border: 1px solid #2a3142;
  border-radius: 16px;
  padding: 20px;
}

.tips-title {
  font-size: 14px;
  font-weight: 600;
  color: #ffffff;
  margin: 0 0 12px 0;
}

.tips-list {
  margin: 0;
  padding-left: 18px;
  font-size: 13px;
  color: #8b92a8;
  line-height: 1.8;
}

.tips-list li {
  margin-bottom: 4px;
}
</style>
