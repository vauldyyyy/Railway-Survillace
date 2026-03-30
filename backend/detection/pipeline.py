"""
Unified Surveillance Pipeline V4.0 — Entity-State Engine
=========================================================
Production-grade multi-entity railway surveillance system.

Architecture:
  Layer 1: Detection        (yolo_world.py)  — Raw bounding boxes
  Layer 2: Classification   (entity_state.py) — Map to EntityClass
  Layer 3: Tracking         (reid.py + CentroidTracker) — Persistent IDs
  Layer 4: Entity Registry  (entity_state.py) — Per-camera entity store
  Layer 5: Spatial Analysis (entity_state.py) — IoU, proximity, zone checks
  Layer 6: State Transition (entity_state.py) — Camera-specific FSM
  Layer 7: Visual Rendering (entity_renderer.py) — Entity-aware drawing
  Layer 8: Alert Publisher  (interpretation.py) — Structured JSON alerts
"""
import time
import cv2
import numpy as np
from collections import deque

from detection.yolo_world import ZeroShotDetector
from detection.reid import ReIDTracker
from detection.temporal_filter import TemporalFilter
from detection.preprocessor import preprocessor
from detection.zone_alert import ZoneIntrusionDetector
from detection.entity_state import (
    EntityClass, EntityState, Entity,
    EntityRegistry, CentroidTracker, SpatialEngine, StateTransitionEngine,
    classify_detection,
)
from detection.entity_renderer import EntityRenderer
from detection.interpretation import ThreatEngine

try:
    from core.remote_client import remote_client
    _REMOTE_AVAILABLE = True
except ImportError:
    _REMOTE_AVAILABLE = False
    remote_client = None


INFERENCE_WIDTH = 800


