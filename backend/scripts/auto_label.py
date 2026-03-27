"""
auto_label.py
Uses the trained YOLO-World model to auto-label extracted frames with pseudo-annotations.
Creates YOLO-format .txt label files alongside each image.
These are then merged with the existing RailFOD23 dataset for training.
"""

import sys
import os
import numpy as np
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

FRAMES_DIR = BASE_DIR / "datasets" / "frames"
LABELS_DIR = BASE_DIR / "datasets" / "auto_labeled" / "labels"
IMAGES_DIR = BASE_DIR / "datasets" / "auto_labeled" / "images"

# YOLO-World class mapping from RailFOD target classes
THREAT_CLASSES = [
    "person on track",       # 0
    "foreign object",        # 1
    "fire",                  # 2
    "smoke",                 # 3
    "abandoned baggage",     # 4
    "crowd",                 # 5
    "track obstruction",     # 6
    "animal",                # 7
]

# Confidence threshold — only keep high-confidence auto-labels
CONF_THRESHOLD = 0.30

# Max images to auto-label (to keep training time reasonable on CPU)
MAX_IMAGES = 3000


def label_frames():
    try:
        from ultralytics import YOLO
    except ImportError:
        print("[ERROR] ultralytics not installed. Run: pip install ultralytics")
        return

    print("[AUTO-LABEL] Loading YOLO-World model...")
    model_path = BASE_DIR / "yolov8s-worldv2.pt"
    if not model_path.exists():
        model_path = "yolov8s-worldv2.pt"
    
    model = YOLO(str(model_path))
    model.set_classes(THREAT_CLASSES)

    LABELS_DIR.mkdir(parents=True, exist_ok=True)
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    image_files = sorted(FRAMES_DIR.rglob("*.jpg"))[:MAX_IMAGES]
    print(f"[AUTO-LABEL] Labeling {len(image_files)} frames...")

    labeled = 0
    skipped = 0  # No detections above threshold

    for i, img_path in enumerate(image_files):
        try:
            results = model(str(img_path), verbose=False, conf=CONF_THRESHOLD)[0]
            
            # Build YOLO label string
            lines = []
            if results.boxes is not None and len(results.boxes) > 0:
                for box, conf, cls in zip(
                    results.boxes.xywhn.cpu().numpy(),
                    results.boxes.conf.cpu().numpy(),
                    results.boxes.cls.cpu().numpy(),
                ):
                    if conf >= CONF_THRESHOLD:
                        cx, cy, w, h = box
                        lines.append(f"{int(cls)} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}")
            
            if lines:
                # Save label
                label_file = LABELS_DIR / f"{img_path.stem}.txt"
                label_file.write_text("\n".join(lines))
                
                # Copy/symlink image to auto_labeled/images
                import shutil
                dst = IMAGES_DIR / img_path.name
                if not dst.exists():
                    shutil.copy2(str(img_path), str(dst))
                
                labeled += 1
            else:
                skipped += 1

            if (i + 1) % 100 == 0:
                print(f"  Progress: {i+1}/{len(image_files)} | Labeled: {labeled} | Empty: {skipped}")

        except Exception as e:
            print(f"  [WARN] {img_path.name}: {e}")
            skipped += 1

    print(f"\n{'='*60}")
    print(f"AUTO-LABELING COMPLETE")
    print(f"  Labeled: {labeled} images")
    print(f"  Empty  : {skipped} images")
    print(f"  Output : {IMAGES_DIR.parent}")
    print(f"\n  Next step: python backend/scripts/build_merged_dataset.py")


if __name__ == "__main__":
    label_frames()
