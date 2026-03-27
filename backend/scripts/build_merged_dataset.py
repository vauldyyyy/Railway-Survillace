"""
build_merged_dataset.py
Merges RailFOD23 + auto-labeled YouTube frames into a single YOLO training dataset.
Outputs: datasets/merged/ with train/val splits and merged.yaml
"""

import os
import shutil
import random
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATASETS_DIR = BASE_DIR / "datasets"

MERGED_DIR = DATASETS_DIR / "merged"
TRAIN_IMG  = MERGED_DIR / "images" / "train"
VAL_IMG    = MERGED_DIR / "images" / "val"
TRAIN_LBL  = MERGED_DIR / "labels" / "train"
VAL_LBL    = MERGED_DIR / "labels" / "val"

VAL_SPLIT = 0.15  # 15% validation

# Class names — unified across all data sources
CLASS_NAMES = [
    "person_on_track",
    "foreign_object",
    "fire",
    "smoke",
    "abandoned_baggage",
    "crowd",
    "track_obstruction",
    "animal",
]

SOURCES = [
    # (images_dir, labels_dir, source_name)
    (DATASETS_DIR / "railfod23" / "images", DATASETS_DIR / "railfod23" / "labels", "railfod23"),
    (DATASETS_DIR / "auto_labeled" / "images", DATASETS_DIR / "auto_labeled" / "labels", "auto_labeled"),
    (DATASETS_DIR / "uav_rsod" / "images", DATASETS_DIR / "uav_rsod" / "labels", "uav_rsod"),
]

# Roboflow merged dataset (built by download_roboflow_datasets.py)
ROBOFLOW_MERGED_DIR = DATASETS_DIR / "roboflow" / "merged"


def copy_split(img_path: Path, lbl_path: Path, is_val: bool):
    img_dst = (VAL_IMG if is_val else TRAIN_IMG) / img_path.name
    lbl_dst = (VAL_LBL if is_val else TRAIN_LBL) / lbl_path.name
    shutil.copy2(str(img_path), str(img_dst))
    if lbl_path.exists():
        shutil.copy2(str(lbl_path), str(lbl_dst))
    else:
        lbl_dst.write_text("")  # Empty label = background image


def _add_source(images_dir: Path, labels_dir: Path, source_name: str, total_train: int, total_val: int):
    """Process a single data source into the merged dataset."""
    if not images_dir.exists():
        print(f"  [SKIP] {source_name}: {images_dir} — not found")
        return total_train, total_val

    images = sorted(images_dir.glob("*.jpg")) + sorted(images_dir.glob("*.png"))
    random.shuffle(images)
    split = int(len(images) * VAL_SPLIT)
    val_set = set(i.name for i in images[:split])

    for img in images:
        lbl = labels_dir / (img.stem + ".txt")
        is_val = img.name in val_set
        try:
            copy_split(img, lbl, is_val)
            if is_val:
                total_val += 1
            else:
                total_train += 1
        except Exception as e:
            print(f"  [WARN] {img.name}: {e}")

    print(f"  [+] {source_name}: {len(images)} images processed")
    return total_train, total_val


def main():
    for d in [TRAIN_IMG, VAL_IMG, TRAIN_LBL, VAL_LBL]:
        d.mkdir(parents=True, exist_ok=True)

    total_train = total_val = 0

    # 1. Standard sources (railfod23, auto_labeled, uav_rsod)
    for img_dir, lbl_dir, src_name in SOURCES:
        total_train, total_val = _add_source(img_dir, lbl_dir, src_name, total_train, total_val)

    # 2. Roboflow merged dataset (already remapped to unified classes)
    if ROBOFLOW_MERGED_DIR.exists():
        roboflow_train_img = ROBOFLOW_MERGED_DIR / "images" / "train"
        roboflow_val_img = ROBOFLOW_MERGED_DIR / "images" / "val"
        roboflow_train_lbl = ROBOFLOW_MERGED_DIR / "labels" / "train"
        roboflow_val_lbl = ROBOFLOW_MERGED_DIR / "labels" / "val"

        for img_dir, lbl_dir, split_name in [
            (roboflow_train_img, roboflow_train_lbl, "roboflow_train"),
            (roboflow_val_img, roboflow_val_lbl, "roboflow_val"),
        ]:
            is_val = "val" in split_name
            if img_dir.exists():
                images = sorted(img_dir.glob("*.jpg")) + sorted(img_dir.glob("*.png"))
                for img in images:
                    lbl = lbl_dir / (img.stem + ".txt")
                    try:
                        copy_split(img, lbl, is_val)
                        if is_val:
                            total_val += 1
                        else:
                            total_train += 1
                    except Exception as e:
                        print(f"  [WARN] {img.name}: {e}")
                print(f"  ✓ {split_name}: {len(images)} images processed")
    else:
        print(f"  [INFO] Roboflow merged dataset not found at {ROBOFLOW_MERGED_DIR}")
        print(f"         Run: python backend/scripts/download_roboflow_datasets.py")

    # 3. Individual Roboflow datasets (fire-smoke already present)
    roboflow_dir = DATASETS_DIR / "roboflow"
    if roboflow_dir.exists():
        for subdir in roboflow_dir.iterdir():
            if not subdir.is_dir() or subdir.name == "merged":
                continue
            for split in ["train", "valid", "val"]:
                img_dir = subdir / split / "images"
                lbl_dir = subdir / split / "labels"
                if img_dir.exists():
                    total_train, total_val = _add_source(
                        img_dir, lbl_dir, f"roboflow/{subdir.name}", total_train, total_val
                    )

    # Write merged.yaml
    yaml_content = f"""# RailGuard AI — Merged Training Dataset
# Auto-generated by build_merged_dataset.py

path: {MERGED_DIR.as_posix()}
train: images/train
val: images/val

nc: {len(CLASS_NAMES)}
names: {CLASS_NAMES}
"""
    yaml_path = MERGED_DIR / "merged.yaml"
    yaml_path.write_text(yaml_content)

    print(f"\n{'='*60}")
    print(f"MERGED DATASET BUILT")
    print(f"  Train: {total_train} images")
    print(f"  Val  : {total_val} images")
    print(f"  YAML : {yaml_path}")
    print(f"\n  Next step: python backend/train_railfod.py")


if __name__ == "__main__":
    main()
