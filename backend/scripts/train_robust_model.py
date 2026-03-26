"""
Phase 4: Safety-Critical YOLOv8 Training Harness
Executes the explicit hyperparameter strategy required for Railway Environmental Tracking.
"""

from ultralytics import YOLO
import argparse
from pathlib import Path

def train_robust_model(dataset_yaml, epochs=100, batch=16, imgsz=1280):
    weights = 'yolov8m.pt' # YOLOv8-Medium (Optimal edge precision/FPS tradeoff)
    print(f"🚀 Initializing Phase 4 YOLOv8-Medium Environment Training on {dataset_yaml}...")
    model = YOLO(weights)
    
    # Phase 4 Parameter Application
    results = model.train(
        data=dataset_yaml,
        epochs=epochs,
        batch=batch,
        imgsz=imgsz,          # 1280 non-negotiable for track debris / FOD
        
        # --- Learning Rate Schedule ---
        optimizer='auto',
        cos_lr=True,          # Cosine annealing
        lr0=0.01,
        lrf=0.0001,           # Smooth final convergence
        
        # --- Freeze Strategy ---
        # Freeze backbone (layers 0-9) to retain COCO spatial understanding,
        # forcing the head layers to adapt strictly to the Railway anomalies.
        freeze=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
        
        # --- Hardware & Precision ---
        half=True,            # FP16 Mixed Precision
        device=0,             # Target Primary GPU
        
        # --- Augmentation Override ---
        # Disable native severe spatial transforms because we handled these offline
        # via the Phase 3 Albumentations pipeline (augment_dataset.py)
        degrees=0.0,
        translate=0.0,
        scale=0.0,
        shear=0.0,
        perspective=0.0,
        flipud=0.0,
        fliplr=0.5,           # Keep horizontal flip
        mosaic=0.0,
        mixup=0.0,
        
        # --- Class Weighting & Hard Example Proxies ---
        # Up-weight classification and DFL (Distribution Focal Loss) to punish 
        # false positives on 'Normal/Background' images containing mere noise.
        cls=1.5,          
        box=7.5,
        dfl=1.5,
        
        project="runs/railguard_phase4",
        name="robust_v8m_env"
    )
    
    print("\n✅ Training Validation Curve Complete. Entering High-Performance Export Phase...")
    
    # --- PHASE 4 EXPORTS ---
    
    # 1. Export ONNX (For standard cross-platform edge)
    print("-> Exporting FP16 ONNX Graph...")
    try:
        onnx_path = model.export(format='onnx', imgsz=imgsz, half=True, simplify=True)
        print(f"   ONNX success: {onnx_path}")
    except Exception as e:
        print(f"   ONNX fail: {e}")
    
    # 2. Export TensorRT Engine (For maximum Jetson/DeepStream inference)
    print("-> Exporting TensorRT Engine (workspace=8GB)...")
    try:
        trt_path = model.export(format='engine', imgsz=imgsz, half=True, workspace=8)
        print(f"   TensorRT success: {trt_path}")
    except Exception as e:
        print(f"   TensorRT fail (Requires NVIDIA TRT toolchain on host OS): {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Phase 4: Railway YOLOv8 Environment Optimizer")
    parser.add_argument("--data", type=str, required=True, help="Path to the Roboflow dataset YAML (e.g., datasets/rail_roboflow/data.yaml)")
    parser.add_argument("--epochs", type=int, default=100, help="Epoch boundary for cosine LR")
    parser.add_argument("--imgsz", type=int, default=1280, help="Inference resolution constraint")
    
    args = parser.parse_args()
    train_robust_model(args.data, args.epochs, batch=16, imgsz=args.imgsz)
