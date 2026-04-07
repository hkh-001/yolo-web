import { Hono } from 'hono';
import { spawn, ChildProcess } from 'child_process';
import { existsSync } from 'fs';
import { join } from 'path';

const router = new Hono({});

// 训练任务状态
interface TrainTask {
    process: ChildProcess | null;
    status: 'idle' | 'running' | 'finished' | 'failed';
    config: any;
    startTime: number;
    logs: string[];
    progress: number;
    currentEpoch: number;
    totalEpochs: number;
    tensorboardUrl: string;
    error?: string;
}

// 全局训练任务状态
let trainTask: TrainTask = {
    process: null,
    status: 'idle',
    config: null,
    startTime: 0,
    logs: [],
    progress: 0,
    currentEpoch: 0,
    totalEpochs: 0,
    tensorboardUrl: 'http://localhost:6006',
    error: '',
};

// 统一响应格式
function jsonResponse(data: any, status = 200) {
    return new Response(JSON.stringify(data), {
        status,
        headers: { 'Content-Type': 'application/json' }
    });
}

// 解析训练日志中的进度
function parseTrainingLog(line: string) {
    // 匹配 epoch 进度
    const epochMatch = line.match(/Epoch\s+(\d+)\/(\d+)/i);
    if (epochMatch) {
        trainTask.currentEpoch = parseInt(epochMatch[1]);
        trainTask.totalEpochs = parseInt(epochMatch[2]);
        trainTask.progress = (trainTask.currentEpoch / trainTask.totalEpochs) * 100;
    }
    
    // 匹配 Ultralytics 进度条格式
    const progressMatch = line.match(/(\d+)%\s*\|/);
    if (progressMatch) {
        trainTask.progress = parseFloat(progressMatch[1]);
    }
}

// 启动训练
router.post('/train/start', async (c) => {
    try {
        // 如果已有训练在运行，返回错误
        if (trainTask.status === 'running') {
            return jsonResponse({
                success: false,
                message: '已有训练任务在运行，请先停止',
            }, 400);
        }
        
        const body = await c.req.json();
        
        // 验证必要参数
        if (!body.data) {
            return jsonResponse({
                success: false,
                message: '缺少数据集配置路径 (data)',
            }, 400);
        }
        
        // 重置状态
        trainTask.config = body;
        trainTask.logs = [];
        trainTask.progress = 0;
        trainTask.currentEpoch = 0;
        trainTask.totalEpochs = body.epochs || 100;
        trainTask.error = '';
        trainTask.status = 'running';
        trainTask.startTime = Date.now();
        
        // 构建训练命令（使用ultralytics Python API）
        const trainScript = `
from ultralytics import YOLO
import sys

try:
    # 加载模型
    model = YOLO('${body.model || 'yolov8n.pt'}')
    
    # 训练
    results = model.train(
        data='${body.data}',
        epochs=${body.epochs || 100},
        imgsz=${body.imgsz || 640},
        batch=${body.batch || 16},
        device='${body.device || '0'}',
        workers=${body.workers || 8},
        patience=${body.patience || 50},
        verbose=True,
    )
    
    print("训练完成!")
    print(f"最佳模型: {results.best}")
    
except Exception as e:
    print(f"训练错误: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
`;
        
        // 保存临时训练脚本
        const scriptPath = '/tmp/train_yolo.py';
        await Bun.write(scriptPath, trainScript);
        
        // 启动训练进程
        const trainProcess = spawn('python', [scriptPath], {
            detached: false,
            stdio: ['ignore', 'pipe', 'pipe'],
            env: {
                ...process.env,
                PYTHONUNBUFFERED: '1',
            },
        });
        
        trainTask.process = trainProcess;
        
        // 处理输出
        trainProcess.stdout?.on('data', (data) => {
            const lines = data.toString().split('\n');
            lines.forEach((line: string) => {
                if (line.trim()) {
                    trainTask.logs.push(line);
                    parseTrainingLog(line);
                    console.log('[Train]', line);
                }
            });
        });
        
        trainProcess.stderr?.on('data', (data) => {
            const lines = data.toString().split('\n');
            lines.forEach((line: string) => {
                if (line.trim()) {
                    trainTask.logs.push(`[ERROR] ${line}`);
                    console.error('[Train Error]', line);
                }
            });
        });
        
        trainProcess.on('close', (code) => {
            if (code === 0) {
                trainTask.status = 'finished';
                trainTask.progress = 100;
                trainTask.logs.push('训练完成！');
            } else {
                trainTask.status = 'failed';
                trainTask.error = `训练进程退出，代码: ${code}`;
                trainTask.logs.push(`[ERROR] 训练失败，退出代码: ${code}`);
            }
        });
        
        trainProcess.on('error', (error) => {
            trainTask.status = 'failed';
            trainTask.error = error.message;
            trainTask.logs.push(`[ERROR] ${error.message}`);
        });
        
        return jsonResponse({
            success: true,
            message: '训练已启动',
            tensorboard_url: trainTask.tensorboardUrl,
        });
        
    } catch (error: any) {
        trainTask.status = 'failed';
        trainTask.error = error.message;
        return jsonResponse({
            success: false,
            message: error.message || '启动训练失败',
        }, 500);
    }
});

// 停止训练
router.post('/train/stop', async (c) => {
    try {
        if (!trainTask.process) {
            return jsonResponse({
                success: false,
                message: '没有运行中的训练任务',
            }, 400);
        }
        
        trainTask.process.kill('SIGTERM');
        
        // 强制终止（如果 graceful 终止失败）
        setTimeout(() => {
            if (trainTask.process && !trainTask.process.killed) {
                trainTask.process.kill('SIGKILL');
            }
        }, 5000);
        
        trainTask.status = 'idle';
        trainTask.logs.push('训练已手动停止');
        
        return jsonResponse({
            success: true,
            message: '训练已停止',
        });
        
    } catch (error: any) {
        return jsonResponse({
            success: false,
            message: error.message || '停止训练失败',
        }, 500);
    }
});

// 获取训练状态
router.get('/train/status', async (c) => {
    return jsonResponse({
        success: true,
        status: trainTask.status,
        progress: trainTask.progress,
        current_epoch: trainTask.currentEpoch,
        total_epochs: trainTask.totalEpochs,
        tensorboard_url: trainTask.tensorboardUrl,
        error: trainTask.error,
    });
});

// 获取训练日志
router.get('/train/logs', async (c) => {
    const limit = parseInt(c.req.query('limit') || '50');
    return jsonResponse({
        success: true,
        logs: trainTask.logs.slice(-limit),
        total: trainTask.logs.length,
    });
});

export default router;
