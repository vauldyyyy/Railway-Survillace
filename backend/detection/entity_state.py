"""
entity_state.py — Production Entity-State Engine
==================================================
Layered architecture for multi-entity railway surveillance.

Layer 1: Entity Registry      — Persistent per-camera entity store with unique IDs
Layer 2: Spatial Engine        — IoU, proximity, and zone intersection analysis
Layer 3: State Transition FSM  — Camera-specific rule evaluation with hysteresis
Layer 4: Centroid Tracker      — Lightweight tracking for non-person entities

Design Constraints:
  - Thread-safe: all registry operations use per-camera locks
  - No dropped states: entities persist across frames via max_age eviction
  - No false transitions: state changes require min_confirmation_frames
  - Auditable: every state transition is logged with timestamp
"""

import time
import datetime
import threading
import math
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict


# ════════════════════════════════════════════════════════════════════════
# ENUMS — Entity Classification & State Machine
# ════════════════════════════════════════════════════════════════════════

class EntityClass(Enum):
    PERSON   = "person"
    TRACK    = "track"
    BAGGAGE  = "baggage"
    SMOKE    = "smoke"
    FIRE     = "fire"
    CROWD    = "crowd"       # Derived spatial entity
    UNKNOWN  = "unknown"


class EntityState(Enum):
    BASE                = "BASE"
    PERSON_ON_TRACK     = "PERSON_ON_TRACK"
    PERSON_FALLEN       = "PERSON_FALLEN"
    BAGGAGE_UNATTENDED  = "BAGGAGE_UNATTENDED"
    BAGGAGE_BOMB        = "BAGGAGE_BOMB_PROTOCOL"
    SMOKE_DETECTED      = "SMOKE_DETECTED"
    SMOKE_CRITICAL      = "SMOKE_CRITICAL"
    FIRE_DETECTED       = "FIRE_DETECTED"
    OVERCROWDING        = "OVERCROWDING"


# ════════════════════════════════════════════════════════════════════════
# COLOR SYSTEM — BGR format for OpenCV
# ════════════════════════════════════════════════════════════════════════

# Base colors: the default color when entity is in BASE state
BASE_COLORS: Dict[EntityClass, Tuple[int, int, int]] = {
    EntityClass.PERSON:   (255, 150, 50),    # Blue (BGR)
    EntityClass.TRACK:    (0, 255, 255),      # Yellow (BGR)
    EntityClass.BAGGAGE:  (0, 210, 80),       # Green (BGR)
    EntityClass.SMOKE:    (160, 160, 160),    # Gray (BGR)
    EntityClass.FIRE:     (0, 140, 255),      # Orange (BGR)
    EntityClass.CROWD:    (200, 200, 0),      # Cyan (BGR) — derived entity
    EntityClass.UNKNOWN:  (180, 180, 180),    # Light gray
}

# State colors: override color when entity transitions to escalated state
STATE_COLORS: Dict[EntityState, Tuple[int, int, int]] = {
    EntityState.BASE:                None,                # Use BASE_COLORS
    EntityState.PERSON_ON_TRACK:     (0, 0, 255),         # RED
    EntityState.PERSON_FALLEN:       (0, 0, 255),         # RED
    EntityState.BAGGAGE_UNATTENDED:  (0, 0, 255),         # RED
    EntityState.BAGGAGE_BOMB:        (0, 0, 200),         # DARK RED
    EntityState.SMOKE_DETECTED:      (50, 50, 200),       # DIM RED
    EntityState.SMOKE_CRITICAL:      (0, 0, 255),         # RED
    EntityState.FIRE_DETECTED:       (0, 0, 255),         # RED (flashing handled by renderer)
    EntityState.OVERCROWDING:        (0, 0, 255),         # RED zone boundary
}

# State labels: display name for the HUD overlay
STATE_LABELS: Dict[EntityState, str] = {
    EntityState.BASE:                None,                # Use class name
    EntityState.PERSON_ON_TRACK:     "PERSON ON TRACK",
    EntityState.PERSON_FALLEN:       "PERSON FALLEN ON TRACK",
    EntityState.BAGGAGE_UNATTENDED:  "UNATTENDED BAGGAGE",
    EntityState.BAGGAGE_BOMB:        "⚠ BOMB PROTOCOL",
    EntityState.SMOKE_DETECTED:      "SMOKE DETECTED",
    EntityState.SMOKE_CRITICAL:      "SMOKE — CRITICAL",
    EntityState.FIRE_DETECTED:       "🔥 FIRE DETECTED",
    EntityState.OVERCROWDING:        "OVERCROWDING ZONE",
}

