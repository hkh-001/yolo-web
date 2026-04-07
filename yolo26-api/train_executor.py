"""
YOLOv8 训练执行器 - 多进程版本
提供训练任务管理、执行和结果解析功能
"""

import os
import sys
import json
import time
import uuid
import threading
import subprocess
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any
from enum import Enum

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent
RUNS_DIR = PROJECT_ROOT / "runs" / "detect"
STATUS_DIR = PROJECT_ROOT / "train_status"
STATUS_DIR.mkdir(exist_ok=True)


class TaskStatus(Enum):
    QUEUED = "queued"
    RUNNING = "running"
    FINISHED = "finished"
    FAILED = "failed"
    STOPPED = "stopped"


@dataclass
class TrainTask:
    """训练任务数据结构"""
    id: str
    config: Dict[str, Any]
    status: TaskStatus = TaskStatus.QUEUED
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    finished_at: Optional[float] = None
    output_dir: Optional[str] = None
    logs: List[str] = field(default_factory=list)
    progress: float = 0.0
    current_epoch: int = 0
    total_epochs: int = 0
    error_message: str = ""
    metrics: Dict[str, Any] = field(default_factory=dict)
    process: Optional[subprocess.Popen] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "config": self.config,
            "status": self.status.value,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "output_dir": self.output_dir,
            "logs": self.logs[-200:],  # 只保存最近200条日志
            "progress": self.progress,
            "current_epoch": self.current_epoch,
            "total_epochs": self.total_epochs,
            "error_message": self.error_message,
            "metrics": self.metrics,
        }


