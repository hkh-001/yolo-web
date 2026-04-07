"""
YOLO26 训练工作进程
在独立进程中运行训练任务
"""

import os
import sys
import json
import time
import re
from pathlib import Path
from ultralytics import YOLO

PROJECT_ROOT = Path(__file__).parent


def run_training(task_id: str, config: dict, status_file: str):
    """
    执行训练任务
    """
    log_file = status_file.replace(".json", ".log")
    
    def log(msg):
        """记录日志到文件和print"""
        print(msg)
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    
    def save_status(status, progress=0, epoch=0, total_epochs=0, error=""):
        """保存状态到文件"""
        try:
            data = {
                "task_id": task_id,
                "status": status,
                "progress": progress,
                "current_epoch": epoch,
                "total_epochs": total_epochs,
                "error": error,
                "timestamp": time.time(),
            }
            with open(status_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
        except Exception as e:
            print(f"[TrainWorker] 保存状态失败: {e}")
    
    # Windows 环境下 workers 必须设为 0
    import platform
    is_windows = platform.system() == 'Windows'
    workers = config.get("workers", 0 if is_windows else 8)
    if is_windows and workers > 0:
        log(f"[Train] Windows 环境强制设置 workers=0")
        workers = 0
    
    # 构建训练参数
    train_args = {
        "data": config["data"],
        "epochs": config.get("epochs", 100),
        "imgsz": config.get("imgsz", 640),
        "batch": config.get("batch", 16),
        "device": config.get("device", "cpu"),
        "workers": workers,
        "patience": config.get("patience", 50),
        "optimizer": config.get("optimizer", "auto"),
        "lr0": config.get("lr0", 0.01),
        "amp": config.get("amp", True),
        "project": config.get("project", "runs/detect"),
        "name": config.get("name", f"train_{task_id}"),
        "exist_ok": config.get("exist_ok", False),
        "plots": config.get("plots", True),
        "save": config.get("save", True),
        "verbose": True,
    }
    
    save_status("running", 0, 0, train_args["epochs"])
    log(f"[Train] 启动训练任务 {task_id}")
    
    try:
        # 加载模型并训练
        log(f"[Train] 加载模型: {config['model']}")
        model = YOLO(config["model"])
        
        log(f"[Train] 开始训练 (workers={workers})...")
        
        # 使用简单的回调来跟踪进度
        def on_train_epoch_end(trainer):
            epoch = trainer.epoch + 1
            total = trainer.epochs
            progress = (epoch / total) * 100
            log(f"[Train] Epoch {epoch}/{total} 完成")
            save_status("running", progress, epoch, total)
        
        # 添加回调
        model.add_callback("on_train_epoch_end", on_train_epoch_end)
        
        results = model.train(**train_args)
        
        log(f"[Train] 训练完成!")
        save_status("finished", 100, train_args["epochs"], train_args["epochs"])
        
        # 解析结果
        metrics = {}
        output_dir = Path(results.save_dir) if hasattr(results, 'save_dir') else PROJECT_ROOT / train_args["project"] / train_args["name"]
        
        metrics["has_best_pt"] = (output_dir / "weights" / "best.pt").exists()
        metrics["has_last_pt"] = (output_dir / "weights" / "last.pt").exists()
        metrics["has_results_png"] = (output_dir / "results.png").exists()
        
        # 保存额外信息
        with open(status_file.replace(".json", "_metrics.json"), "w", encoding="utf-8") as f:
            json.dump(metrics, f, ensure_ascii=False)
        
    except Exception as e:
        error_msg = str(e)
        log(f"[Train] 训练失败: {error_msg}")
        save_status("failed", 0, 0, train_args["epochs"], error_msg)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python train_worker.py <task_id> <config_json> <status_file>")
        sys.exit(1)
    
    task_id = sys.argv[1]
    config = json.loads(sys.argv[2])
    status_file = sys.argv[3]
    
    run_training(task_id, config, status_file)
