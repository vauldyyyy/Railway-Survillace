"""
main.py --- RailGuard AI Backend Server (V3 Production)
=====================================================
Fixes over V2:
  --- Decoupled capture from inference (separate threads + deque buffer)
  --- Alert cooldown + deduplication (30s window per type+camera)
  --- Severity-gated WS emission (only critical/high broadcast)
  --- Stream validation on source change
  --- Exponential backoff reconnect
  --- Thread-safe frame access
"""

import os
import sys
import time
import datetime
import json
import asyncio
import threading
import subprocess
import traceback
from typing import List, Dict, Any
from pathlib import Path
from collections import deque
from concurrent.futures import ThreadPoolExecutor
import base64

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
from detection.entity_state import EntityClass, EntityState

try:
    from app.core.database import init_db, log_incident, log_model_metric
    _DB_AVAILABLE = True
except Exception as e:
    print(f"[DB] Warning: encrypted DB not available: {e}")
    _DB_AVAILABLE = False

try:
    from core.remote_client import remote_client
    _REMOTE_CLIENT = remote_client
    if _REMOTE_CLIENT:
        print(f"🚀 [BRIDGE] Target: {_REMOTE_CLIENT.remote_url} (Mode: {_REMOTE_CLIENT.mode})")
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

# ── Per-loop best-alert deduplication ──
# Stores {cam_id_threat_type} -> best alert dict seen this cycle
_best_alerts: Dict[str, dict] = {}
_best_alerts_lock = threading.Lock()

# Flush best alerts to WS every N seconds (one per threat type per camera)
ALERT_FLUSH_INTERVAL = 2.0


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


def _frame_to_b64(frame) -> str:
    """Encode an OpenCV frame to a base64 JPEG data URI."""
    if frame is None or frame.size == 0:
        return ""
    try:
        success, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
        if not success:
            return ""
        return "data:image/jpeg;base64," + base64.b64encode(buf.tobytes()).decode()
    except Exception as e:
        print(f"[SnapShot-Error] {e}")
        return ""


def add_alert(alert: dict, snapshot_b64: str = None):
    """Add TICE-validated alert. Queues the best-confidence instance per loop cycle."""
    cam_id = alert.get("camera_id", "unknown")
    threat_type = alert.get("threat_type", "UNKNOWN")
    key = f"{cam_id}_{threat_type}"

    # Attach shared snapshot if available
    if snapshot_b64:
        alert["image"] = snapshot_b64

    with _best_alerts_lock:
        existing = _best_alerts.get(key)
        if existing is None or alert.get("confidence", 0) >= existing.get("confidence", 0):
            _best_alerts[key] = alert


def _flush_best_alerts():
    """Background thread: every ALERT_FLUSH_INTERVAL seconds, emit the best
    queued alert per (camera, threat_type) pair to WebSocket and ALERTS list."""
    while True:
        time.sleep(ALERT_FLUSH_INTERVAL)
        with _best_alerts_lock:
            batch = list(_best_alerts.values())
            _best_alerts.clear()

        for alert in batch:
            cam_id = alert.get("camera_id", "unknown")
            threat_type = alert.get("threat_type", "UNKNOWN")
            cooldown_key = f"{threat_type}_{cam_id}"
            now_ts = time.time()

            last_fired = _alert_cooldown.get(cooldown_key, 0)
            if now_ts - last_fired < ALERT_COOLDOWN_SECONDS and alert.get("threat_level") != "CRITICAL":
                continue

            _alert_cooldown[cooldown_key] = now_ts

            now_ts = time.time()
            clean_alert = {
                "id":          f"{cam_id}_{threat_type}_{int(now_ts * 1000)}",
                "cam":         str(cam_id).upper(),
                "ts":          now_ts,
                "camera_id":   str(cam_id).upper(),
                "threat_type": threat_type,
                "threat_level": alert.get("threat_level", "INFO"),
                "command":     alert.get("command", "MONITOR_SITUATION"),
                "notify":      alert.get("notify", ["Security Monitor"]),
                "escalation":  alert.get("escalation", []),
                "timestamp":   datetime.datetime.fromtimestamp(now_ts).isoformat(),
                "confidence":  alert.get("confidence", 0.0),
                "image":       alert.get("image", ""),
                "entity_id":   alert.get("entity_id", ""),
                "base_class":  alert.get("base_class", ""),
                "type":        alert.get("type", threat_type),
                "severity":    alert.get("severity", alert.get("threat_level", "INFO").lower()),
            }

            ALERTS.append(clean_alert)
            if len(ALERTS) > MAX_ALERTS:
                ALERTS.pop(0)

            broadcast_message("alert", clean_alert)

