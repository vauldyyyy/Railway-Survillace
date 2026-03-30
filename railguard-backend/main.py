"""
RailGuard AI — railguard-backend/main.py
GPU-accelerated multi-camera surveillance engine.

Architecture:
  - One dedicated YOLO model instance per camera (no shared state)
  - Each camera runs in its own background thread
  - Thread writes annotated JPEG into a 1-slot frame buffer
  - HTTP endpoint reads buffer instantly — never blocks on YOLO
  - All YOLO inference on CUDA (RTX 3050) via device='cuda'
  - CPU only handles encoding, Re-ID embeddings, alert logic
"""

import cv2
import numpy as np
import time
import uuid
import base64
import threading
import queue
import asyncio
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from ultralytics import YOLO
from vidgear.gears import CamGear
from pydantic import BaseModel
from security.auth import auth_engine

# ─────────────────────────────────────────────────────────────────────────────
# 1. APP INIT
# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(title="RailGuard AI Engine")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class LoginRequest(BaseModel):
    operator_id: str
    password: str

# ─────────────────────────────────────────────────────────────────────────────
# 2. DEVICE DETECTION  — use CUDA if available, else CPU
# ─────────────────────────────────────────────────────────────────────────────

try:
    import torch
    DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
except ImportError:
    DEVICE = "cpu"

print(f"[RailGuard] Inference device: {DEVICE.upper()}")

# ─────────────────────────────────────────────────────────────────────────────
# 3. CAMERA CONFIG
# ─────────────────────────────────────────────────────────────────────────────

JPEG_QUALITY       = 72
WEBCAM_YOLO_EVERY  = 2    # run YOLO every N webcam frames
STREAM_YOLO_EVERY  = 3    # run YOLO every N stream frames
INFER_SIZE         = 416  # inference resolution (faster than 640)
CROWD_THRESHOLD    = 5
BAG_STATIONARY_SECS = 6
FIRE_MIN_PIXELS    = 1500
SMOKE_MIN_PIXELS   = 10000

CAM_NAMES = {
    "cam1": "CAM-01 • Our Camera",
    "cam2": "CAM-02 • Track View",
    "cam3": "CAM-03 • Platform View",
    "cam4": "CAM-04 • Entry View",
    "cam5": "CAM-05 • Exit View",
    "cam6": "CAM-06 • Edge Camera",
}

YT_SOURCES = {
    "cam2": "https://www.youtube.com/watch?v=X-ir2KfXMX0",
    "cam3": "https://youtube.com/shorts/KsWrd5Bbu3w?si=AMr7JToFajUYo2LF",
    "cam4": "https://www.youtube.com/watch?v=X-ir2KfXMX0",
    "cam5": "https://www.youtube.com/watch?v=KeEDEDCOTCU",
    "cam6": "https://www.youtube.com/watch?v=X-ir2KfXMX0",
}

# Feature matrix per camera
FEATURES = {
    "cam1": {"baggage": True,  "track": True,  "crowd": True,  "fire": True},
    "cam2": {"baggage": False, "track": True,  "crowd": False, "fire": False},
    "cam3": {"baggage": True,  "track": False, "crowd": True,  "fire": False},
    "cam4": {"baggage": False, "track": False, "crowd": False, "fire": False},
    "cam5": {"baggage": False, "track": False, "crowd": False, "fire": False},
    "cam6": {"baggage": True,  "track": False, "crowd": True,  "fire": False},
}

# ─────────────────────────────────────────────────────────────────────────────
# 4. GLOBAL SHARED STORES  (Re-ID, alerts — all cameras share these)
# ─────────────────────────────────────────────────────────────────────────────

tracklet_db: dict = {}
embedding_db: dict = {}
db_lock = threading.Lock()

alerts: list = []
alerts_lock = threading.Lock()
_alert_last: dict = {}

yolo_to_trk: dict = {}       # (cam_id, yolo_tid) -> trk_id

bag_tracker: dict = {}        # cam_id -> {spatial_hash -> first_seen}

# Per-camera last-YOLO-result cache (for non-YOLO frames)
_last_boxes: dict       = {}
_last_person_count: dict = {}
_last_fire_smoke: dict  = {}

# ─────────────────────────────────────────────────────────────────────────────
# 5. PER-CAMERA FRAME BUFFER
#    Each camera thread writes its latest annotated JPEG here.
#    The HTTP endpoint reads from here — never waits for YOLO.
# ─────────────────────────────────────────────────────────────────────────────

