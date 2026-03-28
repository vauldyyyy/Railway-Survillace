"""
RailGuard AI — Unified Live Response Server
=============================================
Integrates all 3 security layers into a single FastAPI app:

  Layer 1: Camera Gateway     → TamperDetector → WS broadcast
  Layer 2: Data Shield        → PrivacyEngine  → Encrypted DB
  Layer 3: Logic Gate         → PromptSanitizer → Incident log + WS alert
  Layer 4: Frontend Bridge    → /ws/alerts      → Streamlit
  Layer 5: Terminal Heartbeat → 2s status loop

Run:
    cd backend
    uvicorn server:app --reload --port 8000
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import time
from collections.abc import Generator
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

import cv2
import numpy as np
from fastapi import Depends, FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import Base, SessionLocal, engine
from app import models

from ai.tamper_detector import TamperDetector
from ai.privacy import PrivacyEngine, Mechanism, secure_cleanup
from security.prompt_sanitizer import PromptSanitizer

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("railguard.server")


# ======================================================================
# Connection Manager (fan-out WebSocket broadcaster)
# ======================================================================

class ConnectionManager:
    """Thread-safe WebSocket connection pool with broadcast."""

    def __init__(self) -> None:
        self._connections: list[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._connections.append(ws)
        logger.info("WS client connected. Total: %d", len(self._connections))

    async def disconnect(self, ws: WebSocket) -> None:
        async with self._lock:
            if ws in self._connections:
                self._connections.remove(ws)
        logger.info("WS client disconnected. Total: %d", len(self._connections))

    async def broadcast(self, payload: dict[str, Any]) -> None:
        """Send JSON to every connected client, pruning dead sockets."""
        dead: list[WebSocket] = []
        async with self._lock:
            for ws in self._connections:
                try:
                    await ws.send_json(payload)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                self._connections.remove(ws)

    @property
    def count(self) -> int:
        return len(self._connections)


# ======================================================================
# Singletons
# ======================================================================

manager = ConnectionManager()
detector = TamperDetector()
privacy_engine = PrivacyEngine(
    mechanism=Mechanism.GAUSSIAN,
    embedding_dim=512,
)
sanitizer = PromptSanitizer()


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
    """Prints system status every 2 seconds."""
    while True:
        cam_status = "OK" if detector._calibration_frames > 0 else "IDLE"
        db_status = "Encrypted"
        ws_status = f"Connected ({manager.count} clients)"
        print(
            f"[STATUS] Camera: {cam_status} | DB: {db_status} | Socket: {ws_status}",
            flush=True,
        )
        await asyncio.sleep(2)


# ======================================================================
# Lifespan (startup / shutdown)
# ======================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created.")
    heartbeat_task = asyncio.create_task(_heartbeat_loop())
    logger.info("Heartbeat started.")
    yield
    # Shutdown
    heartbeat_task.cancel()
    logger.info("Server shutting down.")


# ======================================================================
# FastAPI App
# ======================================================================

app = FastAPI(
    title="RailGuard AI — Live Response Server",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ======================================================================
# Layer 1: THE CAMERA GATEWAY
# ======================================================================

@app.websocket("/ws/feed/{camera_id}")
async def camera_feed(ws: WebSocket, camera_id: str) -> None:
    """Receives JPEG frames, runs tamper analysis, broadcasts alerts."""
    await ws.accept()
    logger.info("Camera '%s' feed connected.", camera_id)

    try:
        while True:
            frame_bytes = await ws.receive_bytes()

            # Decode JPEG → BGR numpy array
            buf = np.frombuffer(frame_bytes, dtype=np.uint8)
            frame = cv2.imdecode(buf, cv2.IMREAD_COLOR)
            if frame is None:
                continue

            result = await detector.analyze_frame(frame)
            result_dict = result.to_dict()

            # ── ALERT PATHWAY ──
            if result_dict["status"] == "alert":
                alert_type = result_dict["alert"]
                detail = "SSIM_LOW" if "Block" in alert_type else "SSIM_HIGH"

                alert_payload = {
                    "event": "security_alert",
                    "msg": "CAMERA_TAMPERED",
                    "detail": detail,
                    "alert_type": alert_type,
                    "camera_id": camera_id,
                    "ssim": result_dict["ssim"],
                    "confidence": result_dict["confidence"],
                    "timestamp": time.time(),
                }

                # Broadcast to all Streamlit / frontend clients
                await manager.broadcast(alert_payload)

                # Log to DB
                db = SessionLocal()
                try:
                    incident = models.Incident(
                        threat_type=f"TAMPER: {alert_type}",
                        camera_id=camera_id,
                    )
                    db.add(incident)
                    db.commit()
                    logger.warning(
                        "INCIDENT LOGGED: %s on %s (SSIM=%.4f)",
                        alert_type, camera_id, result_dict["ssim"] or 0,
                    )
                finally:
                    db.close()

            # Echo status back to the camera sender
            await ws.send_json(result_dict)

    except WebSocketDisconnect:
        logger.info("Camera '%s' feed disconnected.", camera_id)


# ======================================================================
# Layer 2: THE DATA SHIELD
# ======================================================================

class PersonDetectionPayload(BaseModel):
    camera_id: str
    raw_embedding: list[float]   # 512 floats
    epsilon: float = 1.0


@app.post("/api/detect-person")
async def detect_person(
    payload: PersonDetectionPayload,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Receives a raw 512-D embedding, applies DP, stores only the noisy vector."""

    raw = np.array(payload.raw_embedding, dtype=np.float32)

    if raw.shape != (512,):
        raise HTTPException(400, f"Expected 512-D vector, got shape {raw.shape}")

    # Apply differential privacy
    result = privacy_engine.privatise(raw, payload.epsilon)
    noisy_vector = result["noisy_vector"]

    # Serialize to base64 for DB storage
    noisy_b64 = base64.b64encode(noisy_vector.tobytes()).decode("ascii")

    # Commit ONLY the noisy vector to DB
    tracked = models.TrackedPerson(
        timestamp=datetime.now(timezone.utc),
        obfuscated_embedding=noisy_b64,
        camera_id=payload.camera_id,
    )
    db.add(tracked)
    db.commit()
    db.refresh(tracked)

    # Destroy raw vector
    secure_cleanup(raw)

    print(
        "DEBUG: Identity Obfuscated. Data committed to Encrypted DB.",
        flush=True,
    )

    return {
        "status": "committed",
        "person_id": tracked.id,
        "utility_loss": result["utility_loss"],
        "snr_db": result["snr_db"],
        "budget_remaining": result["budget_remaining"],
    }


