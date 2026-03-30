"""
Unified Surveillance Pipeline V3.1 — Absolute Zero-Miss
=======================================================
Phase 5 Overhauls:
  - TTA integrated via YOLOWorld class
  - ReID hard-drop for horizontal humans disabled
  - ALWAYS DRAW: Raw detections are drawn transparently to prove vision
  - FALLEN PERSON LOGIC: Aspect Ratio > 1.3 + Track Zone + Motionless checks
"""
import time
import cv2
import numpy as np
from collections import deque

from detection.zone_alert import ZoneIntrusionDetector
from detection.yolo_world import ZeroShotDetector
from detection.reid import ReIDTracker
from detection.temporal_filter import TemporalFilter
from detection.unattended import UnattendedBaggageTracker
from detection.preprocessor import preprocessor
from detection.interpretation import ThreatEngine

try:
    from core.remote_client import remote_client
    _REMOTE_AVAILABLE = True
except ImportError:
    _REMOTE_AVAILABLE = False
    remote_client = None


INFERENCE_WIDTH = 800  # Resize for YOLO inference, keeps original for display

# ── Alert Type Normalization ──
# Maps all YOLO-World class variants to a single canonical alert type
# This prevents the same threat from flooding the dashboard under different names
_ALERT_CATEGORY = {
    "PERSON_ON_TRACK":          "PERSON_ON_TRACK",
    "PERSON_ON_RAILWAY_TRACK":  "PERSON_ON_TRACK",
    "HUMAN_ON_RAIL_TRACK":      "PERSON_ON_TRACK",
    "INTRUDER_ON_TRACK":        "PERSON_ON_TRACK",
    "PERSON_FALLEN_ON_TRACK":   "PERSON_FALLEN_ON_TRACK",
    "FALLEN_HUMAN_ON_TRACKS":   "PERSON_FALLEN_ON_TRACK",
    "PERSON_TRACKED":           "PERSON_TRACKED",
    "PERSON":                   "PERSON_TRACKED",
    "LUGGAGE":                  "BAGGAGE",
    "BACKPACK":                 "BAGGAGE",
    "SUITCASE":                 "BAGGAGE",
    "ABANDONED_SUITCASE":       "BAGGAGE",
    "UNATTENDED_BACKPACK":      "BAGGAGE",
    "UNATTENDED_BAG":           "BAGGAGE",
    "UNATTENDED_BAGGAGE":       "UNATTENDED_BAGGAGE",
    "ABANDONED_BAGGAGE":        "UNATTENDED_BAGGAGE",
    "FIRE":                     "FIRE",
    "FLAMES":                   "FIRE",
    "SMOKE":                    "SMOKE",
    "THICK_SMOKE":              "SMOKE",
    "METAL_DEBRIS_ON_TRACK":    "FOREIGN_OBJECT",
    "ANIMAL_ON_TRACK":          "ANIMAL_ON_TRACK",
    "CROWD_RISK":               "CROWD_RISK",
}

def _normalize_type(raw_type: str) -> str:
    """Map raw detection type to canonical alert category."""
    return _ALERT_CATEGORY.get(raw_type, raw_type)


