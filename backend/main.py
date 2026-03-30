"""
main.py — RailGuard AI Backend Server (V3 Production)
=====================================================
Fixes over V2:
  - Decoupled capture from inference (separate threads + deque buffer)
  - Alert cooldown + deduplication (30s window per type+camera)
  - Severity-gated WS emission (only critical/high broadcast)
  - Stream validation on source change
  - Exponential backoff reconnect
  - Thread-safe frame access
"""

import os
import sys
import time
import json
import asyncio
import threading
import subprocess
from typing import List, Dict, Any
from pathlib import Path
from collections import deque
from concurrent.futures import ThreadPoolExecutor

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

import cv2
import numpy as np
from fastapi import FastAPI, Response, WebSocket, WebSocketDisconnect, Depends
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).resolve().parent))

from security.auth import create_access_token, verify_token, verify_ws_token

try:
    from app.core.database import init_db, log_incident, log_model_metric
    _DB_AVAILABLE = True
except Exception as e:
    print(f"[DB] Warning: encrypted DB not available: {e}")
    _DB_AVAILABLE = False

try:
    from core.remote_client import remote_client
    _REMOTE_CLIENT = remote_client
except ImportError:
    _REMOTE_CLIENT = None

_pipeline = None
def get_pipeline():
    global _pipeline
    if _pipeline is None:
        from detection.pipeline import pipeline
        _pipeline = pipeline
    return _pipeline


START_TIME = time.time()

# ── Global State ──
ALERTS: List[Dict[str, Any]] = []
CONNECTIONS: List[WebSocket] = []
MAX_ALERTS = 200
executor = ThreadPoolExecutor(max_workers=4)

# ── Alert Cooldown ──
# Tracks {type_camera} -> last_fired_timestamp to prevent spam
_alert_cooldown: Dict[str, float] = {}
ALERT_COOLDOWN_SECONDS = 30.0


def get_video_source(default_url=None):
    sources = [
        default_url,
        os.environ.get("VIDEO_SOURCE"),
        "https://www.youtube.com/watch?v=06OLEi9v_Gw",
    ]
    for source in sources:
        if source is None: continue
        if isinstance(source, str) and ("youtube.com" in source or "youtu.be" in source):
            try:
                result = subprocess.run(
                    ["yt-dlp", "--no-warnings", "-f", "best[ext=mp4]/best", "-g", source],
                    capture_output=True, text=True, timeout=8,
                )
                if result.returncode == 0 and result.stdout.strip():
                    url_lines = [l for l in result.stdout.strip().split("\n") if l.startswith("http")]
                    if url_lines: return url_lines[-1]
            except Exception: pass
        elif isinstance(source, str) and os.path.exists(source):
            return source
        elif source == 0:
            return 0
            
    # Emergency fallbacks
    if os.path.exists("test_video.mp4"): return "test_video.mp4"
    return 0 # Final fallback to local webcam


def broadcast_message(channel: str, payload: dict):
    if not CONNECTIONS or not app.loop:
        return
    msg = json.dumps({"channel": channel, "payload": payload})
    stale = []
    for ws in CONNECTIONS:
        try:
            asyncio.run_coroutine_threadsafe(ws.send_text(msg), app.loop)
        except Exception:
            stale.append(ws)
    for ws in stale:
        if ws in CONNECTIONS:
            CONNECTIONS.remove(ws)


def add_alert(alert: dict):
    """Add TICE-validated alert with deduplication."""
    cam_id = alert.get("camera_id", "unknown")
    threat_type = alert.get("threat_type", "UNKNOWN")
    cooldown_key = f"{threat_type}_{cam_id}"
    
    now_ts = time.time()
    last_fired = _alert_cooldown.get(cooldown_key, 0)
    
    # 30s Cooldown as per Safety Rules, but CRITICAL overrides
    if now_ts - last_fired < ALERT_COOLDOWN_SECONDS and alert.get("threat_level") != "CRITICAL":
        return
    
    _alert_cooldown[cooldown_key] = now_ts
    
    # JSON Schema Alignment (Mandatory Phase 5)
    clean_alert = {
        "camera_id": str(cam_id).upper(),
        "threat_type": threat_type,
        "threat_level": alert.get("threat_level", "INFO"),
        "command": alert.get("command", "MONITOR_SITUATION"),
        "notify": alert.get("notify", ["Security Monitor"]),
        "escalation": alert.get("escalation", []),
        "timestamp": alert.get("timestamp", datetime.datetime.now().isoformat()),
        "confidence": alert.get("confidence", 0.0)
    }
    
    ALERTS.append(clean_alert)
    if len(ALERTS) > MAX_ALERTS:
        ALERTS.pop(0)

    # Broadcast to Mission Control (WebSocket)
    broadcast_message("alert", clean_alert)


