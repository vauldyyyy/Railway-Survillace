"""
convert_coco_to_yolo.py — Convert RailFOD23 COCO JSON annotations to YOLO txt format.

Usage:
    cd backend
    python scripts/convert_coco_to_yolo.py

Expects:
    datasets/railfod23/Images/       (raw images from Figshare zip)
    datasets/railfod23/annotations/  (COCO JSON files)

Produces:
    datasets/railfod23/images/train/  + labels/train/
    datasets/railfod23/images/val/    + labels/val/
"""

import json
import os
import shutil
import random
from pathlib import Path

# ── Config ──────────────────────────────────────────────────────────────
DATASET_ROOT = Path(__file__).resolve().parent.parent / "datasets" / "railfod23"
RAW_IMAGES   = DATASET_ROOT / "Images"          # as extracted from zip
RAW_ANNOT    = DATASET_ROOT / "annotations"      # COCO JSON
TRAIN_SPLIT  = 0.8
SEED         = 42

# Output dirs
IMG_TRAIN = DATASET_ROOT / "images" / "train"
IMG_VAL   = DATASET_ROOT / "images" / "val"
LBL_TRAIN = DATASET_ROOT / "labels" / "train"
LBL_VAL   = DATASET_ROOT / "labels" / "val"


def find_coco_json(annot_dir: Path) -> Path:
    """Find the first .json file in the annotations folder."""
    jsons = list(annot_dir.glob("*.json"))
    if not jsons:
        raise FileNotFoundError(f"No .json found in {annot_dir}")
    print(f"[+] Using annotation file: {jsons[0].name}")
    return jsons[0]


def convert(dry_run=False):
    random.seed(SEED)

    # Locate the COCO JSON
    coco_path = find_coco_json(RAW_ANNOT)
    with open(coco_path, "r") as f:
        coco = json.load(f)

    # Build category mapping  →  {coco_cat_id: yolo_class_index}
    cat_map = {}
    print("[+] Categories found:")
    for i, cat in enumerate(coco["categories"]):
        cat_map[cat["id"]] = i
        print(f"    {i}: {cat['name']}  (coco id {cat['id']})")

    # Build image lookup  →  {image_id: filename, width, height}
    img_info = {}
    for img in coco["images"]:
        img_info[img["id"]] = {
            "file_name": img["file_name"],
            "width":     img["width"],
            "height":    img["height"],
        }

    # Group annotations by image_id
    annots_by_img = {}
    for ann in coco["annotations"]:
        iid = ann["image_id"]
        annots_by_img.setdefault(iid, []).append(ann)

    # Split image IDs
    all_ids = list(img_info.keys())
    random.shuffle(all_ids)
    split_idx = int(len(all_ids) * TRAIN_SPLIT)
    train_ids = set(all_ids[:split_idx])
    val_ids   = set(all_ids[split_idx:])

    print(f"[+] Total images: {len(all_ids)}  |  Train: {len(train_ids)}  |  Val: {len(val_ids)}")

    if dry_run:
        print("[DRY RUN] Would convert annotations. Exiting.")
        return

    # Create output dirs
    for d in [IMG_TRAIN, IMG_VAL, LBL_TRAIN, LBL_VAL]:
        d.mkdir(parents=True, exist_ok=True)

    converted = 0
    for img_id, info in img_info.items():
        fname = info["file_name"]
        w, h  = info["width"], info["height"]

        # Determine split
        is_train = img_id in train_ids
        img_dst  = IMG_TRAIN if is_train else IMG_VAL
        lbl_dst  = LBL_TRAIN if is_train else LBL_VAL

        # Copy image
        src_img = RAW_IMAGES / fname
        if not src_img.exists():
            # Try nested subdirs
            candidates = list(RAW_IMAGES.rglob(fname))
            if candidates:
                src_img = candidates[0]
            else:
                continue

        shutil.copy2(src_img, img_dst / fname)

        # Convert annotations to YOLO format
        label_file = lbl_dst / (Path(fname).stem + ".txt")
        lines = []
        for ann in annots_by_img.get(img_id, []):
            cls_idx = cat_map.get(ann["category_id"])
            if cls_idx is None:
                continue

            # COCO bbox = [x_min, y_min, width, height]
            bx, by, bw, bh = ann["bbox"]

            # → YOLO format: x_center, y_center, width, height (normalized 0-1)
            x_center = (bx + bw / 2) / w
            y_center = (by + bh / 2) / h
            nw = bw / w
            nh = bh / h

            # Clamp to [0, 1]
            x_center = max(0, min(1, x_center))
            y_center = max(0, min(1, y_center))
            nw = max(0, min(1, nw))
            nh = max(0, min(1, nh))

            lines.append(f"{cls_idx} {x_center:.6f} {y_center:.6f} {nw:.6f} {nh:.6f}")

        with open(label_file, "w") as f:
            f.write("\n".join(lines))

        converted += 1

    print(f"[✓] Converted {converted} images to YOLO format.")
    print(f"    Train: {IMG_TRAIN}")
    print(f"    Val:   {IMG_VAL}")


if __name__ == "__main__":
    import sys
    dry = "--dry-run" in sys.argv
    convert(dry_run=dry)
