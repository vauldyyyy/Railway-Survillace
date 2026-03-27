"""
main.py - FastAPI server for RailGuard AI surveillance backend.
Sanitized for Windows Console (CP1252)
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

# Add current dir to path
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

# Global State
ALERTS:      List[Dict[str, Any]] = []
CONNECTIONS: List[WebSocket]       = []
MAX_ALERTS   = 200
executor = ThreadPoolExecutor(max_workers=4)

def get_video_source():
    """Fallback logic for video sourcing."""
    sources = [
        os.environ.get("VIDEO_SOURCE"),
        "https://www.youtube.com/watch?v=06OLEi9v_Gw",
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
                print(f"[ERROR] yt-dlp extraction failed: {e}")
                pass
    
    if os.path.exists("test_video.mp4"):
        return "test_video.mp4"
    return None

def broadcast_message(channel: str, payload: dict):
    if not CONNECTIONS: return
    msg = json.dumps({"channel": channel, "payload": payload})
    stale = []
    for ws in CONNECTIONS:
        try:
            asyncio.run_coroutine_threadsafe(ws.send_text(msg), app.loop)
        except Exception:
            stale.append(ws)
    for ws in stale:
        if ws in CONNECTIONS: CONNECTIONS.remove(ws)

def add_alert(alert: dict):
    ALERTS.append(alert)
    if len(ALERTS) > MAX_ALERTS:
        ALERTS.pop(0)
    broadcast_message("alert", alert)

class SharedStreamManager:
    def __init__(self):
        self.cap = None
        self.current_frame = None
        self.is_running = False
        self.thread = None
        self.last_update = 0
        self.source = None
    
    def start(self):
        if self.is_running: return
        self.source = get_video_source()
        if not self.source:
            print("[ERROR] No video source found.")
            return
            
        self.cap = cv2.VideoCapture(self.source)
        if not self.cap.isOpened():
            print(f"[ERROR] Failed to open source: {self.source}")
            return
            
        self.is_running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        print(f"[OK] SharedStreamManager started.")

    def stop(self):
        self.is_running = False
        if self.thread: self.thread.join()
        if self.cap: self.cap.release()

    def _run(self):
        pipeline = get_pipeline()
        last_broadcast_time = 0
        
        while self.is_running:
            start_t = time.time()
            ret, frame = self.cap.read()
            if not ret:
                if isinstance(self.source, str) and ("googlevideo" in self.source or self.source.endswith(".mp4")):
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    time.sleep(0.1)
                    continue
                self.cap.release()
                time.sleep(2)
                self.cap = cv2.VideoCapture(self.source)
                continue

            try:
                out_frame, alerts, all_trajectories = pipeline.run(frame.copy(), "cam1")
                _, jpg = cv2.imencode(".jpg", out_frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
                self.current_frame = jpg.tobytes()
                self.last_update = time.time()

                if (self.last_update - last_broadcast_time) >= 0.5:
                    broadcast_message("metrics", {
                        "model": "railfod", 
                        "metrics": {"fps": float(pipeline.current_fps), "status": "active"}
                    })
                    broadcast_message("trajectories", all_trajectories)
                    last_broadcast_time = self.last_update

                for alert in alerts:
                    add_alert(alert)

            except Exception as e:
                print(f"[Critical Manager Error] {e}")
                time.sleep(1)

            elapsed = time.time() - start_t
            if elapsed < 0.033:
                time.sleep(0.033 - elapsed)

stream_manager = SharedStreamManager()

app = FastAPI(title="RailGuard AI")
app.loop = None

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    app.loop = asyncio.get_running_loop()
    stream_manager.start()

@app.on_event("shutdown")
def shutdown_event():
    stream_manager.stop()

@app.get("/stream/{camera_id}")
async def video_feed(camera_id: str):
    async def mjpeg_generator():
        last_frame_time = 0
        while True:
            if stream_manager.current_frame and stream_manager.last_update > last_frame_time:
                last_frame_time = stream_manager.last_update
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + stream_manager.current_frame + b'\r\n')
            await asyncio.sleep(0.03)
    return StreamingResponse(mjpeg_generator(), media_type="multipart/x-mixed-replace; boundary=frame")

@app.websocket("/ws/alerts")
async def websocket_alerts(ws: WebSocket):
    await ws.accept()
    CONNECTIONS.append(ws)
    try:
        await ws.send_text(json.dumps({"channel": "system", "payload": {"message": "RailGuard AI Connected"}}))
        while True: await ws.receive_text()
    except WebSocketDisconnect:
        if ws in CONNECTIONS: CONNECTIONS.remove(ws)
    except Exception:
        if ws in CONNECTIONS: CONNECTIONS.remove(ws)

@app.get("/health")
def health():
    return {"status": "ok", "uptime": time.time() - START_TIME}

@app.post("/api/auth/token")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    if form_data.username == "admin" and form_data.password == "railguard":
        token = create_access_token({"sub": form_data.username, "role": "soc_operator"})
        return {"access_token": token, "token_type": "bearer"}
    return JSONResponse(status_code=401, content={"detail": "Incorrect credentials"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8001, reload=False)
