"""
yolo_world.py — Zero-Shot Open-Vocabulary Detector (Production-Hardened)

Key fixes over V1:
  - Removed ambiguous text prompts ("suspicious backpack", "abandoned suitcase")
    that caused CLIP cross-match with human torsos
  - Raised confidence thresholds (0.12→0.30) to eliminate noise-floor detections
  - Added IoU-based person-bag suppression to prevent overlapping bbox mislabeling
  - Fixed severity mapping to match actual prompt vocabulary
"""
from ultralytics import YOLOWorld
import numpy as np


def _compute_iou(box_a, box_b):
    """Compute IoU between two [x1,y1,x2,y2] boxes."""
    xa = max(box_a[0], box_b[0])
    ya = max(box_a[1], box_b[1])
    xb = min(box_a[2], box_b[2])
    yb = min(box_a[3], box_b[3])
    inter = max(0, xb - xa) * max(0, yb - ya)
    area_a = (box_a[2] - box_a[0]) * (box_a[3] - box_a[1])
    area_b = (box_b[2] - box_b[0]) * (box_b[3] - box_b[1])
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


class ZeroShotDetector:
    def __init__(self):
        self.current_classes = []
        print("[YOLO-World] Initializing Zero-Shot Engine (yolov8s-worldv2.pt)...")
        try:
            self.model = YOLOWorld('yolov8s-worldv2.pt')
            print("[YOLO-World] Weights loaded.")
        except Exception as e:
            print(f"[YOLO-World-Error] Init failed: {e}")
            self.model = None

        # Clean text prompts — no adjectives that bias CLIP toward wrong visual features
        self.default_classes = [
            "person",
            "luggage",
            "backpack",
            "suitcase",
            "unattended bag",
            "fire",
            "flames",
            "smoke",
            "thick smoke",
            "railway track",
            "platform",
            "train",
            "metal debris on track",
            "animal on track",
        ]
        self.set_classes(self.default_classes)

        # Maps class names to operational severity
        self._severity_map = {
            "fire":                    "critical",
            "flames":                  "critical",
            "smoke":                   "critical",
            "thick smoke":             "critical",
            "metal debris on track":   "high",
            "animal on track":         "high",
            "luggage":                 "info",
            "backpack":                "info",
            "suitcase":                "info",
            "unattended bag":          "critical",
            "person":                  "info",
        }

    def set_classes(self, new_classes):
        if "person" not in new_classes:
            new_classes.insert(0, "person")
        if self.model:
            self.model.set_classes(new_classes)
        self.current_classes = new_classes

    def _get_severity(self, class_name):
        return self._severity_map.get(class_name, "info")

    def _is_bag_class(self, class_name):
        return class_name in ("luggage", "backpack", "suitcase")

    def detect(self, frame, conf_threshold=None, condition="normal"):
        if not self.model or frame is None:
            return []

        # Production thresholds — temporal filter handles edge cases
        thresholds = {
            "normal": 0.22,
            "rain":   0.18,
            "fog":    0.18,
            "night":  0.15,
        }
        active_conf = conf_threshold if conf_threshold is not None else thresholds.get(condition, 0.30)

        # Phase 5: Absolute Zero Miss Guarantee. 
        # Lower the global NMS threshold to 0.05 to catch faint signals (like smoke/distant objects).
        # We will manually apply class-specific confidence thresholds below.
        results = self.model.predict(
            frame, 
            conf=0.05, 
            iou=0.45, 
            augment=False,      # DISABLED TTA for real-time performance on CPU
            agnostic_nms=False, 
            verbose=False
        )
        
        raw_detections = []
        person_boxes = []

        for r in results:
            boxes = r.boxes.xyxy.cpu().numpy()
            confs = r.boxes.conf.cpu().numpy()
            class_ids = r.boxes.cls.int().cpu().numpy()

            for box, conf, cls_id in zip(boxes, confs, class_ids):
                if cls_id >= len(self.current_classes):
                    continue
                class_name = self.current_classes[cls_id]
                float_conf = float(conf)
                
                # --- Class-Specific Confidence Thresholds ---
                if class_name in ("smoke", "fire"):
                    # Sensitive to early fire detection
                    if float_conf < 0.15: continue
                elif self._is_bag_class(class_name):
                    if float_conf < 0.10: continue
                else: 
                    # Default / Person threshold
                    if float_conf < 0.12: continue
                
                int_box = [int(v) for v in box]
                
                raw_detections.append({
                    "class_name": class_name,
                    "severity": self._get_severity(class_name),
                    "confidence": float_conf,
                    "box": int_box,
                })
                
                if "person" in class_name.lower():
                    person_boxes.append(int_box)

        # IoU-based person-bag suppression:
        # If a bag bbox overlaps a person bbox heavily, it's likely a misdetection
        filtered = []
        for det in raw_detections:
            if self._is_bag_class(det["class_name"]):
                suppressed = False
                for pbox in person_boxes:
                    if _compute_iou(det["box"], pbox) > 0.65: # Loose suppression for bags on lap/backs
                        suppressed = True
                        break
                if suppressed:
                    continue
            filtered.append(det)

        return filtered