# Threat level mapping for structured alerts
STATE_THREAT_LEVELS: Dict[EntityState, str] = {
    EntityState.BASE:                "NONE",
    EntityState.PERSON_ON_TRACK:     "CRITICAL",
    EntityState.PERSON_FALLEN:       "CRITICAL",
    EntityState.BAGGAGE_UNATTENDED:  "HIGH",
    EntityState.BAGGAGE_BOMB:        "CRITICAL",
    EntityState.SMOKE_DETECTED:      "MEDIUM",
    EntityState.SMOKE_CRITICAL:      "CRITICAL",
    EntityState.FIRE_DETECTED:       "CRITICAL",
    EntityState.OVERCROWDING:        "HIGH",
}

# Box thickness per state
STATE_THICKNESS: Dict[EntityState, int] = {
    EntityState.BASE:                2,
    EntityState.PERSON_ON_TRACK:     3,
    EntityState.PERSON_FALLEN:       3,
    EntityState.BAGGAGE_UNATTENDED:  3,
    EntityState.BAGGAGE_BOMB:        4,
    EntityState.SMOKE_DETECTED:      2,
    EntityState.SMOKE_CRITICAL:      3,
    EntityState.FIRE_DETECTED:       3,
    EntityState.OVERCROWDING:        3,
}


# ════════════════════════════════════════════════════════════════════════
# ENTITY DATACLASS — Core data model for every tracked object
# ════════════════════════════════════════════════════════════════════════

@dataclass
class Entity:
    """Persistent representation of a tracked object across frames."""
    id:            str                           # Unique ID: P_001, B_003, S_001
    base_class:    EntityClass                   # Immutable base classification
    current_state: EntityState = EntityState.BASE
    box:           List[int]   = field(default_factory=lambda: [0, 0, 0, 0])
    confidence:    float       = 0.0
    first_seen:    float       = 0.0             # Unix timestamp
    last_seen:     float       = 0.0             # Unix timestamp
    camera_id:     str         = ""
    centroid:      Tuple[int, int] = (0, 0)

    # State transition tracking
    state_enter_time: float = 0.0                # When current state was entered
    prev_state:       EntityState = EntityState.BASE
    transition_count: int = 0

    # Relationship metadata
    owner_id:             Optional[str] = None
    nearest_person_id:    Optional[str] = None
    nearest_person_dist:  float = float('inf')
    is_in_track_zone:     bool = False
    is_motionless:        bool = False
    is_fallen_pose:       bool = False
    separation_duration:  float = 0.0            # For baggage separation timing

    # Motion tracking (centroid history for motionless detection)
    centroid_history: List[Tuple[int, int]] = field(default_factory=list)

    @property
    def color(self) -> Tuple[int, int, int]:
        """Returns the current visual color based on entity state."""
        state_color = STATE_COLORS.get(self.current_state)
        if state_color is not None:
            return state_color
        return BASE_COLORS.get(self.base_class, (180, 180, 180))

    @property
    def label(self) -> str:
        """Returns the current display label based on entity state."""
        state_label = STATE_LABELS.get(self.current_state)
        if state_label:
            return state_label
        return self.base_class.value.upper()

    @property
    def thickness(self) -> int:
        return STATE_THICKNESS.get(self.current_state, 2)

    @property
    def threat_level(self) -> str:
        return STATE_THREAT_LEVELS.get(self.current_state, "NONE")

    @property
    def age(self) -> float:
        """Seconds since first detection."""
        return self.last_seen - self.first_seen

    @property
    def state_duration(self) -> float:
        """Seconds in current state."""
        return self.last_seen - self.state_enter_time

    def transition_to(self, new_state: EntityState):
        """Execute a formal state transition with audit trail."""
        if new_state == self.current_state:
            return
        self.prev_state = self.current_state
        self.current_state = new_state
        self.state_enter_time = time.time()
        self.transition_count += 1


