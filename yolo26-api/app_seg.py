"""
YOLO26-Seg 实例分割模型服务
复用 yolo26 检测服务的架构，新增分割功能
"""
from fastapi import FastAPI, UploadFile, File, Form, Request, HTTPException
from fastapi.responses import JSONResponse, Response
from ultralytics import YOLO
import numpy as np
import cv2
import time
from datetime import datetime

app = FastAPI()

# 加载分割模型
MODEL_PATH = "weights/yolov8n-seg.pt"  # YOLOv8 nano segmentation
print(f"[SegModel] 正在加载分割模型: {MODEL_PATH} ...")
try:
    model = YOLO(MODEL_PATH)
    print(f"[SegModel] 分割模型加载完成")
except Exception as e:
    print(f"[SegModel] 模型加载失败: {e}")
    print(f"[SegModel] 请确保模型文件存在: {MODEL_PATH}")
    model = None

@app.get("/health")
def health():
    return {
        "ok": model is not None,
        "model": MODEL_PATH,
        "type": "segmentation",
        "task": "instance-segmentation"
    }

@app.post("/model/yolo26-seg")
async def predict_seg(
    request: Request,
    file: UploadFile = File(...),
    source: str = Form("image"),
    conf: float = Form(0.25),
    iou: float = Form(0.7),
    imgsz: int = Form(640),
    max_det: int = Form(300),
    agnostic_nms: bool = Form(False),
    half: bool = Form(False),
    augment: bool = Form(False),
):
    """
    YOLO26-Seg 实例分割推理接口
    返回：检测框 + 分割掩码
    """
    if model is None:
        return JSONResponse(
            {"error": "分割模型未加载，请检查模型文件"},
            status_code=503
        )
    
    print(f"\n{'='*60}")
    print(f"[SegModel] ⬅️⬅️⬅️ 收到分割请求: {datetime.now()}")
    print(f"[SegModel] 文件: {file.filename if file else 'None'}")
    print(f"{'='*60}\n")
    
    start_time = time.time()
    
    if source != "image":
        return JSONResponse(
            {"error": "当前版本只支持 image，不支持 video"},
            status_code=400
        )

    # 读取图片
    data = await file.read()
    print(f"[SegModel] 文件读取完成: {len(data)} bytes")
    
    arr = np.frombuffer(data, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)

    if img is None:
        raise HTTPException(status_code=400, detail="无法解析上传图片")
    
    print(f"[SegModel] 图片解码完成: {img.shape}, 开始推理...")
    inference_start = time.time()

    # 执行分割推理
    results = model.predict(
        source=img,
        conf=conf,
        iou=iou,
        imgsz=imgsz,
        max_det=max_det,
        agnostic_nms=agnostic_nms,
        half=half,
        augment=augment,
        verbose=False
    )
    
    inference_time = time.time() - inference_start
    total_time = time.time() - start_time
    
    # 解析结果
    r = results[0]
    accept = request.headers.get("accept", "application/json")
    
    # 构建返回数据
    detections = []
    
    if r.boxes is not None:
        names = r.names
        
        for i, box in enumerate(r.boxes):
            cls_id = int(box.cls[0].item())
            conf_val = float(box.conf[0].item())
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            
            detection = {
                "cls": cls_id,
                "name": names.get(cls_id, str(cls_id)),
                "conf": conf_val,
                "box": {
                    "x1": x1,
                    "y1": y1,
                    "x2": x2,
                    "y2": y2
                }
            }
            
            # 添加分割掩码（如果有）
            if r.masks is not None and i < len(r.masks):
                mask = r.masks[i]
                # 获取掩码数据
                mask_data = mask.data.cpu().numpy() if hasattr(mask, 'data') else mask
                
                # 简化处理：返回掩码的轮廓点或 bounding box
                # 实际应用中可以根据需要返回完整掩码或压缩后的数据
                detection["has_mask"] = True
                detection["mask_shape"] = mask_data.shape if hasattr(mask_data, 'shape') else None
            else:
                detection["has_mask"] = False
            
            detections.append(detection)
    
    print(f"[SegModel] 推理完成: {inference_time:.2f}s, 总耗时: {total_time:.2f}s")
    print(f"[SegModel] 检测到 {len(detections)} 个目标")
    
    # 打印前5个结果
    for i, det in enumerate(detections[:5]):
        print(f"[SegModel]   [{i}] {det['name']}: conf={det['conf']:.3f}, mask={det['has_mask']}")
    
    # 根据 Accept 返回不同格式
    if "application/json" in accept:
        return {
            "source": "image",
            "width": int(r.orig_shape[1]),
            "height": int(r.orig_shape[0]),
            "count": len(detections),
            "boxes": detections,
            "predictions": detections,
            "task": "segmentation",
            "model": MODEL_PATH
        }
    
    # 返回可视化图片
    plotted = r.plot()
    ok, encoded = cv2.imencode(".jpg", plotted)
    if not ok:
        raise HTTPException(status_code=500, detail="结果图编码失败")

    return Response(content=encoded.tobytes(), media_type="image/jpeg")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5001)
