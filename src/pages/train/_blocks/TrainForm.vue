<script setup lang="ts">
import { ref, reactive, watch } from 'vue';
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
const tbAutoChecked = ref(false);

// 检测 TensorBoard 状态（自动执行）
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
    tbAutoChecked.value = true;
  }
}

// 智能 TensorBoard 按钮：未运行则启动，已运行则打开
async function handleTensorBoard() {
  if (tbStatus.value.running && tbStatus.value.url) {
    // 已运行，直接打开
    window.open(tbStatus.value.url, '_blank');
  } else {
    // 未运行，启动服务
    tbChecking.value = true;
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
      ElMessage.error('启动可视化服务失败');
    } finally {
      tbChecking.value = false;
    }
  }
}

// 页面显示 TensorBoard 区域时自动检测状态
watch(() => status.value, (newStatus) => {
  if ((newStatus === 'running' || newStatus === 'completed') && !tbAutoChecked.value) {
    checkTensorBoard();
  }
});

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
            
            <!-- 训练可视化入口 -->
            <div v-if="status === 'running' || status === 'completed'" class="tensorboard-section">
              <h4 class="tb-section-title">
                {{ status === 'running' ? '📈 训练实时可视化' : '📊 训练结果分析' }}
              </h4>
              <p class="tb-desc">
                查看训练曲线与核心指标变化，包括 mAP、Precision、Recall、Loss 等
              </p>
              
              <div class="tb-actions">
                <!-- 智能按钮：未运行则启动，已运行则打开 -->
                <button 
                  v-if="!tbChecking" 
                  class="tb-button"
                  :class="{ 'tb-button-ready': tbStatus.running }"
                  @click="handleTensorBoard"
                >
                  <span class="tb-icon">{{ tbStatus.running ? '📊' : '🚀' }}</span>
                  <span class="tb-text">
                    {{ tbStatus.running 
                      ? (status === 'running' ? '打开实时训练曲线' : '打开训练结果详情') 
                      : '启动可视化服务' }}
                  </span>
                </button>
                
                <!-- 检测中 -->
                <button 
                  v-else 
                  class="tb-check-button"
                  disabled
                >
                  <span class="tb-icon">⏳</span>
                  <span class="tb-text">正在检测服务状态...</span>
                </button>
              </div>
              
              <p class="tb-hint">
                <span v-if="tbStatus.running">✅ 可视化服务已就绪，点击上方按钮查看训练曲线与指标</span>
                <span v-else-if="tbAutoChecked">💡 服务未启动，点击上方按钮自动启动并打开</span>
                <span v-else>⏳ 正在检测可视化服务状态...</span>
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
  padding: 24px;
}

.content-grid {
  display: grid;
  grid-template-columns: 1fr 320px;
  gap: 20px;
  align-items: start;
}

@media (max-width: 960px) {
  .content-grid {
    grid-template-columns: 1fr;
  }
}

/* ========== 主卡片 ========== */
.main-card {
  background: #1e2333;
  border: 1px solid #2d3548;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
}

.card-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 16px 20px;
  background: #252b3d;
  border-bottom: 1px solid #2d3548;
}

.header-icon {
  font-size: 18px;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(64, 158, 255, 0.12);
  border-radius: 8px;
}

.header-title {
  font-size: 16px;
  font-weight: 600;
  color: #e8eaf0;
  margin: 0;
}

.card-body {
  padding: 20px;
}

.card-footer {
  padding: 16px 20px;
  background: #181c29;
  border-top: 1px solid #2d3548;
  display: flex;
  justify-content: center;
}

/* ========== 表单分区 ========== */
.form-section {
  margin-bottom: 20px;
}

.form-section:last-child {
  margin-bottom: 0;
}

.section-title {
  font-size: 12px;
  font-weight: 600;
  color: #7a839c;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin: 0 0 12px 0;
}

.divider {
  height: 1px;
  background: #2d3548;
  margin: 20px 0;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-bottom: 14px;
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
  gap: 6px;
}

.form-field.full-width {
  grid-column: 1 / -1;
}

.field-label {
  font-size: 13px;
  font-weight: 500;
  color: #a0a8c0;
  display: flex;
  align-items: center;
  gap: 4px;
}

.label-required {
  color: #f56c6c;
}

