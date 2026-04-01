from fastapi import FastAPI, UploadFile, File, Form, Request, HTTPException
from fastapi.responses import JSONResponse, Response
from ultralytics import YOLO
import numpy as np
import cv2
import time
from datetime import datetime
from PIL import Image, ImageFilter
import io

app = FastAPI()

# ========== YOLO26 检测模型 ==========

MODEL_PATH = "weights/yolo26n.pt"
print(f"[Model] 正在加载模型: {MODEL_PATH} ...")
model = YOLO(MODEL_PATH)
print(f"[Model] 模型加载完成")

@app.get("/health")
def health():
    return {"ok": True, "model": MODEL_PATH}

@app.post("/model/yolo26n")
async def predict(
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
    print(f"\n{'='*60}")
    print(f"[Model] ⬅️⬅️⬅️ 收到请求: {datetime.now()}")
    print(f"[Model] 文件: {file.filename if file else 'None'}")
    print(f"{'='*60}\n")
    start_time = time.time()
    
    if source != "image":
        return JSONResponse(
            {"error": "当前版本只支持 image，不支持 video"},
            status_code=400
        )

    data = await file.read()
    print(f"[Model] 文件读取完成: {len(data)} bytes")
    
    arr = np.frombuffer(data, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)

    if img is None:
        raise HTTPException(status_code=400, detail="无法解析上传图片")
    
    print(f"[Model] 图片解码完成: {img.shape}, 开始推理...")
    inference_start = time.time()

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
    print(f"[Model] 推理完成: {inference_time:.2f}s, 总耗时: {total_time:.2f}s")
    
    r = results[0]
    accept = request.headers.get("accept", "application/json")

    boxes_out = []
    if r.boxes is not None:
        names = r.names
        for b in r.boxes:
            cls_id = int(b.cls[0].item())
            conf_val = float(b.conf[0].item())
            x1, y1, x2, y2 = b.xyxy[0].tolist()
            boxes_out.append({
                "cls": cls_id,
                "name": names.get(cls_id, str(cls_id)),
                "conf": conf_val,
                "box": {
                    "x1": x1,
                    "y1": y1,
                    "x2": x2,
                    "y2": y2
                }
            })

    # 打印检测结果详情
    print(f"[Model] ========== 检测结果 ==========")
    print(f"[Model] 检测到的目标数量: {len(boxes_out)}")
    print(f"[Model] 当前参数: conf={conf}, iou={iou}, imgsz={imgsz}, max_det={max_det}")
    for i, box in enumerate(boxes_out[:5]):  # 只打印前5个
        print(f"[Model]   [{i}] {box['name']}: conf={box['conf']:.3f}, box=({box['box']['x1']:.1f}, {box['box']['y1']:.1f}, {box['box']['x2']:.1f}, {box['box']['y2']:.1f})")
    if len(boxes_out) > 5:
        print(f"[Model]   ... 还有 {len(boxes_out) - 5} 个目标")
    print(f"[Model] =================================")

    if "application/json" in accept:
        return {
            "source": "image",
            "width": int(r.orig_shape[1]),
            "height": int(r.orig_shape[0]),
            "count": len(boxes_out),
            "boxes": boxes_out,
            "predictions": boxes_out
        }

    plotted = r.plot()
    ok, encoded = cv2.imencode(".jpg", plotted)
    if not ok:
        raise HTTPException(status_code=500, detail="结果图编码失败")

    return Response(content=encoded.tobytes(), media_type="image/jpeg")


# ========== YOLO26-Seg 实例分割路由 ==========

SEG_MODEL_PATH = "weights/yolov8n-seg.pt"
seg_model = None

def load_seg_model():
    """懒加载分割模型"""
    global seg_model
    if seg_model is None:
        print(f"[SegModel] 正在加载分割模型: {SEG_MODEL_PATH} ...")
        try:
            seg_model = YOLO(SEG_MODEL_PATH)
            print(f"[SegModel] 分割模型加载完成")
        except Exception as e:
            print(f"[SegModel] 模型加载失败: {e}")
            print(f"[SegModel] 请确保模型文件存在: {SEG_MODEL_PATH}")
    return seg_model

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
    """YOLO26-Seg 实例分割推理"""
    model = load_seg_model()
    if model is None:
        return JSONResponse(
            {"error": "分割模型未加载，请下载模型文件", "model_path": SEG_MODEL_PATH},
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

    data = await file.read()
    print(f"[SegModel] 文件读取完成: {len(data)} bytes")
    
    arr = np.frombuffer(data, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)

    if img is None:
        raise HTTPException(status_code=400, detail="无法解析上传图片")
    
    print(f"[SegModel] 图片解码完成: {img.shape}, 开始推理...")
    inference_start = time.time()

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
    
    r = results[0]
    accept = request.headers.get("accept", "application/json")
    
    print(f"[SegModel] 推理完成: {inference_time:.2f}s, 总耗时: {total_time:.2f}s")
    
    # 根据 Accept 返回不同格式
    if "application/json" in accept:
        # JSON 格式：返回详细检测数据
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
                    "box": {"x1": x1, "y1": y1, "x2": x2, "y2": y2}
                }
                
                # 添加掩码信息
                if r.masks is not None and i < len(r.masks):
                    detection["has_mask"] = True
                else:
                    detection["has_mask"] = False
                
                detections.append(detection)
        
        print(f"[SegModel] 返回 JSON 格式，{len(detections)} 个目标")
        return {
            "source": "image",
            "width": int(r.orig_shape[1]),
            "height": int(r.orig_shape[0]),
            "count": len(detections),
            "boxes": detections,
            "predictions": detections,
            "task": "segmentation"
        }
    
    # 图片格式：返回 r.plot() 生成的真实 mask overlay 图
    print(f"[SegModel] 生成 overlay 结果图...")
    plotted = r.plot()
    ok, encoded = cv2.imencode(".jpg", plotted)
    if not ok:
        raise HTTPException(status_code=500, detail="结果图编码失败")
    
    print(f"[SegModel] 返回图片格式，包含真实 mask overlay")
    return Response(content=encoded.tobytes(), media_type="image/jpeg")


# ========== 图像增强路由 ==========

# 注：当前为基础增强模式（OpenCV 插值 + 降噪）
# 如需 Real-ESRGAN 超分辨率，请安装：pip install realesrgan basicsr
# 并下载模型文件到 weights/ 目录

ENHANCE_MAX_SIZE = 2048  # 最大输入尺寸限制

def basic_enhance(img: np.ndarray, scale: int = 2, denoise: float = 0) -> np.ndarray:
    """
    基础图像增强（OpenCV 实现）
    
    Args:
        img: 输入图像 (BGR格式)
        scale: 放大倍数 (1-4)
        denoise: 降噪强度 (0-1)
    
    Returns:
        增强后的图像
    """
    h, w = img.shape[:2]
    
    # 限制最大尺寸
    if max(h, w) > ENHANCE_MAX_SIZE:
        scale_factor = ENHANCE_MAX_SIZE / max(h, w)
        new_w, new_h = int(w * scale_factor), int(h * scale_factor)
        img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)
        print(f"[Enhance] 图片尺寸过大，已缩放至 {new_w}x{new_h}")
    
    # 放大处理
    if scale > 1:
        h, w = img.shape[:2]
        new_w, new_h = w * scale, h * scale
        # 使用 Lanczos 插值（比双线性更好）
        img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)
        print(f"[Enhance] 放大 {scale}x -> {new_w}x{new_h}")
    
    # 降噪处理
    if denoise > 0:
        # 转换为 PIL Image 进行降噪
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(img_rgb)
        
        # 使用中值滤波降噪
        filter_size = int(3 + denoise * 4)  # 3-7 的滤波器大小
        if filter_size % 2 == 0:
            filter_size += 1
        
        pil_img = pil_img.filter(ImageFilter.MedianFilter(size=filter_size))
        
        # 可选：轻微锐化
        if denoise < 0.5:
            enhancer = ImageFilter.UnsharpMask(radius=2, percent=100, threshold=3)
            pil_img = pil_img.filter(enhancer)
        
        # 转回 OpenCV 格式
        img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        print(f"[Enhance] 降噪处理完成 (强度: {denoise:.2f})")
    
    return img