class SurveillancePipeline:
    def __init__(self):
        print("\n=======================================================")
        print("  INITIALIZING MASTER INTELLIGENCE PIPELINE (V3.1)")
        print("  ZERO-MISS ENFORCEMENT & FALLEN PERSON LOGIC ACTIVE")
        print("=======================================================")
        self.yolo = ZeroShotDetector()
        self.reid = ReIDTracker(threshold=0.72, epsilon=0.1)
        self.zone_detector = ZoneIntrusionDetector()
        self.temp_filter = TemporalFilter(min_hits=3, max_age=8)
        self.baggage_tracker = UnattendedBaggageTracker(threshold_seconds=5)
        self.threat_engine = ThreatEngine()
        self.remote_client = remote_client if _REMOTE_AVAILABLE else None

        # FPS tracking — rolling window of last 30 frame timestamps
        self._fps_timestamps = deque(maxlen=30)
        self.current_fps = 0.0
        self.last_run_time = time.time()

        self.rolling_confidence = 0.0
        self.heatmap_grid = [[0.0] * 20 for _ in range(20)]
        self.inference_source = "local"
        self.inference_latency = 0.0

        self.crowd_threshold = 8

        print("[OK] Pipeline V3.1 Core Loaded.")
        if self.remote_client and self.remote_client.mode == "remote":
            print("[Pipeline] Hybrid Inference ENABLED (Remote GPU Bridge)\n")
        else:
            print("[Pipeline] Local Inference Mode\n")

    def _update_fps(self):
        """Rolling FPS from actual frame timestamps."""
        now = time.time()
        self._fps_timestamps.append(now)
        if len(self._fps_timestamps) >= 2:
            elapsed = self._fps_timestamps[-1] - self._fps_timestamps[0]
            if elapsed > 0:
                self.current_fps = round((len(self._fps_timestamps) - 1) / elapsed, 1)

    def _resize_for_inference(self, frame):
        """Resize to inference width while maintaining aspect ratio."""
        h, w = frame.shape[:2]
        if w <= INFERENCE_WIDTH:
            return frame, 1.0
        scale = INFERENCE_WIDTH / w
        new_w = INFERENCE_WIDTH
        new_h = int(h * scale)
        resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        return resized, scale

    def _scale_box(self, box, scale):
        """Scale detection box back to original frame coordinates."""
        if scale == 1.0:
            return box
        inv = 1.0 / scale
        return [int(box[0] * inv), int(box[1] * inv), int(box[2] * inv), int(box[3] * inv)]

    def run(self, frame, camera_id="default"):
        """
        Single end-to-end inference pass.
        Returns: (annotated_frame, alerts, trajectories)
        """
        print(f"[Pipeline] Processing frame for {camera_id}...")
        self._update_fps()
        annotated_frame = frame.copy()  # Annotate on a copy to prevent in-place corruption
        h, w = frame.shape[:2]

        # 0. Adverse Condition Preprocessing
        frame_enhanced, condition = preprocessor.process(frame)

        # 1. Resize for inference (saves GPU/CPU time)
        inference_frame, scale = self._resize_for_inference(frame_enhanced)

        # 2. Hybrid Inference: Remote GPU first, local fallback
        detections = None
        if self.remote_client and self.remote_client.is_connected:
            detections = self.remote_client.detect_remote(inference_frame, condition=condition)
            if detections is not None:
                self.inference_source = "remote"
                self.inference_latency = self.remote_client.latency_ms
            else:
                self.inference_latency = 0.0

        if detections is None:
            # Phase 5: Absolute Crowd Coverage. Lower threshold for CAM2 to mark as many as possible.
            active_conf = 0.15 if camera_id == "cam2" else None
            detections = self.yolo.detect(inference_frame, conf_threshold=active_conf, condition=condition)
            self.inference_source = "local"

        # Scale boxes back to original resolution
        if scale != 1.0:
            for det in detections:
                det["box"] = self._scale_box(det["box"], scale)

        # 4. Update rolling confidence
        if detections:
            valid_confs = [d["confidence"] for d in detections if d["confidence"] > 0.30]
            if valid_confs:
                avg_conf = sum(valid_confs) / len(valid_confs)
                self.rolling_confidence = (self.rolling_confidence * 0.95) + (avg_conf * 0.05)

        # 5. Heatmap decay
        for i in range(20):
            for j in range(20):
                self.heatmap_grid[i][j] *= 0.98

        # 6. Collect Observations for TICE
        observations = []
        person_detections = []
        bag_detections = []

        for det in detections:
            cls_name = det["class_name"].lower()
            box = det["box"]
            conf = det["confidence"]
            x1, y1, x2, y2 = box
            
            _is_person = any(tag in cls_name for tag in ("person", "human", "intruder"))
            
            obs_id = None
            is_motionless = False
            is_fallen_pose = False
            is_intrusion = False

            if _is_person:
                # ROI & Posture
                is_intrusion = self.zone_detector.check_intrusion(box)
                w_box = max(x2 - x1, 1); h_box = max(y2 - y1, 1)
                is_fallen_pose = (w_box / h_box) > 1.3
                
                # Tracking
                obs_id, path = self.reid.update(frame, box, camera_id)
                
                # Motion Analytics
                if path and len(path) >= 3:
                    pts = [p["center"] for p in path[-3:]]
                    dist = np.linalg.norm(np.array(pts[0]) - np.array(pts[-1]))
                    if dist < 8.0: is_motionless = True
                
                person_detections.append(det)
            
            elif any(tag in cls_name for tag in ("bag", "luggage", "backpack", "suitcase")):
                obs_id = f"bag_{camera_id}_{x1}_{y1}" # Temporal baggage ID
                bag_detections.append(det)
            
            else:
                obs_id = f"{cls_name}_{camera_id}"
            
            observations.append({
                "id": obs_id if obs_id else f"tmp_{time.time()}",
                "class": "person" if _is_person else cls_name,
                "box": box,
                "confidence": conf,
                "is_intrusion": is_intrusion,
                "is_fallen_pose": is_fallen_pose,
                "is_motionless": is_motionless
            })

        # 7. Unattended Baggage Sub-logic
        if bag_detections and person_detections:
            tracks_for_bag = []
            for i, p in enumerate(person_detections): tracks_for_bag.append({"id":f"p{i}", "class_id":0, "box":p["box"]})
            for i, b in enumerate(bag_detections): tracks_for_bag.append({"id":f"b{i}", "class_id":1, "box":b["box"]})
            
            bag_alerts = self.baggage_tracker.update(frame, tracks_for_bag, camera_id)
            # Map baggage alerts back to observations
            for ba in bag_alerts:
                for obs in observations:
                    if "bag" in obs["class"]:
                        obs["is_unattended"] = True
                        obs["duration_s"] = ba["details"].get("duration_s", 0)

        # 8. Crowd Detection State
        confirmed_ids = self.temp_filter.update([o["id"] for o in observations if o["class"] == "person"])
        if len(confirmed_ids) >= self.crowd_threshold:
            observations.append({
                "id": f"crowd_{camera_id}",
                "class": "crowd_detected",
                "box": [0,0,w,h],
                "confidence": 1.0
            })

        # 9. TICE INTERPRETATION & DYNAMIC RENDERING
        final_structured_alerts = self.threat_engine.process_observations(camera_id, observations)

        # --- PHASE 5: Entity-State Aware Vision Pass ---
        for obs in observations:
            if obs["class"] == "crowd_detected": continue
            
            x1, y1, x2, y2 = [int(v) for v in obs["box"]]
            cls_name = obs["class"].lower()
            
            # Determine Final Operational Label
            display_label = cls_name.upper()
            color = (255, 255, 0) # Default Cyan
            thickness = 1

            if "person" in cls_name:
                if obs.get("is_intrusion"):
                    display_label = "PERSON ON TRACK"
                    color = (0, 0, 255) # RED
                    thickness = 2
                elif camera_id == "cam2":
                    color = (0, 255, 0) # CROWD GREEN
                    thickness = 2
            
            elif "bag" in cls_name or cls_name in ("luggage", "backpack", "suitcase"):
                if obs.get("is_unattended"):
                    display_label = "BAGGAGE UNATTENDED"
                    color = (0, 0, 255) # RED
                    thickness = 3
                else:
                    color = (255, 191, 0) # AMBER

            elif "fire" in cls_name or "smoke" in cls_name or "flame" in cls_name:
                display_label = cls_name.upper()
                color = (0, 0, 255) # RED
                thickness = 3

            # Draw Final Operational Square
            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, thickness)
            
            # High-Contrast Operation Label
            label_text = f"{display_label} {obs['confidence']:.2f}"
            (tw, th), _ = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.35, 1)
            cv2.rectangle(annotated_frame, (x1, y1 - th - 4), (x1 + tw, y1), color, -1)
            cv2.putText(annotated_frame, label_text, (x1, y1 - 4), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 255, 255), 1)

        # 10. HUD & Annotation
        person_count = len(confirmed_ids)
        for alert in final_structured_alerts:
            # Simple visual indicator for the command being issued
            cv2.putText(annotated_frame, f"COMMAND: {alert['command']}", (20, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

        hud_h = 35
        overlay = annotated_frame.copy()
        cv2.rectangle(overlay, (0, h - hud_h), (w, h), (10, 10, 15), -1)
        cv2.addWeighted(overlay, 0.82, annotated_frame, 0.18, 0, annotated_frame)

        src_tag = "GPU BRIDGE" if self.inference_source == "remote" else "LOCAL CPU"
        font = cv2.FONT_HERSHEY_SIMPLEX
        cv2.putText(annotated_frame, f"PIPELINE: ACTIVE | {src_tag}",
                    (15, h - 12), font, 0.42, (255, 191, 0), 1, cv2.LINE_AA)
        stats_text = f"LAT:{self.inference_latency:.0f}ms | AI:{self.current_fps}FPS | PRSN:{person_count} | THREATS:{len(final_structured_alerts)}"
        cv2.putText(annotated_frame, stats_text,
                    (w - 420, h - 12), font, 0.42, (220, 220, 220), 1, cv2.LINE_AA)

        return annotated_frame, final_structured_alerts, confirmed_ids


# Global singleton
pipeline = SurveillancePipeline()