# cam_id -> latest MJPEG bytes  (replaced atomically)
frame_buffer: dict[str, bytes] = {}
frame_lock:   dict[str, threading.Event] = {}

for _cid in CAM_NAMES:
    frame_buffer[_cid] = b""
    frame_lock[_cid]   = threading.Event()

# ─────────────────────────────────────────────────────────────────────────────
# 6. HELPERS: alerts, Re-ID, time
# ─────────────────────────────────────────────────────────────────────────────

def push_alert(cam: str, atype: str, desc: str, frame: np.ndarray = None):
    key = f"{cam}:{atype}"
    now = time.time()
    if now - _alert_last.get(key, 0) < 10:
        return
    _alert_last[key] = now
    
    img_b64 = ""
    if frame is not None:
        ok, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 60])
        if ok:
            img_b64 = "data:image/jpeg;base64," + base64.b64encode(buf.tobytes()).decode()

    with alerts_lock:
        alerts.append({"id": str(uuid.uuid4())[:8],
                        "cam": cam, "type": atype, "desc": desc, "ts": now, "image": img_b64})
        if len(alerts) > 60:
            alerts.pop(0)

def rel_time(ts: float) -> str:
    d = int(time.time() - ts)
    if d < 60:   return "just now"
    if d < 3600: return f"{d//60} min ago"
    return f"{d//3600} hr ago"

def extract_embedding(crop: np.ndarray) -> np.ndarray:
    if crop is None or crop.size == 0:
        return np.zeros(512, dtype=np.float32)
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    h = cv2.calcHist([hsv], [0], None, [180], [0, 180]).flatten()
    s = cv2.calcHist([hsv], [1], None, [256], [0, 256]).flatten()
    v = cv2.calcHist([hsv], [2], None, [256], [0, 256]).flatten()
    vec = np.concatenate([h, s[:166], v[:166]])[:512].astype(np.float32)
    vec /= (vec.sum() + 1e-7)
    vec += np.random.normal(0, 0.1, vec.shape).astype(np.float32)
    return vec

def cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na == 0 or nb == 0: return 0.0
    return float(np.dot(a, b) / (na * nb))

def find_match(emb: np.ndarray, threshold: float = 0.82):
    best_id, best_score = None, -1.0
    with db_lock:
        for tid, e in embedding_db.items():
            s = cosine_sim(emb, e)
            if s > best_score:
                best_score, best_id = s, tid
    return best_id if best_score >= threshold else None

def new_trk_id() -> str:
    tid = f"TRK-{int(uuid.uuid4().int % 9000) + 1000:04d}"
    while tid in tracklet_db:
        tid = f"TRK-{int(uuid.uuid4().int % 9000) + 1000:04d}"
    return tid

def crop_b64(crop: np.ndarray) -> str:
    ok, buf = cv2.imencode('.jpg', crop, [cv2.IMWRITE_JPEG_QUALITY, 70])
    if not ok: return ""
    return "data:image/jpeg;base64," + base64.b64encode(buf.tobytes()).decode()

def register_person(crop: np.ndarray, cam_id: str) -> str:
    emb     = extract_embedding(crop)
    matched = find_match(emb)
    label   = CAM_NAMES.get(cam_id, cam_id.upper())
    now     = time.time()
    with db_lock:
        if matched:
            trk = tracklet_db[matched]
            if label not in trk["cameras_seen"]:
                trk["cameras_seen"].append(label)
                trk["cam"]     = label
                trk["journey"] = f"{len(trk['cameras_seen'])} cameras"
            trk["last_seen"] = now
            return matched
        tid = new_trk_id()
        tracklet_db[tid] = {
            "id": tid, "status": "NORMAL",
            "cam": label, "time": "just now",
            "journey": None, "image": crop_b64(crop),
            "first_seen": now, "last_seen": now,
            "cameras_seen": [label],
        }
        embedding_db[tid] = emb
        return tid

# ─────────────────────────────────────────────────────────────────────────────
# 7. DETECTION HELPERS (stateless, take frame + return annotated frame)
# ─────────────────────────────────────────────────────────────────────────────

TRACK_POLYGON = np.array(
    [[330, 185], [390, 185], [640, 290], [640, 360], [480, 360]], np.int32)

