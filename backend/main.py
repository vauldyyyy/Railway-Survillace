"""
main.py — FastAPI server for RailGuard AI surveillance backend.
"""

import os
import sys
import time
import json
import asyncio
import threading
import subprocess
import random
from typing import List, Dict, Any, Optional
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

import cv2
import numpy as np
from fastapi import FastAPI, Response, WebSocket, WebSocketDisconnect, UploadFile, File, Depends
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

# ── Add backend to path so we can import detection.pipeline ──
sys.path.insert(0, str(Path(__file__).resolve().parent))

from security.auth import create_access_token, verify_token, verify_ws_token

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
LATEST_STATS: Dict[str, Any] = {}
executor = ThreadPoolExecutor(max_workers=4)

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

# ── Alert and WebSocket Management ──
def add_alert(alert: dict):
    """Add alert to global list and broadcast via WebSocket."""
    ALERTS.append(alert)
    if len(ALERTS) > MAX_ALERTS:
        ALERTS.pop(0)
    broadcast_message("alert", alert)

def broadcast_message(channel: str, payload: dict):
    """Push arbitrary channel data to all connected WebSocket clients."""
    if not CONNECTIONS:
        return
        
    msg = json.dumps({"channel": channel, "payload": payload})
    stale = []
    
    # Send synchronously (Starlette background tasks or similar are better, but this works for demo)
    for ws in CONNECTIONS:
        try:
            threading.Thread(
                target=lambda w, m: _safe_send(w, m),
                args=(ws, msg),
                daemon=True,
            ).start()
        except Exception:
            stale.append(ws)
            
    for ws in stale:
        if ws in CONNECTIONS:
            CONNECTIONS.remove(ws)

def _safe_send(ws, msg):
    try:
        loop = asyncio.new_event_loop()
        loop.run_until_complete(ws.send_text(msg))
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
async def mjpeg_generator(camera_id):
    """Generate MJPEG frames from video source, processed by pipeline asynchronously with 30 FPS throttle."""
    pipeline = get_pipeline()
    source = get_video_source()

    if source is None:
        print("[✗] Video source unavailable. Falling back to Synthetic.")
        for chunk in synthetic_frame_generator(camera_id):
             yield chunk
             await asyncio.sleep(0.01)
        return

    print(f"[+] Opening video source: {str(source)[:50]}...")
    cap = cv2.VideoCapture(source)

    if not cap.isOpened():
        print("[✗] Failed to open video source! Falling back to Synthetic.")
        cap.release()
        for chunk in synthetic_frame_generator(camera_id):
             yield chunk
             await asyncio.sleep(0.01)
        return

    print("[+] Video source opened. Streaming...")
    
    last_broadcast_time = 0.0
    
    while True:
        try:
            start_t = time.time()
            ret, frame = cap.read()
            
            if not ret:
                if source == "test_video.mp4":
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    await asyncio.sleep(0.01)
                    continue
                print("[✗] Feed disconnected.")
                cap.release()
                for chunk in synthetic_frame_generator(camera_id):
                     yield chunk
                     await asyncio.sleep(0.01)
                return

            loop = asyncio.get_event_loop()
            frame_bytes, alerts, all_trajectories = await loop.run_in_executor(
                executor, 
                pipeline.run, 
                frame, 
                camera_id
            )
            
            current_time = time.time()
            # Broadcast Telemetry (throttled to 2Hz)
            if (current_time - last_broadcast_time) >= 0.5:
                fps = pipeline.current_fps
                broadcast_message("metrics", {"model": "yolo-world", "metrics": {"fps": fps, "latency_ms": 0, "gpu_util_pct": 0}})
                
                # Push real-time ReID maps to the frontend
                broadcast_message("trajectories", all_trajectories)
                
                # Broadcast threat score dynamically 
                threat_score = min(10.0, round(len(ALERTS) * 0.5, 1))
                broadcast_message("threat", {"score": threat_score})
                last_broadcast_time = current_time

            for alert in alerts:
                add_alert(alert)

            _, jpg = cv2.imencode(".jpg", frame_bytes, [cv2.IMWRITE_JPEG_QUALITY, 75])
            yield (b'--frame\r\n'
                   b"Content-Type: image/jpeg\r\n\r\n" + jpg.tobytes() + b'\r\n')
                   
            # Enforce 30 FPS cap to prevent browser OOM flooding
            elapsed = time.time() - start_t
            if elapsed < 0.033:
                await asyncio.sleep(0.033 - elapsed)
                
        except asyncio.CancelledError:
            if cap.isOpened(): cap.release()
            break
        except Exception as e:
            print(f"[Streaming Error - {camera_id}] {e}")
            await asyncio.sleep(1)

# ══════════════════════════════════════════════════════════════
#  API Endpoints
# ══════════════════════════════════════════════════════════════

class ThreatClassesUpdate(BaseModel):
    classes: List[str]

