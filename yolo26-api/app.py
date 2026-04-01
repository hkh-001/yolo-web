from fastapi import FastAPI, UploadFile, File, Form, Request, HTTPException
from fastapi.responses import JSONResponse, Response
from ultralytics import YOLO
import numpy as np
import cv2

app = FastAPI()

MODEL_PATH = "weights/yolo26n.pt"
model = YOLO(MODEL_PATH)

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
    if source != "image":
        return JSONResponse(
            {"error": "当前版本只支持 image，不支持 video"},
            status_code=400
        )

    data = await file.read()
    arr = np.frombuffer(data, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)

    if img is None:
        raise HTTPException(status_code=400, detail="无法解析上传图片")

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