def draw_track_zone(frame: np.ndarray) -> np.ndarray:
    overlay = frame.copy()
    cv2.fillPoly(overlay, [TRACK_POLYGON], (0, 0, 255))
    cv2.addWeighted(overlay, 0.25, frame, 0.75, 0, frame)
    cv2.polylines(frame, [TRACK_POLYGON], True, (0, 0, 255), 2)
    cv2.putText(frame, "RESTRICTED TRACK ZONE",
                (10, frame.shape[0] - 12),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
    return frame

def check_track_intrusion(frame, x1, y1, x2, y2, trk_id, cam_id) -> bool:
    bc     = (int((x1 + x2) / 2), y2)
    inside = cv2.pointPolygonTest(TRACK_POLYGON, bc, False) >= 0
    if inside:
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 3)
        cv2.putText(frame, f"TRACK INTRUSION {trk_id}",
                    (x1, y1 - 10), cv2.FONT_HERSHEY_DUPLEX, 0.55, (0, 0, 255), 2)
        push_alert(CAM_NAMES.get(cam_id, cam_id), "TRACK_INTRUSION",
                   f"{trk_id} entered restricted track zone", frame)
        with db_lock:
            if trk_id in tracklet_db:
                tracklet_db[trk_id]["status"] = "FLAGGED"
    return inside

def check_crowd(person_count: int, cam_id: str, frame: np.ndarray) -> np.ndarray:
    color = (0, 230, 230) if person_count < CROWD_THRESHOLD else (0, 50, 255)
    label = f"CROWD: {person_count}"
    if person_count >= CROWD_THRESHOLD:
        label += "  !! OVERCROWD !!"
        push_alert(CAM_NAMES.get(cam_id, cam_id), "OVERCROWDING",
                   f"{person_count} persons – threshold exceeded", frame)
    cv2.putText(frame, label, (10, frame.shape[0] - 12),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)
    return frame