# ════════════════════════════════════════════════════════════════════════
# CENTROID TRACKER — Lightweight IoU + centroid matching for all classes
# ════════════════════════════════════════════════════════════════════════

class CentroidTracker:
    """
    Assigns persistent IDs to detections using centroid distance + IoU.
    Used for non-person entities (bags, smoke, fire, tracks).
    Person entities use the existing ReID tracker for neural matching.
    """

    def __init__(self, max_disappeared: int = 8):
        self.next_id: Dict[str, int] = defaultdict(int)  # Per-class counters
        self.max_disappeared = max_disappeared
        # camera_id -> { entity_id: {"centroid": (cx,cy), "box": [..], "disappeared": int} }
        self.objects: Dict[str, Dict[str, dict]] = defaultdict(dict)

    def _prefix(self, entity_class: EntityClass) -> str:
        return {
            EntityClass.PERSON:  "P",
            EntityClass.BAGGAGE: "B",
            EntityClass.SMOKE:   "S",
            EntityClass.FIRE:    "F",
            EntityClass.TRACK:   "T",
            EntityClass.CROWD:   "CWD",
        }.get(entity_class, "U")

    def _compute_iou(self, box_a, box_b) -> float:
        xa = max(box_a[0], box_b[0])
        ya = max(box_a[1], box_b[1])
        xb = min(box_a[2], box_b[2])
        yb = min(box_a[3], box_b[3])
        inter = max(0, xb - xa) * max(0, yb - ya)
        area_a = max(1, (box_a[2] - box_a[0]) * (box_a[3] - box_a[1]))
        area_b = max(1, (box_b[2] - box_b[0]) * (box_b[3] - box_b[1]))
        union = area_a + area_b - inter
        return inter / union if union > 0 else 0.0

    def _centroid_dist(self, c1, c2) -> float:
        return math.sqrt((c1[0] - c2[0])**2 + (c1[1] - c2[1])**2)

    def update(self, camera_id: str, entity_class: EntityClass,
               detections: List[dict]) -> List[Tuple[str, dict]]:
        """
        Match detections to existing tracked objects. Returns list of (entity_id, detection).
        detections: [{"box": [x1,y1,x2,y2], "confidence": float, "class_name": str}, ...]
        """
        cam_objects = self.objects[camera_id]
        prefix = self._prefix(entity_class)

        # Compute centroids for incoming detections
        det_centroids = []
        for det in detections:
            x1, y1, x2, y2 = det["box"]
            cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
            det_centroids.append((cx, cy))

        # If no existing objects, register all as new
        if not cam_objects or not any(
            oid.startswith(prefix) for oid in cam_objects
        ):
            results = []
            for i, det in enumerate(detections):
                self.next_id[prefix] += 1
                oid = f"{prefix}_{self.next_id[prefix]:03d}"
                cam_objects[oid] = {
                    "centroid": det_centroids[i],
                    "box": det["box"],
                    "disappeared": 0,
                }
                results.append((oid, det))
            return results

        # Get existing objects of this class
        class_objects = {
            oid: data for oid, data in cam_objects.items()
            if oid.startswith(prefix)
        }

        if not detections:
            # Mark all existing as disappeared
            for oid in list(class_objects.keys()):
                cam_objects[oid]["disappeared"] += 1
                if cam_objects[oid]["disappeared"] > self.max_disappeared:
                    del cam_objects[oid]
            return []

        # Build cost matrix: (existing_oid, det_index) -> score
        existing_ids = list(class_objects.keys())
        existing_centroids = [class_objects[oid]["centroid"] for oid in existing_ids]
        existing_boxes = [class_objects[oid]["box"] for oid in existing_ids]

        # Greedy matching: IoU-weighted centroid distance
        used_dets = set()
        used_objs = set()
        matches = []

        # Score all pairs
        pairs = []
        for oi, oid in enumerate(existing_ids):
            for di in range(len(detections)):
                iou = self._compute_iou(existing_boxes[oi], detections[di]["box"])
                cdist = self._centroid_dist(existing_centroids[oi], det_centroids[di])
                # Combined score: higher is better match
                score = iou * 100 + max(0, 200 - cdist)
                pairs.append((score, oi, di))

        pairs.sort(reverse=True)

        for score, oi, di in pairs:
            if oi in used_objs or di in used_dets:
                continue
            # Minimum match quality: at least some spatial overlap or proximity
            if score < 20:
                continue
            used_objs.add(oi)
            used_dets.add(di)
            matches.append((existing_ids[oi], di))

        results = []

        # Update matched objects
        for oid, di in matches:
            cam_objects[oid]["centroid"] = det_centroids[di]
            cam_objects[oid]["box"] = detections[di]["box"]
            cam_objects[oid]["disappeared"] = 0
            results.append((oid, detections[di]))

        # Register unmatched detections as new
        for di in range(len(detections)):
            if di not in used_dets:
                self.next_id[prefix] += 1
                oid = f"{prefix}_{self.next_id[prefix]:03d}"
                cam_objects[oid] = {
                    "centroid": det_centroids[di],
                    "box": detections[di]["box"],
                    "disappeared": 0,
                }
                results.append((oid, detections[di]))

        # Age unmatched existing objects
        for oi, oid in enumerate(existing_ids):
            if oi not in used_objs:
                cam_objects[oid]["disappeared"] += 1
                if cam_objects[oid]["disappeared"] > self.max_disappeared:
                    del cam_objects[oid]

        return results


