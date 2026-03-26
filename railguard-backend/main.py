import cv2
import numpy as np
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
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
# 2. CAMERA 1 ENGINE (LOCAL WEBCAM)
# ==========================================
def generate_cam1_stream():
    cap = cv2.VideoCapture(0)
    cap.set(3, 640) 
    cap.set(4, 360)

    while True:
        success, frame = cap.read()
        if not success:
            break

        results = model(frame, conf=0.45, classes=[0, 24, 26, 28], verbose=False)[0]

        for box in results.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            confidence = float(box.conf[0]) * 100
            label_name = model.names[int(box.cls[0])]

            if label_name == "person":
                color = (255, 200, 0)
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                cv2.putText(frame, f"TRACKING: {confidence:.1f}%", (x1, y1 - 10), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
            
            elif label_name in ["backpack", "suitcase", "handbag"]:
                color = (0, 0, 255)
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                cv2.rectangle(frame, (x1, y2 - 20), (x2, y2), color, -1)
                cv2.putText(frame, f"SUSPECT ITEM: {confidence:.1f}%", (x1 + 5, y2 - 5), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)

        ret, buffer = cv2.imencode('.jpg', frame)
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

# ==========================================
# 3. CAMERA 4 ENGINE (VIDGEAR YOUTUBE STREAM)
# ==========================================
def generate_cam4_stream():
    print("📡 Starting Vidgear YouTube Stream...")
    
    options = {"STREAM_RESOLUTION": "720p"} 
    stream = CamGear(source="https://www.youtube.com/watch?v=X-ir2KfXMX0", stream_mode=True, logging=True, **options).start()
    
    # ---------------------------------------------------------
    # EXACT YELLOW TRACK MAPPING (AVOIDING PLATFORM ENTIRELY)
    # ---------------------------------------------------------
    track_polygon = np.array([
        [330, 185],  # 1. Top Left: Vanishing point, strictly off the platform edge
        [390, 185],  # 2. Top Right: Vanishing point, right side of rails
        [640, 290],  # 3. Middle Right: Where the outer track hits the right edge of the screen
        [640, 360],  # 4. Bottom Right Corner
        [480, 360]   # 5. Bottom Left: Pulled extremely far to the right, avoiding platform concrete
    ], np.int32)

    while True:
        frame = stream.read()
        
        if frame is None:
            continue
            
        frame = cv2.resize(frame, (640, 360))

        # Draw the transparent red track zone
        overlay = frame.copy()
        cv2.fillPoly(overlay, [track_polygon], (0, 0, 255))
        cv2.addWeighted(overlay, 0.3, frame, 0.7, 0, frame)
        cv2.polylines(frame, [track_polygon], isClosed=True, color=(0, 0, 255), thickness=2)
        cv2.putText(frame, "RESTRICTED TRACK ZONE", (10, 340), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

        # Look for people (0) and trains (6)
        results = model(frame, conf=0.40, classes=[0, 6], verbose=False)[0]

        for box in results.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            label_name = model.names[int(box.cls[0])]

            if label_name == "train":
                cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 255, 0), 2)
                cv2.putText(frame, "TRAIN DETECTED", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 2)

            elif label_name == "person":
                bottom_center = (int((x1 + x2) / 2), y2)
                is_inside = cv2.pointPolygonTest(track_polygon, bottom_center, False) >= 0

                if is_inside:
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 3)
                    cv2.putText(frame, "⚠️ TRACK INTRUSION!", (x1, y1 - 10), cv2.FONT_HERSHEY_DUPLEX, 0.6, (0, 0, 255), 2)
                else:
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 200, 0), 2)

        ret, img_buffer = cv2.imencode('.jpg', frame)
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + img_buffer.tobytes() + b'\r\n')

# ==========================================
# 4. API ENDPOINTS
# ==========================================
@app.get("/video/cam1")
def video_feed_cam1():
    return StreamingResponse(generate_cam1_stream(), media_type="multipart/x-mixed-replace; boundary=frame")

@app.get("/video/cam4")
def video_feed_cam4():
    return StreamingResponse(generate_cam4_stream(), media_type="multipart/x-mixed-replace; boundary=frame")