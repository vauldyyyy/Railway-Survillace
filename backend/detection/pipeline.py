"""
Unified Next-Gen Surveillance Pipeline
Integrates YOLO-World Foundation Vision via Zero-Shot text prompting
with OSNet cross-camera Re-Identification (ReID) and Differential Privacy.
"""
import time
import cv2
from detection.zone_alert import ZoneIntrusionDetector
from detection.yolo_world import ZeroShotDetector
from detection.reid import ReIDTracker
from detection.temporal_filter import TemporalFilter
from detection.preprocessor import preprocessor

class SurveillancePipeline:
    def __init__(self):
        print("\n=======================================================")
        print("🚀 INITIALIZING MASTER INTELLIGENCE PIPELINE (V2) ")
        print("=======================================================")
        self.yolo = ZeroShotDetector()
        self.reid = ReIDTracker(threshold=0.72, epsilon=0.1)
        self.zone_detector = ZoneIntrusionDetector()
        self.temp_filter = TemporalFilter(min_hits=5, max_age=15)
        
        self._fps_buffer = []
        self.current_fps = 0
        self.last_run_time = time.time()
        print("✅ Pipeline Core Loaded Successfully.")
        print("[Pipeline] ✓ AdverseConditionPreprocessor Initialized\n")

    def run(self, frame, camera_id="default"):
        """
        Executes a single end-to-end inference pass.
        Returns:
            annotated_frame (np.ndarray): For live MJPEG streaming
            alerts (list): High-priority threat dictionaries
            trajectories (dict): UUID to spatial path mappings
        """
        # Start with a clean copy of the frame for annotation
        annotated_frame = frame.copy()
        
        alerts = []
        raw_alerts = []
        
        # 0. Adverse Condition Preprocessing (Dehazing / Low-light enhancement)
        frame_enhanced, condition = preprocessor.process(frame)
        if condition != "normal":
            print(f"[Pipeline] Adverse Condition Detected: {condition.upper()}")
        
        # 1. Zero-Shot Vision Inference (Using enhanced frame + dynamic thresholds)
        detections = self.yolo.detect(frame_enhanced, condition=condition)
        
        # 2. Resolve Detections & Cascade into Secondary Networks
        current_active_ids = []
        raw_alerts = []
        
        for det in detections:
            cls_name = det["class_name"]
            box = det["box"]
            conf = det["confidence"]
            base_severity = det["severity"]
            x1, y1, x2, y2 = box
            
            # --- STAGE 2: OSNet Re-Identification (Persons Only) ---
            if cls_name == "person":
                uuid, trajectory = self.reid.update(frame, box, camera_id)
                if uuid:
                    current_active_ids.append(uuid)
                    is_intrusion = self.zone_detector.check_intrusion(box)
                    
                    if is_intrusion:
                        base_severity = "critical"
                        alert_type = "PERSON ON TRACK (REID MATCHED)"
                    else:
                        alert_type = "ReID_Track"

                    raw_alerts.append({
                        "type": alert_type,
                        "uuid": uuid,
                        "severity": base_severity,
                        "camera": camera_id,
                        "path": trajectory,
                        "confidence": round(conf, 2),
                        "alert": is_intrusion,
                        "ts": time.time(),
                        "box": box
                    })
            else:
                # For non-person objects, use class-based temporal filtering
                obj_id = f"{cls_name}_{camera_id}_raw" 
                current_active_ids.append(obj_id)
                
                raw_alerts.append({
                    "type": cls_name.upper(),
                    "uuid": obj_id,
                    "severity": base_severity,
                    "camera": camera_id,
                    "confidence": round(conf, 2),
                    "ts": time.time(),
                    "box": box
                })

        # 3. Apply Temporal Filtering (Hardening Layer)
        confirmed_ids = self.temp_filter.update(current_active_ids)
        
        for alert in raw_alerts:
            if alert["uuid"] in confirmed_ids:
                alerts.append(alert)
                
                # Annotate confirmed alerts only
                x1, y1, x2, y2 = alert["box"]
                severity = alert["severity"]
                color = (0, 0, 255) if severity == "critical" else (255, 165, 0)
                
                if "uuid" in alert and "person" in alert["type"].lower() or "reid" in alert["type"].lower():
                    #HUD for Persons
                    tag = f"ID:{alert['uuid']}" + (" [INTRUDER]" if alert.get("alert") else "")
                    cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)
                    cv2.putText(annotated_frame, tag, (x1, y1 - 10), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                else:
                    #HUD for Generic Objects (Fire, Stone etc)
                    color = (0, 0, 255) if severity == "critical" else (0, 255, 255)
                    cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)
                    cv2.putText(annotated_frame, alert["type"], (x1, y2 + 20), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        # Calculate Latency / FPS via Sliding Buffer
        now = time.time()
        self._fps_buffer.append(now)
        self._fps_buffer = [t for t in self._fps_buffer if now - t < 2.0]  # 2s window
        self.current_fps = len(self._fps_buffer) // 2  # Average over 2s
        
        cv2.putText(annotated_frame, f"SYS V2 FPS: {self.current_fps}", (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        # Retrieve global cross-camera paths mapping
        all_trajectories = {k: v["path"] for k, v in self.reid.gallery.items()}

        return annotated_frame, alerts, all_trajectories

# Global Singleton instantiation for FastAPI access
pipeline = SurveillancePipeline()