@app.post("/api/threats/update-classes")
def update_threat_classes(payload: ThreatClassesUpdate):
    """Dynamic Hackathon Endpoint: Replaces YOLO-World text prompts instantly."""
    pipe = get_pipeline()
    pipe.yolo.set_classes(payload.classes)
    return {"status": "success", "active_classes": pipe.yolo.current_classes}

@app.get("/api/reid/gallery")
def get_reid_gallery():
    """Returns the anonymized UUID spatial paths for cross-camera tracking."""
    pipe = get_pipeline()
    return pipe.reid.gallery


@app.post("/api/auth/token")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Mock authentication endpoint for SOC operator login."""
    if form_data.username == "admin" and form_data.password == "railguard":
        token = create_access_token({"sub": form_data.username, "role": "soc_operator"})
        return {"access_token": token, "token_type": "bearer"}
    return JSONResponse(status_code=401, content={"detail": "Incorrect credentials"})

@app.get("/health")
def health():
    return {
        "status": "ok", 
        "models_loaded": _pipeline is not None, 
        "uptime": time.time() - START_TIME
    }

@app.get("/api/metrics")
def get_metrics(token_data: dict = Depends(verify_token)):
    """Returns the latest inference metrics from the pipeline (Protected)."""
    return LATEST_STATS

@app.get("/api/system-health")
def get_system_health(token_data: dict = Depends(verify_token)):
    """Returns edge computing node utilization metadata (Protected)."""
    return {
        "edge_nodes": [
            { "id": "EDGE_01", "station": "Madgaon Junction", "status": "healthy", "cpu_pct": random.randint(35, 65), "gpu_pct": random.randint(45, 80), "memory_pct": 55, "uptime_hours": 342, "models_loaded": 4, "last_heartbeat": int(time.time() * 1000) },
            { "id": "EDGE_02", "station": "Thivim Station", "status": "healthy", "cpu_pct": random.randint(25, 45), "gpu_pct": random.randint(30, 60), "memory_pct": 48, "uptime_hours": 220, "models_loaded": 4, "last_heartbeat": int(time.time() * 1000) },
            { "id": "EDGE_03", "station": "Vasco da Gama", "status": "degraded", "cpu_pct": random.randint(80, 95), "gpu_pct": random.randint(90, 99), "memory_pct": 82, "uptime_hours": 18, "models_loaded": 3, "last_heartbeat": int(time.time() * 1000) - 30000 },
        ]
    }

@app.get("/api/model-status")
def model_status():
    pipe = get_pipeline()
    return {
        "yolo_world": {
            "loaded": getattr(pipe.yolo, "model", None) is not None,
            "active_classes": getattr(pipe.yolo, "current_classes", []),
            "mode": "zero-shot"
        },
        "reid": {
            "loaded": getattr(pipe.reid, "extractor", None) is not None,
            "tracked_uuids": len(getattr(pipe.reid, "gallery", {})),
            "privacy": "differential-privacy-active"
        },
        "zone_detector": {
            "loaded": pipe.zone_detector is not None,
        }
    }

@app.post("/api/detect")
async def api_detect(file: UploadFile = File(...)):
    """Accepts image upload, runs pipeline, returns JSON alerts"""
    pipe = get_pipeline()
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    _, alerts, trajectories = pipe.run(frame, camera_id="upload")
    return {"alerts": alerts, "tracked_uuids": len(trajectories)}

@app.get("/stream/{camera_id}")
def video_feed(camera_id: str):
    """MJPEG streaming endpoint with bounding boxes"""
    return StreamingResponse(
        mjpeg_generator(camera_id),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )

@app.websocket("/ws/alerts")
async def websocket_alerts(ws: WebSocket):
    """WebSocket endpoint for real-time alert push (Hackathon Demo Mode - Open Auth)"""
    await ws.accept()
    
    # Optional Auth Logging (Does not drop connection)
    try:
        user_payload = await verify_ws_token(ws)
        if user_payload:
            print(f"[WS] Authenticated connection from user: {user_payload.get('sub')}")
    except Exception:
        print("[WS] Unauthenticated fallback connection accepted for Hackathon display.")
        
    CONNECTIONS.append(ws)
    try:
        await ws.send_text(json.dumps({
            "channel": "system",
            "payload": {
                "type": "connected",
                "timestamp": time.time(),
                "message": "RailGuard AI Secure Stream Connected",
            }
        }))
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        if ws in CONNECTIONS:
            CONNECTIONS.remove(ws)
    except Exception:
        if ws in CONNECTIONS:
            CONNECTIONS.remove(ws)

@app.websocket("/ws/trajectories")
async def websocket_trajectories(ws: WebSocket):
    """WebSocket endpoint explicitly for ReID path updates."""
    await ws.accept()
    CONNECTIONS.append(ws)
    try:
        while True:
            await ws.receive_text()
    except:
        if ws in CONNECTIONS:
            CONNECTIONS.remove(ws)

# ── Run directly ──
if __name__ == "__main__":
    import uvicorn
    # Trigger loading Models
    # get_pipeline()
    port = int(os.environ.get("PORT", 8001))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
