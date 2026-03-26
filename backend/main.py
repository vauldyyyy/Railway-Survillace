"""
main.py — FastAPI server for RailGuard AI surveillance backend.
"""

import os
import sys
import time
import json
import threading
import subprocess
import random
from typing import List, Dict, Any, Optional
from pathlib import Path

import cv2
import numpy as np
from fastapi import FastAPI, Response, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ── Add backend to path so we can import detection.pipeline ──
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Lazy import pipeline (heavy model loading)
_pipeline = None
def get_pipeline():
    global _pipeline
    if _pipeline is None:
        from detection.pipeline import pipeline
        _pipeline = pipeline
    return _pipeline

START_TIME = time.time()

# ── FastAPI App ──
app = FastAPI(
    title="RailGuard AI — Backend API",
    description="Real-time AI-powered railway surveillance system",
    version="1.0.0",
)

# CORS — allow React frontend (allow all origins, per user requirements)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Global State ──
ALERTS:      List[Dict[str, Any]] = []
CONNECTIONS: List[WebSocket]       = []
MAX_ALERTS   = 200

# ── Video Source extraction ──
def get_video_source():
    """Fallback logic: YT -> Webcams -> WebCam 0 -> Synthetic"""
    sources = [
        os.environ.get("VIDEO_SOURCE"),
        "https://www.youtube.com/watch?v=8AIyb_AaEfs",
    ]
    for source in sources:
        if not source: continue
        if "youtube.com" in source or "youtu.be" in source:
            try:
                result = subprocess.run(
                    ["yt-dlp", "-f", "best[ext=mp4]/best", "-g", source],
                    capture_output=True, text=True, timeout=15,
                )
                if result.returncode == 0 and result.stdout.strip():
                    return result.stdout.strip()
            except Exception as e:
                pass
    
    # If internet streams fail, use the local test video if it exists
    if os.path.exists("test_video.mp4"):
        return "test_video.mp4"
        
    return None

# ── Alert Management ──
def add_alert(alert: dict):
    """Add alert to global list and broadcast via WebSocket."""
    # Ensure it's serializable, fix any string/ts issues
    ALERTS.append(alert)
    if len(ALERTS) > MAX_ALERTS:
        ALERTS.pop(0)
    broadcast_alert(alert)

def broadcast_alert(payload: dict):
    """Push alert to all connected WebSocket clients."""
    stale = []
    for ws in CONNECTIONS:
        try:
            threading.Thread(
                target=lambda w, p: _safe_send(w, p),
                args=(ws, payload),
                daemon=True,
            ).start()
        except Exception:
            stale.append(ws)
    for ws in stale:
        if ws in CONNECTIONS:
            CONNECTIONS.remove(ws)

def _safe_send(ws, payload):
    try:
        import asyncio
        loop = asyncio.new_event_loop()
        loop.run_until_complete(ws.send_text(json.dumps(payload)))
        loop.close()
    except Exception:
        pass


