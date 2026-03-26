import time, threading, json, cv2, numpy as np
from fastapi import FastAPI, Response, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from ultralytics import YOLO
from deep_sort_realtime.deepsort_tracker import DeepSort
from typing import List, Dict, Any
from pydantic import BaseModel

app = FastAPI()
model = YOLO("yolov8n.pt")
tracker = DeepSort(max_age=30, n_init=3, max_cosine_distance=0.25)

ALERTS: List[Dict[str, Any]] = []
CONNECTIONS: List[WebSocket] = []
last_frame = None
lock = threading.Lock()

UNATTENDED_INTERVAL = 15        # seconds before baggage declared unattended
MIN_BAG_AREA = 0.05             # relative area threshold for "bag"

# fixation: object_id -> last_seen_time, first_seen_time, class_name, last_position
object_state: Dict[int, Dict[str, Any]] = {}

def is_baggage_class(cls):
    return cls in ["backpack", "handbag", "suitcase"]  # YOLO names

def broadcast_alert(payload):
    stale = []
    for ws in CONNECTIONS:
        try:
            threading.Thread(target=lambda w,s: w.send_text(json.dumps(s)), args=(ws,payload)).start()
        except Exception:
            stale.append(ws)
    for ws in stale:
        CONNECTIONS.remove(ws)

def generate_alert(event_type, details):
    alert = {
        "type": event_type,
        "ts": time.time(),
        "details": details,
    }
    ALERTS.append(alert)
    if len(ALERTS) > 100: ALERTS.pop(0)
    broadcast_alert(alert)

def process_frame(frame):
    global object_state
    h,w = frame.shape[:2]
    detections = model(frame)[0]
    det_boxes=[]
    for box in detections.boxes:
        clsid = int(box.cls.cpu().item())
        clsname = model.names[clsid]
        if not is_baggage_class(clsname): continue
        x1,y1,x2,y2 = map(int, box.xyxy.cpu().numpy().tolist())
        score = float(box.conf.cpu().item())
        area = ((x2-x1)*(y2-y1))/(w*h)
        if area < MIN_BAG_AREA: continue
        det_boxes.append(([x1,y1,x2-x1,y2-y1], score, clsname))
    tracks = tracker.update_tracks(det_boxes, frame=frame)
    now = time.time()

    for tr in tracks:
        if not tr.is_confirmed(): continue
        tid = tr.track_id
        lbox = tr.to_ltrb()
        cx = (lbox[0]+lbox[2])//2
        cy = (lbox[1]+lbox[3])//2
        if tid not in object_state:
            object_state[tid] = {
                "first_positive": now,
                "last_positive": now,
                "class": tr.get_det_class(),
                "last_pos": (cx,cy),
                "alerted": False,
            }
        else:
            dx = abs(cx - object_state[tid]["last_pos"][0])
            dy = abs(cy - object_state[tid]["last_pos"][1])
            object_state[tid]["last_pos"] = (cx,cy)
            object_state[tid]["last_positive"] = now

            # if object stays near same place for 15 seconds yet still tracked
            duration = now - object_state[tid]["first_positive"]
            moved_dist = np.sqrt(dx*dx + dy*dy)
            if duration > UNATTENDED_INTERVAL and moved_dist < 20 and not object_state[tid]["alerted"]:
                object_state[tid]["alerted"] = True
                generate_alert("unattended_baggage", {
                    "track_id": tid,
                    "class": object_state[tid]["class"],
                    "duration_s": int(duration),
                    "box": [int(v) for v in lbox],
                })

        # draw in frame
        cv2.rectangle(frame, (int(lbox[0]), int(lbox[1])), (int(lbox[2]), int(lbox[3])), (0,200,255), 2)
        cv2.putText(frame, f"{tr.track_id}:{tr.get_det_class()}", (int(lbox[0]), int(lbox[1]-10)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255),1)

    # cleanup stale tracks
    stale = [tid for tid,v in object_state.items() if now - v["last_positive"] > 30]
    for tid in stale: object_state.pop(tid, None)
    return frame

def mjpeg_generator():
    global last_frame
    capture = cv2.VideoCapture(0)
    if not capture.isOpened():
        raise RuntimeError("Camera not available")
    while True:
        ret, frame = capture.read()
        if not ret: break
        out = process_frame(frame)
        with lock:
            last_frame = out
        _, jpg = cv2.imencode(".jpg", out)
        yield (b"--frame\r\n"
               b"Content-Type: image/jpeg\r\n\r\n" + jpg.tobytes() + b"\r\n")
    capture.release()

@app.get("/video_feed")
def video_feed():
    return StreamingResponse(mjpeg_generator(), media_type="multipart/x-mixed-replace; boundary=frame")

@app.get("/latest_frame")
def latest_frame():
    with lock:
        if last_frame is None:
            raise RuntimeError("no frame yet")
        _, jpg = cv2.imencode(".jpg", last_frame)
        return Response(content=jpg.tobytes(), media_type="image/jpeg")

@app.get("/alerts")
def list_alerts():
    return {"alerts": ALERTS[-50:]}

@app.websocket("/ws/alerts")
async def websocket_alerts(ws: WebSocket):
    await ws.accept()
    CONNECTIONS.append(ws)
    try:
        await ws.send_text(json.dumps({"type":"ready","ts":time.time()}))
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        CONNECTIONS.remove(ws)
    except Exception:
        CONNECTIONS.remove(ws)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("unattended:app", host="0.0.0.0", port=8000, reload=False)