def check_unattended_bags(frame: np.ndarray, boxes, cam_id: str,
                           model_ref) -> np.ndarray:
    if cam_id not in bag_tracker:
        bag_tracker[cam_id] = {}
    now  = time.time()
    seen = set()
    for box in boxes:
        lname = model_ref.names[int(box.cls[0])]
        if lname not in ["backpack", "suitcase", "handbag"]:
            continue
        x1, y1, x2, y2 = map(int, box.xyxy[0].cpu().numpy())
        bh = ((x1 + x2) // 2 // 40, (y1 + y2) // 2 // 40)
        seen.add(bh)
        if bh not in bag_tracker[cam_id]:
            bag_tracker[cam_id][bh] = now
        elapsed    = now - bag_tracker[cam_id][bh]
        unattended = elapsed >= BAG_STATIONARY_SECS
        color      = (0, 0, 255) if unattended else (0, 165, 255)
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        cv2.putText(frame,
                    f"UNATTENDED {elapsed:.0f}s" if unattended else f"BAG {elapsed:.1f}s",
                    (x1, y1 - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
        if unattended:
            push_alert(CAM_NAMES.get(cam_id, cam_id), "UNATTENDED_BAGGAGE",
                       f"Bag stationary {elapsed:.0f}s", frame)
    for k in [k for k in bag_tracker[cam_id] if k not in seen]:
        del bag_tracker[cam_id][k]
    return frame

def detect_fire_smoke(frame: np.ndarray):
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    m1  = cv2.inRange(hsv, np.array([0,  150, 200]), np.array([10, 255, 255]))
    m2  = cv2.inRange(hsv, np.array([15, 150, 200]), np.array([30, 255, 255]))
    kernel    = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    fire_mask = cv2.morphologyEx(cv2.bitwise_or(m1, m2), cv2.MORPH_OPEN, kernel)
    fire      = cv2.countNonZero(fire_mask) > FIRE_MIN_PIXELS

    smoke_raw  = cv2.inRange(hsv, np.array([0, 0, 100]), np.array([180, 25, 210]))
    smoke_morph = cv2.morphologyEx(
        smoke_raw, cv2.MORPH_CLOSE,
        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15)))
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    smoke = (cv2.countNonZero(smoke_morph) > SMOKE_MIN_PIXELS and
             cv2.Laplacian(gray, cv2.CV_64F).var() < 80)
    return fire, smoke

def draw_fire_smoke(frame: np.ndarray, fire: bool, smoke: bool) -> np.ndarray:
    if fire:
        ov = frame.copy()
        cv2.rectangle(ov, (0, 0), (frame.shape[1], frame.shape[0]), (0, 0, 220), -1)
        cv2.addWeighted(ov, 0.07, frame, 0.93, 0, frame)
        cv2.putText(frame, "!! FIRE DETECTED !!", (10, 45),
                    cv2.FONT_HERSHEY_DUPLEX, 0.7, (0, 50, 255), 2)
    if smoke:
        cv2.putText(frame, "!! SMOKE DETECTED !!", (10, 75),
                    cv2.FONT_HERSHEY_DUPLEX, 0.65, (100, 100, 240), 2)
    return frame

def _mjpeg_bytes(frame: np.ndarray) -> bytes:
    _, buf = cv2.imencode('.jpg', frame,
                          [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
    return (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n'
            + buf.tobytes() + b'\r\n')

def placeholder_frame(cam_id: str) -> bytes:
    f = np.zeros((360, 640, 3), dtype=np.uint8)
    cv2.putText(f, f"{cam_id.upper()}: LOADING AI ENGINE...",
                (80, 180), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (60, 60, 60), 2)
    return _mjpeg_bytes(f)

# ─────────────────────────────────────────────────────────────────────────────
# 8. CORE ANNOTATOR  (called inside each camera thread with its OWN model)
# ─────────────────────────────────────────────────────────────────────────────

def annotate(frame: np.ndarray, cam_id: str, fc: int,
             model_ref, yolo_every: int) -> np.ndarray:
    feat    = FEATURES.get(cam_id, {})
    run_yolo = (fc % yolo_every == 0)

    if feat.get("track") and cam_id == "cam2":
        frame = draw_track_zone(frame)

    if run_yolo:
        classes = [0]
        if feat.get("baggage"):
            classes += [24, 26, 28]

        # ── GPU inference on this camera's dedicated model ────────────────
        results  = model_ref.track(
            frame,
            imgsz=INFER_SIZE,          # smaller = faster
            conf=0.42,
            classes=classes,
            persist=True,
            verbose=False,
            device=DEVICE,
        )[0]

        _last_boxes[cam_id] = results.boxes
        person_count = 0

        for box in results.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            conf  = float(box.conf[0]) * 100
            lname = model_ref.names[int(box.cls[0])]
            tid   = int(box.id[0]) if box.id is not None else -1

            if lname == "person":
                person_count += 1
                trk_id = yolo_to_trk.get((cam_id, tid))
                if trk_id is None or fc % 30 == 0:
                    pad  = 4
                    crop = frame[max(0, y1-pad):min(frame.shape[0], y2+pad),
                                 max(0, x1-pad):min(frame.shape[1], x2+pad)]
                    if crop.size > 0:
                        trk_id = register_person(crop, cam_id)
                        yolo_to_trk[(cam_id, tid)] = trk_id

                intrusion = False
                if feat.get("track"):
                    intrusion = check_track_intrusion(
                        frame, x1, y1, x2, y2, trk_id or "UNK", cam_id)
                if not intrusion:
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 200, 0), 2)
                    cv2.putText(frame, trk_id or f"{conf:.0f}%",
                                (x1, y1 - 8),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 200, 0), 1)

        if feat.get("baggage"):
            frame = check_unattended_bags(frame, results.boxes, cam_id, model_ref)

        _last_person_count[cam_id] = person_count

        if feat.get("fire"):
            fire, smoke = detect_fire_smoke(frame)
            _last_fire_smoke[cam_id] = (fire, smoke)
            frame = draw_fire_smoke(frame, fire, smoke)
            if fire:
                push_alert(CAM_NAMES.get(cam_id, cam_id), "FIRE", "Fire detected", frame)
            if smoke:
                push_alert(CAM_NAMES.get(cam_id, cam_id), "SMOKE", "Smoke detected", frame)

    else:
        # ── Non-YOLO frames: redraw cached boxes (zero inference cost) ────
        boxes = _last_boxes.get(cam_id)
        if boxes is not None:
            for box in boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                lname = model_ref.names[int(box.cls[0])]
                tid   = int(box.id[0]) if box.id is not None else -1
                if lname == "person":
                    trk_id    = yolo_to_trk.get((cam_id, tid))
                    intrusion = (feat.get("track") and
                                 cv2.pointPolygonTest(
                                     TRACK_POLYGON,
                                     (int((x1+x2)/2), y2), False) >= 0)
                    color = (0, 0, 255) if intrusion else (255, 200, 0)
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                    cv2.putText(frame, trk_id or "",
                                (x1, y1 - 8),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.42, color, 1)
                elif lname in ["backpack","suitcase","handbag"] and feat.get("baggage"):
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 165, 255), 2)

        if feat.get("fire"):
            fire, smoke = _last_fire_smoke.get(cam_id, (False, False))
            frame = draw_fire_smoke(frame, fire, smoke)

    if feat.get("crowd"):
        frame = check_crowd(_last_person_count.get(cam_id, 0), cam_id, frame)

    cv2.putText(frame, f"{CAM_NAMES.get(cam_id, cam_id)} | RAILGUARD AI",
                (8, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 220, 220), 1)
    return frame

