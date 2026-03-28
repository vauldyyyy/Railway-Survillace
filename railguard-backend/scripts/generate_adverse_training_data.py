# backend/scripts/generate_adverse_training_data.py
import cv2
import numpy as np
import albumentations as A
import os
from pathlib import Path

# -- Condition-Specific Augmentors --

night_aug = A.Compose([
    A.RandomBrightnessContrast(
        brightness_limit=(-0.7, -0.3),
        contrast_limit=(-0.2, 0.1), p=1.0
    ),
    A.ISONoise(color_shift=(0.05, 0.15),
               intensity=(0.4, 0.9), p=0.8),
    A.GaussNoise(var_limit=(1000, 4000), p=0.5),
], bbox_params=A.BboxParams(format='yolo',
   label_fields=['labels'], min_visibility=0.2))

fog_aug = A.Compose([
    A.RandomFog(fog_coef_lower=0.4,
                fog_coef_upper=0.8, p=1.0),
    A.RandomBrightnessContrast(
        brightness_limit=(0.0, 0.2), p=0.5),
    A.GaussianBlur(blur_limit=(3, 7), p=0.4),
], bbox_params=A.BboxParams(format='yolo',
   label_fields=['labels'], min_visibility=0.2))

rain_aug = A.Compose([
    A.RandomRain(
        slant_lower=-20, slant_upper=20,
        drop_length=25, drop_width=2,
        drop_color=(180, 180, 180),
        blur_value=5, p=1.0
    ),
    A.MotionBlur(blur_limit=(5, 11), p=0.4),
    A.GaussNoise(var_limit=(200, 800), p=0.3),
], bbox_params=A.BboxParams(format='yolo',
   label_fields=['labels'], min_visibility=0.2))

smoke_aug = A.Compose([
    A.RandomFog(fog_coef_lower=0.3,
                fog_coef_upper=0.6, p=1.0),
    A.RandomBrightnessContrast(
        brightness_limit=(-0.2, 0.1), p=0.7),
    A.GaussNoise(var_limit=(500, 2000), p=0.5),
    A.MotionBlur(blur_limit=(3, 9), p=0.3),
], bbox_params=A.BboxParams(format='yolo',
   label_fields=['labels'], min_visibility=0.2))

combined_aug = A.Compose([
    # Rain + night combined (worst case)
    A.RandomRain(p=0.7),
    A.RandomBrightnessContrast(
        brightness_limit=(-0.5, -0.2), p=0.8),
    A.MotionBlur(blur_limit=(9, 21), p=0.5),
    A.ISONoise(intensity=(0.3, 0.7), p=0.6),
    A.ImageCompression(
        quality_lower=15, quality_upper=45, p=0.7),
], bbox_params=A.BboxParams(format='yolo',
   label_fields=['labels'], min_visibility=0.2))

CONDITIONS = {
    "night":    (night_aug,    400),
    "fog":      (fog_aug,      400),
    "rain":     (rain_aug,     400),
    "smoke":    (smoke_aug,    300),
    "combined": (combined_aug, 500),  # rain+night is hardest
}

def load_labels(label_path):
    if not os.path.exists(label_path):
        return []
    with open(label_path) as f:
        lines = f.read().strip().split('\n')
    labels = []
    bboxes = []
    for line in lines:
        if not line: continue
        parts = line.split()
        labels.append(int(parts[0]))
        bboxes.append([float(x) for x in parts[1:]])
    return labels, bboxes

def main():
    BASE_DIR = Path(__file__).resolve().parent.parent
    source_dir = BASE_DIR / "datasets" / "merged" / "images"
    label_dir  = BASE_DIR / "datasets" / "merged" / "labels"
    out_base   = BASE_DIR / "datasets" / "adverse_augmented"

    if not source_dir.exists():
        print(f"[Error] Source dir not found: {source_dir}")
        return

    total_generated = 0
    print(f"[*] Starting adverse augmentation on: {source_dir}")

    for condition, (augmentor, target_count) in CONDITIONS.items():
        img_out = out_base / condition / "images"
        lbl_out = out_base / condition / "labels"
        img_out.mkdir(parents=True, exist_ok=True)
        lbl_out.mkdir(parents=True, exist_ok=True)
        
        images = list(source_dir.glob("*.jpg")) + list(source_dir.glob("*.png"))
        if not images:
            print(f"[Warning] No images in {source_dir}")
            continue
            
        np.random.shuffle(images)
        
        generated = 0
        limit_reached = False
        while generated < target_count and not limit_reached:
            for img_path in images:
                if generated >= target_count:
                    limit_reached = True
                    break
                
            img = cv2.imread(str(img_path))
            if img is None:
                continue
                
            label_path = label_dir / (img_path.stem + ".txt")
            labels, bboxes = load_labels(str(label_path))
                
            try:
                result = augmentor(
                    image=img,
                    bboxes=bboxes if bboxes else [],
                    labels=labels if labels else []
                )
            except Exception as e:
                continue
            
            out_name = f"{condition}_{generated:04d}"
            cv2.imwrite(str(img_out / f"{out_name}.jpg"), result['image'])
            
            with open(lbl_out / f"{out_name}.txt", 'w') as f:
                for label, bbox in zip(
                    result['labels'], result['bboxes']
                ):
                    f.write(f"{label} {' '.join(map(str, bbox))}\n")
            
            generated += 1
        
        total_generated += generated
        print(f"[✓] {condition.upper()}: {generated} images generated")

    print(f"\n[✓] Total adverse images: {total_generated}")
    print(f"[✓] Saved to: {out_base}")

if __name__ == "__main__":
    main()
