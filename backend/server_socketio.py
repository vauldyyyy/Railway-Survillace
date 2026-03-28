"""
RailGuard AI — Socket.IO Real-Time Server
============================================
Replaces raw WebSockets with python-socketio for zero-lag
security alerts, live camera streaming, and structured events.

Architecture:
  - socketio.AsyncServer mounted inside FastAPI via ASGIApp
  - Default namespace: security alerts, heartbeat
  - /live namespace: camera frame streaming at 20fps
  - Phase 2 integration: TamperDetector + PrivacyEngine + PromptSanitizer

Run:
    cd backend
    uvicorn server_socketio:app --reload --port 8000
"""

from __future__ import annotations

import asyncio
import base64
import gc
import json
import logging
import time
from collections.abc import Generator
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

import cv2
import numpy as np
import socketio
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import Base, SessionLocal, engine
from app import models

from ai.tamper_detector import TamperDetector
from ai.privacy import PrivacyEngine, Mechanism, secure_cleanup
from security.prompt_sanitizer import PromptSanitizer

# ======================================================================
# Logging
# ======================================================================

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("railguard.socketio")


# ======================================================================
# 1. THE SERVER — Socket.IO AsyncServer + FastAPI mount
# ======================================================================

sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*",
    logger=False,
    engineio_logger=False,
    ping_timeout=60,
    ping_interval=25,
)

# Security singletons
detector = TamperDetector()
privacy_engine = PrivacyEngine(mechanism=Mechanism.GAUSSIAN, embedding_dim=512)
sanitizer = PromptSanitizer()


# ======================================================================
# 5. ERROR HANDLING — Connect / Disconnect events (default namespace)
# ======================================================================

@sio.event
async def connect(sid: str, environ: dict) -> None:
    print(f"[SOCKET.IO] Client Connected: {sid}", flush=True)
    logger.info("Client connected: sid=%s", sid)
    await sio.emit("server_info", {
        "msg": "Connected to RailGuard AI Real-Time Server",
        "timestamp": time.time(),
    }, to=sid)


@sio.event
async def disconnect(sid: str) -> None:
    print(f"[SOCKET.IO] Client Disconnected: {sid}", flush=True)
    logger.info("Client disconnected: sid=%s", sid)


@sio.event
async def ping(sid: str, data: Any = None) -> str:
    """Client can send ping to verify connection."""
    return "pong"


# ======================================================================
# 2. THE SECURITY EMITTER — TamperDetector + PromptSanitizer → sio.emit
# ======================================================================

@sio.event
async def submit_frame(sid: str, data: dict) -> dict:
    """Client sends a base64-encoded JPEG frame for tamper analysis.

    Payload: {"camera_id": "CAM-01", "frame_b64": "<base64 jpeg>"}
    """
    camera_id = data.get("camera_id", "UNKNOWN")
    frame_b64 = data.get("frame_b64", "")

    try:
        frame_bytes = base64.b64decode(frame_b64)
        buf = np.frombuffer(frame_bytes, dtype=np.uint8)
        frame = cv2.imdecode(buf, cv2.IMREAD_COLOR)
        if frame is None:
            return {"status": "error", "msg": "Invalid frame data"}
    except Exception as e:
        return {"status": "error", "msg": str(e)}

    result = await detector.analyze_frame(frame)
    result_dict = result.to_dict()

    # ── ALERT PATHWAY ──
    if result_dict["status"] == "alert":
        alert_payload = {
            "msg": "TAMPER_DETECTED",
            "alert_type": result_dict["alert"],
            "camera_id": camera_id,
            "ssim": result_dict["ssim"],
            "confidence": result_dict["confidence"],
            "timestamp": time.time(),
        }

        # Broadcast to ALL connected clients
        await sio.emit("security_alert", alert_payload)
        print(f"[SOCKET.IO] 🚨 SECURITY ALERT emitted: {alert_payload['msg']} on {camera_id}", flush=True)

        # Log to DB
        db = SessionLocal()
        try:
            incident = models.Incident(
                threat_type=f"TAMPER: {result_dict['alert']}",
                camera_id=camera_id,
            )
            db.add(incident)
            db.commit()
        finally:
            db.close()

    return result_dict


@sio.event
async def submit_ocr_text(sid: str, data: dict) -> dict:
    """Client sends OCR text for injection scanning.

    Payload: {"text": "...", "camera_id": "OCR-01"}
    """
    text = data.get("text", "")
    camera_id = data.get("camera_id", "OCR-SOURCE")

    scan_result = sanitizer.scan(text)

    if scan_result.action.value == "block":
        alert_payload = {
            "msg": "INJECTION_ATTEMPT",
            "risk_score": scan_result.risk_score,
            "matched_rules": scan_result.matched_rules,
            "camera_id": camera_id,
            "text_preview": text[:100],
            "timestamp": time.time(),
        }

        # Broadcast injection alert
        await sio.emit("security_alert", alert_payload)
        print(f"[SOCKET.IO] 🛑 INJECTION ALERT emitted from {camera_id}", flush=True)

        # Log to Incident_Logs
        db = SessionLocal()
        try:
            incident = models.Incident(
                threat_type="PROMPT_INJECTION_ATTACK",
                camera_id=camera_id,
            )
            db.add(incident)
            db.commit()
        finally:
            db.close()

        return {
            "status": "blocked",
            "risk_score": scan_result.risk_score,
            "rules": scan_result.matched_rules,
        }

    safe_text = sanitizer.frame_untrusted_input(text)
    return {"status": "clean", "framed_text": safe_text}


# ======================================================================
# 3. THE DATA STREAMER — /live namespace for camera frames at 20fps
# ======================================================================

