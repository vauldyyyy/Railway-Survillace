import cv2
import numpy as np
import time
import uuid
import base64
import threading
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from ultralytics import YOLO
from vidgear.gears import CamGear

# ==========================================
# 1. APP + MODEL INIT
# ==========================================
app = FastAPI(title="RailGuard AI Engine")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

print("Loading YOLO model...")
model = YOLO("yolov8n.pt")
print("YOLO loaded.")

# ==========================================
# 2. PERFORMANCE SETTINGS
# ==========================================

# Run YOLO only every N frames — key to eliminating lag
YOLO_INTERVAL_WEBCAM = 3    # webcam: run every 3rd frame
YOLO_INTERVAL_STREAM = 5    # youtube streams: run every 5th frame

# Encode JPEG at lower quality for speed
JPEG_QUALITY = 70

# ==========================================
# 3. RE-ID STORE
# ==========================================
tracklet_db: dict = {}
embedding_db: dict = {}
db_lock = threading.Lock()
yolo_to_trk: dict = {}

alerts: list = []
alerts_lock = threading.Lock()

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

# ==========================================
# 4. RE-ID HELPERS
# ==========================================

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
    if na == 0 or nb == 0:
        return 0.0
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
    if not ok:
        return ""
    return "data:image/jpeg;base64," + base64.b64encode(buf.tobytes()).decode()

def register_person(crop: np.ndarray, cam_id: str) -> str:
    emb = extract_embedding(crop)
    matched = find_match(emb)
    cam_label = CAM_NAMES.get(cam_id, cam_id.upper())
    now = time.time()
    with db_lock:
        if matched:
            trk = tracklet_db[matched]
            if cam_label not in trk["cameras_seen"]:
                trk["cameras_seen"].append(cam_label)
                trk["cam"] = cam_label
                trk["journey"] = f"{len(trk['cameras_seen'])} cameras"
            trk["last_seen"] = now
            return matched
        tid = new_trk_id()
        tracklet_db[tid] = {
            "id": tid, "status": "NORMAL",
            "cam": cam_label, "time": "just now",
            "journey": None, "image": crop_b64(crop),
            "first_seen": now, "last_seen": now,
            "cameras_seen": [cam_label],
        }
        embedding_db[tid] = emb
        return tid

def rel_time(ts: float) -> str:
    d = int(time.time() - ts)
    if d < 60: return "just now"
    if d < 3600: return f"{d//60} min ago"
    return f"{d//3600} hr ago"

# ── Alert push (throttled per type per cam — max 1 per 10 sec) ───────────────
_alert_last: dict = {}

def push_alert(cam: str, atype: str, desc: str):
    key = f"{cam}:{atype}"
    now = time.time()
    if now - _alert_last.get(key, 0) < 10:
        return   # throttle repeated alerts
    _alert_last[key] = now
    with alerts_lock:
        alerts.append({
            "id": str(uuid.uuid4())[:8],
            "cam": cam, "type": atype, "desc": desc,
            "ts": now,
        })
        if len(alerts) > 50:
            alerts.pop(0)

# ==========================================
# 5. FIRE / SMOKE DETECTION  ← FIXED HSV
#
#  KEY FIXES:
#  - Fire: requires BOTH high saturation AND high brightness
#           with a minimum pixel area + morphological filtering
#  - Smoke: requires LOW saturation, LOW brightness variance,
#           large connected blob — completely different from skin
#  - Skin tones: H=0-25, S=40-170, V=80-255 → excluded from both
# ==========================================

# Minimum pixel counts to avoid false positives
FIRE_MIN_PIXELS  = 1500   # raised from 800
SMOKE_MIN_PIXELS = 10000  # raised from 6000

