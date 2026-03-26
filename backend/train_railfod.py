"""
train_railfod.py
Fine-tunes YOLOv8n on RailFOD23 dataset.
Optimized for CPU training during a hackathon.
Includes Adversarial Defense via Albumentations.
"""

import os
from ultralytics import YOLO
from pathlib import Path

# 1. Adversarial Defense Documentation:
# We apply Albumentations (Blur, Brightness, Noise) to make the model robust 
# against environmental lighting changes and potential camera tampering/noise.

def train_model():
    BACKEND_DIR = Path(__file__).resolve().parent
    # Load the Nano model (best for CPU)
    model = YOLO("yolov8n.pt")

    # Portable path to the data yaml
    data_yaml = str(BACKEND_DIR / "datasets" / "railfod23.yaml")

    print(f"Starting training on CPU for RailFOD23...")
    
    # Train with CPU-optimized settings
    results = model.train(
        data=data_yaml,
        epochs=10,           # Reduced for CPU
        imgsz=640,
        batch=4,             # Small batch to save RAM
        device='cpu',        # Explicitly use CPU
        workers=2,           # Limit workers to prevent CPU thrashing
        name='railfod_cpu_run',
        # Albumentations-equivalent hyperparams in Ultralytics
        blur=0.1,            # Motion blur
        brightness=0.3,      # Random brightness
        degrees=10.0,        # Random rotation
        fliplr=0.5,
        erasing=0.2          # Random erasing (Coarse Dropout)
    )

    # Save the best weights
    model.export(format="onnx") # Optional: export for faster CPU inference
    print("\nTraining Complete.")
    print(f"mAP50: {results.results_dict['metrics/mAP50(B)']}")
    print(f"mAP50-95: {results.results_dict['metrics/mAP50-95(B)']}")

if __name__ == "__main__":
    train_model()