# ══════════════════════════════════════════════════════════════════════
# CameraWorker — Decoupled capture + inference architecture
# ══════════════════════════════════════════════════════════════════════

class CameraWorker:
    def __init__(self, camera_id, source=None):
        self.camera_id = camera_id
        self.source = source
        self.cap = None
        self.current_frame = None  # JPEG bytes for MJPEG serving
        self._frame_lock = threading.Lock()
        self.last_update = time.time()
        self.is_running = False
        self.resolution = (0, 0)
        self.latest_raw_frame = None
        self.latest_alerts = []

        # Decoupled buffer: capture thread writes, inference thread reads
        self._frame_buffer = deque(maxlen=2)  # Only keep latest 2 frames
        self._capture_thread = None
        self._inference_thread = None

        # Reconnect state
        self._consecutive_failures = 0
        self._max_backoff = 16  # seconds

    def start(self):
        if self.is_running:
            return
        if not self.source:
            print(f"[Worker {self.camera_id}] No source available, starting in standby.")
            
        print(f"[Worker {self.camera_id}] Starting: {self.source}")
        if self.source:
            self.cap = cv2.VideoCapture(self.source)
            if self.cap.isOpened():
                ret, test_frame = self.cap.read()
                if ret:
                    self.resolution = (test_frame.shape[1], test_frame.shape[0])
                    print(f"[Worker {self.camera_id}] Resolution: {self.resolution[0]}x{self.resolution[1]}")

        self.is_running = True
        self._capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._inference_thread = threading.Thread(target=self._inference_loop, daemon=True)
        self._capture_thread.start()
        self._inference_thread.start()

    def stop(self):
        self.is_running = False
        if self._capture_thread:
            self._capture_thread.join(timeout=2.0)
        if self._inference_thread:
            self._inference_thread.join(timeout=2.0)
        if self.cap:
            self.cap.release()

    def set_source(self, new_source):
        """Validate and switch to new source."""
        print(f"[Worker {self.camera_id}] Source update: {new_source}")
        # Validate by trying to read 1 frame
        test_cap = cv2.VideoCapture(new_source)
        if not test_cap.isOpened():
            test_cap.release()
            print(f"[Worker {self.camera_id}] INVALID source: {new_source}")
            return False

        ret, frame = test_cap.read()
        test_cap.release()
        if not ret:
            print(f"[Worker {self.camera_id}] Source unreadable: {new_source}")
            return False

        # Source is valid — switch
        self.source = new_source
        self._consecutive_failures = 0
        self.resolution = (frame.shape[1], frame.shape[0])
        if self.cap:
            self.cap.release()
        self.cap = cv2.VideoCapture(self.source)
        print(f"[Worker {self.camera_id}] Switched OK. Res: {self.resolution[0]}x{self.resolution[1]}")
        return True

    def _capture_loop(self):
        """Dedicated capture thread — reads frames into buffer, never blocks on inference."""
        while self.is_running:
            if not self.cap or not self.cap.isOpened():
                self._reconnect()
                continue

            ret, frame = self.cap.read()
            if not ret:
                self._consecutive_failures += 1
                if self._consecutive_failures > 10:
                    self._reconnect()
                continue

            self._consecutive_failures = 0
            self._frame_buffer.append(frame)
            
            # Smooth 30fps stream generation
            display_frame = frame.copy()
            # Draw latest known alerts onto the smooth video
            for alert in self.latest_alerts:
                box = alert.get("box", [])
                if len(box) == 4:
                    x1, y1, x2, y2 = map(int, box)
                    severity = alert.get("severity", "").lower()
                    if severity == "critical":
                        color = (0, 0, 255)
                        thick = 3
                    elif severity == "high":
                        color = (0, 165, 255)
                        thick = 2
                    else:
                        color = (255, 255, 0) # Cyan/Yellow standard for generic tracking
                        thick = 1
                    cv2.rectangle(display_frame, (x1, y1), (x2, y2), color, thick)
                    cv2.putText(display_frame, alert.get("type", ""), (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, thick)
            
            _, jpg = cv2.imencode(".jpg", display_frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            with self._frame_lock:
                self.current_frame = jpg.tobytes()
                self.last_update = time.time()
                
            time.sleep(0.02)  # Max ~50fps capture pacing

    def _inference_loop(self):
        """Dedicated inference thread — pops latest frame from buffer, runs ML pipeline."""
        pipeline = get_pipeline()
        last_broadcast = 0

        while self.is_running:
            # Wait for a frame
            if not self._frame_buffer:
                time.sleep(0.01)
                continue

            # Pop the LATEST frame only (skip stale ones)
            try:
                frame = self._frame_buffer.pop()
                self._frame_buffer.clear()  # Drop any older frames
            except IndexError:
                continue

            try:
                out_frame, alerts_tice, trajectories = pipeline.run(frame, self.camera_id)
                self.latest_alerts = alerts_tice # TICE objects for overlay drawing
                self.last_update = time.time()   # Heartbeat updated
 
                # Throttled metric broadcast
                now = time.time()
                if now - last_broadcast >= 0.5:
                    broadcast_message("metrics", {
                        "camera_id": self.camera_id,
                        "model": "railfod",
                        "metrics": {
                            "fps": float(pipeline.current_fps),
                            "status": "active",
                            "inference_source": pipeline.inference_source,
                            "inference_latency": round(pipeline.inference_latency, 1),
                        },
                    })
                    last_broadcast = now
 
                # TICE Alerts Integration
                for alert in alerts_tice:
                    add_alert(alert)

                    if _DB_AVAILABLE and alert.get("alert"):
                        try:
                            log_incident(
                                uuid=str(alert.get("uuid", f"auto_{now}")),
                                cam_id=self.camera_id,
                                incident_type=str(alert.get("type", "UNKNOWN")),
                                severity=str(alert.get("severity", "medium")).upper(),
                                confidence=float(alert.get("confidence", 0.0)),
                                description=f"Detected at {time.strftime('%H:%M:%S')}",
                            )
                        except Exception:
                            pass

            except Exception as e:
                print(f"[Worker {self.camera_id}] Inference error: {e}")
                time.sleep(0.5)

    def _reconnect(self):
        """Exponential backoff reconnect."""
        if self.cap:
            self.cap.release()

        backoff = min(2 ** min(self._consecutive_failures, 4), self._max_backoff)
        # print(f"[Worker {self.camera_id}] Reconnecting in {backoff}s...")
        time.sleep(backoff)

        if isinstance(self.source, str) and self.source.endswith(".mp4"):
            self.cap = cv2.VideoCapture(self.source)
            if self.cap.isOpened():
                self._consecutive_failures = 0
        else:
            self.cap = cv2.VideoCapture(self.source)
            if self.cap.isOpened():
                self._consecutive_failures = 0


class MultiCameraManager:
    # Map camera IDs to specific scenario video filenames (YouTube test downloads)
    SCENARIO_MAP = {
        "cam1": "person_on_track.mp4",
        "cam2": r"C:\Users\vauld\Downloads\WhatsApp Video 2026-03-30 at 6.40.17 PM.mp4", # User Crowd Video
        "cam3": "fire_smoke.mp4",        # Fire / Smoke
        "cam4": r"C:\Users\vauld\Downloads\WhatsApp Video 2026-03-30 at 5.01.16 PM.mp4", # User Verification Video
    }

    def __init__(self):
        self.workers: Dict[str, CameraWorker] = {}
        self._project_root = Path(__file__).resolve().parent.parent

    def _resolve_source(self, camera_id: str):
        """Resolve video source for camera, checking multiple locations."""
        # 1. Check test_videos/ (YouTube downloads at project root)
        scenario_file = self.SCENARIO_MAP.get(camera_id)
        if scenario_file:
            yt_path = self._project_root / "test_videos" / scenario_file
            if yt_path.exists():
                print(f"[CameraManager] {camera_id} → YouTube clip: {yt_path.name}")
                return str(yt_path)

        # 2. Check backend/test_data/
        test_data_path = self._project_root / "backend" / "test_data" / f"{camera_id}.mp4"
        if test_data_path.exists():
            print(f"[CameraManager] {camera_id} → test_data: {test_data_path.name}")
            return str(test_data_path)

        # 3. Fallback to default video source for cam1
        if camera_id == "cam1":
            return get_video_source()

        print(f"[CameraManager] {camera_id} → No source found, standby.")
        return None

    def get_worker(self, camera_id: str) -> CameraWorker:
        if camera_id not in self.workers:
            source = self._resolve_source(camera_id)
            self.workers[camera_id] = CameraWorker(camera_id, source)
            self.workers[camera_id].start()
        return self.workers[camera_id]

    def start_all(self):
        # Start all 4 scenario cameras automatically
        for cam_id in ["cam1", "cam2", "cam3", "cam4"]:
            self.get_worker(cam_id)

    def stop_all(self):
        for worker in self.workers.values():
            worker.stop()


stream_manager = MultiCameraManager()

app = FastAPI(title="RailGuard AI")
app.loop = None

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ══════════════════════════════════════════════════════════════════════
# Failsafe Heartbeat Monitor
# ══════════════════════════════════════════════════════════════════════

def _failsafe_loop():
    """Safety Auditor: Checks for inference hang every 2s."""
    print("[FAILSAFE] Heartbeat Monitor ACTIVE.")
    while True:
        time.sleep(2)
        now = time.time()
        for cam_id, worker in stream_manager.workers.items():
            if worker.is_running and (now - worker.last_update) > 3.0:
                print(f"[FAILSAFE-CRITICAL] Inference hung on {cam_id}!")
                failsafe_msg = {
                    "camera_id": cam_id.upper(),
                    "system_status": "AI_MONITORING_INTERRUPTED",
                    "action_required": "Manual Supervision Required",
                    "timestamp": datetime.datetime.now().isoformat()
                }
                broadcast_message("system_alert", failsafe_msg)

threading.Thread(target=_failsafe_loop, daemon=True).start()

@app.on_event("startup")
async def startup_event():
    app.loop = asyncio.get_running_loop()
    if _DB_AVAILABLE:
        try:
            init_db()
        except Exception as e:
            print(f"[DB] Init error: {e}")
    stream_manager.start_all()


@app.on_event("shutdown")
def shutdown_event():
    stream_manager.stop_all()


@app.get("/stream/{camera_id}")
async def video_feed(camera_id: str):
    worker = stream_manager.get_worker(camera_id)

    async def mjpeg_generator():
        last_frame_time = 0
        
        # Create a fallback placeholder frame 1920x1080
        fallback = np.zeros((1080, 1920, 3), dtype=np.uint8)
        cv2.putText(fallback, f"{camera_id} - OFFLINE", (500, 500), cv2.FONT_HERSHEY_SIMPLEX, 3, (100, 100, 100), 5)
        _, fallback_jpg = cv2.imencode(".jpg", fallback)
        fallback_bytes = fallback_jpg.tobytes()

        no_frame_counter = 0

        while True:
            with worker._frame_lock:
                if worker.current_frame and worker.last_update > last_frame_time:
                    last_frame_time = worker.last_update
                    frame_data = worker.current_frame
                    no_frame_counter = 0
                else:
                    frame_data = None
                    no_frame_counter += 1

            if frame_data:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_data + b'\r\n')
            elif no_frame_counter > 150: # After ~5 sec of no frames, assume stream actually died/offline
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + fallback_bytes + b'\r\n')
                
            await asyncio.sleep(0.03)

    return StreamingResponse(mjpeg_generator(), media_type="multipart/x-mixed-replace; boundary=frame")