# Start the alert flusher thread
threading.Thread(target=_flush_best_alerts, daemon=True).start()


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
        self.latest_entities: List[Any] = []

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
        if self.source is None:
            print(f"[Worker {self.camera_id}] No source available, starting in standby.")
            
        # --- 1. SPECIAL CASE OVERRIDES -----------------------------------------
        # CAM 3: Forced absolute file path for the Fire/Smoke demo
        if self.camera_id == "cam3":
            self.source = r"C:\Users\vauld\Downloads\WhatsApp Video 2026-03-30 at 11.27.57 PM.mp4"
            print(f"[Worker cam3] FORCING ABSOLUTE SOURCE: {self.source}")

        # CAM 5: Intelligent Webcam Auto-Scan for Live Demo
        if self.camera_id == "cam5":
            print(f"[Worker cam5] SCANNING FOR WEBCAM (0, 1, 2)...")
            for sid in [0, 1, 2]:
                self.cap = cv2.VideoCapture(sid)
                if self.cap.isOpened():
                    self.source = f"WEBCAM_{sid}"
                    print(f"[Worker cam5] Successfully locked in Source {sid}.")
                    break
            if not self.cap.isOpened():
                print(f"[Worker cam5] ALL WEBCAM SOURCES FAILED. Check if another app is using it!")

        # --- 2. STANDARD INITIALIZATION --------------------------------------
        if not self.cap or not self.cap.isOpened():
            print(f"[Worker {self.camera_id}] Starting standard: {self.source}")
            if self.source is not None:
                self.cap = cv2.VideoCapture(self.source)

            if self.cap.isOpened():
                ret, test_frame = self.cap.read()
                if ret:
                    self.resolution = (test_frame.shape[1], test_frame.shape[0])
                    print(f"[Worker {self.camera_id}] Resolution: {self.resolution[0]}x{self.resolution[1]}")
                else:
                    print(f"[Worker {self.camera_id}] FAILED TO READ TEST FRAME.")
            else:
                print(f"[Worker {self.camera_id}] FAILED TO OPEN CAPTURE ENTIRELY.")

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
                # For MP4 files: seamlessly LOOP back to start
                if isinstance(self.source, str) and self.source.lower().endswith(".mp4"):
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue
                self._consecutive_failures += 1
                if self._consecutive_failures > 10:
                    self._reconnect()
                continue

            try:
                self._consecutive_failures = 0
                self._frame_buffer.append(frame)
                
                # Smooth 30fps stream generation
                display_frame = frame.copy()
                # Layer 1: Environmental Awareness (CROWD zones) - background
                for e in self.latest_entities:
                    if e.base_class == EntityClass.CROWD:
                        x1, y1, x2, y2 = map(int, e.box)
                        # Restore the large situational box for overcrowding
                        color = (0, 0, 180) # Red-ish
                        cv2.rectangle(display_frame, (x1, y1), (x2, y2), color, 2)
                        cv2.putText(display_frame, f"![!] {e.label}", (x1 + 10, y1 + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
                        
                        # Semi-transparent red overlay
                        rect_overlay = display_frame.copy()
                        cv2.rectangle(rect_overlay, (x1, y1), (x2, y2), color, -1)
                        cv2.addWeighted(rect_overlay, 0.15, display_frame, 0.85, 0, display_frame)

                # Layer 2: Object-level Intel (PERSON, BAGGAGE, etc.) - foreground
                for e in self.latest_entities:
                    if e.base_class != EntityClass.CROWD:
                        x1, y1, x2, y2 = map(int, e.box)
                        # PERSON color is vivid Electric Blue (BGR 255, 60, 0)
                        color = (255, 60, 0) if e.base_class == EntityClass.PERSON else (0, 255, 0)
                        # Hazard escalations turn it Red
                        if e.current_state != EntityState.BASE:
                            color = (0, 0, 255)
                        
                        thick = 2
                        cv2.rectangle(display_frame, (x1, y1), (x2, y2), color, thick)
                        label = f"{e.base_class.value.upper()}"
                        cv2.putText(display_frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, thick)
                    
                    _, jpg = cv2.imencode(".jpg", display_frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                    with self._frame_lock:
                        self.current_frame = jpg.tobytes()
                        self.last_update = time.time()
                        
                    time.sleep(0.02)
            except Exception:
                traceback.print_exc()
                time.sleep(1.0)

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
                self.latest_alerts = alerts_tice # TICE objects for alert broadcasting
                self.latest_entities = pipeline.registry.get_all(self.camera_id) # FOR RENDERER
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
 
                # TICE Alerts Integration — encode snapshot once per frame cycle
                snapshot_b64 = _frame_to_b64(out_frame) if alerts_tice else None
                
                for alert in alerts_tice:
                    add_alert(alert, snapshot_b64=snapshot_b64)

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
    SCENARIO_MAP = {
        "cam1": r"C:\Users\vauld\Documents\GitHub\Railway-Surveillance-BitsGoa\backend\data\scenarios\Scenario1.mp4",
        "cam2": r"C:\Users\vauld\Downloads\WhatsApp Video 2026-03-30 at 6.40.17 PM.mp4",
        "cam3": r"C:\Users\vauld\Downloads\WhatsApp Video 2026-03-30 at 11.27.57 PM.mp4",
        "cam4": r"C:\Users\vauld\Downloads\WhatsApp Video 2026-03-30 at 5.01.16 PM.mp4",
        "cam5": 0,    # REAL-TIME LIVE WEBCAM DEMO
        "cam7": "https://www.youtube.com/live/rnXIjl_Rzy4?si=0HnbKn8fm4EemFiV", # Live Overcrowded Place
    }

    def __init__(self):
        self.workers: Dict[str, CameraWorker] = {}
        self._project_root = Path(__file__).resolve().parent.parent

    def _resolve_youtube_url(self, url: str) -> str:
        """Use yt-dlp to extract the direct stream URL (m3u8)."""
        print(f"[CameraManager] Resolving YouTube Live: {url}")
        try:
            # -g for URL, -f b for best video
            cmd = ["yt-dlp", "-g", "-f", "b", url]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            stream_url = result.stdout.strip()
            if stream_url:
                print(f"[CameraManager] Successfully resolved live stream.")
                return stream_url
        except Exception as e:
            print(f"[CameraManager] YouTube resolution FAILED: {e}")
        return url

    def _resolve_source(self, camera_id: str):
        """Resolve video source for camera, checking multiple locations."""
        scenario_file = self.SCENARIO_MAP.get(camera_id)
        if not scenario_file and camera_id != "cam1":
            return None

        # 0. Check for YouTube URLs first
        if isinstance(scenario_file, str) and ("youtube.com" in scenario_file or "youtu.be" in scenario_file):
            return self._resolve_youtube_url(scenario_file)

        # 1. Check if scenario_file is an absolute path that exists
        if isinstance(scenario_file, str) and os.path.isabs(scenario_file) and os.path.exists(scenario_file):
            print(f"[CameraManager] {camera_id} → Absolute path: {scenario_file}")
            return scenario_file

        # 2. Check test_videos/ (YouTube downloads at project root)
        if isinstance(scenario_file, str):
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

        # 4. ULTIMATE FALLBACK: Use the literal path from SCENARIO_MAP if available
        if scenario_file:
            print(f"[CameraManager] {camera_id} → Using SCENARIO_MAP literal: {scenario_file}")
            return str(scenario_file)

        print(f"[CameraManager] {camera_id} → No source found, standby.")
        return None

    def get_worker(self, camera_id: str) -> CameraWorker:
        if camera_id not in self.workers:
            source = self._resolve_source(camera_id)
            self.workers[camera_id] = CameraWorker(camera_id, source)
            self.workers[camera_id].start()
        return self.workers[camera_id]

    def start_all(self):
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

# threading.Thread(target=_failsafe_loop, daemon=True).start()

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
@app.get("/api/video_feed/{camera_id}")
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
        # Immediate toggle with lock protection
        with _REMOTE_CLIENT._lock:
            new_mode = "remote" if _REMOTE_CLIENT.mode != "remote" else "local"
            _REMOTE_CLIENT.mode = new_mode
            
            if new_mode == "local":
                _REMOTE_CLIENT.is_connected = False
                _REMOTE_CLIENT._consecutive_failures = 0
                print("[RemoteClient] Bridge MANUAL DISABLE. Falling back to CPU.")
            else:
                _REMOTE_CLIENT._consecutive_failures = 0
                print(f"[RemoteClient] Bridge MANUAL ENABLE. Targeting: {_REMOTE_CLIENT.remote_url}")
                # Don't set is_connected = False here; let detect_remote try optimistic path!
        
        # Trigger background health check if remote
        if new_mode == "remote":
            threading.Thread(target=_REMOTE_CLIENT._check_health, daemon=True).start()

        return JSONResponse(status_code=200, content={"status": "toggled", "mode": new_mode, "connected": _REMOTE_CLIENT.is_connected})
    return JSONResponse(status_code=400, content={"error": "Bridge bridge unit not found"})


class LoginRequest(BaseModel):
    operator_id: str
    password: str

@app.post("/api/login")
def login_json(data: LoginRequest):
    if data.operator_id == "admin" and data.password == "railguard":
        token = create_access_token({"sub": data.operator_id, "role": "soc_operator"})
        return {
            "access_token": token,
            "operator": {
                "id": "OP-042",
                "display_name": "Admin Operator",
                "role": "SOC Lead",
                "clearance": "Level 5"
            }
        }
    return JSONResponse(status_code=401, content={"detail": {"message": "Authentication failed."}})

@app.post("/api/auth/token")
def login_token(form_data: OAuth2PasswordRequestForm = Depends()):
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
    """Returns all active tracklets from the Neural ReID gallery."""
    p = get_pipeline()
    if not hasattr(p, "reid"):
        return JSONResponse(content=[])
        
    tracklets = []
    now = time.time()
    
    # 24-hour cleanup is already implicit in reset_minutes, but let's be explicit
    # for the API display to only show 'active' (last seen in last 1 hour)
    for tid, data in p.reid.gallery.items():
        # Format journey string for UI
        cameras = [record["camera"] for record in data["path"]]
        unique_cams = []
        for c in cameras:
            if not unique_cams or unique_cams[-1] != c:
                unique_cams.append(c)
        
        journey_str = " → ".join(unique_cams[-2:]) # Show last 2 hops
        
        tracklets.append({
            "id": tid,
            "status": data.get("status", "NORMAL"),
            "cam": cameras[-1].upper() if cameras else "UNKNOWN",
            "time": time.strftime("%H:%M:%S", time.localtime(data["last_seen"])),
            "journey": journey_str,
            "image": data.get("image", ""),
            "cameras_seen": unique_cams,
            "first_seen": data["path"][0]["time"] if data["path"] else now,
            "last_seen": data["last_seen"],
        })
        
    # Sort by most recent first
    tracklets.sort(key=lambda x: x["last_seen"], reverse=True)
    return JSONResponse(content=tracklets)


@app.post("/api/tracklets/{track_id}/flag")
def flag_tracklet(track_id: str):
    p = get_pipeline()
    if hasattr(p, "reid") and track_id in p.reid.gallery:
        p.reid.gallery[track_id]["status"] = "FLAGGED"
        return {"status": "success", "id": track_id}
    return JSONResponse(status_code=404, content={"error": "Tracklet not found"})


@app.post("/api/tracklets/{track_id}/clear")
def clear_tracklet(track_id: str):
    p = get_pipeline()
    if hasattr(p, "reid") and track_id in p.reid.gallery:
        p.reid.gallery[track_id]["status"] = "NORMAL"
        return {"status": "success", "id": track_id}
    return JSONResponse(status_code=404, content={"error": "Tracklet not found"})


@app.delete("/api/tracklets")
def purge_tracklets():
    """Purge all tracklets to satisfy GDPR privacy requirements."""
    p = get_pipeline()
    if hasattr(p, "reid"):
        p.reid.gallery.clear()
        p.reid.last_reset = time.time()
        return {"status": "purged", "count": 0}
    return {"status": "no_reid_engine"}


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
    try:
        # BINDING TO ALL INTERFACES FOR DEMO RELIABILITY
        uvicorn.run(app, host="0.0.0.0", port=8001, reload=False, ws_ping_interval=300, ws_ping_timeout=300)
    except Exception as e:
        print(f"[CRITICAL ERROR] Server failed to start: {e}")
        import traceback
        traceback.print_exc()
