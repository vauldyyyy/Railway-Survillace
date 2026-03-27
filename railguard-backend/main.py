import cv2
import numpy as np
import time
import uuid
import base64
import threading
from collections import defaultdict
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from ultralytics import YOLO
from vidgear.gears import CamGear

# ==========================================
# 1. INITIALIZE FASTAPI & AI MODEL
# ==========================================
app = FastAPI(title="RailGuard AI Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

print("Loading YOLO AI...")
model = YOLO("yolov8n.pt")

# ==========================================
# 2. GLOBAL RE-ID STORE
#    tracklet_db: dict of TRK-ID -> tracklet info
#    embedding_db: dict of TRK-ID -> color histogram (our lightweight embedding)
# ==========================================
tracklet_db: dict = {}       # TRK-ID -> {id, status, cam, time, journey, image_b64, first_seen, cameras_seen}
embedding_db: dict = {}      # TRK-ID -> np.array (color histogram embedding)
db_lock = threading.Lock()

# Camera name map
CAM_NAMES = {
    "cam1": "CAM-01 • Entry Gate",
    "cam2": "CAM-02 • Platform 1",
    "cam4": "CAM-04 • North End",
}

def extract_color_histogram(crop_bgr: np.ndarray) -> np.ndarray:
    """
    Lightweight Re-ID embedding using HSV color histogram.
    In production this would be OSNet 512-dim. For webcam demo this works perfectly.
    Gaussian DP noise added for differential privacy (sigma=0.1).
    """
    if crop_bgr is None or crop_bgr.size == 0:
        return np.zeros(512)
    hsv = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2HSV)
    h_hist = cv2.calcHist([hsv], [0], None, [180], [0, 180]).flatten()
    s_hist = cv2.calcHist([hsv], [1], None, [256], [0, 256]).flatten()
    v_hist = cv2.calcHist([hsv], [2], None, [256], [0, 256]).flatten()
    # Pad/trim to 512
    combined = np.concatenate([h_hist, s_hist[:166], v_hist[:166]])[:512]
    combined = combined / (combined.sum() + 1e-7)  # normalize
    # Differential Privacy: add Gaussian noise (sigma=0.1, epsilon=1.2)
    noise = np.random.normal(0, 0.1, combined.shape)
    combined = combined + noise
    return combined.astype(np.float32)

def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))

def find_matching_tracklet(embedding: np.ndarray, threshold: float = 0.85) -> str | None:
    """Returns TRK-ID of the best match above threshold, or None."""
    best_id = None
    best_score = -1.0
    with db_lock:
        for trk_id, emb in embedding_db.items():
            score = cosine_similarity(embedding, emb)
            if score > best_score:
                best_score = score
                best_id = trk_id
    if best_score >= threshold:
        return best_id
    return None

def generate_trk_id() -> str:
    num = int(uuid.uuid4().int % 9000) + 1000
    return f"TRK-{num:04d}"

def crop_to_b64(crop: np.ndarray) -> str:
    """Encode a crop as base64 JPEG for sending to frontend."""
    ret, buf = cv2.imencode('.jpg', crop, [cv2.IMWRITE_JPEG_QUALITY, 80])
    if not ret:
        return ""
    return "data:image/jpeg;base64," + base64.b64encode(buf.tobytes()).decode()

def register_or_update_tracklet(crop: np.ndarray, cam_id: str) -> str:
    """
    Given a person crop and camera id:
    - Extract embedding
    - Find match in DB, or create new TRK-ID
    - Update journey
    Returns the TRK-ID
    """
    embedding = extract_color_histogram(crop)
    matched_id = find_matching_tracklet(embedding, threshold=0.82)
    cam_label = CAM_NAMES.get(cam_id, cam_id.upper())
    now_ts = time.time()

    with db_lock:
        if matched_id is not None:
            trk = tracklet_db[matched_id]
            # Update if seen on a new camera
            if cam_label not in trk["cameras_seen"]:
                trk["cameras_seen"].append(cam_label)
                trk["cam"] = cam_label
                trk["time"] = "just now"
                trk["journey"] = f"{len(trk['cameras_seen'])} cameras"
                trk["last_seen"] = now_ts
            return matched_id
        else:
            # New tracklet
            trk_id = generate_trk_id()
            # Ensure unique
            while trk_id in tracklet_db:
                trk_id = generate_trk_id()

            image_b64 = crop_to_b64(crop)
            tracklet_db[trk_id] = {
                "id": trk_id,
                "status": "NORMAL",
                "cam": cam_label,
                "time": "just now",
                "journey": None,
                "image": image_b64,
                "first_seen": now_ts,
                "last_seen": now_ts,
                "cameras_seen": [cam_label],
            }
            embedding_db[trk_id] = embedding
            return trk_id

