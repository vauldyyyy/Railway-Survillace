# =====================================================================
# RailGuard AI - Remote GPU Bridge Worker
# =====================================================================
# Optimized for Google Colab T4 / Remote GPU Runtimes
# ---------------------------------------------------------------------

import os
import sys
import time
import threading
import subprocess

# Auto-install missing dependencies if running on a fresh Colab instance
try:
    import fastapi
    import uvicorn
    from pyngrok import ngrok
except ImportError:
    print("[Worker] Installing dependencies...")
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
from ultralytics import YOLOWorld

# Global configuration
MODEL_PATH = "yolov8s-worldv2.pt"
PORT = 8000

print(f"[Worker] Loading Zero-Shot Engine ({MODEL_PATH})...")
try:
    model = YOLOWorld(MODEL_PATH)
    
    # Default Railway Prompts (Sync with yolo_world.py)
    DEFAULT_CLASSES = [
        "person on railway track",
        "person near platform edge",
        "metal debris on track",
        "plastic bag on track",
        "stone or rock on track",
        "fire",
        "smoke",
        "unattended backpack on platform",
        "abandoned suitcase or luggage",
        "person fighting or brawling",
        "crowd surge on platform",
        "animal on track",
        "person climbing fence",
        "drone or UAV in restricted area",
        "person",
    ]
    model.set_classes(DEFAULT_CLASSES)
    print("[Worker] Model loaded and vocabulary initialized.")
except Exception as e:
    print(f"[Worker-Error] Model initialization failed: {e}")
    model = None

app = FastAPI(title="RailGuard AI Remote Inference Worker")

@app.get("/health")
def health():
    return {
        "status": "ok",
        "gpu_active": True,
        "model_loaded": model is not None,
        "device": "cuda" if model and hasattr(model, 'device') else "cpu",
        "timestamp": time.time()
    }

@app.post("/detect")
async def detect(image: UploadFile = File(...), condition: str = Form("normal")):
    """
    Receives an image and returns zero-shot detections.
    Standardized 'image' field for client compatibility.
    """
    if model is None:
        return {"detections": [], "error": "Model not loaded"}

    # Read image
    contents = await image.read()
    nparr = np.frombuffer(contents, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if frame is None:
        return {"detections": [], "error": "Invalid image data"}

    start_time = time.time()
    
    # Dynamic thresholds based on condition
    thresholds = {
        "normal": 0.12,
        "rain":   0.08,
        "fog":    0.08,
        "night":  0.08,
    }
    active_conf = thresholds.get(condition, 0.10)

    # Inference
    results = model.predict(frame, conf=active_conf, verbose=False)
    
    detections = []
    
    def get_severity(class_name):
        if any(kw in class_name for kw in ["track", "fire", "smoke", "fighting", "fence"]):
            return "critical"
        elif any(kw in class_name for kw in ["edge", "backpack", "suitcase", "drone", "surge"]):
            return "warning"
        return "info"

    for r in results:
        boxes = r.boxes.xyxy.cpu().numpy()
        confs = r.boxes.conf.cpu().numpy()
        class_ids = r.boxes.cls.int().cpu().numpy()
        
        for box, conf, cls_id in zip(boxes, confs, class_ids):
            class_name = DEFAULT_CLASSES[cls_id] if cls_id < len(DEFAULT_CLASSES) else str(cls_id)
            
            detections.append({
                "class_name": class_name,
                "confidence": float(conf),
                "box": [int(v) for v in box],
                "severity": get_severity(class_name)
            })
    
    latency_ms = (time.time() - start_time) * 1000
    return {"detections": detections, "latency_ms": latency_ms}

def start_bridge():
    """Starts the Ngrok tunnel and the FastAPI server."""
    # Use environment variables if present, else fallback
    auth_token = os.environ.get("NGROK_AUTH_TOKEN", "3BZhk7iUmp5UwGperiFtCX2Grg5_5smvYsP62aYfoARe9CsnK")
    ngrok.set_auth_token(auth_token)
    
    try:
        # Clean up old tunnels
        tunnels = ngrok.get_tunnels()
        for t in tunnels:
            ngrok.disconnect(t.public_url)
    except:
        pass

    # Connect to Ngrok
    # For Hackathon stability, use a static domain if provided via env
    static_domain = os.environ.get("NGROK_STATIC_DOMAIN")
    if static_domain:
        public_url = ngrok.connect(addr=PORT, domain=static_domain).public_url
    else:
        public_url = ngrok.connect(addr=PORT).public_url

    print("\n" + "="*60)
    print(f"🚀 RAILGUARD REMOTE GPU BRIDGE ACTIVE")
    print(f"🔗 URL: {public_url}")
    print(f"📡 Status: Listening on Port {PORT}")
    print("="*60 + "\n")

    # Start Uvicorn in a sub-thread or directly if main
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="info")

if __name__ == "__main__":
    start_bridge()