def detect_fire_smoke(frame: np.ndarray):
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    # ── FIRE ──────────────────────────────────────────────────────────────
    # Real fire: orange-red hue, HIGH saturation (>150), HIGH brightness (>200)
    # Skin:      saturation is typically < 170, brightness < 220 → fire needs BOTH >150 and >200
    fire_lower1 = np.array([0,  150, 200])   # red fire  (hue 0-10)
    fire_upper1 = np.array([10, 255, 255])
    fire_lower2 = np.array([15, 150, 200])   # orange fire (hue 15-30)
    fire_upper2 = np.array([30, 255, 255])

    m1 = cv2.inRange(hsv, fire_lower1, fire_upper1)
    m2 = cv2.inRange(hsv, fire_lower2, fire_upper2)
    fire_raw = cv2.bitwise_or(m1, m2)

    # Morphological opening: remove small noise blobs (skin glints etc.)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    fire_mask = cv2.morphologyEx(fire_raw, cv2.MORPH_OPEN, kernel)
    fire_pixels = cv2.countNonZero(fire_mask)
    fire = fire_pixels > FIRE_MIN_PIXELS

    # ── SMOKE ─────────────────────────────────────────────────────────────
    # Real smoke: very LOW saturation (<25), mid brightness (100-210),
    #             must cover a LARGE area (>10000 px) — skin can't do this
    smoke_lower = np.array([0,   0,  100])
    smoke_upper = np.array([180, 25, 210])
    smoke_raw   = cv2.inRange(hsv, smoke_lower, smoke_upper)

    # Only count large connected blobs (smoke is diffuse, not small patches)
    smoke_morph = cv2.morphologyEx(
        smoke_raw,
        cv2.MORPH_CLOSE,
        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
    )
    smoke_pixels = cv2.countNonZero(smoke_morph)

    # Extra check: smoke has LOW local contrast — use Laplacian variance
    gray   = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    lap    = cv2.Laplacian(gray, cv2.CV_64F)
    sharpness = lap.var()
    # Smoke makes image blurry → sharpness < 80 AND large low-sat area
    smoke = (smoke_pixels > SMOKE_MIN_PIXELS) and (sharpness < 80)

    return fire, smoke

def draw_fire_smoke(frame: np.ndarray, fire: bool, smoke: bool) -> np.ndarray:
    if fire:
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (frame.shape[1], frame.shape[0]), (0, 0, 220), -1)
        cv2.addWeighted(overlay, 0.07, frame, 0.93, 0, frame)
        cv2.putText(frame, "!! FIRE DETECTED !!", (10, 45),
                    cv2.FONT_HERSHEY_DUPLEX, 0.7, (0, 50, 255), 2)
    if smoke:
        cv2.putText(frame, "!! SMOKE DETECTED !!", (10, 75),
                    cv2.FONT_HERSHEY_DUPLEX, 0.65, (100, 100, 240), 2)
    return frame

# ==========================================
# 6. OVERCROWDING
# ==========================================

CROWD_THRESHOLD = 5

def check_crowd(person_count: int, cam_id: str, frame: np.ndarray) -> np.ndarray:
    color = (0, 230, 230) if person_count < CROWD_THRESHOLD else (0, 50, 255)
    label = f"CROWD: {person_count}"
    if person_count >= CROWD_THRESHOLD:
        label += "  !! OVERCROWD !!"
        push_alert(CAM_NAMES.get(cam_id, cam_id), "OVERCROWDING",
                   f"{person_count} persons – density threshold exceeded")
    cv2.putText(frame, label, (10, frame.shape[0] - 12),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)
    return frame

# ==========================================
# 7. UNATTENDED BAGGAGE
# ==========================================

bag_tracker: dict = {}
BAG_STATIONARY_SECS = 5