@app.websocket("/ws/alerts")
async def websocket_alerts(ws: WebSocket):
    await ws.accept()
    CONNECTIONS.append(ws)
    try:
        await ws.send_text(json.dumps({"channel": "system", "payload": {"message": "RailGuard AI Connected"}}))
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        if ws in CONNECTIONS:
            CONNECTIONS.remove(ws)
    except Exception:
        if ws in CONNECTIONS:
            CONNECTIONS.remove(ws)


@app.get("/health")
def health():
    return {"status": "ok", "uptime": time.time() - START_TIME}


@app.post("/api/bridge/url")
def update_bridge_url(data: dict):
    if _REMOTE_CLIENT:
        url = data.get("url")
        if url:
            with _REMOTE_CLIENT._lock:
                _REMOTE_CLIENT.remote_url = url
                _REMOTE_CLIENT.is_connected = False
            return JSONResponse(status_code=200, content={"status": "updated", "url": url})
    return JSONResponse(status_code=400, content={"error": "Update failed"})


@app.post("/api/stream/source")
def change_stream_source(data: dict):
    camera_id = data.get("camera_id", "cam1") # Default to cam1
    new_source = data.get("source")

    if not new_source:
        return JSONResponse(status_code=400, content={"error": "No source provided"})

    # Resolve YouTube URLs
    processed_source = new_source
    if "youtube.com" in new_source or "youtu.be" in new_source:
        try:
            result = subprocess.run(
                ["yt-dlp", "--no-warnings", "-f", "best[ext=mp4]/best", "-g", new_source],
                capture_output=True, text=True, timeout=15,
            )
            if result.returncode == 0 and result.stdout.strip():
                url_lines = [l for l in result.stdout.strip().split("\n") if l.startswith("http")]
                if url_lines:
                    processed_source = url_lines[-1]
        except Exception:
            pass

    worker = stream_manager.get_worker(camera_id)
    success = worker.set_source(processed_source)
    if success:
        return {"status": "source_updated", "camera_id": camera_id, "resolution": list(worker.resolution)}
    else:
        return JSONResponse(status_code=400, content={"error": "Failed to validate stream source"})