class SurveillancePipeline:
    def __init__(self):
        print("\n" + "=" * 60)
        print("  INITIALIZING ENTITY-STATE SURVEILLANCE ENGINE V4.0")
        print("  MULTI-ENTITY FSM | PER-CAMERA RULES | ZERO-MISS")
        print("=" * 60)

        # ── Layer 1: Detection ──
        self.yolo = ZeroShotDetector()

        # ── Layer 2-3: Tracking ──
        self.reid = ReIDTracker(threshold=0.72, epsilon=0.1)
        self.centroid_tracker = CentroidTracker(max_disappeared=8)
        self.temp_filter = TemporalFilter(min_hits=3, max_age=8)

        # ── Layer 4: Entity Registry ──
        self.registry = EntityRegistry(max_age_seconds=5.0)

        # ── Layer 5: Spatial Engine ──
        self.zone_detector = ZoneIntrusionDetector()

        # ── Layer 6: State Transition Engine ──
        self.state_engine = StateTransitionEngine(zone_detector=self.zone_detector)

        # ── Layer 7: Renderer ──
        self.renderer = EntityRenderer()

        # ── Layer 8: Alert Publisher (legacy compat) ──
        self.threat_engine = ThreatEngine()

        # ── Infrastructure ──
        self.remote_client = remote_client if _REMOTE_AVAILABLE else None
        self._fps_timestamps = deque(maxlen=30)
        self.current_fps = 0.0
        self.rolling_confidence = 0.0
        self.inference_source = "local"
        self.inference_latency = 0.0
        self.heatmap_grid = [[0.0] * 20 for _ in range(20)]

        print("[OK] Entity-State Engine V4.0 Loaded.")
        if self.remote_client and self.remote_client.mode == "remote":
            print("[Pipeline] Hybrid Inference ENABLED (Remote GPU Bridge)\n")
        else:
            print("[Pipeline] Local Inference Mode\n")

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
        new_w = INFERENCE_WIDTH
        new_h = int(h * scale)
        resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        return resized, scale

    def _scale_box(self, box, scale):
        if scale == 1.0:
            return box
        inv = 1.0 / scale
        return [int(box[0] * inv), int(box[1] * inv), int(box[2] * inv), int(box[3] * inv)]

    def run(self, frame, camera_id="default"):
        """
        Single end-to-end inference pass through the Entity-State Engine.
        Returns: (annotated_frame, alerts, entity_ids)
        """
        self._update_fps()
        h, w = frame.shape[:2]

        # ══════════════════════════════════════════════════════════════
        # LAYER 1: DETECTION
        # ══════════════════════════════════════════════════════════════
        frame_enhanced, condition = preprocessor.process(frame)
        inference_frame, scale = self._resize_for_inference(frame_enhanced)

        detections = None
        if self.remote_client and self.remote_client.is_connected:
            detections = self.remote_client.detect_remote(inference_frame, condition=condition)
            if detections is not None:
                self.inference_source = "remote"
                self.inference_latency = self.remote_client.latency_ms
            else:
                self.inference_latency = 0.0

        if detections is None:
            active_conf = 0.15 if camera_id == "cam2" else None
            detections = self.yolo.detect(inference_frame, conf_threshold=active_conf, condition=condition)
            self.inference_source = "local"

        # Scale boxes back to original resolution
        if scale != 1.0:
            for det in detections:
                det["box"] = self._scale_box(det["box"], scale)

        # Update rolling confidence
        if detections:
            valid_confs = [d["confidence"] for d in detections if d["confidence"] > 0.30]
            if valid_confs:
                avg_conf = sum(valid_confs) / len(valid_confs)
                self.rolling_confidence = (self.rolling_confidence * 0.95) + (avg_conf * 0.05)

        # Heatmap decay
        for i in range(20):
            for j in range(20):
                self.heatmap_grid[i][j] *= 0.98

        # ══════════════════════════════════════════════════════════════
        # LAYER 2: CLASSIFICATION — Map raw class names to EntityClass
        # ══════════════════════════════════════════════════════════════
        classified: dict = {
            EntityClass.PERSON:  [],
            EntityClass.BAGGAGE: [],
            EntityClass.SMOKE:   [],
            EntityClass.FIRE:    [],
            EntityClass.TRACK:   [],
            EntityClass.UNKNOWN: [],
        }

        for det in detections:
            entity_class = classify_detection(det["class_name"])
            classified[entity_class].append(det)

        # ══════════════════════════════════════════════════════════════
        # LAYER 3: TRACKING — Assign persistent IDs to each detection
        # ══════════════════════════════════════════════════════════════

        # Persons: use neural ReID tracker
        person_tracked = []
        for det in classified[EntityClass.PERSON]:
            reid_id, path = self.reid.update(frame, det["box"], camera_id)
            if reid_id:
                person_tracked.append((f"P_{reid_id[:5]}", det))
            else:
                # Fallback to centroid tracker if ReID fails
                ct_results = self.centroid_tracker.update(
                    camera_id, EntityClass.PERSON, [det]
                )
                person_tracked.extend(ct_results)

        # Non-person entities: centroid tracker
        bag_tracked = self.centroid_tracker.update(
            camera_id, EntityClass.BAGGAGE, classified[EntityClass.BAGGAGE]
        )
        smoke_tracked = self.centroid_tracker.update(
            camera_id, EntityClass.SMOKE, classified[EntityClass.SMOKE]
        )
        fire_tracked = self.centroid_tracker.update(
            camera_id, EntityClass.FIRE, classified[EntityClass.FIRE]
        )

        # ══════════════════════════════════════════════════════════════
        # LAYER 4: ENTITY REGISTRY — Upsert all tracked entities
        # ══════════════════════════════════════════════════════════════
        all_tracked = (
            [(EntityClass.PERSON, tid, det) for tid, det in person_tracked] +
            [(EntityClass.BAGGAGE, tid, det) for tid, det in bag_tracked] +
            [(EntityClass.SMOKE, tid, det) for tid, det in smoke_tracked] +
            [(EntityClass.FIRE, tid, det) for tid, det in fire_tracked]
        )

        for entity_class, entity_id, det in all_tracked:
            self.registry.upsert(
                camera_id, entity_id, entity_class,
                det["box"], det["confidence"]
            )

        # ══════════════════════════════════════════════════════════════
        # LAYER 5 + 6: SPATIAL ANALYSIS + STATE TRANSITIONS
        # ══════════════════════════════════════════════════════════════
        active_entities = self.registry.get_all(camera_id)
        state_alerts = self.state_engine.evaluate(camera_id, active_entities, self.registry)

        # Also run legacy ThreatEngine for operational command mapping
        # Build observations for backward compatibility
        observations = []
        for e in active_entities:
            obs = {
                "id": e.id,
                "class": e.base_class.value,
                "box": e.box,
                "confidence": e.confidence,
                "is_intrusion": e.is_in_track_zone,
                "is_fallen_pose": e.is_fallen_pose,
                "is_motionless": e.is_motionless,
            }
            if e.base_class == EntityClass.BAGGAGE:
                obs["is_unattended"] = e.current_state in (
                    EntityState.BAGGAGE_UNATTENDED, EntityState.BAGGAGE_BOMB
                )
                obs["duration_s"] = e.separation_duration
            observations.append(obs)

        # Temporal filter for confirmed person tracks
        person_ids = [e.id for e in active_entities if e.base_class == EntityClass.PERSON]
        confirmed_ids = self.temp_filter.update(person_ids)

        # Legacy threat engine alerts (for operational command mapping)
        legacy_alerts = self.threat_engine.process_observations(camera_id, observations)

        # Merge: use state_alerts for entity-specific data, legacy for command mapping
        final_alerts = []
        for sa in state_alerts:
            # Find matching legacy alert for command/notify/escalation
            matched_legacy = None
            for la in legacy_alerts:
                if la.get("threat_type", "").lower() in sa.get("new_state", "").lower():
                    matched_legacy = la
                    break

            if matched_legacy:
                sa["command"] = matched_legacy.get("command", "MONITOR_SITUATION")
                sa["notify"] = matched_legacy.get("notify", ["Security Monitor"])
                sa["escalation"] = matched_legacy.get("escalation", [])
            else:
                sa["command"] = "MONITOR_SITUATION"
                sa["notify"] = ["Security Monitor"]
                sa["escalation"] = []

            final_alerts.append(sa)

        # If legacy produced alerts not covered by state engine, include them too
        for la in legacy_alerts:
            if not any(sa.get("camera_id") == la.get("camera_id") and
                       sa.get("new_state", "").lower() in la.get("threat_type", "").lower()
                       for sa in state_alerts):
                # Convert to entity-alert format
                final_alerts.append({
                    "camera_id": la.get("camera_id", camera_id.upper()),
                    "entity_id": "LEGACY",
                    "base_class": "Unknown",
                    "new_state": la.get("threat_type", "UNKNOWN"),
                    "threat_level": la.get("threat_level", "INFO"),
                    "timestamp": la.get("timestamp", ""),
                    "confidence": la.get("confidence", 0.0),
                    "command": la.get("command", "MONITOR_SITUATION"),
                    "notify": la.get("notify", []),
                    "escalation": la.get("escalation", []),
                    "box": [],
                })

        # ══════════════════════════════════════════════════════════════
        # LAYER 7: VISUAL RENDERING
        # ══════════════════════════════════════════════════════════════
        pipeline_stats = {
            "inference_source": self.inference_source,
            "fps": self.current_fps,
            "latency": self.inference_latency,
            "person_count": len(confirmed_ids),
            "threat_count": len(final_alerts),
            "entity_count": len(active_entities),
        }

        annotated_frame = self.renderer.render(frame, active_entities, pipeline_stats)

        # ══════════════════════════════════════════════════════════════
        # LAYER 8: GARBAGE COLLECTION
        # ══════════════════════════════════════════════════════════════
        self.registry.gc(camera_id)

        return annotated_frame, final_alerts, confirmed_ids


# Global singleton
pipeline = SurveillancePipeline()