@app.post("/model/enhance")
async def predict_enhance(
    request: Request,
    file: UploadFile = File(...),
    source: str = Form("image"),
    scale: int = Form(2),
    denoise: float = Form(0),
):
    """
    图像增强接口
    
    参数:
        scale: 放大倍数 (1-4)
        denoise: 降噪强度 (0.0-1.0)
    """
    print(f"\n{'='*60}")
    print(f"[Enhance] ⬅️⬅️⬅️ 收到增强请求: {datetime.now()}")
    print(f"[Enhance] 文件: {file.filename if file else 'None'}, 缩放: {scale}x, 降噪: {denoise}")
    print(f"{'='*60}\n")
    
    start_time = time.time()
    
    if source != "image":
        return JSONResponse(
            {"error": "当前版本只支持 image，不支持 video"},
            status_code=400
        )
    
    # 验证参数
    scale = max(1, min(4, int(scale)))  # 限制 1-4
    denoise = max(0, min(1, float(denoise)))  # 限制 0-1
    
    try:
        # 读取图片
        data = await file.read()
        print(f"[Enhance] 文件读取完成: {len(data)} bytes")
        
        arr = np.frombuffer(data, np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        
        if img is None:
            raise HTTPException(status_code=400, detail="无法解析上传图片")
        
        orig_h, orig_w = img.shape[:2]
        print(f"[Enhance] 原图尺寸: {orig_w}x{orig_h}")
        
        # 执行增强
        enhanced_img = basic_enhance(img, scale=scale, denoise=denoise)
        
        new_h, new_w = enhanced_img.shape[:2]
        process_time = time.time() - start_time
        
        print(f"[Enhance] 增强完成: {new_w}x{new_h}, 耗时: {process_time:.2f}s")
        
        # 编码为 JPEG
        # 根据输出尺寸调整质量
        quality = 95 if max(new_w, new_h) < 2000 else 90
        encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
        ok, encoded = cv2.imencode(".jpg", enhanced_img, encode_params)
        
        if not ok:
            raise HTTPException(status_code=500, detail="结果图编码失败")
        
        print(f"[Enhance] 输出图片: {len(encoded.tobytes()) / 1024:.1f} KB")
        
        return Response(
            content=encoded.tobytes(), 
            media_type="image/jpeg",
            headers={
                "X-Process-Time": str(process_time),
                "X-Original-Size": f"{orig_w}x{orig_h}",
                "X-Enhanced-Size": f"{new_w}x{new_h}"
            }
        )
        
    except Exception as e:
        print(f"[Enhance] ❌ 处理失败: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"增强处理失败: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