class TrainExecutor:
    """YOLO26 训练执行器"""
    
    # 支持的模型列表（YOLO26 系列）
    VALID_MODELS = [
        "yolo26n.pt", "yolo26s.pt", "yolo26m.pt", "yolo26l.pt", "yolo26x.pt"
    ]
    
    # 默认参数
    # 注意：project 和 name 由系统自动管理，不在前端暴露
    DEFAULT_CONFIG = {
        "epochs": 100,
        "imgsz": 640,
        "batch": 16,
        "workers": 8,
        "amp": True,
        "patience": 50,
        "optimizer": "auto",
        "lr0": 0.01,
        "exist_ok": False,
        "plots": True,
        "save": True,
    }
    
    def __init__(self):
        self.tasks: Dict[str, TrainTask] = {}
        self._lock = threading.Lock()
        self._monitors: Dict[str, threading.Thread] = {}
        
        RUNS_DIR.mkdir(parents=True, exist_ok=True)
        self._load_tasks()
    
    def _get_status_file(self, task_id: str) -> Path:
        """获取任务状态文件路径"""
        return STATUS_DIR / f"{task_id}.json"
    
    def _get_log_file(self, task_id: str) -> Path:
        """获取任务日志文件路径"""
        return STATUS_DIR / f"{task_id}.log"
    
    def _load_tasks(self):
        """从磁盘加载任务状态"""
        tasks_file = PROJECT_ROOT / "train_tasks.json"
        if tasks_file.exists():
            try:
                with open(tasks_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for task_data in data.values():
                        if task_data.get("status") == "running":
                            task_data["status"] = "failed"
                            task_data["error_message"] = "服务重启，训练中断"
                        
                        task = TrainTask(
                            id=task_data["id"],
                            config=task_data["config"],
                            status=TaskStatus(task_data["status"]),
                            created_at=task_data["created_at"],
                            started_at=task_data.get("started_at"),
                            finished_at=task_data.get("finished_at"),
                            output_dir=task_data.get("output_dir"),
                            logs=task_data.get("logs", []),
                            progress=task_data.get("progress", 0),
                            current_epoch=task_data.get("current_epoch", 0),
                            total_epochs=task_data.get("total_epochs", 0),
                            error_message=task_data.get("error_message", ""),
                            metrics=task_data.get("metrics", {}),
                        )
                        self.tasks[task.id] = task
            except Exception as e:
                print(f"[TrainExecutor] 加载任务状态失败: {e}")
    
    def _save_tasks(self):
        """保存任务状态到磁盘"""
        tasks_file = PROJECT_ROOT / "train_tasks.json"
        try:
            data = {tid: task.to_dict() for tid, task in self.tasks.items()}
            with open(tasks_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[TrainExecutor] 保存任务状态失败: {e}")
    
    def validate_config(self, config: Dict[str, Any]) -> tuple[bool, str]:
        """验证训练配置"""
        if not config.get("data"):
            return False, "缺少数据集配置文件路径 (data)"
        
        model = config.get("model", "yolov8n.pt")
        if model not in self.VALID_MODELS:
            return False, f"不支持的模型: {model}"
        
        data_path = Path(config["data"])
        if not data_path.is_absolute():
            data_path = PROJECT_ROOT / data_path
        if not data_path.exists():
            return False, f"数据集配置文件不存在: {config['data']}"
        
        epochs = config.get("epochs", self.DEFAULT_CONFIG["epochs"])
        if not (1 <= epochs <= 1000):
            return False, "epochs 必须在 1-1000 之间"
        
        return True, ""
    
    def create_task(self, config: Dict[str, Any]) -> TrainTask:
        """创建新的训练任务"""
        valid, error = self.validate_config(config)
        if not valid:
            raise ValueError(error)
        
        merged_config = {**self.DEFAULT_CONFIG, **config}
        
        task_id = str(uuid.uuid4())[:8]
        task = TrainTask(
            id=task_id,
            config=merged_config,
        )
        
        self.tasks[task_id] = task
        self._save_tasks()
        
        print(f"[TrainExecutor] 创建任务 {task_id}")
        return task
    
    def start_training(self, task_id: str) -> bool:
        """启动训练任务（独立进程）"""
        task = self.tasks.get(task_id)
        if not task:
            raise ValueError(f"任务不存在: {task_id}")
        
        if task.status == TaskStatus.RUNNING:
            raise ValueError("任务已在运行中")
        
        # 自动管理输出目录（不依赖前端传入的 project）
        # 使用系统内部路径：runs/detect/{task_id}/
        output_dir = PROJECT_ROOT / "runs" / "detect" / task_id
        task.output_dir = str(output_dir)
        
        # 设置内部使用的 project 和 name
        task.config["project"] = str(PROJECT_ROOT / "runs" / "detect")
        task.config["name"] = task_id
        
        # 状态文件
        status_file = self._get_status_file(task_id)
        
        # 构建命令
        config_json = json.dumps(task.config, ensure_ascii=False)
        cmd = [
            sys.executable,
            str(PROJECT_ROOT / "train_worker.py"),
            task_id,
            config_json,
            str(status_file),
        ]
        
        # 启动独立进程
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        
        # 启动独立进程，不捕获stdout/stderr避免管道阻塞
        # 日志由train_worker直接写入文件
        task.process = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=env,
            cwd=str(PROJECT_ROOT),
        )
        
        task.status = TaskStatus.RUNNING
        task.started_at = time.time()
        self._save_tasks()
        
        # 启动监控线程
        monitor = threading.Thread(target=self._monitor_task, args=(task,))
        monitor.daemon = True
        monitor.start()
        self._monitors[task_id] = monitor
        
        print(f"[TrainExecutor] 任务 {task_id} 已启动，PID: {task.process.pid}")
        return True
    
    def _monitor_task(self, task: TrainTask):
        """监控训练任务状态"""
        status_file = self._get_status_file(task.id)
        log_file = self._get_log_file(task.id)
        
        while task.status == TaskStatus.RUNNING:
            try:
                # 读取状态文件
                if status_file.exists():
                    with open(status_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        task.progress = data.get("progress", 0)
                        task.current_epoch = data.get("current_epoch", 0)
                        task.total_epochs = data.get("total_epochs", 0)
                        
                        status = data.get("status", "running")
                        if status in ["finished", "failed"]:
                            task.status = TaskStatus(status)
                            task.error_message = data.get("error", "")
                            task.finished_at = time.time()
                            
                            # 加载 metrics
                            metrics_file = status_file.with_suffix("_metrics.json")
                            if metrics_file.exists():
                                with open(metrics_file, 'r', encoding='utf-8') as f:
                                    task.metrics = json.load(f)
                            
                            self._save_tasks()
                            break
                
                # 读取日志文件
                if log_file.exists():
                    with open(log_file, 'r', encoding='utf-8') as f:
                        task.logs = f.read().strip().split('\n')[-200:]
                
                # 检查进程是否还在运行
                if task.process and task.process.poll() is not None:
                    # 进程已结束
                    if task.status == TaskStatus.RUNNING:
                        # 读取最终状态
                        if status_file.exists():
                            with open(status_file, 'r', encoding='utf-8') as f:
                                data = json.load(f)
                                task.status = TaskStatus(data.get("status", "failed"))
                                task.error_message = data.get("error", "")
                        else:
                            task.status = TaskStatus.FAILED
                            task.error_message = "训练进程异常退出"
                        task.finished_at = time.time()
                        self._save_tasks()
                    break
                
                time.sleep(1)
                
            except Exception as e:
                print(f"[TrainExecutor] 监控任务 {task.id} 出错: {e}")
                time.sleep(1)
        
        # 最终解析结果
        if task.status == TaskStatus.FINISHED:
            self._parse_results(task)
        
        self._monitors.pop(task.id, None)
        print(f"[TrainExecutor] 任务 {task.id} 监控结束，状态: {task.status.value}")
    
    def _parse_results(self, task: TrainTask):
        """解析训练结果"""
        if not task.output_dir:
            return
        
        output_path = Path(task.output_dir)
        
        task.metrics["has_best_pt"] = (output_path / "weights" / "best.pt").exists()
        task.metrics["has_last_pt"] = (output_path / "weights" / "last.pt").exists()
        task.metrics["has_results_png"] = (output_path / "results.png").exists()
        
        results_csv = output_path / "results.csv"
        if results_csv.exists():
            try:
                import pandas as pd
                df = pd.read_csv(results_csv)
                if not df.empty:
                    last_row = df.iloc[-1]
                    task.metrics["final_map50"] = float(last_row.get("metrics/mAP50(B)", 0))
                    task.metrics["final_map50_95"] = float(last_row.get("metrics/mAP50-95(B)", 0))
            except Exception as e:
                print(f"[TrainExecutor] 解析 results.csv 失败: {e}")
        
        self._save_tasks()
    
    def stop_training(self, task_id: str) -> bool:
        """停止训练任务"""
        task = self.tasks.get(task_id)
        if not task:
            raise ValueError(f"任务不存在: {task_id}")
        
        if task.status != TaskStatus.RUNNING:
            raise ValueError("任务未在运行")
        
        if task.process:
            task.process.terminate()
            try:
                task.process.wait(timeout=5)
            except:
                task.process.kill()
        
        task.status = TaskStatus.STOPPED
        task.finished_at = time.time()
        self._save_tasks()
        
        return True
    
    def get_task(self, task_id: str) -> Optional[TrainTask]:
        """获取任务信息"""
        return self.tasks.get(task_id)
    
    def get_task_logs(self, task_id: str, limit: int = 100) -> List[str]:
        """获取任务日志"""
        task = self.tasks.get(task_id)
        if not task:
            return []
        return task.logs[-limit:]
    
    def get_task_results(self, task_id: str) -> Dict[str, Any]:
        """获取训练结果文件列表"""
        task = self.tasks.get(task_id)
        if not task:
            raise ValueError(f"任务不存在: {task_id}")
        
        if not task.output_dir:
            return {"files": [], "metrics": {}}
        
        output_path = Path(task.output_dir)
        files = []
        
        key_files = [
            ("weights/best.pt", "最佳权重"),
            ("weights/last.pt", "最新权重"),
            ("results.png", "训练曲线"),
            ("results.csv", "训练数据"),
            ("args.yaml", "训练参数"),
        ]
        
        for rel_path, description in key_files:
            file_path = output_path / rel_path
            if file_path.exists():
                files.append({
                    "name": file_path.name,
                    "path": str(file_path.relative_to(PROJECT_ROOT)),
                    "description": description,
                    "size": file_path.stat().st_size,
                })
        
        return {
            "files": files,
            "metrics": task.metrics,
            "output_dir": task.output_dir,
        }
    
    def list_tasks(self, limit: int = 20) -> List[Dict[str, Any]]:
        """列出所有任务"""
        tasks = sorted(
            self.tasks.values(),
            key=lambda t: t.created_at,
            reverse=True
        )[:limit]
        return [t.to_dict() for t in tasks]


# 全局执行器实例
_executor: Optional[TrainExecutor] = None


def get_executor() -> TrainExecutor:
    """获取全局训练执行器实例"""
    global _executor
    if _executor is None:
        _executor = TrainExecutor()
    return _executor