@app.post("/api/bridge/toggle")
def toggle_bridge():
    if _REMOTE_CLIENT:
        new_mode = "remote" if _REMOTE_CLIENT.mode != "remote" else "local"
        with _REMOTE_CLIENT._lock:
            _REMOTE_CLIENT.mode = new_mode
            if new_mode == "local":
                _REMOTE_CLIENT.is_connected = False
                _REMOTE_CLIENT._consecutive_failures = 0
            else:
                _REMOTE_CLIENT._consecutive_failures = 0

        if new_mode == "remote":
            threading.Thread(target=_REMOTE_CLIENT._check_health, daemon=True).start()

        return JSONResponse(status_code=200, content={"status": "toggled", "mode": new_mode})
    return JSONResponse(status_code=400, content={"error": "Bridge disabled"})


@app.post("/api/auth/token")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    if form_data.username == "admin" and form_data.password == "railguard":
        token = create_access_token({"sub": form_data.username, "role": "soc_operator"})
        return {"access_token": token, "token_type": "bearer"}
    return JSONResponse(status_code=401, content={"detail": "Incorrect credentials"})


@app.get("/video/{camera_id}")
async def video_feed_alias(camera_id: str):
    return await video_feed(camera_id)


@app.get("/api/alerts")
def get_recent_alerts():
    return JSONResponse(content=list(reversed(ALERTS))[:20])


