from fastapi import FastAPI, UploadFile, File, Form, Request, HTTPException
from fastapi.responses import JSONResponse, Response
from ultralytics import YOLO
import numpy as np
import cv2
import time
from datetime import datetime
from PIL import Image, ImageFilter
import io
import base64

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
        # JSON 格式：返回详细检测数据 + mask 数据
        detections = []
        mask_list = []  # 新增：mask 数据列表
        
        # 调试：打印 masks 信息
        print(f"[SegModel] r.masks type: {type(r.masks)}")
        print(f"[SegModel] r.masks is None: {r.masks is None}")
        if r.masks is not None:
            print(f"[SegModel] r.masks.data shape: {r.masks.data.shape if hasattr(r.masks.data, 'shape') else 'N/A'}")
            print(f"[SegModel] len(r.masks): {len(r.masks)}")
        
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
                
                # 添加掩码信息标记
                has_mask = r.masks is not None and i < len(r.masks)
                detection["has_mask"] = has_mask
                
                detections.append(detection)
                
                # 新增：提取并编码 mask 数据
                if has_mask:
                    try:
                        print(f"[SegModel] 开始提取 mask {i}...")
                        
                        # 获取 mask 数据 - 修正：使用 r.masks.data[i] 而不是 r.masks[i].data[0]
                        # r.masks.data shape: (N, H, W)，N 是 mask 数量
                        mask_tensor = r.masks.data[i]  # shape: (H, W)
                        mask_data = mask_tensor.cpu().numpy()
                        
                        print(f"[SegModel] mask {i} 原始尺寸: {mask_data.shape}")
                        
                        # 二值化 (0-1 浮点 -> 0/255 整数)
                        mask_binary = (mask_data > 0.5).astype(np.uint8) * 255
                        
                        # 获取 bbox 区域（局部 mask）
                        x1_int, y1_int, x2_int, y2_int = int(x1), int(y1), int(x2), int(y2)
                        x1_int = max(0, x1_int)
                        y1_int = max(0, y1_int)
                        x2_int = min(mask_binary.shape[1], x2_int)
                        y2_int = min(mask_binary.shape[0], y2_int)
                        
                        print(f"[SegModel] mask {i} bbox 裁剪: ({x1_int}, {y1_int}, {x2_int}, {y2_int})")
                        
                        if x2_int > x1_int and y2_int > y1_int:
                            mask_roi = mask_binary[y1_int:y2_int, x1_int:x2_int]
                            
                            # 编码为 PNG（比 JPG 更适合二值图）
                            ok, encoded = cv2.imencode(".png", mask_roi)
                            if ok:
                                mask_base64 = base64.b64encode(encoded.tobytes()).decode('utf-8')
                                
                                mask_list.append({
                                    "bbox": [x1, y1, x2, y2],
                                    "width": mask_roi.shape[1],
                                    "height": mask_roi.shape[0],
                                    "mask": mask_base64,
                                    "name": names.get(cls_id, str(cls_id)),
                                    "conf": conf_val,
                                    "index": i
                                })
                                print(f"[SegModel] mask {i} 提取成功，base64 长度: {len(mask_base64)}")
                            else:
                                print(f"[SegModel] mask {i} PNG 编码失败")
                        else:
                            print(f"[SegModel] mask {i} bbox 区域无效，跳过")
                    except Exception as e:
                        print(f"[SegModel] 提取 mask {i} 失败: {e}")
                        import traceback
                        traceback.print_exc()
                        # mask 提取失败不影响整体返回
        
        print(f"[SegModel] 返回 JSON 格式，{len(detections)} 个目标，{len(mask_list)} 个 mask")
        return {
            "source": "image",
            "width": int(r.orig_shape[1]),
            "height": int(r.orig_shape[0]),
            "count": len(detections),
            "boxes": detections,
            "predictions": detections,
            "masks": mask_list,  # 新增
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


# ========== 图像增强路由 (Real-ESRGAN) ==========

# 导入 Real-ESRGAN 模型定义（内嵌，无需安装 realesrgan/basicsr 包）
from realesrgan_model import get_realesrgan_model, RealESRGANer

ENHANCE_MAX_SIZE = 2048  # 最大输入尺寸限制

# Real-ESRGAN 模型配置
REALESRGAN_MODEL_PATH = "weights/RealESRGAN_x4plus.pth"
REALESRGAN_SCALE = 4  # x4plus 模型固定输出 4x

# 全局模型实例（启动时预加载）
_realesrgan_model = None

def get_model():
    """获取 RealESRGAN 模型实例（单例模式）"""
    global _realesrgan_model
    if _realesrgan_model is None:
        print("[RealESRGAN] 正在加载模型，请稍候...")
        _realesrgan_model = get_realesrgan_model(
            model_path=REALESRGAN_MODEL_PATH,
            scale=REALESRGAN_SCALE,
            tile=512  # 使用 512x512 tiles 避免大图爆显存
        )
        print("[RealESRGAN] 模型加载完成")
    return _realesrgan_model

# 预加载 Real-ESRGAN 模型（避免首次请求超时）
print("[RealESRGAN] 预加载 Real-ESRGAN 模型...")
try:
    get_model()
    print("[RealESRGAN] 预加载完成，服务已就绪")
except Exception as e:
    print(f"[RealESRGAN] 预加载失败: {e}")
    print("[RealESRGAN] 将在首次请求时尝试加载")

@app.post("/model/enhance")
async def predict_enhance(
    request: Request,
    file: UploadFile = File(...),
    source: str = Form("image"),
    scale: int = Form(4),  # 默认 4x，与 RealESRGAN_x4plus 对应
    denoise: float = Form(0),
):
    """
    图像增强接口（Real-ESRGAN 超分辨率）
    
    参数:
        scale: 目标放大倍数 (1-4)，模型输出固定 4x，其他尺寸会再缩放
        denoise: 降噪强度 (0.0-1.0)，在神经网络增强后作为后处理
    """
    print(f"\n{'='*60}")
    print(f"[RealESRGAN] === 收到增强请求: {datetime.now()} ===")
    print(f"[RealESRGAN] 文件: {file.filename if file else 'None'}, 目标缩放: {scale}x")
    print(f"{'='*60}\n")
    
    start_time = time.time()
    
    if source != "image":
        print("[RealESRGAN] 错误: 不支持的 source 类型")
        return JSONResponse(
            {"error": "当前版本只支持 image，不支持 video"},
            status_code=400
        )
    
    # 验证参数
    target_scale = max(1, min(4, int(scale)))  # 目标缩放 1-4
    denoise = max(0, min(1, float(denoise)))  # 降噪强度 0-1
    print(f"[RealESRGAN] 参数验证通过: target_scale={target_scale}, denoise={denoise}")
    
    try:
        # 读取图片
        print("[RealESRGAN] 步骤 1/6: 读取上传文件...")
        data = await file.read()
        print(f"[RealESRGAN] 步骤 1/6 完成: 读取 {len(data)} bytes")
        
        print("[RealESRGAN] 步骤 2/6: 解码图片...")
        arr = np.frombuffer(data, np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        
        if img is None:
            print("[RealESRGAN] 错误: cv2.imdecode 返回 None")
            raise HTTPException(status_code=400, detail="无法解析上传图片")
        
        orig_h, orig_w = img.shape[:2]
        print(f"[RealESRGAN] 步骤 2/6 完成: 原图尺寸 {orig_w}x{orig_h}")
        
        # 限制最大输入尺寸（避免显存/内存不足）
        if max(orig_h, orig_w) > ENHANCE_MAX_SIZE:
            print(f"[RealESRGAN] 图片尺寸过大，需要预缩放")
            scale_factor = ENHANCE_MAX_SIZE / max(orig_h, orig_w)
            new_w, new_h = int(orig_w * scale_factor), int(orig_h * scale_factor)
            img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)
            orig_h, orig_w = new_h, new_w
            print(f"[RealESRGAN] 预缩放完成: {orig_w}x{orig_h}")
        
        # 获取模型并执行 Real-ESRGAN 推理
        print("[RealESRGAN] 步骤 3/6: 获取模型实例...")
        model = get_model()
        print(f"[RealESRGAN] 步骤 3/6 完成: 模型设备={model.device}")
        
        print("[RealESRGAN] 步骤 4/6: 开始神经网络推理...")
        inference_start = time.time()
        
        # Real-ESRGAN 推理（固定输出 4x）
        enhanced_img = model.enhance(img, outscale=REALESRGAN_SCALE)
        
        inference_time = time.time() - inference_start
        print(f"[RealESRGAN] 步骤 4/6 完成: 推理耗时 {inference_time:.2f}s")
        
        # 如果目标 scale 不是 4，需要再缩放
        if target_scale != REALESRGAN_SCALE:
            h4, w4 = enhanced_img.shape[:2]
            target_w = int(orig_w * target_scale)
            target_h = int(orig_h * target_scale)
            enhanced_img = cv2.resize(enhanced_img, (target_w, target_h), interpolation=cv2.INTER_LANCZOS4)
            print(f"[RealESRGAN] 从 4x ({w4}x{h4}) 缩放到目标 {target_scale}x ({target_w}x{target_h})")
        
        # 可选：后处理降噪（PIL）
        if denoise > 0:
            print(f"[RealESRGAN] 应用后处理降噪 (强度: {denoise:.2f})...")
            img_rgb = cv2.cvtColor(enhanced_img, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(img_rgb)
            filter_size = int(3 + denoise * 4)
            if filter_size % 2 == 0:
                filter_size += 1
            pil_img = pil_img.filter(ImageFilter.MedianFilter(size=filter_size))
            if denoise < 0.5:
                enhancer = ImageFilter.UnsharpMask(radius=2, percent=100, threshold=3)
                pil_img = pil_img.filter(enhancer)
            enhanced_img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        
        new_h, new_w = enhanced_img.shape[:2]
        process_time = time.time() - start_time
        
        print(f"[RealESRGAN] 推理完成: 神经网络耗时 {inference_time:.2f}s, 总耗时 {process_time:.2f}s")
        print(f"[RealESRGAN] 输出尺寸: {new_w}x{new_h}")
        
        # 编码为 JPEG
        quality = 95 if max(new_w, new_h) < 2000 else 90
        encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
        ok, encoded = cv2.imencode(".jpg", enhanced_img, encode_params)
        
        if not ok:
            raise HTTPException(status_code=500, detail="结果图编码失败")
        
        print(f"[RealESRGAN] 输出图片: {len(encoded.tobytes()) / 1024:.1f} KB")
        
        return Response(
            content=encoded.tobytes(), 
            media_type="image/jpeg",
            headers={
                "X-Process-Time": str(process_time),
                "X-Inference-Time": str(inference_time),
                "X-Original-Size": f"{orig_w}x{orig_h}",
                "X-Enhanced-Size": f"{new_w}x{new_h}"
            }
        )
        
    except Exception as e:
        print(f"[RealESRGAN] 处理失败: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"增强处理失败: {str(e)}")


# ========== ROI 增强并回拼路由 (第一阶段最小链路) ==========

import json

@app.post("/model/enhance-roi")
async def predict_enhance_roi(
    request: Request,
    file: UploadFile = File(...),
    bbox: str = Form(...),  # JSON string: "[x1, y1, x2, y2]"
    source: str = Form("image"),
    scale: int = Form(4),
    denoise: float = Form(0),
):
    """
    ROI 增强并回拼原图接口（第一阶段最小链路）
    
    参数:
        bbox: JSON 字符串格式的坐标数组 [x1, y1, x2, y2]（绝对像素坐标）
        scale: 增强倍数（默认 4）
        denoise: 降噪强度 0-1（默认 0）
    
    处理流程:
        1. 读取原图
        2. 解析 bbox 并边界检查
        3. 裁剪 ROI
        4. Real-ESRGAN 增强（4x）
        5. resize ROI 回原 bbox 尺寸
        6. 回拼到原图
        7. 返回 stitched image
    """
    print(f"\n{'='*60}")
    print(f"[ROI-Enhance] === 收到 ROI 增强请求: {datetime.now()} ===")
    print(f"[ROI-Enhance] 文件: {file.filename if file else 'None'}")
    print(f"[ROI-Enhance] bbox 参数: {bbox}")
    print(f"{'='*60}\n")
    
    start_time = time.time()
    
    if source != "image":
        return JSONResponse(
            {"error": "当前版本只支持 image"},
            status_code=400
        )
    
    # 1. 读取原图
    print("[ROI-Enhance] 步骤 1/7: 读取原图...")
    data = await file.read()
    img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(status_code=400, detail="无法解析上传图片")
    
    img_h, img_w = img.shape[:2]
    print(f"[ROI-Enhance] 步骤 1/7 完成: 原图尺寸 {img_w}x{img_h}")
    
    # 2. 解析 bbox
    print("[ROI-Enhance] 步骤 2/7: 解析 bbox...")
    try:
        bbox_coords = json.loads(bbox)
        if not isinstance(bbox_coords, list) or len(bbox_coords) != 4:
            raise ValueError("bbox 必须是包含 4 个元素的数组")
        x1, y1, x2, y2 = map(int, bbox_coords)
        print(f"[ROI-Enhance] 原始 bbox: ({x1}, {y1}, {x2}, {y2})")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"bbox 格式错误: {str(e)}")
    
    # 3. 边界检查和处理
    print("[ROI-Enhance] 步骤 3/7: 边界检查...")
    # 确保 x1 < x2, y1 < y2
    x1, x2 = min(x1, x2), max(x1, x2)
    y1, y2 = min(y1, y2), max(y1, y2)
    
    # 裁剪到图像边界
    x1 = max(0, min(x1, img_w))
    y1 = max(0, min(y1, img_h))
    x2 = max(0, min(x2, img_w))
    y2 = max(0, min(y2, img_h))
    
    roi_w = x2 - x1
    roi_h = y2 - y1
    
    print(f"[ROI-Enhance] 裁剪后 bbox: ({x1}, {y1}, {x2}, {y2}), 尺寸: {roi_w}x{roi_h}")
    
    # ROI 尺寸检查
    MIN_ROI_SIZE = 32
    if roi_w < MIN_ROI_SIZE or roi_h < MIN_ROI_SIZE:
        raise HTTPException(
            status_code=400, 
            detail=f"ROI 尺寸过小: {roi_w}x{roi_h}, 最小要求: {MIN_ROI_SIZE}x{MIN_ROI_SIZE}"
        )
    
    print(f"[ROI-Enhance] 步骤 3/7 完成: ROI 尺寸 {roi_w}x{roi_h}")
    
    # 4. 裁剪 ROI
    print("[ROI-Enhance] 步骤 4/7: 裁剪 ROI...")
    roi = img[y1:y2, x1:x2].copy()
    print(f"[ROI-Enhance] 步骤 4/7 完成: ROI 裁剪成功")
    
    # 5. Real-ESRGAN 增强
    print("[ROI-Enhance] 步骤 5/7: Real-ESRGAN 增强...")
    model = get_model()
    inference_start = time.time()
    enhanced_roi = model.enhance(roi, outscale=REALESRGAN_SCALE)
    inference_time = time.time() - inference_start
    enhanced_h, enhanced_w = enhanced_roi.shape[:2]
    print(f"[ROI-Enhance] 步骤 5/7 完成: 增强后尺寸 {enhanced_w}x{enhanced_h}, 耗时 {inference_time:.2f}s")
    
    # 6. resize 回原 ROI 尺寸
    print("[ROI-Enhance] 步骤 6/7: resize 回原尺寸...")
    if enhanced_w != roi_w or enhanced_h != roi_h:
        resized_roi = cv2.resize(enhanced_roi, (roi_w, roi_h), interpolation=cv2.INTER_LANCZOS4)
        print(f"[ROI-Enhance] resize: {enhanced_w}x{enhanced_h} -> {roi_w}x{roi_h}")
    else:
        resized_roi = enhanced_roi
        print(f"[ROI-Enhance] 无需 resize")
    
    # 可选：后处理降噪
    if denoise > 0:
        print(f"[ROI-Enhance] 应用降噪 (强度: {denoise:.2f})...")
        img_rgb = cv2.cvtColor(resized_roi, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(img_rgb)
        filter_size = int(3 + denoise * 4)
        if filter_size % 2 == 0:
            filter_size += 1
        pil_img = pil_img.filter(ImageFilter.MedianFilter(size=filter_size))
        if denoise < 0.5:
            enhancer = ImageFilter.UnsharpMask(radius=2, percent=100, threshold=3)
            pil_img = pil_img.filter(enhancer)
        resized_roi = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    
    print(f"[ROI-Enhance] 步骤 6/7 完成")
    
    # 7. 回拼到原图
    print("[ROI-Enhance] 步骤 7/7: 回拼到原图...")
    img[y1:y2, x1:x2] = resized_roi
    process_time = time.time() - start_time
    print(f"[ROI-Enhance] 步骤 7/7 完成: 总耗时 {process_time:.2f}s")
    
    # 编码返回
    quality = 95 if max(img_w, img_h) < 2000 else 90
    encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
    ok, encoded = cv2.imencode(".jpg", img, encode_params)
    
    if not ok:
        raise HTTPException(status_code=500, detail="结果图编码失败")
    
    print(f"[ROI-Enhance] 输出图片: {len(encoded.tobytes()) / 1024:.1f} KB")
    print(f"[ROI-Enhance] === 处理完成 ===\n")
    
    return Response(
        content=encoded.tobytes(),
        media_type="image/jpeg",
        headers={
            "X-Process-Time": str(process_time),
            "X-Inference-Time": str(inference_time),
            "X-Original-Size": f"{img_w}x{img_h}",
            "X-Roi-Size": f"{roi_w}x{roi_h}",
            "X-Roi-Count": "1"
        }
    )


@app.post("/model/enhance-mask")
async def predict_enhance_mask(
    request: Request,
    file: UploadFile = File(...),
    bbox: str = Form(...),      # JSON: [x1, y1, x2, y2]
    mask: str = Form(...),      # base64 编码的 PNG mask
    scale: int = Form(4),
    denoise: float = Form(0),
):
    """
    Mask 级精确增强接口（阶段 2B）
    
    参数:
        bbox: 目标区域 [x1, y1, x2, y2]
        mask: base64 编码的局部二值 mask (PNG 格式)
        scale: 增强倍数
        denoise: 降噪强度
    
    处理流程:
        1. 读取原图
        2. 解析 bbox
        3. 解码 mask base64
        4. 校验 mask 尺寸与 bbox 匹配
        5. 按 bbox 裁剪 ROI
        6. Real-ESRGAN 增强 ROI
        7. mask 引导融合（mask 内 enhanced，mask 外原图）
        8. 贴回原图
        9. 返回结果
    """
    print(f"\n{'='*60}")
    print(f"[Mask-Enhance] === 收到 Mask 精确增强请求: {datetime.now()} ===")
    print(f"[Mask-Enhance] bbox: {bbox}")
    print(f"{'='*60}\n")
    
    start_time = time.time()
    
    # 1. 读取原图
    print("[Mask-Enhance] 步骤 1/8: 读取原图...")
    data = await file.read()
    img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(status_code=400, detail="无法解析上传图片")
    
    img_h, img_w = img.shape[:2]
    print(f"[Mask-Enhance] 步骤 1/8 完成: 原图尺寸 {img_w}x{img_h}")
    
    # 2. 解析 bbox
    print("[Mask-Enhance] 步骤 2/8: 解析 bbox...")
    try:
        bbox_coords = json.loads(bbox)
        if not isinstance(bbox_coords, list) or len(bbox_coords) != 4:
            raise ValueError("bbox 必须是包含 4 个元素的数组")
        x1, y1, x2, y2 = map(int, bbox_coords)
        x1, x2 = max(0, min(x1, img_w)), max(0, min(x2, img_w))
        y1, y2 = max(0, min(y1, img_h)), max(0, min(y2, img_h))
        roi_w, roi_h = x2 - x1, y2 - y1
        print(f"[Mask-Enhance] bbox: ({x1}, {y1}, {x2}, {y2}), ROI: {roi_w}x{roi_h}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"bbox 格式错误: {str(e)}")
    
    # ROI 尺寸检查
    MIN_ROI_SIZE = 32
    if roi_w < MIN_ROI_SIZE or roi_h < MIN_ROI_SIZE:
        raise HTTPException(status_code=400, detail=f"ROI 尺寸过小: {roi_w}x{roi_h}")
    
    # 3. 解码 mask
    print("[Mask-Enhance] 步骤 3/8: 解码 mask...")
    try:
        mask_bytes = base64.b64decode(mask)
        mask_arr = np.frombuffer(mask_bytes, np.uint8)
        mask_img = cv2.imdecode(mask_arr, cv2.IMREAD_GRAYSCALE)
        
        if mask_img is None:
            raise ValueError("无法解码 mask 图像")
        
        print(f"[Mask-Enhance] mask 尺寸: {mask_img.shape[1]}x{mask_img.shape[0]}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"mask 解码失败: {str(e)}")
    
    # 4. 校验 mask 尺寸与 bbox 匹配
    print("[Mask-Enhance] 步骤 4/8: 校验 mask 尺寸...")
    if mask_img.shape[1] != roi_w or mask_img.shape[0] != roi_h:
        raise HTTPException(
            status_code=400, 
            detail=f"mask 尺寸 ({mask_img.shape[1]}x{mask_img.shape[0]}) 与 bbox ({roi_w}x{roi_h}) 不匹配"
        )
    
    # 二值化 mask（确保是 0/255）
    mask_binary = (mask_img > 127).astype(np.uint8) * 255
    print(f"[Mask-Enhance] mask 有效像素数: {np.sum(mask_binary > 0)}")
    
    # 5. 裁剪 ROI
    print("[Mask-Enhance] 步骤 5/8: 裁剪 ROI...")
    roi = img[y1:y2, x1:x2].copy()
    
    # 6. Real-ESRGAN 增强
    print("[Mask-Enhance] 步骤 6/8: Real-ESRGAN 增强...")
    model = get_model()
    inference_start = time.time()
    enhanced_roi = model.enhance(roi, outscale=REALESRGAN_SCALE)
    inference_time = time.time() - inference_start
    
    # resize 回原 ROI 尺寸
    if enhanced_roi.shape[1] != roi_w or enhanced_roi.shape[0] != roi_h:
        enhanced_roi = cv2.resize(enhanced_roi, (roi_w, roi_h), interpolation=cv2.INTER_LANCZOS4)
    
    print(f"[Mask-Enhance] 增强完成，耗时 {inference_time:.2f}s")
    
    # 可选降噪
    if denoise > 0:
        img_rgb = cv2.cvtColor(enhanced_roi, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(img_rgb)
        filter_size = int(3 + denoise * 4)
        if filter_size % 2 == 0:
            filter_size += 1
        pil_img = pil_img.filter(ImageFilter.MedianFilter(size=filter_size))
        if denoise < 0.5:
            enhancer = ImageFilter.UnsharpMask(radius=2, percent=100, threshold=3)
            pil_img = pil_img.filter(enhancer)
        enhanced_roi = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    
    # 7. mask 引导融合（hard paste，第一版无 feather）
    print("[Mask-Enhance] 步骤 7/8: mask 引导融合...")
    result_roi = roi.copy()
    
    # mask == 255 的区域使用 enhanced，mask == 0 的区域保留原图
    mask_bool = mask_binary > 0
    result_roi[mask_bool] = enhanced_roi[mask_bool]
    
    enhanced_pixels = np.sum(mask_bool)
    total_pixels = mask_bool.size
    print(f"[Mask-Enhance] 融合完成: {enhanced_pixels}/{total_pixels} 像素被增强 ({enhanced_pixels/total_pixels*100:.1f}%)")
    
    # 8. 贴回原图
    print("[Mask-Enhance] 步骤 8/8: 贴回原图...")
    img[y1:y2, x1:x2] = result_roi
    process_time = time.time() - start_time
    
    # 编码返回
    quality = 95 if max(img_w, img_h) < 2000 else 90
    encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
    ok, encoded = cv2.imencode(".jpg", img, encode_params)
    
    if not ok:
        raise HTTPException(status_code=500, detail="结果图编码失败")
    
    print(f"[Mask-Enhance] 输出图片: {len(encoded.tobytes()) / 1024:.1f} KB")
    print(f"[Mask-Enhance] === 处理完成 ===\n")
    
    return Response(
        content=encoded.tobytes(),
        media_type="image/jpeg",
        headers={
            "X-Process-Time": str(process_time),
            "X-Inference-Time": str(inference_time),
            "X-Original-Size": f"{img_w}x{img_h}",
            "X-Roi-Size": f"{roi_w}x{roi_h}",
            "X-Enhanced-Pixels": str(enhanced_pixels)
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