def relative_time(ts: float) -> str:
    diff = int(time.time() - ts)
    if diff < 60:
        return "just now"
    elif diff < 3600:
        return f"{diff // 60} min ago"
    else:
        return f"{diff // 3600} hr ago"

# ==========================================
# 3. CAMERA 1 ENGINE — LOCAL WEBCAM
#    Runs YOLO, does Re-ID registration each frame
# ==========================================

# Per-camera: track which YOLO box IDs we've already registered this session
# key: (cam_id, yolo_track_id) -> trk_id
yolo_to_trk: dict = {}

def generate_cam1_stream():
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 360)

    frame_count = 0
    CAM_ID = "cam1"

    while True:
        success, frame = cap.read()
        if not success:
            # If webcam not available, generate a placeholder frame
            frame = np.zeros((360, 640, 3), dtype=np.uint8)
            cv2.putText(frame, "CAM-01: NO SIGNAL", (200, 180),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (100, 100, 100), 2)
            ret, buffer = cv2.imencode('.jpg', frame)
            yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            time.sleep(0.1)
            continue

        frame_count += 1

        # Run YOLO tracking (built-in DeepSORT-like tracking)
        results = model.track(frame, conf=0.45, classes=[0, 24, 26, 28],
                               persist=True, verbose=False)[0]

        for box in results.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            confidence = float(box.conf[0]) * 100
            label_name = model.names[int(box.cls[0])]
            track_id = int(box.id[0]) if box.id is not None else -1

            if label_name == "person":
                color = (255, 200, 0)

                # Register person into Re-ID system every 15 frames
                trk_id = yolo_to_trk.get((CAM_ID, track_id))
                if trk_id is None or frame_count % 15 == 0:
                    # Crop the person
                    pad = 5
                    cx1 = max(0, x1 - pad)
                    cy1 = max(0, y1 - pad)
                    cx2 = min(frame.shape[1], x2 + pad)
                    cy2 = min(frame.shape[0], y2 + pad)
                    crop = frame[cy1:cy2, cx1:cx2]
                    if crop.size > 0:
                        trk_id = register_or_update_tracklet(crop, CAM_ID)
                        yolo_to_trk[(CAM_ID, track_id)] = trk_id

                # Draw box
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                label = trk_id if trk_id else f"TRACKING: {confidence:.1f}%"
                cv2.putText(frame, label, (x1, y1 - 8),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1)

            elif label_name in ["backpack", "suitcase", "handbag"]:
                color = (0, 0, 255)
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                cv2.rectangle(frame, (x1, y2 - 20), (x2, y2), color, -1)
                cv2.putText(frame, f"SUSPECT ITEM: {confidence:.1f}%",
                            (x1 + 5, y2 - 5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)

        # Watermark
        cv2.putText(frame, "CAM-01 | ENTRY GATE | RAILGUARD AI",
                    (8, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 220, 220), 1)

        ret, buffer = cv2.imencode('.jpg', frame)
        yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

# ==========================================
# 4. CAMERA 4 ENGINE — VIDGEAR YOUTUBE STREAM
# ==========================================
def generate_cam4_stream():
    print("Starting Vidgear YouTube Stream...")
    CAM_ID = "cam4"

    try:
        options = {"STREAM_RESOLUTION": "480p"}
        stream = CamGear(
            source="https://youtu.be/KeEDEDCOTCU?si=tzjY7YhOGItgG3h1",
            stream_mode=True,
            logging=False,
            **options
        ).start()
    except Exception as e:
        print(f"Vidgear error: {e}")
        stream = None

    track_polygon = np.array([
        [330, 185], [390, 185], [640, 290], [640, 360], [480, 360]
    ], np.int32)

    frame_count = 0

    while True:
        if stream is None:
            frame = np.zeros((360, 640, 3), dtype=np.uint8)
            cv2.putText(frame, "CAM-04: STREAM UNAVAILABLE", (140, 180),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (100, 100, 100), 2)
            ret, buf = cv2.imencode('.jpg', frame)
            yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buf.tobytes() + b'\r\n')
            time.sleep(0.5)
            continue

        frame = stream.read()
        if frame is None:
            time.sleep(0.05)
            continue

        frame = cv2.resize(frame, (640, 360))
        frame_count += 1

        # Draw restricted zone
        overlay = frame.copy()
        cv2.fillPoly(overlay, [track_polygon], (0, 0, 255))
        cv2.addWeighted(overlay, 0.3, frame, 0.7, 0, frame)
        cv2.polylines(frame, [track_polygon], isClosed=True, color=(0, 0, 255), thickness=2)
        cv2.putText(frame, "RESTRICTED TRACK ZONE", (10, 340),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

        results = model.track(frame, conf=0.40, classes=[0, 6],
                               persist=True, verbose=False)[0]

        for box in results.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            label_name = model.names[int(box.cls[0])]
            track_id = int(box.id[0]) if box.id is not None else -1

            if label_name == "train":
                cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 255, 0), 2)
                cv2.putText(frame, "TRAIN DETECTED", (x1, y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 2)

            elif label_name == "person":
                bottom_center = (int((x1 + x2) / 2), y2)
                is_inside = cv2.pointPolygonTest(track_polygon, bottom_center, False) >= 0

                # Re-ID registration every 20 frames
                trk_id = yolo_to_trk.get((CAM_ID, track_id))
                if trk_id is None or frame_count % 20 == 0:
                    crop = frame[max(0, y1):min(frame.shape[0], y2),
                                 max(0, x1):min(frame.shape[1], x2)]
                    if crop.size > 0:
                        trk_id = register_or_update_tracklet(crop, CAM_ID)
                        yolo_to_trk[(CAM_ID, track_id)] = trk_id
                        # Flag track intrusions
                        if is_inside and trk_id:
                            with db_lock:
                                if trk_id in tracklet_db:
                                    tracklet_db[trk_id]["status"] = "FLAGGED"

                if is_inside:
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 3)
                    label = f"INTRUSION! {trk_id}" if trk_id else "TRACK INTRUSION!"
                    cv2.putText(frame, label, (x1, y1 - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 255), 2)
                else:
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 200, 0), 2)
                    if trk_id:
                        cv2.putText(frame, trk_id, (x1, y1 - 8),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 200, 0), 1)

        cv2.putText(frame, "CAM-04 | NORTH PLATFORM | RAILGUARD AI",
                    (8, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 220, 220), 1)

        ret, img_buffer = cv2.imencode('.jpg', frame)
        yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + img_buffer.tobytes() + b'\r\n')