# ======================================================================
# Layer 3: THE LOGIC GATE (OCR text middleware)
# ======================================================================

class OCRTextPayload(BaseModel):
    text: str
    camera_id: str = "OCR-SOURCE"


@app.post("/api/process-ocr")
async def process_ocr(
    payload: OCRTextPayload,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Scans OCR text for prompt injection before passing to LLM agents."""

    scan_result = sanitizer.scan(payload.text)
    scan_dict = scan_result.to_dict()

    if scan_result.action.value == "block":
        # Log to Incident_Logs table
        incident = models.Incident(
            threat_type="PROMPT_INJECTION_ATTACK",
            camera_id=payload.camera_id,
        )
        db.add(incident)
        db.commit()

        logger.warning(
            "PROMPT_INJECTION_ATTACK logged  |  risk=%.2f  |  hash=%s  |  text=%r",
            scan_result.risk_score, scan_result.input_hash, payload.text[:100],
        )

        # Broadcast alert to frontend
        await manager.broadcast({
            "event": "security_alert",
            "msg": "INJECTION_ATTEMPT",
            "detail": scan_dict,
            "camera_id": payload.camera_id,
            "timestamp": time.time(),
        })

        raise HTTPException(
            status_code=400,
            detail={
                "error": "PROMPT_INJECTION_ATTACK",
                "risk_score": scan_result.risk_score,
                "rules_matched": scan_result.matched_rules,
            },
        )

    if scan_result.action.value == "flag":
        logger.warning(
            "SUSPICIOUS OCR text flagged (not blocked)  |  risk=%.2f  |  text=%r",
            scan_result.risk_score, payload.text[:100],
        )

    # Clean text → defensive framing
    safe_text = sanitizer.frame_untrusted_input(payload.text)
    return {"status": "clean", "framed_text": safe_text}


# ======================================================================
# Layer 4: THE FRONTEND BRIDGE (WebSocket alert subscription)
# ======================================================================

@app.websocket("/ws/alerts")
async def alert_socket(ws: WebSocket) -> None:
    """Streamlit / frontend clients subscribe here for real-time alerts."""
    await manager.connect(ws)
    try:
        while True:
            msg = await ws.receive_text()
            # Client can send pings / heartbeat acks
            if msg == "ping":
                await ws.send_text("pong")
    except WebSocketDisconnect:
        await manager.disconnect(ws)


# ======================================================================
# Existing REST endpoints (preserved)
# ======================================================================

@app.get("/cameras")
def list_cameras(db: Session = Depends(get_db)):
    return db.query(models.Camera).all()


@app.get("/incidents")
def list_incidents(db: Session = Depends(get_db)):
    return db.query(models.Incident).order_by(models.Incident.timestamp.desc()).all()


@app.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "running",
        "websocket_clients": manager.count,
        "privacy_budget": privacy_engine.accountant.report(),
        "tamper_calibrated": detector._calibration_frames >= 60,
    }