.field-hint {
  font-size: 11px;
  color: #6b7280;
  margin-top: 2px;
}

/* ========== Element Plus 样式覆盖 ========== */
:deep(.field-select) {
  width: 100%;
}

:deep(.field-select .el-input__wrapper) {
  background: #151922;
  border: 1px solid #2d3548;
  border-radius: 8px;
  box-shadow: none !important;
  padding: 9px 12px;
  height: 40px;
  transition: all 0.2s;
}

:deep(.field-select .el-input__wrapper:hover) {
  border-color: #409eff;
}

:deep(.field-select .el-input__wrapper.is-focus) {
  border-color: #409eff;
  box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.15) !important;
}

:deep(.field-select .el-input__inner) {
  color: #e8eaf0;
  font-size: 13px;
}

:deep(.field-select .el-input__inner::placeholder) {
  color: #5c6275;
}

:deep(.field-number) {
  width: 100%;
}

:deep(.field-number .el-input__wrapper) {
  background: #151922;
  border: 1px solid #2d3548;
  border-radius: 8px;
  box-shadow: none !important;
  height: 40px;
}

:deep(.field-number .el-input__inner) {
  color: #e8eaf0;
  font-size: 13px;
}

:deep(.field-input .el-input__wrapper) {
  background: #151922;
  border: 1px solid #2d3548;
  border-radius: 8px;
  box-shadow: none !important;
  height: 40px;
}

:deep(.field-input .el-input__inner) {
  color: #e8eaf0;
  font-size: 13px;
}

/* ========== 下拉选项样式 ========== */
.select-option {
  display: flex;
  flex-direction: column;
  padding: 3px 0;
}

.option-name {
  font-size: 13px;
  font-weight: 500;
  color: #e8eaf0;
}

.option-desc {
  font-size: 11px;
  color: #7a839c;
  margin-top: 2px;
}

:deep(.train-select-dropdown) {
  background: #1e2333 !important;
  border: 1px solid #2d3548 !important;
  border-radius: 8px !important;
}

:deep(.train-select-dropdown .el-select-dropdown__item) {
  padding: 10px 14px;
  border-bottom: 1px solid #252b3d;
}

:deep(.train-select-dropdown .el-select-dropdown__item:last-child) {
  border-bottom: none;
}

:deep(.train-select-dropdown .el-select-dropdown__item:hover) {
  background: #252b3d;
}

:deep(.train-select-dropdown .el-select-dropdown__item.selected) {
  background: rgba(64, 158, 255, 0.1);
}

/* ========== 设备选择 ========== */
.device-options {
  display: flex;
  gap: 10px;
}

.device-option {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 12px;
  background: #151922;
  border: 1px solid #2d3548;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.device-option:hover {
  border-color: #409eff;
}

.device-option.active {
  border-color: #409eff;
  background: rgba(64, 158, 255, 0.08);
}

.device-option input {
  display: none;
}

.device-icon {
  font-size: 20px;
}

.device-name {
  font-size: 13px;
  font-weight: 500;
  color: #a0a8c0;
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
  gap: 10px;
  padding: 12px 16px;
  background: #151922;
  border: 1px solid #2d3548;
  border-radius: 8px;
  width: 100%;
  transition: all 0.2s;
}

.amp-option:hover .amp-box {
  border-color: #409eff;
}

.amp-checkbox:checked + .amp-box {
  border-color: #409eff;
  background: rgba(64, 158, 255, 0.08);
}

.amp-icon {
  font-size: 20px;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(64, 158, 255, 0.12);
  border-radius: 8px;
}

.amp-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.amp-title {
  font-size: 13px;
  font-weight: 500;
  color: #e8eaf0;
}

.amp-desc {
  font-size: 11px;
  color: #7a839c;
}

/* ========== 训练按钮 ========== */
.train-button {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-width: 180px;
  padding: 12px 28px;
  background: #409eff;
  border: none;
  border-radius: 8px;
  color: #ffffff;
  font-size: 15px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.train-button:hover:not(:disabled) {
  background: #5cadff;
  transform: translateY(-1px);
}

.train-button:disabled {
  background: #2a5a8c;
  cursor: not-allowed;
  opacity: 0.8;
}

.btn-spinner {
  width: 16px;
  height: 16px;
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
  gap: 16px;
}

/* ========== 状态卡片 ========== */
.status-card {
  background: #1e2333;
  border: 1px solid #2d3548;
  border-radius: 12px;
  padding: 16px 20px;
  transition: all 0.2s;
}

.status-card.running {
  border-color: #d4a03a;
}

.status-card.completed {
  border-color: #5cb85c;
}

.status-card.error {
  border-color: #d9534f;
}

.status-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 14px;
}

