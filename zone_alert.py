import time, threading, json, cv2, numpy as np
from fastapi import FastAPI, Response, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from ultralytics import YOLO

app = FastAPI()
model = YOLO("yolov8n.pt")  # or yolov8n-seg
last_frame = None
lock = threading.Lock()

CONNECTIONS = []
ALERTS = []
ZONE_POLY = np.array([(100,400),(540,400),(640,480),(0,480)])  # adjust to your scene
TRACK_ZONE_NAME = "track_zone"

def broadcast_alert(payload):
    bad=[]
    for ws in CONNECTIONS:
        try:
            ws.send_text(json.dumps(payload))
        except Exception:
            bad.append(ws)
    for ws in bad:
        CONNECTIONS.remove(ws)

def add_alert(atype, detail):
    alert={"type":atype,"ts":time.time(),"detail":detail}
    ALERTS.append(alert)
    if len(ALERTS)>200: ALERTS.pop(0)
    broadcast_alert(alert)

def point_in_poly(x,y,poly):
    return cv2.pointPolygonTest(poly,(x,y),False) >= 0

def process_frame(frame):
    global last_frame
    h,w = frame.shape[:2]
    dets = model(frame)[0]
    for box in dets.boxes:
        conf=float(box.conf.cpu().item())
        clsid=int(box.cls.cpu().item())
        clsname=model.names[clsid]
        if clsname != "person" or conf < 0.3: continue
        x1,y1,x2,y2 = map(int, box.xyxy.cpu().numpy().tolist())
        cx,cy = (x1+x2)//2,(y1+y2)//2
        if point_in_poly(cx,cy,ZONE_POLY):
            add_alert("person_on_track", {
                "cls":clsname, "conf":round(conf,2), 
                "box":[x1,y1,x2,y2], "center":[cx,cy]
            })
            cv2.putText(frame, "ON TRACK", (x1,y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,0,255),2)
        cv2.rectangle(frame,(x1,y1),(x2,y2),(0,255,0),2)
    cv2.polylines(frame,[ZONE_POLY],isClosed=True,color=(0,0,255),thickness=3)
    with lock:
        last_frame=frame
    return frame

def mjpeg_generator():
    cap=cv2.VideoCapture(0)
    if not cap.isOpened(): raise RuntimeError("camera not available")
    while True:
        ret,frame=cap.read()
        if not ret: break
        out=process_frame(frame)
        _,jpg=cv2.imencode(".jpg",out)
        yield (b"--frame\r\nContent-Type:image/jpeg\r\n\r\n"+jpg.tobytes()+b"\r\n")
    cap.release()

@app.get("/video_feed")
def video_feed():
    return StreamingResponse(mjpeg_generator(), media_type="multipart/x-mixed-replace; boundary=frame")

@app.get("/alerts")
def get_alerts():
    return {"alerts":ALERTS[-50:]}

@app.websocket("/ws/alerts")
async def ws_alert(ws: WebSocket):
    await ws.accept()
    CONNECTIONS.append(ws)
    try:
        await ws.send_text(json.dumps({"type":"connected","ts":time.time()}))
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        CONNECTIONS.remove(ws)
    except:
        if ws in CONNECTIONS: CONNECTIONS.remove(ws)

@app.get("/latest_frame")
def latest_frame():
    with lock:
        if last_frame is None:
            return Response(status_code=404)
        _,jpg=cv2.imencode(".jpg",last_frame)
    return Response(content=jpg.tobytes(), media_type="image/jpeg")

if __name__=="__main__":
    import uvicorn
    uvicorn.run("zone_alert:app", host="0.0.0.0", port=8000, reload=False)