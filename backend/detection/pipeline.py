"""
pipeline.py -- Unified Surveillance Pipeline V4.0 (Entity-State Engine)
========================================================================
Fully wires detections through the Entity-State Engine:
  1. YOLO-World detection
  2. Class-to-EntityClass routing via classify_detection()
  3. CentroidTracker assigns persistent IDs per entity class
  4. EntityRegistry stores all entity state (thread-safe, per-camera)
  5. StateTransitionEngine evaluates per-camera FSM rules
  6. EntityRenderer draws color-coded bounding boxes from entity state
  7. Structured JSON alerts emitted to main.py alert publisher
"""
import time
import cv2
import numpy as np
from collections import deque

from detection.zone_alert import ZoneIntrusionDetector
from detection.yolo_world import ZeroShotDetector
from detection.reid import ReIDTracker
from detection.preprocessor import preprocessor
from detection.entity_state import (
    EntityClass, EntityRegistry, CentroidTracker,
    StateTransitionEngine, classify_detection
)
from detection.entity_renderer import EntityRenderer

try:
    from core.remote_client import remote_client
    _REMOTE_AVAILABLE = True
except ImportError:
    _REMOTE_AVAILABLE = False
    remote_client = None


INFERENCE_WIDTH = 800


class SurveillancePipeline:
    def __init__(self):
        print("\n-------------------------------------------------------")
        print("  INITIALIZING MASTER INTELLIGENCE PIPELINE (V4.0)")
        print("  ENTITY-STATE ENGINE -- ALL CAMERAS ACTIVE")
        print("-------------------------------------------------------")

        # Detection
        self.yolo = ZeroShotDetector()
        self.reid = ReIDTracker(threshold=0.75, epsilon=1.2)
        self.zone_detector = ZoneIntrusionDetector()
        self.remote_client = remote_client if _REMOTE_AVAILABLE else None

        # Entity-State Engine layers
        self.registry   = EntityRegistry(max_age_seconds=6.0)
        self.tracker    = CentroidTracker(max_disappeared=8)
        self.fsm        = StateTransitionEngine(zone_detector=self.zone_detector)
        self.renderer   = EntityRenderer()

        # FPS tracking
        self._fps_timestamps = deque(maxlen=30)
        self.current_fps = 0.0
        self.rolling_confidence = 0.0
        self.heatmap_grid = [[0.0] * 20 for _ in range(20)]
        self.inference_source = "local"
        self.inference_latency = 0.0

        self.crowd_threshold = 10

        print("[OK] Pipeline V4.0 Entity-State Engine Loaded.")

    # ------------------------------------------------------------------ #
    #  INTERNAL HELPERS                                                    #
    # ------------------------------------------------------------------ #

    def _update_fps(self):
        now = time.time()
        self._fps_timestamps.append(now)
        if len(self._fps_timestamps) >= 2:
            elapsed = self._fps_timestamps[-1] - self._fps_timestamps[0]
            if elapsed > 0:
                self.current_fps = round((len(self._fps_timestamps) - 1) / elapsed, 1)

    def _resize_for_inference(self, frame):
        h, w = frame.shape[:2]
        if w <= INFERENCE_WIDTH:
            return frame, 1.0
        scale = INFERENCE_WIDTH / w
        resized = cv2.resize(frame, (INFERENCE_WIDTH, int(h * scale)), interpolation=cv2.INTER_LINEAR)
        return resized, scale

    def _scale_box(self, box, scale):
        if scale == 1.0:
            return box
        inv = 1.0 / scale
        return [int(v * inv) for v in box]

    # ------------------------------------------------------------------ #
    #  MAIN PIPELINE RUN                                                   #
    # ------------------------------------------------------------------ #

    def run(self, frame, camera_id="default"):
        """
        Single end-to-end inference pass.
        Returns: (annotated_frame, structured_alerts, confirmed_ids)
        """
        self._update_fps()
        h, w = frame.shape[:2]

        # --- 0. Preprocessing (denoise, enhance contrast) ---------------
        frame_enhanced, condition = preprocessor.process(frame)

        # --- 1. Resize for inference ------------------------------------
        inference_frame, scale = self._resize_for_inference(frame_enhanced)

        # --- 2. Hybrid Inference (Remote GPU / Local CPU) ---------------
        # SPEED-SPLIT: Force Cam 5 (Webcam Demo) to Local. 
        # Cam 3 (Fire Demo) moves to REMOTE GPU for zero-lag 30FPS motion.
        is_hybrid_local = (camera_id == "cam5")
        
        detections = None
        if not is_hybrid_local and self.remote_client and self.remote_client.is_connected:
            try:
                detections = self.remote_client.detect_remote(inference_frame, condition=condition)
                if detections is not None:
                    self.inference_source = "remote"
                    self.inference_latency = self.remote_client.latency_ms
                else:
                    self.inference_latency = 0.0
            except Exception as e:
                print(f"[Pipeline] Remote AI bridge error: {e}. Defaulting to LOCAL AI.")
                detections = None

        if not detections:
            active_conf = 0.08 if camera_id == "cam2" else None
            detections = self.yolo.detect(inference_frame, conf_threshold=active_conf, condition=condition, camera_id=camera_id)
            self.inference_source = "local"

        # Scale boxes back to original resolution
        if scale != 1.0:
            for det in detections:
                det["box"] = self._scale_box(det["box"], scale)

        # --- 3. Update rolling confidence --------------------------------
        if detections:
            valid = [d["confidence"] for d in detections if d["confidence"] > 0.30]
            if valid:
                avg = sum(valid) / len(valid)
                self.rolling_confidence = self.rolling_confidence * 0.95 + avg * 0.05

        # --- 4. Heatmap decay --------------------------------------------
        for i in range(20):
            for j in range(20):
                self.heatmap_grid[i][j] *= 0.98

        # --- 5. Bucket detections by EntityClass -------------------------
        buckets: dict[EntityClass, list] = {
            EntityClass.PERSON:  [],
            EntityClass.BAGGAGE: [],
            EntityClass.SMOKE:   [],
            EntityClass.FIRE:    [],
            EntityClass.TRACK:   [],
            EntityClass.UNKNOWN: [],
        }
        for det in detections:
            # Specialization: Cam 1 is PLATFORM ONLY (No bag/smoke/fire)
            if camera_id == "cam1":
                if det["class_name"].lower() not in ("person", "track", "rail"):
                    continue

            # Specialization: Cam 2 is OVERCROWDING ONLY (No bag/fire/smoke)
            if camera_id == "cam2":
                if det["class_name"].lower() not in ("person", "human", "intruder"):
                    continue


            # Specialization: Cam 4 is BAGGAGE-OWNERSHIP ONLY
            if camera_id == "cam4":
                if det["class_name"].lower() not in ("person", "bag", "luggage", "backpack", "suitcase"):
                    continue


            # Specialization: Cam 7 is PEOPLE-ONLY LIVE STREAM
            if camera_id == "cam7":
                if det["class_name"].lower() not in ("person", "human", "intruder"):
                    continue

            ec = classify_detection(det["class_name"])
            buckets[ec].append(det)

        # --- 6. Track each class with CentroidTracker --------------------
        #        Person entities also go through ReID for cross-frame IDs
        structured_entities = []  # [(entity_id, EntityClass, det)]

        for ec, dets in buckets.items():
            if ec == EntityClass.UNKNOWN or not dets:
                continue

            if ec == EntityClass.PERSON:
                # Use ReID tracker for persons (neural 512-D matching)
                for det in dets:
                    reid_id, path = self.reid.update(frame, det["box"], camera_id)
                    if reid_id is None:
                        # Crop too small for ReID — still register with centroid ID
                        x1, y1, x2, y2 = det["box"]
                        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
                        reid_id = f"P_f{cx}_{cy}"
                        path = []
                    structured_entities.append((reid_id, ec, det, path))

            else:
                # Use CentroidTracker for all other classes
                matches = self.tracker.update(camera_id, ec, dets)
                for eid, det in matches:
                    structured_entities.append((eid, ec, det, None))

        # --- 7. Upsert all entities into the EntityRegistry --------------
        for item in structured_entities:
            eid, ec, det, path = item
            entity = self.registry.upsert(camera_id, eid, ec, det["box"], det["confidence"])
            
            # ATTACH SEGMENTATION MASK (For precision outlines like Fire)
            if "mask" in det:
                entity.mask = det["mask"]

            # Enrich person entities with motion/pose metadata from ReID path
            if ec == EntityClass.PERSON and path:
                if len(path) >= 3:
                    pts = [p["center"] for p in path[-3:]]
                    dist = np.linalg.norm(np.array(pts[0]) - np.array(pts[-1]))
                    entity.is_motionless = dist < 8.0

                x1, y1, x2, y2 = det["box"]
                bw = max(x2 - x1, 1); bh = max(y2 - y1, 1)
                entity.is_fallen_pose = (bw / bh) > 1.3

        # --- 8. Garbage collect stale entities ---------------------------
        self.registry.gc(camera_id)

        # --- 9. Run State Transition Engine (FSM) ------------------------
        all_entities = self.registry.get_all(camera_id)
        fsm_alerts = self.fsm.evaluate(camera_id, all_entities, self.registry)

        # Re-fetch after FSM may have added derived entities (crowd)
        all_entities = self.registry.get_all(camera_id)

        # --- 10. Render entities onto frame using EntityRenderer ---------
        pipeline_stats = {
            "camera_id":        camera_id.upper(),
            "inference_source": self.inference_source,
            "fps":              self.current_fps,
            "latency":          self.inference_latency,
            "confidence":       self.rolling_confidence,
            "threat_count":     len(fsm_alerts),
        }
        annotated_frame = self.renderer.render(frame, all_entities, pipeline_stats)

        # --- 11. Convert FSM alerts to TICE-format for main.py ----------
        import datetime
        tice_alerts = []
        for alert in fsm_alerts:
            threat_level = alert.get("threat_level", "INFO")
            tice_alerts.append({
                # TICE-compatible keys used by main.py alert publisher
                "camera_id":   alert["camera_id"],
                "threat_type": alert["new_state"].replace(" ", "_").upper(),
                "threat_level": threat_level,
                "command": _threat_command(threat_level),
                "notify": ["Security Monitor"],
                "escalation": ["Station Commander"] if threat_level == "CRITICAL" else [],
                "timestamp": alert.get("timestamp", datetime.datetime.now().isoformat()),
                "confidence": alert.get("confidence", 0.0),
                # Extra metadata kept for UI
                "entity_id":  alert.get("entity_id"),
                "base_class": alert.get("base_class"),
                "box":        alert.get("box", []),
                "type":       alert.get("new_state", ""),
                "severity":   threat_level.lower(),
                "alert":      True,
                "uuid":       f"{camera_id}_{alert.get('entity_id')}_{int(time.time())}",
            })

        # Confirmed person IDs for crowd count in HUD
        confirmed_ids = set(
            e.id for e in all_entities
            if e.base_class == EntityClass.PERSON
        )

        return annotated_frame, tice_alerts, confirmed_ids


def _threat_command(threat_level: str) -> str:
    return {
        "CRITICAL": "EVACUATE_IMMEDIATELY",
        "HIGH":     "DISPATCH_SECURITY",
        "MEDIUM":   "MONITOR_CLOSELY",
        "LOW":      "LOG_INCIDENT",
    }.get(threat_level, "MONITOR_SITUATION")


# Global singleton
pipeline = SurveillancePipeline()