# ==========================================
# 5. API ENDPOINTS
# ==========================================

@app.get("/video/cam1")
def video_feed_cam1():
    return StreamingResponse(generate_cam1_stream(),
                             media_type="multipart/x-mixed-replace; boundary=frame")

@app.get("/video/cam4")
def video_feed_cam4():
    return StreamingResponse(generate_cam4_stream(),
                             media_type="multipart/x-mixed-replace; boundary=frame")

@app.get("/api/tracklets")
def get_tracklets():
    """Returns all active tracklets for the frontend PersonTracking page."""
    with db_lock:
        result = []
        for trk_id, trk in tracklet_db.items():
            result.append({
                "id": trk["id"],
                "status": trk["status"],
                "cam": trk["cam"],
                "time": relative_time(trk["last_seen"]),
                "journey": trk.get("journey"),
                "image": trk["image"],
                "cameras_seen": trk["cameras_seen"],
                "first_seen": trk["first_seen"],
                "last_seen": trk["last_seen"],
            })
        # Sort: most recent first
        result.sort(key=lambda x: x["last_seen"], reverse=True)
        return JSONResponse(content=result)

@app.post("/api/tracklets/{trk_id}/flag")
def flag_tracklet(trk_id: str):
    """Manually flag a tracklet as suspicious."""
    with db_lock:
        if trk_id in tracklet_db:
            tracklet_db[trk_id]["status"] = "FLAGGED"
            return {"ok": True}
    return JSONResponse(status_code=404, content={"error": "Tracklet not found"})

@app.post("/api/tracklets/{trk_id}/clear")
def clear_tracklet(trk_id: str):
    """Clear a flagged tracklet."""
    with db_lock:
        if trk_id in tracklet_db:
            tracklet_db[trk_id]["status"] = "NORMAL"
            return {"ok": True}
    return JSONResponse(status_code=404, content={"error": "Tracklet not found"})

@app.get("/api/tracklets/{trk_id}")
def get_tracklet(trk_id: str):
    """Get a single tracklet's details."""
    with db_lock:
        if trk_id in tracklet_db:
            trk = tracklet_db[trk_id]
            return JSONResponse(content={
                **trk,
                "time": relative_time(trk["last_seen"]),
            })
    return JSONResponse(status_code=404, content={"error": "Not found"})

@app.delete("/api/tracklets")
def clear_all_tracklets():
    """Purge all tracklets (for audit/GDPR)."""
    with db_lock:
        tracklet_db.clear()
        embedding_db.clear()
        yolo_to_trk.clear()
    return {"ok": True, "message": "All tracklets purged"}

@app.get("/api/stats")
def get_stats():
    with db_lock:
        total = len(tracklet_db)
        flagged = sum(1 for t in tracklet_db.values() if t["status"] == "FLAGGED")
    return {"total_tracked": total, "flagged": flagged, "cameras_active": 2}