# ─────────────────────────────────────────────────────────────────────────────
# 9. CAMERA WORKER THREADS
#    Each thread owns its YOLO model → no lock contention on inference
#    Thread writes to frame_buffer[cam_id] atomically
# ─────────────────────────────────────────────────────────────────────────────

def _worker_webcam():
    """Dedicated thread for CAM-01 (local webcam)."""
    cam_id = "cam1"
    print(f"[{cam_id}] Loading YOLO on {DEVICE}...")
    m = YOLO("yolov8n.pt").to(DEVICE)  # <--- ADD .to(DEVICE) HERE

    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)  # <--- Forces low-latency hardware capture
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 360)
    cap.set(cv2.CAP_PROP_BUFFERSIZE,   1)   # discard stale frames
    cap.set(cv2.CAP_PROP_FPS,          30)

    fc = 0
    print(f"[{cam_id}] Thread started.")
    while True:
        ok, frame = cap.read()
        if not ok:
            time.sleep(0.05)
            continue
        fc += 1
        try:
            frame = annotate(frame, cam_id, fc, m, WEBCAM_YOLO_EVERY)
        except Exception as e:
            print(f"[{cam_id}] annotate error: {e}")

        data = _mjpeg_bytes(frame)
        frame_buffer[cam_id] = data
        frame_lock[cam_id].set()    # signal that a new frame is ready


def _worker_yt(cam_id: str):
    """Dedicated thread for a YouTube stream camera."""
    url = YT_SOURCES.get(cam_id, "")
    print(f"[{cam_id}] Loading YOLO on {DEVICE}...")
    m = YOLO("yolov8n.pt").to(DEVICE)  # <--- ADD .to(DEVICE) HERE

    stream = None
    while stream is None:
        try:
            stream = CamGear(
                source=url,
                stream_mode=True,
                logging=False,
                **{"STREAM_RESOLUTION": "360p"},
            ).start()
            print(f"[{cam_id}] Stream connected.")
        except Exception as e:
            print(f"[{cam_id}] CamGear error: {e} — retrying in 5s")
            time.sleep(5)

    fc = 0
    while True:
        frame = stream.read()
        if frame is None:
            time.sleep(0.04)
            continue
        frame = cv2.resize(frame, (640, 360))
        fc   += 1
        try:
            frame = annotate(frame, cam_id, fc, m, STREAM_YOLO_EVERY)
        except Exception as e:
            print(f"[{cam_id}] annotate error: {e}")

        data = _mjpeg_bytes(frame)
        frame_buffer[cam_id] = data
        frame_lock[cam_id].set()


# ─────────────────────────────────────────────────────────────────────────────
# 10. START ALL CAMERA THREADS ON STARTUP
# ─────────────────────────────────────────────────────────────────────────────

def _start_camera_threads():
    # Pre-fill buffers so HTTP never returns empty
    for cid in CAM_NAMES:
        frame_buffer[cid] = placeholder_frame(cid)

    # CAM-01: local webcam
    t1 = threading.Thread(target=_worker_webcam, daemon=True, name="cam1-thread")
    t1.start()

    # CAM-02 to CAM-06: YouTube streams
    for cid in ["cam2", "cam3", "cam4", "cam5", "cam6"]:
        t = threading.Thread(
            target=_worker_yt, args=(cid,),
            daemon=True, name=f"{cid}-thread")
        t.start()

    print("[RailGuard] All camera threads launched.")

_start_camera_threads()

