"""
YOLO26 训练 API - 最小可运行版本（带进度解析）
"""

import os
import json
import time
import subprocess
import platform
import re
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/train", tags=["train"])

PROJECT_ROOT = Path(__file__).parent
STATUS_DIR = PROJECT_ROOT / "train_status"
STATUS_DIR.mkdir(exist_ok=True)

# 存储任务状态
tasks = {}


class TrainConfig(BaseModel):
    """训练配置 - 7个核心参数"""
    model: str
    data: str
    epochs: int
    imgsz: int
    device: str
    amp: bool = False
    name: Optional[str] = None


def get_status_file(task_id: str) -> Path:
    return STATUS_DIR / f"{task_id}.json"


def get_log_file(task_id: str) -> Path:
    return STATUS_DIR / f"{task_id}.log"


def parse_epoch_from_log(log_file: Path, total_epochs: int) -> tuple[int, int]:
    """
    从日志文件解析当前 epoch
    返回: (current_epoch, total_epochs)
    """
    if not log_file.exists():
        return 0, total_epochs
    
    try:
        with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        
        if not content:
            return 0, total_epochs
        
        # Ultralytics 格式: "1/3" 在 Epoch 列
        # 匹配行首的 epoch 进度，如 "        1/3         0G      1.365..."
        pattern = r"\s+(\d+)/(\d+)\s+\d+G"
        matches = re.findall(pattern, content)
        
        if matches:
            # 取最后一个匹配，表示最新的 epoch
            last_match = matches[-1]
            current_epoch = int(last_match[0])
            if int(last_match[1]) > 0:
                total_epochs = int(last_match[1])
            return current_epoch, total_epochs
        
        # 备选：尝试其他格式
        alt_patterns = [
            r"epoch\s+(\d+)/(\d+)",
            r"Epoch\s+(\d+)/(\d+)",
            r"(\d+)/(\d+)\s+\[",
        ]
        
        for pattern in alt_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                last_match = matches[-1]
                return int(last_match[0]), int(last_match[1]) if int(last_match[1]) > 0 else total_epochs
        
        return 0, total_epochs
        
    except Exception as e:
        print(f"[Train] 解析日志失败: {e}")
        return 0, total_epochs


@router.post("/start")
async def start_training(config: TrainConfig):
    """
    启动训练任务 - 最小实现（输出到日志文件）
    """
    task_id = f"exp_{int(time.time())}"
    exp_name = config.name or task_id
    
    # Windows 强制 workers=0
    workers = 0 if platform.system() == "Windows" else 8
    
    # 构建 yolo 命令
    cmd = [
        "yolo", "detect", "train",
        f"data={config.data}",
        f"model={config.model}",
        f"epochs={config.epochs}",
        f"imgsz={config.imgsz}",
        f"device={config.device}",
        f"amp={config.amp}",
        f"name={exp_name}",
        f"workers={workers}",
        "plots=True",
        "save=True",
    ]
    
    # 保存状态
    status_file = get_status_file(task_id)
    status = {
        "task_id": task_id,
        "status": "running",
        "config": config.model_dump(),
        "started_at": time.time(),
    }
    with open(status_file, "w", encoding="utf-8") as f:
        json.dump(status, f, ensure_ascii=False)
    
    # 启动训练进程（输出到日志文件，避免 PIPE 阻塞）
    log_file = get_log_file(task_id)
    try:
        with open(log_file, "w", encoding="utf-8") as log_f:
            process = subprocess.Popen(
                cmd,
                stdout=log_f,
                stderr=subprocess.STDOUT,
                cwd=str(PROJECT_ROOT),
            )
        tasks[task_id] = {"process": process, "config": config}
        
        return {
            "success": True,
            "task_id": task_id,
            "message": f"训练已启动: {task_id}",
        }
    except Exception as e:
        status["status"] = "error"
        status["error"] = str(e)
        with open(status_file, "w", encoding="utf-8") as f:
            json.dump(status, f, ensure_ascii=False)
        raise HTTPException(status_code=500, detail=f"启动失败: {str(e)}")


@router.get("/status/{task_id}")
async def get_status(task_id: str):
    """获取任务状态（含进度信息）"""
    status_file = get_status_file(task_id)
    if not status_file.exists():
        raise HTTPException(status_code=404, detail="任务不存在")
    
    with open(status_file, "r", encoding="utf-8") as f:
        status = json.load(f)
    
    config = status.get("config", {})
    total_epochs = config.get("epochs", 0)
    
    # 检查进程是否结束
    if task_id in tasks and tasks[task_id].get("process"):
        process = tasks[task_id]["process"]
        if process.poll() is not None:
            return_code = process.returncode
            if return_code == 0:
                status["status"] = "completed"
            else:
                status["status"] = "error"
            with open(status_file, "w", encoding="utf-8") as f:
                json.dump(status, f, ensure_ascii=False)
    
    # 解析当前 epoch
    log_file = get_log_file(task_id)
    current_epoch, parsed_total = parse_epoch_from_log(log_file, total_epochs)
    
    # 计算进度百分比
    if status.get("status") == "completed":
        progress = 100
        current_epoch = total_epochs
    elif status.get("status") == "error":
        progress = 0
    elif total_epochs > 0:
        progress = min(int((current_epoch / total_epochs) * 100), 99)
    else:
        progress = 0
    
    return {
        "success": True,
        "task_id": task_id,
        "status": status.get("status", "unknown"),
        "current_epoch": current_epoch,
        "total_epochs": total_epochs,
        "progress": progress,
    }