class LiveNamespace(socketio.AsyncNamespace):
    """Dedicated namespace for live video streaming."""

    async def on_connect(self, sid: str, environ: dict) -> None:
        print(f"[SOCKET.IO] /live Client Connected: {sid}", flush=True)

    async def on_disconnect(self, sid: str) -> None:
        print(f"[SOCKET.IO] /live Client Disconnected: {sid}", flush=True)

    async def on_start_stream(self, sid: str, data: dict = None) -> None:
        """Client requests the server to start streaming from webcam.

        This runs in a background task to avoid blocking.
        """
        camera_index = (data or {}).get("camera_index", 0)
        asyncio.create_task(self._stream_camera(sid, camera_index))

    async def on_stop_stream(self, sid: str, data: dict = None) -> None:
        """Client requests stream stop (handled via disconnect)."""
        print(f"[SOCKET.IO] /live Stream stop requested by {sid}", flush=True)

    async def _stream_camera(self, sid: str, camera_index: int = 0) -> None:
        """Capture frames from webcam and emit as base64 at ~20fps."""
        cap = cv2.VideoCapture(camera_index)
        if not cap.isOpened():
            await self.emit("stream_error", {
                "msg": f"Cannot open camera {camera_index}"
            }, to=sid)
            return

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        frame_interval = 1.0 / 20  # 20 fps
        print(f"[SOCKET.IO] /live Streaming camera {camera_index} to {sid} @ 20fps", flush=True)

        try:
            while True:
                t_start = time.monotonic()

                ret, frame = cap.read()
                if not ret:
                    await self.emit("stream_error", {"msg": "Frame capture failed"}, to=sid)
                    break

                # Encode frame as JPEG → base64
                _, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                b64_frame = base64.b64encode(buffer).decode("ascii")

                await self.emit("video_frame", {
                    "data": b64_frame,
                    "timestamp": time.time(),
                }, to=sid)

                # Also run tamper detection on every frame
                result = await detector.analyze_frame(frame)
                if result.status == "alert":
                    await self.server.emit("security_alert", {
                        "msg": "TAMPER_DETECTED",
                        "alert_type": result.alert,
                        "camera_id": f"WEBCAM-{camera_index}",
                        "confidence": result.confidence,
                        "timestamp": time.time(),
                    })

                # Maintain 20fps
                elapsed = time.monotonic() - t_start
                sleep_time = max(0, frame_interval - elapsed)
                await asyncio.sleep(sleep_time)

        except asyncio.CancelledError:
            pass
        finally:
            cap.release()
            print(f"[SOCKET.IO] /live Camera {camera_index} released for {sid}", flush=True)


sio.register_namespace(LiveNamespace("/live"))


# ======================================================================
# DB dependency
# ======================================================================

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ======================================================================
# Heartbeat background task
# ======================================================================

async def _heartbeat_loop() -> None:
    """Terminal heartbeat every 2 seconds."""
    while True:
        cam = "OK" if detector._calibration_frames > 0 else "IDLE"
        print(
            f"[STATUS] Camera: {cam} | DB: Encrypted | Socket: {sio.manager.rooms if hasattr(sio.manager, 'rooms') else 'Active'}",
            flush=True,
        )
        await asyncio.sleep(2)


# ======================================================================
# FastAPI Lifespan
# ======================================================================

@asynccontextmanager
async def lifespan(app_instance: FastAPI):
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created.")
    heartbeat = asyncio.create_task(_heartbeat_loop())
    logger.info("Heartbeat started.")
    yield
    heartbeat.cancel()
    logger.info("Server shutting down.")


# ======================================================================
# FastAPI App + Socket.IO Mount
# ======================================================================

fastapi_app = FastAPI(
    title="RailGuard AI — Socket.IO Real-Time Server",
    lifespan=lifespan,
)

fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── REST endpoints (preserved from server.py) ──

class PersonDetectionPayload(BaseModel):
    camera_id: str
    raw_embedding: list[float]
    epsilon: float = 1.0


@fastapi_app.post("/api/detect-person")
async def detect_person(
    payload: PersonDetectionPayload,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    raw = np.array(payload.raw_embedding, dtype=np.float32)
    if raw.shape != (512,):
        raise HTTPException(400, f"Expected 512-D vector, got {raw.shape}")

    result = privacy_engine.privatise(raw, payload.epsilon)
    noisy = result["noisy_vector"]
    noisy_b64 = base64.b64encode(noisy.tobytes()).decode("ascii")

    tracked = models.TrackedPerson(
        timestamp=datetime.now(timezone.utc),
        obfuscated_embedding=noisy_b64,
        camera_id=payload.camera_id,
    )
    db.add(tracked)
    db.commit()
    db.refresh(tracked)

    secure_cleanup(raw)
    print("DEBUG: Identity Obfuscated. Data committed to Encrypted DB.", flush=True)

    return {
        "status": "committed",
        "person_id": tracked.id,
        "utility_loss": result["utility_loss"],
        "snr_db": result["snr_db"],
        "budget_remaining": result["budget_remaining"],
    }


@fastapi_app.get("/cameras")
def list_cameras(db: Session = Depends(get_db)):
    return db.query(models.Camera).all()


@fastapi_app.get("/incidents")
def list_incidents(db: Session = Depends(get_db)):
    return db.query(models.Incident).order_by(models.Incident.timestamp.desc()).all()


@fastapi_app.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "running",
        "transport": "socket.io",
        "privacy_budget": privacy_engine.accountant.report(),
        "tamper_calibrated": detector._calibration_frames >= 60,
    }


# Mount Socket.IO on top of FastAPI
app = socketio.ASGIApp(sio, other_app=fastapi_app)