# ─────────────────────────────────────────────────────────────────────────────
# 11. MJPEG STREAM ENDPOINT HELPER
#     Reads from frame_buffer — instant, never blocks on YOLO
# ─────────────────────────────────────────────────────────────────────────────

async def _stream_from_buffer(cam_id: str):
    """
    Async generator: Prevents FastAPI from choking.
    Broadcasts at a perfectly smooth 30 FPS to unlimited viewers.
    """
    try:
        while True:
            data = frame_buffer.get(cam_id)
            if data:
                yield data
            await asyncio.sleep(0.033)
    except asyncio.CancelledError:
        pass

# ─────────────────────────────────────────────────────────────────────────────
# 12. VIDEO ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/video/cam1")
def v1():
    return StreamingResponse(_stream_from_buffer("cam1"),
                             media_type="multipart/x-mixed-replace; boundary=frame")
@app.get("/video/cam2")
def v2():
    return StreamingResponse(_stream_from_buffer("cam2"),
                             media_type="multipart/x-mixed-replace; boundary=frame")
@app.get("/video/cam3")
def v3():
    return StreamingResponse(_stream_from_buffer("cam3"),
                             media_type="multipart/x-mixed-replace; boundary=frame")
@app.get("/video/cam4")
def v4():
    return StreamingResponse(_stream_from_buffer("cam4"),
                             media_type="multipart/x-mixed-replace; boundary=frame")
@app.get("/video/cam5")
def v5():
    return StreamingResponse(_stream_from_buffer("cam5"),
                             media_type="multipart/x-mixed-replace; boundary=frame")
@app.get("/video/cam6")
def v6():
    return StreamingResponse(_stream_from_buffer("cam6"),
                             media_type="multipart/x-mixed-replace; boundary=frame")

# ─────────────────────────────────────────────────────────────────────────────
# 13. DATA ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/tracklets")
def get_tracklets():
    with db_lock:
        result = [
            {**trk, "time": rel_time(trk["last_seen"])}
            for trk in sorted(tracklet_db.values(),
                               key=lambda x: x["last_seen"], reverse=True)
        ]
    return JSONResponse(content=result)

@app.post("/api/tracklets/{trk_id}/flag")
def flag_tracklet(trk_id: str):
    with db_lock:
        if trk_id in tracklet_db:
            tracklet_db[trk_id]["status"] = "FLAGGED"
            return {"ok": True}
    return JSONResponse(status_code=404, content={"error": "Not found"})

@app.post("/api/tracklets/{trk_id}/clear")
def clear_tracklet(trk_id: str):
    with db_lock:
        if trk_id in tracklet_db:
            tracklet_db[trk_id]["status"] = "NORMAL"
            return {"ok": True}
    return JSONResponse(status_code=404, content={"error": "Not found"})

@app.delete("/api/tracklets")
def purge_tracklets():
    with db_lock:
        tracklet_db.clear()
        embedding_db.clear()
        yolo_to_trk.clear()
    return {"ok": True}

@app.get("/api/alerts")
def get_alerts():
    with alerts_lock:
        return JSONResponse(
            content=sorted(alerts, key=lambda x: x["ts"], reverse=True)[:20])

@app.get("/api/stats")
def get_stats():
    with db_lock:
        total   = len(tracklet_db)
        flagged = sum(1 for t in tracklet_db.values() if t["status"] == "FLAGGED")
    with alerts_lock:
        recent = len([a for a in alerts if time.time() - a["ts"] < 300])
    return {"total_tracked": total, "flagged": flagged,
            "cameras_active": 6, "recent_alerts": recent}

@app.get("/api/bridge-status")
def bridge_status():
    return JSONResponse(content={
        "mode": "local" if DEVICE == "cpu" else "remote",
        "connected": DEVICE == "cuda",
        "latency_ms": 0,
        "inference_source": DEVICE,
    })

@app.post("/api/login")
def login(req: LoginRequest):
    result = auth_engine.authenticate(req.operator_id, req.password)
    return JSONResponse(content=result)

@app.get("/api/verify")
def verify_token(req: Request):
    auth_header = req.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return JSONResponse(status_code=401, content={"error": "Missing token"})
    try:
        auth_engine.decode_token(auth_header.split(" ")[1])
        return {"ok": True}
    except Exception:
        return JSONResponse(status_code=401, content={"error": "Token expired"})