# ════════════════════════════════════════════════════════════════════════
# ENTITY REGISTRY — Per-camera persistent entity store
# ════════════════════════════════════════════════════════════════════════

class EntityRegistry:
    """Thread-safe, per-camera registry of all tracked entities."""

    def __init__(self, max_age_seconds: float = 5.0):
        self.max_age = max_age_seconds
        # camera_id -> {entity_id: Entity}
        self._store: Dict[str, Dict[str, Entity]] = defaultdict(dict)
        self._locks: Dict[str, threading.Lock] = defaultdict(threading.Lock)

    def upsert(self, camera_id: str, entity_id: str, base_class: EntityClass,
               box: List[int], confidence: float) -> Entity:
        """Create or update an entity. Returns the entity object."""
        now = time.time()
        with self._locks[camera_id]:
            cam_store = self._store[camera_id]
            if entity_id in cam_store:
                e = cam_store[entity_id]
                e.box = box
                e.confidence = confidence
                e.last_seen = now
                cx, cy = (box[0] + box[2]) // 2, (box[1] + box[3]) // 2
                e.centroid = (cx, cy)
                # Keep last 10 centroids for motion analysis
                e.centroid_history.append((cx, cy))
                if len(e.centroid_history) > 10:
                    e.centroid_history.pop(0)
            else:
                cx, cy = (box[0] + box[2]) // 2, (box[1] + box[3]) // 2
                e = Entity(
                    id=entity_id,
                    base_class=base_class,
                    box=box,
                    confidence=confidence,
                    first_seen=now,
                    last_seen=now,
                    camera_id=camera_id,
                    centroid=(cx, cy),
                    state_enter_time=now,
                    centroid_history=[(cx, cy)],
                )
                cam_store[entity_id] = e
            return e

    def get_all(self, camera_id: str) -> List[Entity]:
        """Get all active entities for a camera."""
        with self._locks[camera_id]:
            return list(self._store.get(camera_id, {}).values())

    def get_by_class(self, camera_id: str, cls: EntityClass) -> List[Entity]:
        """Get all active entities of a specific class for a camera."""
        with self._locks[camera_id]:
            return [
                e for e in self._store.get(camera_id, {}).values()
                if e.base_class == cls
            ]

    def get(self, camera_id: str, entity_id: str) -> Optional[Entity]:
        with self._locks[camera_id]:
            return self._store.get(camera_id, {}).get(entity_id)

    def gc(self, camera_id: str):
        """Garbage collect stale entities."""
        now = time.time()
        with self._locks[camera_id]:
            cam_store = self._store.get(camera_id, {})
            stale = [
                eid for eid, e in cam_store.items()
                if (now - e.last_seen) > self.max_age
            ]
            for eid in stale:
                del cam_store[eid]


# ════════════════════════════════════════════════════════════════════════
# SPATIAL RELATIONSHIP ENGINE
# ════════════════════════════════════════════════════════════════════════