def check_unattended_bags(frame: np.ndarray, boxes, cam_id: str) -> np.ndarray:
    if cam_id not in bag_tracker:
        bag_tracker[cam_id] = {}
    now = time.time()
    seen = set()
    for box in boxes:
        lname = model.names[int(box.cls[0])]
        if lname not in ["backpack", "suitcase", "handbag"]:
            continue
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
        bh = (cx // 40, cy // 40)
        seen.add(bh)
        if bh not in bag_tracker[cam_id]:
            bag_tracker[cam_id][bh] = {"first_seen": now}
        elapsed = now - bag_tracker[cam_id][bh]["first_seen"]
        unattended = elapsed >= BAG_STATIONARY_SECS
        color = (0, 0, 255) if unattended else (0, 165, 255)
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        tag = f"UNATTENDED {elapsed:.0f}s" if unattended else f"BAG {elapsed:.1f}s"
        cv2.putText(frame, tag, (x1, y1 - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
        if unattended:
            push_alert(CAM_NAMES.get(cam_id, cam_id), "UNATTENDED_BAGGAGE",
                       f"Bag stationary for {elapsed:.0f}s")
    for k in [k for k in bag_tracker[cam_id] if k not in seen]:
        del bag_tracker[cam_id][k]
    return frame

# ==========================================
# 8. TRACK INTRUSION
# ==========================================

TRACK_POLYGON = np.array([
    [330, 185], [390, 185], [640, 290], [640, 360], [480, 360]
], np.int32)

def draw_track_zone(frame: np.ndarray) -> np.ndarray:
    overlay = frame.copy()
    cv2.fillPoly(overlay, [TRACK_POLYGON], (0, 0, 255))
    cv2.addWeighted(overlay, 0.25, frame, 0.75, 0, frame)
    cv2.polylines(frame, [TRACK_POLYGON], True, (0, 0, 255), 2)
    cv2.putText(frame, "RESTRICTED TRACK ZONE", (10, frame.shape[0] - 12),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
    return frame

def check_track_intrusion(frame: np.ndarray, x1, y1, x2, y2,
                           trk_id: str, cam_id: str) -> bool:
    bc = (int((x1 + x2) / 2), y2)
    inside = cv2.pointPolygonTest(TRACK_POLYGON, bc, False) >= 0
    if inside:
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 3)
        cv2.putText(frame, f"TRACK INTRUSION {trk_id}", (x1, y1 - 10),
                    cv2.FONT_HERSHEY_DUPLEX, 0.55, (0, 0, 255), 2)
        push_alert(CAM_NAMES.get(cam_id, cam_id), "TRACK_INTRUSION",
                   f"{trk_id} entered restricted track zone")
        with db_lock:
            if trk_id in tracklet_db:
                tracklet_db[trk_id]["status"] = "FLAGGED"
    return inside

# ==========================================
# 9. FRAME ANNOTATOR  ← cached last result
#    YOLO runs every N frames; other frames
#    reuse last_boxes to stay smooth
# ==========================================

# Per-cam last YOLO result cache
_last_boxes: dict = {}           # cam_id -> boxes
_last_person_count: dict = {}    # cam_id -> int
_last_fire_smoke: dict = {}      # cam_id -> (fire, smoke)

def annotate_frame(frame: np.ndarray, cam_id: str, fc: int,
                   yolo_interval: int) -> np.ndarray:
    do_baggage = cam_id in ("cam1", "cam3", "cam6")
    do_track   = cam_id in ("cam1", "cam2")
    do_crowd   = cam_id in ("cam1", "cam3", "cam6")
    do_fire    = cam_id == "cam1"

    run_yolo = (fc % yolo_interval == 0)

    if do_track and cam_id == "cam2":
        frame = draw_track_zone(frame)

    # ── YOLO inference (only every N frames) ─────────────────────────────
    if run_yolo:
        classes = [0]
        if do_baggage:
            classes += [24, 26, 28]
        results = model.track(frame, conf=0.42, classes=classes,
                               persist=True, verbose=False)[0]
        _last_boxes[cam_id] = results.boxes
        person_count = 0

        for box in results.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            conf = float(box.conf[0]) * 100
            lname = model.names[int(box.cls[0])]
            tid   = int(box.id[0]) if box.id is not None else -1

            if lname == "person":
                person_count += 1
                trk_id = yolo_to_trk.get((cam_id, tid))
                # Register Re-ID every 30 frames (not every YOLO frame)
                if trk_id is None or fc % 30 == 0:
                    pad  = 4
                    crop = frame[max(0, y1-pad):min(frame.shape[0], y2+pad),
                                 max(0, x1-pad):min(frame.shape[1], x2+pad)]
                    if crop.size > 0:
                        trk_id = register_person(crop, cam_id)
                        yolo_to_trk[(cam_id, tid)] = trk_id

                intrusion = False
                if do_track:
                    intrusion = check_track_intrusion(
                        frame, x1, y1, x2, y2, trk_id or "UNK", cam_id)
                if not intrusion:
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 200, 0), 2)
                    cv2.putText(frame, trk_id or f"{conf:.0f}%",
                                (x1, y1 - 8), cv2.FONT_HERSHEY_SIMPLEX,
                                0.42, (255, 200, 0), 1)

        if do_baggage:
            frame = check_unattended_bags(frame, results.boxes, cam_id)

        _last_person_count[cam_id] = person_count

        # Fire/smoke only on YOLO frames (expensive) — cam1 only
        if do_fire:
            fire, smoke = detect_fire_smoke(frame)
            _last_fire_smoke[cam_id] = (fire, smoke)
            frame = draw_fire_smoke(frame, fire, smoke)
            if fire:
                push_alert(CAM_NAMES.get(cam_id, cam_id), "FIRE", "Fire detected")
            if smoke:
                push_alert(CAM_NAMES.get(cam_id, cam_id), "SMOKE", "Smoke detected")

    else:
        # ── Non-YOLO frames: redraw cached boxes cheaply ─────────────────
        boxes = _last_boxes.get(cam_id)
        if boxes is not None:
            for box in boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                lname = model.names[int(box.cls[0])]
                tid   = int(box.id[0]) if box.id is not None else -1
                if lname == "person":
                    trk_id = yolo_to_trk.get((cam_id, tid))
                    intrusion = (cam_id in ("cam1", "cam2") and
                                 cv2.pointPolygonTest(
                                     TRACK_POLYGON,
                                     (int((x1+x2)/2), y2), False) >= 0)
                    color = (0, 0, 255) if intrusion else (255, 200, 0)
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                    cv2.putText(frame, trk_id or "",
                                (x1, y1 - 8), cv2.FONT_HERSHEY_SIMPLEX,
                                0.42, color, 1)
                elif lname in ["backpack", "suitcase", "handbag"] and do_baggage:
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 165, 255), 2)

        # Redraw last fire/smoke text if any
        if do_fire:
            fs = _last_fire_smoke.get(cam_id, (False, False))
            frame = draw_fire_smoke(frame, *fs)

    # Crowd counter (cheap, every frame from cached count)
    if do_crowd:
        frame = check_crowd(_last_person_count.get(cam_id, 0), cam_id, frame)

    # Watermark
    cv2.putText(frame, f"{CAM_NAMES.get(cam_id, cam_id)} | RAILGUARD AI",
                (8, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 220, 220), 1)
    return frame

