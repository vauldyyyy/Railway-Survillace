"""
train_uav.py
Fine-tunes YOLOv8n on UAV-RSOD dataset.
Optimized for CPU training.
"""

from ultralytics import YOLO
from pathlib import Path

def train_model():
    BACKEND_DIR = Path(__file__).resolve().parent
    # Load the Nano model
    model = YOLO("yolov8n.pt")

    # Portable path to the data yaml
    data_yaml = str(BACKEND_DIR / "datasets" / "uav_rsod.yaml")

    print(f"Starting training on CPU for UAV-RSOD...")
    
    results = model.train(
        data=data_yaml,
        epochs=10,
        imgsz=640,
        batch=4,
        device='cpu',
        workers=2,
        name='uav_cpu_run',
        # Augmentations
        blur=0.1,
        brightness=0.3,
        degrees=15.0,
        erasing=0.2,
        mixup=0.1 # Helps with overlapping obstacles in UAV views
    )

    print("\nTraining Complete.")
    print(f"mAP50: {results.results_dict['metrics/mAP50(B)']}")
    print(f"mAP50-95: {results.results_dict['metrics/mAP50-95(B)']}")
    # Best weights are saved in runs/detect/uav_cpu_run/weights/best.pt

if __name__ == "__main__":
    train_model()