# =====================================================================
# Google Colab GPU Bridge Server
# =====================================================================

# Install required dependencies quietly
import os
import sys

# Install into the ACTIVE Python interpreter (fixes Colab env issues)
import subprocess
subprocess.check_call([
    sys.executable, "-m", "pip", "install", "-q",
    "fastapi", "uvicorn", "python-multipart",
    "pyngrok", "nest-asyncio", "ultralytics", "opencv-python-headless"
])

import nest_asyncio
import uvicorn
from fastapi import FastAPI, UploadFile, File, Form
from pyngrok import ngrok
import cv2
import numpy as np
import time

try:
    from ultralytics import YOLO
    print("Loading YOLOv8s-World model on GPU...")
    model = YOLO("yolov8s-world.pt")
except Exception as e:
    print(f"Error loading model: {e}")
    model = None

app = FastAPI(title="Colab Remote Inference Worker")

@app.post("/detect")
async def detect(file: UploadFile = File(...), condition: str = Form("normal")):
    if model is None:
        return {"detections": []}

    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    start = time.time()
    
    # Custom YOLO-World prompting based on condition
    if hasattr(model, "set_classes"):
        classes = ["person", "backpack", "suitcase", "train", "animal"]
        if condition == "low_light":
            classes.extend(["flashlight"])
        model.set_classes(classes)

    results = model(frame, verbose=False)
    
    detections = []
    # Allowed classes from main app
    target_classes = ["person", "backpack", "suitcase", "train", "animal"]
    
    for r in results:
        for box in r.boxes:
            conf = float(box.conf[0])
            if conf < 0.25:
                continue
                
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            cls_id = int(box.cls[0])
            cls_name = model.names[cls_id] if hasattr(model, 'names') else str(cls_id)
            
            if cls_name not in target_classes and not hasattr(model, "set_classes"):
                continue

            severity = "medium"
            if cls_name in ["weapon", "fire", "smoke"]:
                severity = "critical"
            
            detections.append({
                "class_name": cls_name,
                "box": [x1, y1, x2, y2],
                "confidence": conf,
                "severity": severity,
                "condition": condition
            })
    
    latency_ms = (time.time() - start) * 1000
    return {"detections": detections, "latency_ms": latency_ms}

@app.get("/health")
def health():
    return {"status": "ok", "gpu_active": True, "model_loaded": model is not None}

# --- Start Bridge ---
NGROK_TOKEN = "3BZhk7iUmp5UwGperiFtCX2Grg5_5smvYsP62aYfoARe9CsnK"

ngrok.set_auth_token(NGROK_TOKEN)
tunnel = ngrok.connect(addr=8000, domain="diane-nectarous-medicably.ngrok-free.dev")
public_url = tunnel.public_url
print("=========================================")
print(f"REMOTE GPU BRIDGE ACTIVE:")
print(f"URL: {public_url}")
print("Paste this into your .env as REMOTE_INFERENCE_URL")
print("=========================================")

# Run uvicorn inside Colab's existing event loop
import asyncio
config = uvicorn.Config(app, host="0.0.0.0", port=8000)
server = uvicorn.Server(config)
asyncio.get_event_loop().create_task(server.serve())