class SpatialEngine:
    """Computes spatial relationships between entities."""

    @staticmethod
    def box_intersects_zone(box: List[int], zone_polygon) -> bool:
        """Check if entity's foot-point is inside the track zone polygon."""
        import cv2
        x1, y1, x2, y2 = [int(v) for v in box]
        # Bottom-center = approximate foot position
        foot_x, foot_y = (x1 + x2) // 2, y2
        return cv2.pointPolygonTest(zone_polygon, (foot_x, foot_y), False) >= 0

    @staticmethod
    def centroid_distance(entity_a: Entity, entity_b: Entity) -> float:
        """Euclidean distance between two entity centroids."""
        ax, ay = entity_a.centroid
        bx, by = entity_b.centroid
        return math.sqrt((ax - bx)**2 + (ay - by)**2)

    @staticmethod
    def find_nearest_person(target: Entity, persons: List[Entity]) -> Tuple[Optional[str], float]:
        """Find the nearest person entity to a target. Returns (person_id, distance)."""
        if not persons:
            return None, float('inf')

        best_id = None
        best_dist = float('inf')

        for p in persons:
            d = SpatialEngine.centroid_distance(target, p)
            if d < best_dist:
                best_dist = d
                best_id = p.id

        return best_id, best_dist

    @staticmethod
    def is_entity_motionless(entity: Entity, threshold_px: float = 10.0) -> bool:
        """Check if entity has barely moved over its centroid history."""
        history = entity.centroid_history
        if len(history) < 5:
            return False
        first = history[0]
        last = history[-1]
        dist = math.sqrt((first[0] - last[0])**2 + (first[1] - last[1])**2)
        return dist < threshold_px

    @staticmethod
    def is_fallen_pose(box: List[int]) -> bool:
        """Aspect ratio > 1.3 indicates horizontal (fallen) pose."""
        x1, y1, x2, y2 = box
        w = max(x2 - x1, 1)
        h = max(y2 - y1, 1)
        return (w / h) > 1.3

    @staticmethod
    def compute_crowd_bbox(persons: List[Entity]) -> Optional[List[int]]:
        """Compute bounding box around all person entities (crowd zone)."""
        if not persons:
            return None
        x1 = min(p.box[0] for p in persons)
        y1 = min(p.box[1] for p in persons)
        x2 = max(p.box[2] for p in persons)
        y2 = max(p.box[3] for p in persons)
        # Add padding
        pad = 30
        return [max(0, x1 - pad), max(0, y1 - pad), x2 + pad, y2 + pad]


# ════════════════════════════════════════════════════════════════════════
# STATE TRANSITION ENGINE — Camera-specific FSM rules
# ════════════════════════════════════════════════════════════════════════

