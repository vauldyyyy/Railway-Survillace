import os
import random
import shutil
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
FRAMES_DIR = BASE_DIR / "datasets" / "frames"
LABELS_DIR = BASE_DIR / "datasets" / "auto_labeled" / "labels"
OUT_DIR = BASE_DIR / "datasets" / "hard_negatives"
OUT_IMAGES = OUT_DIR / "images"
OUT_LABELS = OUT_DIR / "labels"

def generate_hard_negatives(count=500):
    print(f"[HARDENING] Starting Task 3: Generating {count} hard negatives...")
    
    # 1. Find all frames that DO NOT have labels (potential empty tracks)
    all_frames = list(FRAMES_DIR.rglob("*.jpg"))
    labeled_names = {p.stem for p in LABELS_DIR.glob("*.txt")}
    
    # Filter for frames where "parent__filename" is NOT in labeled_names
    empty_candidates = []
    for f in all_frames:
        unique_name = f"{f.parent.name}__{f.stem}"
        if unique_name not in labeled_names:
            empty_candidates.append(f)
            
    if not empty_candidates:
        print("[WARN] No empty frames found. Check path.")
        return

    print(f"  Found {len(empty_candidates)} candidate empty frames.")
    
    # 2. Select diverse sample
    # Prioritize different folders (categories)
    random.shuffle(empty_candidates)
    selected = empty_candidates[:count]
    
    # 3. Save as hard negatives
    OUT_IMAGES.mkdir(parents=True, exist_ok=True)
    OUT_LABELS.mkdir(parents=True, exist_ok=True)
    
    for i, img_path in enumerate(selected):
        unique_name = f"hard_neg_{img_path.parent.name}__{img_path.stem}"
        dst_img = OUT_IMAGES / f"{unique_name}.jpg"
        dst_lbl = OUT_LABELS / f"{unique_name}.txt"
        
        # Copy image
        shutil.copy2(str(img_path), str(dst_img))
        
        # Create empty label file (YOLO format for background)
        dst_lbl.touch()
        
        if (i+1) % 50 == 0:
            print(f"  Processed {i+1}/{count}...")

    print(f"[OK] Task 3 Complete: {len(selected)} hard negatives generated in {OUT_DIR}")

if __name__ == "__main__":
    generate_hard_negatives(500)
