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

class SurveillancePipeline:
    def __init__(self):
        print("\n=======================================================")
        print("🚀 INITIALIZING MASTER INTELLIGENCE PIPELINE (V2) ")
        print("=======================================================")
        self.yolo = ZeroShotDetector()
        self.reid = ReIDTracker(threshold=0.72, epsilon=0.1)
        self.zone_detector = ZoneIntrusionDetector()
        
        self._fps_buffer = []
        self.current_fps = 0
        self.last_run_time = time.time()
        print("✅ Pipeline Core Loaded Successfully.\n")

    def run(self, frame, camera_id="default"):
        """
        Executes a single end-to-end inference pass.
        Returns:
            annotated_frame (np.ndarray): For live MJPEG streaming
            alerts (list): High-priority threat dictionaries
            trajectories (dict): UUID to spatial path mappings
        """
        # 0. Apply Extreme Optical Blur / Smoke Lens Corruption (Hackathon Demo Requirement)
        frame = cv2.GaussianBlur(frame, (99, 99), 15)
        annotated_frame = frame.copy()
        cv2.putText(annotated_frame, "[SIMULATED SENSOR CORRUPTION : HEAVY BLUR]", (10, 60), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        
        alerts = []
        
        # 1. Zero-Shot Vision Inference (Evaluating on heavily corrupted pixels)
        detections = self.yolo.detect(frame, conf_threshold=0.10)
        
        # 2. Resolve Detections & Cascade into Secondary Networks
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
                    is_intrusion = self.zone_detector.check_intrusion(box)
                    
                    if is_intrusion:
                        # Critical tactical escalation
                        base_severity = "critical"
                        alert_type = "PERSON ON TRACK (REID MATCHED)"
                    else:
                        alert_type = "ReID_Track"

                    alerts.append({
                        "type": alert_type,
                        "uuid": uuid,
                        "severity": base_severity,
                        "camera": camera_id,
                        "path": trajectory,
                        "confidence": round(conf, 2),
                        "alert": is_intrusion,
                        "ts": time.time()
                    })
                    
                    # Target Annotation
                    color = (0, 0, 255) if base_severity == "critical" else (255, 165, 0)
                    cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)
                    
                    # HUD Display for ReID Tracking
                    tag = f"ID:{uuid}" + (" [INTRUDER]" if is_intrusion else "")
                    cv2.putText(annotated_frame, tag, (x1, y1 - 10), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            else:
                # --- STAGE 2: Environmental Hazards & General Prompts ---
                alerts.append({
                    "type": cls_name.upper(),
                    "severity": base_severity,
                    "camera": camera_id,
                    "confidence": round(conf, 2),
                    "ts": time.time()
                })
                
                color = (0, 0, 255) if base_severity == "critical" else (0, 255, 255)
                cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)
                cv2.putText(annotated_frame, cls_name, (x1, y2 + 20), 
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
