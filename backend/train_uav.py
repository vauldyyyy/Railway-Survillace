"""
train_uav.py
Fine-tunes YOLOv8n on the UAV-RSOD dataset for aerial obstacle detection.
Upgraded to 50 epochs with robust augmentation.
"""

import os
import shutil
from ultralytics import YOLO
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def train_model():
    uav_yaml = BASE_DIR / "datasets" / "uav_rsod" / "data.yaml"

    if not uav_yaml.exists():
        print(f"[UAV] Dataset not found at {uav_yaml}")
        print("[UAV] Skipping UAV training. Please download UAV-RSOD dataset.")
        return

    model = YOLO("yolov8n.pt")

    print(f"[UAV] Starting training: epochs=50, imgsz=640")
    results = model.train(
        data=str(uav_yaml),
        epochs=50,
        imgsz=640,
        batch=4,
        device="cpu",
        workers=2,
        name="uav_run",
        patience=12,
        # Augmentation for aerial views
        hsv_h=0.015,
        hsv_s=0.5,
        hsv_v=0.4,
        degrees=30.0,           # UAV can rotate significantly
        translate=0.1,
        scale=0.6,              # Wider scale range for zoom
        fliplr=0.5,
        flipud=0.3,             # Aerial images can be upside-down
        mosaic=1.0,
        mixup=0.1,
        blur=0.1,
        erasing=0.15,
        save=True,
        verbose=True,
    )

    models_dir = BASE_DIR / "models"
    models_dir.mkdir(exist_ok=True)

    best_weight = Path("runs/detect/uav_run/weights/best.pt")
    if best_weight.exists():
        shutil.copy(str(best_weight), str(models_dir / "uav_best.pt"))
        print(f"[UAV] ✓ Weights saved → {models_dir / 'uav_best.pt'}")

    print(f"\n[UAV] Training Complete.")
    try:
        print(f"  mAP50    : {results.results_dict['metrics/mAP50(B)']:.4f}")
        print(f"  mAP50-95 : {results.results_dict['metrics/mAP50-95(B)']:.4f}")
    except Exception:
        print("  (metrics not available)")


if __name__ == "__main__":
    train_model()