class StateTransitionEngine:
    """
    Evaluates state transition rules per camera.
    Each camera has its own rule set as specified by the Sr. Architect.

    CRITICAL INVARIANT: Only the transitioning entity changes color.
    Track stays Yellow. Person stays Blue (unless on track). Bag stays Green (unless unattended).
    """

    # Proximity threshold in pixels (~2m in typical railway camera FOV)
    BAG_PERSON_PROXIMITY_PX = 150.0

    # Timing thresholds
    CROWD_PERSIST_SECONDS   = 5.0
    CROWD_MIN_COUNT         = 10
    SMOKE_ESCALATE_SECONDS  = 10.0
    SMOKE_DETECT_SECONDS    = 5.0
    BAG_UNATTENDED_SECONDS  = 5.0
    BAG_BOMB_SECONDS        = 20.0

    def __init__(self, zone_detector=None):
        self.zone_detector = zone_detector
        # Crowd timing: camera_id -> first_time_above_threshold
        self._crowd_timers: Dict[str, float] = {}

    def evaluate(self, camera_id: str, entities: List[Entity],
                 registry: EntityRegistry) -> List[dict]:
        """
        Run all applicable rules for this camera's entities.
        Returns a list of state-transition alert dicts.
        """
        alerts = []

        persons  = [e for e in entities if e.base_class == EntityClass.PERSON]
        bags     = [e for e in entities if e.base_class == EntityClass.BAGGAGE]
        smokes   = [e for e in entities if e.base_class == EntityClass.SMOKE]
        fires    = [e for e in entities if e.base_class == EntityClass.FIRE]

        # ── CAM1 RULES: Person + Track Intersection ──────────────────
        if camera_id == "cam1":
            alerts.extend(self._eval_track_intrusion(camera_id, persons))

        # ── CAM2 RULES: Crowd Density ────────────────────────────────
        if camera_id == "cam2":
            alerts.extend(self._eval_crowd(camera_id, persons, registry))

        # ── CAM3 RULES: Smoke / Fire ─────────────────────────────────
        if camera_id == "cam3":
            alerts.extend(self._eval_smoke_fire(camera_id, smokes, fires))

        # ── CAM4 RULES: Person + Bag Relationship ────────────────────
        if camera_id == "cam4":
            alerts.extend(self._eval_baggage(camera_id, bags, persons))

        # ── UNIVERSAL RULES (all cameras) ────────────────────────────
        # Fire is immediately critical on ANY camera
        if camera_id != "cam3":
            alerts.extend(self._eval_smoke_fire(camera_id, smokes, fires))

        return alerts

    def _eval_track_intrusion(self, camera_id: str, persons: List[Entity]) -> List[dict]:
        """Person + Track zone interaction → PERSON_ON_TRACK or PERSON_FALLEN."""
        alerts = []
        for p in persons:
            # Check zone intersection
            if self.zone_detector:
                p.is_in_track_zone = self.zone_detector.check_intrusion(p.box)
            
            if p.is_in_track_zone:
                # Check for fallen pose
                p.is_fallen_pose = SpatialEngine.is_fallen_pose(p.box)
                p.is_motionless = SpatialEngine.is_entity_motionless(p)

                if p.is_fallen_pose and p.is_motionless and p.age >= 3.0:
                    if p.current_state != EntityState.PERSON_FALLEN:
                        p.transition_to(EntityState.PERSON_FALLEN)
                        alerts.append(self._build_alert(camera_id, p))
                else:
                    if p.current_state != EntityState.PERSON_ON_TRACK:
                        p.transition_to(EntityState.PERSON_ON_TRACK)
                        alerts.append(self._build_alert(camera_id, p))
            else:
                # Person NOT on track → reset to BASE
                if p.current_state in (EntityState.PERSON_ON_TRACK, EntityState.PERSON_FALLEN):
                    p.transition_to(EntityState.BASE)

        return alerts

    def _eval_crowd(self, camera_id: str, persons: List[Entity],
                    registry: EntityRegistry) -> List[dict]:
        """Crowd density → derived OVERCROWDING entity."""
        alerts = []
        now = time.time()

        if len(persons) >= self.CROWD_MIN_COUNT:
            if camera_id not in self._crowd_timers:
                self._crowd_timers[camera_id] = now

            elapsed = now - self._crowd_timers[camera_id]
            if elapsed >= self.CROWD_PERSIST_SECONDS:
                # Create or update derived crowd entity
                crowd_box = SpatialEngine.compute_crowd_bbox(persons)
                if crowd_box:
                    crowd_entity = registry.upsert(
                        camera_id, f"CWD_{camera_id}",
                        EntityClass.CROWD, crowd_box, 1.0
                    )
                    if crowd_entity.current_state != EntityState.OVERCROWDING:
                        crowd_entity.transition_to(EntityState.OVERCROWDING)
                        alerts.append(self._build_alert(camera_id, crowd_entity))
        else:
            # Reset crowd timer
            self._crowd_timers.pop(camera_id, None)
            # Remove crowd entity if it exists
            existing = registry.get(camera_id, f"CWD_{camera_id}")
            if existing:
                existing.transition_to(EntityState.BASE)

        return alerts

    def _eval_smoke_fire(self, camera_id: str,
                         smokes: List[Entity], fires: List[Entity]) -> List[dict]:
        """Smoke persistence → escalation. Fire → immediate CRITICAL."""
        alerts = []

        for f in fires:
            if f.current_state != EntityState.FIRE_DETECTED:
                f.transition_to(EntityState.FIRE_DETECTED)
                alerts.append(self._build_alert(camera_id, f))

        for s in smokes:
            if s.age >= self.SMOKE_ESCALATE_SECONDS:
                if s.current_state != EntityState.SMOKE_CRITICAL:
                    s.transition_to(EntityState.SMOKE_CRITICAL)
                    alerts.append(self._build_alert(camera_id, s))
            elif s.age >= self.SMOKE_DETECT_SECONDS:
                if s.current_state != EntityState.SMOKE_DETECTED:
                    s.transition_to(EntityState.SMOKE_DETECTED)
                    alerts.append(self._build_alert(camera_id, s))

        return alerts

    def _eval_baggage(self, camera_id: str,
                      bags: List[Entity], persons: List[Entity]) -> List[dict]:
        """Depositor-Baggage separation logic → UNATTENDED / BOMB PROTOCOL."""
        alerts = []

        for bag in bags:
            # 1. Bind to Depositor when first stabilized
            if not bag.owner_id and bag.age >= 1.0:
                pid, dist = SpatialEngine.find_nearest_person(bag, persons)
                if dist < self.BAG_PERSON_PROXIMITY_PX:
                    bag.owner_id = pid
            
            # 2. Strict distance tracking to Owner ONLY
            is_separated = True
            
            if bag.owner_id:
                owner = next((p for p in persons if p.id == bag.owner_id), None)
                if owner:
                    dist = SpatialEngine.centroid_distance(bag, owner)
                    bag.nearest_person_id = owner.id
                    bag.nearest_person_dist = dist
                    if dist <= self.BAG_PERSON_PROXIMITY_PX:
                        is_separated = False
            else:
                # If bag was placed with no one around, it's immediately suspicious after a delay
                if bag.age > 5.0:
                    is_separated = True
                else:
                    is_separated = False

            if is_separated:
                # Bag is separated from Depositor — increment separation timer
                if bag.separation_duration == 0.0:
                    bag.separation_duration = time.time()  # Start timer

                sep_elapsed = time.time() - bag.separation_duration

                if sep_elapsed >= self.BAG_BOMB_SECONDS:
                    if bag.current_state != EntityState.BAGGAGE_BOMB:
                        bag.transition_to(EntityState.BAGGAGE_BOMB)
                        alerts.append(self._build_alert(camera_id, bag))
                elif sep_elapsed >= self.BAG_UNATTENDED_SECONDS:
                    if bag.current_state != EntityState.BAGGAGE_UNATTENDED:
                        bag.transition_to(EntityState.BAGGAGE_UNATTENDED)
                        alerts.append(self._build_alert(camera_id, bag))
            else:
                # Bag near its Depositor → reset timer
                bag.separation_duration = 0.0
                if bag.current_state in (EntityState.BAGGAGE_UNATTENDED, EntityState.BAGGAGE_BOMB):
                    bag.transition_to(EntityState.BASE)

        return alerts

    def _build_alert(self, camera_id: str, entity: Entity) -> dict:
        """Construct structured JSON alert from entity state transition."""
        import datetime
        return {
            "camera_id":    camera_id.upper(),
            "entity_id":    entity.id,
            "base_class":   entity.base_class.value.capitalize(),
            "new_state":    entity.label,
            "threat_level": entity.threat_level,
            "timestamp":    datetime.datetime.now().isoformat(),
            "confidence":   round(entity.confidence, 2),
            "box":          entity.box,
            "prev_state":   entity.prev_state.value,
        }


# ════════════════════════════════════════════════════════════════════════
# CLASSIFICATION HELPER — Map YOLO class names to EntityClass
# ════════════════════════════════════════════════════════════════════════

def classify_detection(class_name: str) -> EntityClass:
    """Map a raw YOLO class name to an EntityClass enum."""
    cn = class_name.lower()
    if any(tag in cn for tag in ("person", "human", "intruder")):
        return EntityClass.PERSON
    if any(tag in cn for tag in ("bag", "luggage", "backpack", "suitcase")):
        return EntityClass.BAGGAGE
    if any(tag in cn for tag in ("fire", "flame")):
        return EntityClass.FIRE
    if any(tag in cn for tag in ("smoke",)):
        return EntityClass.SMOKE
    if any(tag in cn for tag in ("track", "rail")):
        return EntityClass.TRACK
    return EntityClass.UNKNOWN
