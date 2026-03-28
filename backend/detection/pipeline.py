"""
Unified Next-Gen Surveillance Pipeline
Integrates YOLO-World Foundation Vision via Zero-Shot text prompting
with OSNet cross-camera Re-Identification (ReID) and Differential Privacy.
Supports Hybrid Inference: Remote GPU Bridge (Colab) + Local Fallback.
"""
import time
import cv2
from detection.zone_alert import ZoneIntrusionDetector
from detection.yolo_world import ZeroShotDetector
from detection.reid import ReIDTracker
from detection.temporal_filter import TemporalFilter
from detection.preprocessor import preprocessor

try:
    from core.remote_client import remote_client
    _REMOTE_AVAILABLE = True
except ImportError:
    _REMOTE_AVAILABLE = False
    remote_client = None

class SurveillancePipeline:
    def __init__(self):
        print("\n=======================================================")
        print("  INITIALIZING MASTER INTELLIGENCE PIPELINE (V2)")
        print("=======================================================")
        self.yolo = ZeroShotDetector()
        self.reid = ReIDTracker(threshold=0.72, epsilon=0.1)
        self.zone_detector = ZoneIntrusionDetector()
        self.temp_filter = TemporalFilter(min_hits=5, max_age=15)
        self.remote_client = remote_client if _REMOTE_AVAILABLE else None
        
        self._fps_buffer = []
        self.current_fps = 0
        self.last_run_time = time.time()
        
        self.rolling_confidence = 0.942
        self.heatmap_grid = [[0.0]*20 for _ in range(20)]
        self.inference_source = "local"  # "local" or "remote"
        print("[OK] Pipeline Core Loaded Successfully.")
        print("[Pipeline] AdverseConditionPreprocessor Initialized")
        if self.remote_client and self.remote_client.mode == "remote":
            print("[Pipeline] Hybrid Inference ENABLED (Remote GPU Bridge)\n")
        else:
            print("[Pipeline] Local Inference Mode\n")

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
        
        # 1. Hybrid Inference: Try Remote GPU first, fall back to local
        detections = None
        if self.remote_client and self.remote_client.is_connected:
            detections = self.remote_client.detect_remote(frame_enhanced, condition=condition)
            if detections is not None:
                self.inference_source = "remote"
        
        if detections is None:
            # Local YOLO-World fallback
            detections = self.yolo.detect(frame_enhanced, condition=condition)
            self.inference_source = "local"
        
        if detections:
            avg_conf = sum(d["confidence"] for d in detections) / len(detections)
            self.rolling_confidence = (self.rolling_confidence * 0.95) + (avg_conf * 0.05)
            
        h, w = frame.shape[:2]
        for i in range(20):
            for j in range(20):
                self.heatmap_grid[i][j] *= 0.98  # slower decay for stability
        
        # 2. Resolve Detections & Cascade into Secondary Networks
        current_active_ids = []
        raw_alerts = []
        
        for det in detections:
            cls_name = det["class_name"]
            box = det["box"]
            conf = det["confidence"]
            base_severity = det["severity"]
            x1, y1, x2, y2 = box
            
            if cls_name == "person":
                cx, cy = (x1+x2)/2, (y1+y2)/2
                grid_x = min(int((cx/w)*20), 19)
                grid_y = min(int((cy/h)*20), 19)
                self.heatmap_grid[grid_y][grid_x] = min(self.heatmap_grid[grid_y][grid_x] + 1.0, 10.0)
            
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
        
        src_tag = "GPU" if self.inference_source == "remote" else "CPU"
        cv2.putText(annotated_frame, f"SYS V2 FPS: {self.current_fps} [{src_tag}]", (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        # Retrieve global cross-camera paths mapping
        all_trajectories = {k: v["path"] for k, v in self.reid.gallery.items()}

        return annotated_frame, alerts, all_trajectories

# Global Singleton instantiation for FastAPI access
pipeline = SurveillancePipeline()
