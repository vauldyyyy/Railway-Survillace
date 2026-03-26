import os
import cv2
import glob
from pathlib import Path
import albumentations as A

# The exact adversarial augmentation pipeline for generating robust training data
railway_augment = A.Compose([
    # CCTV compression simulation
    A.ImageCompression(quality_lower=30, quality_upper=70, p=0.5),
    
    # Lighting conditions
    A.OneOf([
        A.RandomBrightnessContrast(brightness_limit=(-0.4, 0.1), p=1),  # night
        A.RandomBrightnessContrast(brightness_limit=(0.1, 0.3), p=1),   # overexposed
    ], p=0.4),
    
    # Weather simulation
    A.OneOf([
        A.RandomRain(slant_lower=-10, slant_upper=10, drop_length=15, drop_width=1, drop_color=(200,200,200), p=1),
        A.RandomFog(fog_coef_lower=0.2, fog_coef_upper=0.5, p=1),
    ], p=0.3),
    
    # Motion blur (camera shake / fast movement)
    A.OneOf([
        A.MotionBlur(blur_limit=(5, 15), p=1),
        A.GaussianBlur(blur_limit=(3, 7), p=1),
    ], p=0.4),
    
    # Sensor noise
    A.GaussNoise(var_limit=(500, 2500), p=0.3),
    A.ISONoise(color_shift=(0.01, 0.05), intensity=(0.1, 0.5), p=0.3),
    
    # Adversarial patch simulation (Security demo)
    A.CoarseDropout(
        max_holes=8, max_height=32, max_width=32,
        min_holes=1, min_height=8, min_width=8,
        fill_value=0, p=0.4
    ),
    
    # Perspective / camera angle variation
    A.Perspective(scale=(0.05, 0.15), p=0.3),
    A.ShiftScaleRotate(shift_limit=0.05, scale_limit=0.1, rotate_limit=5, p=0.3),
    
]) # Note: For offline augmentation without bounding boxes, we drop bbox_params temporarily or assume labels are adjusted via Roboflow natively.

def augment_directory(input_dir, output_dir, multiplier=2):
    """
    Reads all existing frames in input_dir and generates `multiplier` corrupted versions
    to synthetically inflate the dataset size for Roboflow uploaded.
    """
    os.makedirs(output_dir, exist_ok=True)
    images = glob.glob(os.path.join(input_dir, "*.jpg"))
    
    print(f"Found {len(images)} images in {input_dir}. Generating {multiplier}x augmented copies...")
    
    for img_path in images:
        basename = os.path.basename(img_path)
        name, ext = os.path.splitext(basename)
        
        # Read image
        image = cv2.imread(img_path)
        if image is None: continue
            
        # Generate N augmented versions
        for i in range(multiplier):
            augmented = railway_augment(image=image)
            aug_img = augmented["image"]
            
            out_name = f"{name}_aug_{i}{ext}"
            cv2.imwrite(os.path.join(output_dir, out_name), aug_img)
            
    print(f"✓ Augmentation complete for {input_dir}")

if __name__ == "__main__":
    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    FRAMES_DIR = BASE_DIR / "datasets" / "frames"
    AUG_DIR = BASE_DIR / "datasets" / "frames_augmented"
    
    if not FRAMES_DIR.exists():
        print(f"No frames found in {FRAMES_DIR}. Please run extract_frames.py first.")
    else:
        # Augment all subdirectories
        for subdir in [x for x in FRAMES_DIR.iterdir() if x.is_dir()]:
            augment_directory(str(subdir), str(AUG_DIR / subdir.name))