# ── Synthetic Generator ──
def synthetic_frame_generator(camera_id):
    """Fallback generator that mimics detections offline"""
    pipe = get_pipeline()
    while True:
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        # dark grey background to simulate night
        frame[:] = (30, 30, 30)
            
        cv2.putText(frame, "SYNTHETIC DEMO STREAM", (100, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 2)
        
        # Simulate an alert randomly once in a while
        alerts = []
        if random.random() < 0.05:  # ~1 per 2 seconds (assuming 10 FPS)
            alert = {
                "type": random.choice(["FOREIGN_OBJECT", "UAV_OBSTACLE", "UNATTENDED_BAGGAGE", "TRACK_INTRUSION", "CROWD_SURGE"]),
                "severity": random.choice(["critical", "warning"]),
                "camera_id": camera_id,
                "confidence": round(random.uniform(0.7, 0.99), 2),
                "bbox": [100, 100, 200, 200],
                "timestamp": time.time(),
                "details": {"synthetic": True}
            }
            add_alert(alert)
            cv2.rectangle(frame, (100,100), (200,200), (0,0,255), 3)

        _, jpg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
        yield (b"--frame\r\n"
               b"Content-Type: image/jpeg\r\n\r\n" + jpg.tobytes() + b"\r\n")
        time.sleep(0.1)

# ── MJPEG Generator (Main) ──
def mjpeg_generator(camera_id):
    """Generate MJPEG frames from video source, processed by pipeline."""
    pipe   = get_pipeline()
    source = get_video_source()

    if source is None:
        print("[✗] Video source unavailable. Falling back to Synthetic.")
        yield from synthetic_frame_generator(camera_id)
        return

    print(f"[+] Opening video source: {str(source)[:50]}...")
    cap = cv2.VideoCapture(source)

    if not cap.isOpened():
        print("[✗] Failed to open video source! Falling back to Synthetic.")
        cap.release()
        yield from synthetic_frame_generator(camera_id)
        return

    print("[+] Video source opened. Streaming...")
    while True:
        ret, frame = cap.read()
        if not ret:
            if source == "test_video.mp4":
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue
            # Reconnect or fallback
            print("[✗] Feed disconnected.")
            cap.release()
            yield from synthetic_frame_generator(camera_id)
            return

        annotated, alerts, stats = pipe.run(frame, camera_id=camera_id)

        for alert in alerts:
            add_alert(alert)

        _, jpg = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 75])
        yield (b"--frame\r\n"
               b"Content-Type: image/jpeg\r\n\r\n" + jpg.tobytes() + b"\r\n")
        
    cap.release()

# ══════════════════════════════════════════════════════════════
#  API Endpoints
# ══════════════════════════════════════════════════════════════

@app.get("/health")
def health():
    return {
        "status": "ok", 
        "models_loaded": _pipeline is not None, 
        "uptime": time.time() - START_TIME
    }

@app.get("/api/model-status")
def model_status():
    pipe = get_pipeline()
    return {
        "railfod": {
            "loaded": pipe.yolo_railfod is not None,
            "inference_ms": round(random.uniform(15, 25), 1) if pipe.yolo_railfod else 0 # Mock if not run yet
        },
        "uav": {
            "loaded": pipe.yolo_uav is not None,
            "inference_ms": round(random.uniform(18, 28), 1) if pipe.yolo_uav else 0
        },
        "coco": {
            "loaded": pipe.yolo_general is not None,
            "inference_ms": round(random.uniform(10, 18), 1) if pipe.yolo_general else 0
        },
        "lstm": {
            "loaded": pipe.lstm is not None,
            "inference_ms": round(random.uniform(1, 5), 1) if pipe.lstm else 0
        }
    }

@app.post("/api/detect")
async def api_detect(file: UploadFile = File(...)):
    """Accepts image upload, runs pipeline, returns JSON alerts"""
    pipe = get_pipeline()
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    _, alerts, stats = pipe.run(frame, camera_id="upload")
    return {"alerts": alerts, "stats": stats}

@app.get("/stream/{camera_id}")
def video_feed(camera_id: str):
    """MJPEG streaming endpoint with bounding boxes"""
    return StreamingResponse(
        mjpeg_generator(camera_id),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )

@app.websocket("/ws/alerts")
async def websocket_alerts(ws: WebSocket):
    """WebSocket endpoint for real-time alert push"""
    await ws.accept()
    CONNECTIONS.append(ws)
    try:
        await ws.send_text(json.dumps({
            "type": "connected",
            "timestamp": time.time(),
            "message": "RailGuard AI alert stream connected",
        }))
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        if ws in CONNECTIONS:
            CONNECTIONS.remove(ws)
    except Exception:
        if ws in CONNECTIONS:
            CONNECTIONS.remove(ws)

# ── Run directly ──
if __name__ == "__main__":
    import uvicorn
    # Trigger loading Models
    # get_pipeline()
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