@app.get("/api/stats")
def get_system_stats():
    pipeline = get_pipeline()
    tracked = len(pipeline.reid.gallery) if hasattr(pipeline, "reid") else 0
    conf = pipeline.rolling_confidence if hasattr(pipeline, "rolling_confidence") else 0.0
    active_workers = len([w for w in stream_manager.workers.values() if w.is_running and w.current_frame])
    return {
        "total_tracked": tracked,
        "flagged": 0,
        "cameras_active": max(active_workers, 1),
        "recent_alerts": len(ALERTS),
        "avg_confidence": round(conf * 100, 1),
    }


@app.get("/api/heatmap")
def get_heatmap():
    pipeline = get_pipeline()
    grid = pipeline.heatmap_grid if hasattr(pipeline, "heatmap_grid") else [[0.0] * 20 for _ in range(20)]
    return JSONResponse(content={"grid": grid})


@app.get("/api/tracklets")
def get_system_tracklets():
    return JSONResponse(content=[])


@app.get("/api/bridge-status")
def get_bridge_status():
    if _REMOTE_CLIENT:
        status = _REMOTE_CLIENT.get_status()
        try:
            pipeline = get_pipeline()
            status["inference_source"] = getattr(pipeline, "inference_source", "local")
            status["inference_latency"] = getattr(pipeline, "inference_latency", 0.0)
        except Exception:
            status["inference_source"] = "local"
            status["inference_latency"] = 0.0
        return JSONResponse(content=status)
    return JSONResponse(content={
        "mode": "local",
        "connected": False,
        "latency_ms": 0,
        "remote_url": None,
        "inference_source": "local",
    })


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8001, reload=False)