.status-icon {
  font-size: 24px;
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #252b3d;
  border-radius: 10px;
}

.status-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.status-title {
  font-size: 13px;
  font-weight: 500;
  color: #7a839c;
  margin: 0;
}

.status-badge {
  display: inline-flex;
  align-items: center;
  padding: 3px 10px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
  width: fit-content;
}

.status-badge.idle {
  background: rgba(160, 168, 192, 0.1);
  color: #a0a8c0;
}

.status-badge.running {
  background: rgba(212, 160, 58, 0.12);
  color: #d4a03a;
}

.status-badge.completed {
  background: rgba(92, 184, 92, 0.12);
  color: #5cb85c;
}

.status-badge.error {
  background: rgba(217, 83, 79, 0.12);
  color: #d9534f;
}

.status-body {
  padding-top: 14px;
  border-top: 1px solid #2d3548;
}

.status-message {
  font-size: 13px;
  color: #a0a8c0;
  margin: 0 0 12px 0;
  line-height: 1.5;
}

/* ========== TensorBoard 入口 ========== */
.tensorboard-section {
  margin: 14px 0;
  padding-top: 14px;
  border-top: 1px solid #2d3548;
}

.tb-button {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  background: rgba(64, 158, 255, 0.1);
  border: 1px solid rgba(64, 158, 255, 0.25);
  border-radius: 6px;
  color: #409eff;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.tb-button:hover {
  background: rgba(64, 158, 255, 0.18);
  border-color: rgba(64, 158, 255, 0.4);
}

.tb-button-ready {
  background: rgba(92, 184, 92, 0.1);
  border-color: rgba(92, 184, 92, 0.25);
  color: #5cb85c;
}

.tb-button-ready:hover {
  background: rgba(92, 184, 92, 0.18);
  border-color: rgba(92, 184, 92, 0.4);
}

.tb-check-button {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  background: rgba(160, 168, 192, 0.08);
  border: 1px solid rgba(160, 168, 192, 0.2);
  border-radius: 6px;
  color: #a0a8c0;
  font-size: 12px;
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
  color: #6b7280;
}

.tb-section-title {
  font-size: 13px;
  font-weight: 600;
  color: #e8eaf0;
  margin: 0 0 6px 0;
}

.tb-desc {
  font-size: 11px;
  color: #7a839c;
  margin: 0 0 10px 0;
  line-height: 1.5;
}

.tb-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

/* ========== 训练进度 ========== */
.progress-section {
  margin-bottom: 14px;
}

.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.progress-epoch {
  font-size: 12px;
  color: #7a839c;
}

.progress-percent {
  font-size: 13px;
  font-weight: 600;
  color: #409eff;
}

.progress-bar {
  height: 6px;
  background: #252b3d;
  border-radius: 3px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: #409eff;
  border-radius: 3px;
  transition: width 0.3s ease;
}

.task-id {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #2d3548;
}

.id-label {
  font-size: 11px;
  color: #6b7280;
}

.id-value {
  font-family: 'Monaco', 'Consolas', monospace;
  font-size: 11px;
  color: #7a839c;
  background: transparent;
}

.status-footer {
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid #2d3548;
}

.success-notice {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  background: rgba(92, 184, 92, 0.08);
  border-radius: 6px;
}

.notice-icon {
  font-size: 16px;
}

.notice-text {
  font-size: 12px;
  color: #5cb85c;
  font-weight: 500;
}

/* ========== 提示卡片 ========== */
.tips-card {
  background: #1e2333;
  border: 1px solid #2d3548;
  border-radius: 12px;
  padding: 16px 20px;
}

.tips-title {
  font-size: 13px;
  font-weight: 600;
  color: #a0a8c0;
  margin: 0 0 10px 0;
}

.tips-list {
  margin: 0;
  padding-left: 16px;
  font-size: 12px;
  color: #7a839c;
  line-height: 1.7;
}

.tips-list li {
  margin-bottom: 4px;
}
</style>
