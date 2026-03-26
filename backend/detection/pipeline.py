"""
pipeline.py — Unified multi-model inference pipeline for RailGuard AI.
"""

import time
import cv2
import numpy as np
from pathlib import Path
from ultralytics import YOLO

from detection.unattended import UnattendedBaggageTracker
from detection.zone_alert import ZoneIntrusionDetector

# ── Paths ──
BACKEND_DIR = Path(__file__).resolve().parent.parent
MODEL_DIR   = BACKEND_DIR / "models"

# ── COCO class IDs for person/baggage ──
PERSON_CLS    = 0       # "person"
BAGGAGE_CLS   = [24, 26, 28]  # backpack, handbag, suitcase

# ── Thresholds ──
UNATTENDED_SECONDS  = 15       # seconds before baggage = unattended
PERSON_CONF_THRESH  = 0.4
BAGGAGE_CONF_THRESH = 0.35
RAILFOD_CONF_THRESH = 0.4
SSIM_TAMPER_THRESH  = 0.3      # if SSIM drops below this → camera tamper

class SurveillancePipeline:
    def __init__(self):
        print("[Pipeline] Loading models...")

        # 1. General COCO model (persons, bags)
        self.yolo_general = YOLO("yolov8n.pt")
        print("  ✓ General YOLO (COCO) loaded")

        # 2. RailFOD custom model (foreign objects on track)
        railfod_path = MODEL_DIR / "railfod_best.pt"
        if railfod_path.exists():
            self.yolo_railfod = YOLO(str(railfod_path))
            print("  ✓ RailFOD detector loaded")
        else:
            self.yolo_railfod = None
            print("  ⚠ RailFOD model not found — skipping (train it first)")

        # 3. UAV obstacle model
        uav_path = MODEL_DIR / "uav_best.pt"
        if uav_path.exists():
            self.yolo_uav = YOLO(str(uav_path))
            print("  ✓ UAV obstacle detector loaded")
        else:
            self.yolo_uav = None
            print("  ⚠ UAV model not found — skipping (train it first)")

        # 4. LSTM crowd predictor
        self.lstm = None
        self.scaler = None
        lstm_path   = MODEL_DIR / "lstm_crowd.h5"
        scaler_path = MODEL_DIR / "lstm_scaler.pkl"
        if lstm_path.exists() and scaler_path.exists():
            try:
                import tensorflow as tf
                import joblib
                self.lstm   = tf.keras.models.load_model(str(lstm_path))
                self.scaler = joblib.load(str(scaler_path))
                print("  ✓ LSTM crowd predictor loaded")
            except Exception as e:
                print(f"  ⚠ LSTM load failed: {e}")
        else:
            print("  ⚠ LSTM model not found — skipping (train it first)")

        # Sub-modules
        self.unattended_tracker = UnattendedBaggageTracker(threshold_seconds=UNATTENDED_SECONDS)
        self.zone_detector = ZoneIntrusionDetector()

        # State tracking
        self.prev_gray = None
        self.crowd_history = []

        print("[Pipeline] Ready.\n")

    def run(self, frame, camera_id="platform1"):
        alerts = []
        now = time.time()
        
        # 1. SSIM Camera Tamper Detection
        tamper_alert = self._check_tamper(frame)
        if tamper_alert:
            alerts.append(tamper_alert)
            
        # 2. General Output (COCO)
        general = self.yolo_general(frame, conf=0.4, verbose=False)[0]
        
        detections_for_tracker = []
        person_count = 0
        
        for box in general.boxes:
            conf = float(box.conf.cpu().item())
            cls_id = int(box.cls.cpu().item())
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
            w, h = x2 - x1, y2 - y1
            
            if cls_id == PERSON_CLS and conf >= PERSON_CONF_THRESH:
                detections_for_tracker.append(([x1, y1, w, h], conf, cls_id))
            elif cls_id in BAGGAGE_CLS and conf >= BAGGAGE_CONF_THRESH:
                detections_for_tracker.append(([x1, y1, w, h], conf, cls_id))

        # Update Unattended Baggage Tracker (DeepSORT)
        tracks, u_alerts = self.unattended_tracker.update(frame, detections_for_tracker, camera_id)
        for a in u_alerts:
            alerts.append(a)
            bx1, by1, bx2, by2 = a["details"]["box"]
            cv2.rectangle(frame, (bx1, by1), (bx2, by2), (0, 165, 255), 3)
            cv2.putText(frame, "UNATTENDED", (bx1, by1 - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 2)

        # Track Intrusion Detection (Zone)
        for track in tracks:
            if not track.is_confirmed() or track.time_since_update > 1:
                continue
            if track.det_class == PERSON_CLS:
                person_count += 1
                ltrb = track.to_ltrb() # x1, y1, x2, y2
                
                # Explaining Differential Privacy: Add subtle noise to embeddings to protect identity
                if track.features is not None and len(track.features) > 0:
                     embed = track.features[-1]
                     embed += np.random.normal(0, 0.05, embed.shape)
                     
                if self.zone_detector.check_intrusion(ltrb):
                    x1, y1, x2, y2 = [int(x) for x in ltrb]
                    alerts.append({
                        "type": "Person on Track",
                        "severity": "critical",
                        "camera": camera_id,
                        "details": {"box": [x1, y1, x2, y2]},
                        "ts": now
                    })
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 3)
                    cv2.putText(frame, "!! ON TRACK !!", (x1, y1 - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                else:
                    # Draw normal person bbox
                    x1, y1, x2, y2 = [int(x) for x in ltrb]
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 1)

        # 3. Foreign Object Detection (RailFOD)
        if self.yolo_railfod is not None:
            railfod = self.yolo_railfod(frame, conf=RAILFOD_CONF_THRESH, verbose=False)[0]
            for box in railfod.boxes:
                coords = box.xyxy[0].cpu().numpy().astype(int)
                cls_name = railfod.names[int(box.cls.cpu().item())]
                x1, y1, x2, y2 = coords
                alerts.append({
                    "type": "Foreign Object on Track",
                    "severity": "critical",
                    "camera": camera_id,
                    "details": {"class": cls_name},
                    "ts": now,
                })
                cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 255), 2)
                cv2.putText(frame, f"FOD: {cls_name}", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 255), 2)

        # Draw overlays
        self.zone_detector.draw(frame)
        
        # 4. Crowd prediction (LSTM)
        crowd_prediction = None
        if self.lstm is not None and self.scaler is not None:
            self.crowd_history.append(person_count)
            if len(self.crowd_history) >= 20: # Needs 20 time steps
                crowd_prediction = self._predict_crowd()
                if crowd_prediction and crowd_prediction > 85:
                     alerts.append({
                         "type": "Crowd Surge Expected",
                         "severity": "warning",
                         "camera": camera_id,
                         "details": {"predicted_count": crowd_prediction},
                         "ts": now
                     })

        return frame, alerts, {
            "person_count": person_count,
            "crowd_prediction": crowd_prediction,
        }

    def _check_tamper(self, frame):
        import skimage.metrics
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.resize(gray, (160, 120))  # downsample for speed

        if self.prev_gray is not None:
            score = skimage.metrics.structural_similarity(self.prev_gray, gray, data_range=255)
            if score < SSIM_TAMPER_THRESH:
                self.prev_gray = gray
                return {
                    "type": "Camera Tamper Detected",
                    "severity": "critical",
                    "camera": "unknown",
                    "details": {"ssim_score": round(score, 3)},
                    "ts": time.time(),
                }

        self.prev_gray = gray
        return None

    def _predict_crowd(self):
        try:
            recent = self.crowd_history[-20:]
            hour = time.localtime().tm_hour
            day  = time.localtime().tm_wday
            features = np.array([[hour, day, c, 3] for c in recent], dtype=np.float32)
            features_scaled = self.scaler.transform(features)
            pred = self.lstm.predict(features_scaled.reshape(1, 20, 4), verbose=0)
            
            dummy = np.zeros((1, 4))
            dummy[0, 2] = pred[0][0]
            result = self.scaler.inverse_transform(dummy)[0][2]
            return max(0, int(result))
        except Exception:
            return None

pipeline = SurveillancePipeline()