# ==========================================
# 10. STREAM GENERATORS
# ==========================================

def _mjpeg(frame: np.ndarray) -> bytes:
    _, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
    return b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buf.tobytes() + b'\r\n'

def placeholder(cam_id: str):
    while True:
        f = np.zeros((360, 640, 3), dtype=np.uint8)
        cv2.putText(f, f"{cam_id.upper()}: NO SIGNAL / LOADING",
                    (90, 180), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (70, 70, 70), 2)
        yield _mjpeg(f)
        time.sleep(0.8)

def webcam_stream():
    """Camera 1 — local webcam, YOLO every 3rd frame."""
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 360)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)   # ← minimize buffer lag
    fc = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            yield from placeholder("cam1")
            return
        fc += 1
        frame = annotate_frame(frame, "cam1", fc, YOLO_INTERVAL_WEBCAM)
        yield _mjpeg(frame)

def yt_stream(cam_id: str):
    """YouTube stream, YOLO every 5th frame."""
    url = YT_SOURCES.get(cam_id)
    if not url:
        yield from placeholder(cam_id)
        return
    try:
        stream = CamGear(
            source=url,
            stream_mode=True,
            logging=False,
            **{"STREAM_RESOLUTION": "360p"}   # ← lower res = faster
        ).start()
    except Exception as e:
        print(f"CamGear {cam_id}: {e}")
        yield from placeholder(cam_id)
        return
    fc = 0
    while True:
        frame = stream.read()
        if frame is None:
            time.sleep(0.04)
            continue
        frame = cv2.resize(frame, (640, 360))
        fc += 1
        frame = annotate_frame(frame, cam_id, fc, YOLO_INTERVAL_STREAM)
        yield _mjpeg(frame)

# ==========================================
# 11. VIDEO ENDPOINTS
# ==========================================

@app.get("/video/cam1")
def v1(): return StreamingResponse(webcam_stream(),
                                    media_type="multipart/x-mixed-replace; boundary=frame")
@app.get("/video/cam2")
def v2(): return StreamingResponse(yt_stream("cam2"),
                                    media_type="multipart/x-mixed-replace; boundary=frame")
@app.get("/video/cam3")
def v3(): return StreamingResponse(yt_stream("cam3"),
                                    media_type="multipart/x-mixed-replace; boundary=frame")
@app.get("/video/cam4")
def v4(): return StreamingResponse(yt_stream("cam4"),
                                    media_type="multipart/x-mixed-replace; boundary=frame")
@app.get("/video/cam5")
def v5(): return StreamingResponse(yt_stream("cam5"),
                                    media_type="multipart/x-mixed-replace; boundary=frame")
@app.get("/video/cam6")
def v6(): return StreamingResponse(yt_stream("cam6"),
                                    media_type="multipart/x-mixed-replace; boundary=frame")

# ==========================================
# 12. DATA ENDPOINTS
# ==========================================

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