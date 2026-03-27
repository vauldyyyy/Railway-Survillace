"""
train_railfod.py
Fine-tunes YOLOv8s on merged data (RailFOD23 + YouTube frames).
If RailFOD23 images are missing, trains only on YouTube-extracted frames.
Upgraded from nano to small model, 50 epochs, max augmentation.
"""

import os
import shutil
from ultralytics import YOLO
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def count_images(directory: Path) -> int:
    if not directory.exists():
        return 0
    return len(list(directory.glob("*.jpg")) + list(directory.glob("*.png")))


def train_model():
    models_dir = BASE_DIR / "models"
    models_dir.mkdir(exist_ok=True)

    # Priority: merged > railfod23 > youtube frames only
    merged_yaml  = BASE_DIR / "datasets" / "merged" / "merged.yaml"
    railfod_yaml = BASE_DIR / "datasets" / "railfod23" / "data.yaml"
    youtube_yaml = BASE_DIR / "datasets" / "youtube_frames" / "data.yaml"

    railfod_train_count = count_images(BASE_DIR / "datasets" / "railfod23" / "images" / "train")
    merged_train_count  = count_images(BASE_DIR / "datasets" / "merged" / "images" / "train")

    if merged_yaml.exists() and merged_train_count > 0:
        data_yaml  = str(merged_yaml)
        model_name = "railfod_merged"
        print(f"[RailFOD] ✓ Using MERGED dataset ({merged_train_count} training images)")

    elif railfod_yaml.exists() and railfod_train_count > 0:
        data_yaml  = str(railfod_yaml)
        model_name = "railfod_run"
        print(f"[RailFOD] Using RailFOD23 only ({railfod_train_count} training images)")

    elif youtube_yaml.exists():
        data_yaml  = str(youtube_yaml)
        model_name = "railfod_youtube"
        yt_count   = count_images(BASE_DIR / "datasets" / "youtube_frames" / "images" / "train")
        print(f"[RailFOD] Using YouTube-only dataset ({yt_count} training images)")

    else:
        print("[RailFOD] ✗ No training dataset found. Please run:")
        print("  1. python backend/scripts/download_youtube_datasets.py")
        print("  2. python backend/scripts/extract_frames.py")
        print("  3. python backend/scripts/auto_label.py")
        print("  4. python backend/scripts/build_merged_dataset.py")
        print("[RailFOD] Or download RailFOD23 from: https://doi.org/10.6084/m9.figshare.24180738")
        return

    # YOLOv8s — much better than nano for production
    model = YOLO("yolov8s.pt")

    print(f"[RailFOD] Starting training (epochs=50, imgsz=640, YOLOv8s)...")
    results = model.train(
        data=data_yaml,
        epochs=50,
        imgsz=640,
        batch=8,
        device="cpu",
        workers=2,
        name=model_name,
        patience=15,
        # Max augmentation for railway robustness
        hsv_h=0.015,
        hsv_s=0.7,
        hsv_v=0.4,
        degrees=10.0,
        translate=0.1,
        scale=0.5,
        shear=2.0,
        perspective=0.0005,
        flipud=0.1,
        fliplr=0.5,
        mosaic=1.0,
        mixup=0.15,
        blur=0.1,
        erasing=0.2,
        lr0=0.01,
        lrf=0.01,
        momentum=0.937,
        weight_decay=0.0005,
        warmup_epochs=3.0,
        save=True,
        save_period=10,
        verbose=True,
        plots=True,
    )

    # Migrate the best weights
    best_weight = Path("runs/detect") / model_name / "weights" / "best.pt"
    if best_weight.exists():
        shutil.copy(str(best_weight), str(models_dir / "railfod_best.pt"))
        print(f"[RailFOD] ✓ Weights saved → {models_dir / 'railfod_best.pt'}")

    print(f"\n[RailFOD] Training Complete.")
    try:
        print(f"  mAP50    : {results.results_dict['metrics/mAP50(B)']:.4f}")
        print(f"  mAP50-95 : {results.results_dict['metrics/mAP50-95(B)']:.4f}")
    except Exception:
        print("  (metrics not available in this ultralytics version)")


if __name__ == "__main__":
    train_model()