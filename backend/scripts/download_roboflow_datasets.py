"""
download_roboflow_datasets.py
Downloads railway-relevant datasets from Roboflow Universe using the official SDK.
Each dataset is saved to datasets/roboflow/<name>/ in YOLO format.

Usage:
  python backend/scripts/download_roboflow_datasets.py
  python backend/scripts/download_roboflow_datasets.py --api-key YOUR_KEY
  python backend/scripts/download_roboflow_datasets.py --datasets fire-smoke

Environment:
  ROBOFLOW_API_KEY — Your Roboflow API key (https://app.roboflow.com/settings/api)
"""

import argparse
import os
import sys
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATASETS_DIR = BASE_DIR.parent / "datasets" / "roboflow"

# ── Railway-Relevant Roboflow Dataset Registry ──
# Each entry: (workspace, project, version, format)
# These are curated datasets covering the core surveillance threat categories.
DATASET_REGISTRY = {
    "fire-smoke": {
        "workspace": "sayed-gamall",
        "project": "fire-smoke-detection-yolov11",
        "version": 2,
        "format": "yolov11",
        "description": "Fire and Smoke detection (9k+ images) — manually downloaded",
        "classes": ["Fire", "Smoke"],
        "target_class_map": {
            "Fire": "fire",
            "Smoke": "smoke",
        },
    },
    "person-detect": {
        "workspace": "personalprojects",
        "project": "person-detect",
        "version": 4,
        "format": "yolov8",
        "description": "Person detection for crowd monitoring",
        "classes": ["person"],
        "target_class_map": {
            "person": "person",
        },
    },
    "fall-detection": {
        "workspace": "personalprojects",
        "project": "fall-detection",
        "version": 2,
        "format": "yolov8",
        "description": "Fall/lying person detection",
        "classes": ["Fall Detected"],
        "target_class_map": {
            "Fall Detected": "person_fallen",
        },
    },
}


def download_dataset(api_key: str, name: str, config: dict) -> bool:
    """Download a single dataset from Roboflow Universe."""
    import zipfile
    import time

    try:
        from roboflow import Roboflow
    except ImportError:
        print("[ERROR] roboflow package not installed. Run: pip install roboflow")
        return False

    workspace = config["workspace"]
    project = config["project"]
    version = config["version"]
    fmt = config["format"]

    output_dir = DATASETS_DIR / name
    if output_dir.exists() and any(output_dir.iterdir()):
        # Check if it's a properly extracted dataset (has train/ or valid/ dirs)
        has_images = any(
            (output_dir / d / "images").exists()
            for d in ["train", "valid", "val", "test"]
        )
        if has_images:
            print(f"  [SKIP] {name} already exists at {output_dir}")
            return True
        # It's likely a broken download — clean it up
        import shutil
        shutil.rmtree(output_dir)

    print(f"\n{'='*60}")
    print(f"  Downloading: {name}")
    print(f"  {config['description']}")
    print(f"  Source: {workspace}/{project} v{version}")
    print(f"  Format: {fmt}")
    print(f"{'='*60}")

    # Retry loop for datasets that need time to export
    max_retries = 3
    for attempt in range(max_retries):
        try:
            rf = Roboflow(api_key=api_key)
            ws = rf.workspace(workspace)
            proj = ws.project(project)
            ver = proj.version(version)

            # Trigger download
            dataset = ver.download(fmt, location=str(output_dir))

            # Validate: check if we got actual files, not an error page
            zip_files = list(output_dir.glob("*.zip"))
            if zip_files:
                zip_path = zip_files[0]
                # Verify it's a real zip (not an XML error response)
                if zipfile.is_zipfile(str(zip_path)):
                    print(f"  Extracting {zip_path.name}...")
                    with zipfile.ZipFile(str(zip_path), 'r') as zf:
                        zf.extractall(str(output_dir))
                    zip_path.unlink()
                else:
                    # It's an error response — clean up and retry
                    content = zip_path.read_text()[:100]
                    print(f"  [WARN] Invalid zip (attempt {attempt+1}): {content}")
                    import shutil
                    shutil.rmtree(output_dir)
                    output_dir.mkdir(parents=True, exist_ok=True)
                    if attempt < max_retries - 1:
                        wait = 10 * (attempt + 1)
                        print(f"  Waiting {wait}s for export to complete...")
                        time.sleep(wait)
                    continue

            # Verify we actually got images
            has_content = any(output_dir.rglob("*.jpg")) or any(output_dir.rglob("*.png"))
            if not has_content:
                print(f"  [WARN] No images found after download (attempt {attempt+1}).")
                import shutil
                shutil.rmtree(output_dir)
                output_dir.mkdir(parents=True, exist_ok=True)
                if attempt < max_retries - 1:
                    time.sleep(10)
                continue

            print(f"  [OK] Downloaded {name} -> {output_dir}")
            return True

        except Exception as e:
            print(f"  [FAIL] {name} (attempt {attempt+1}): {e}")
            if output_dir.exists():
                import shutil
                shutil.rmtree(output_dir)
            if attempt < max_retries - 1:
                time.sleep(5)

    return False


def generate_unified_yaml(roboflow_dir: Path):
    """
    Generates a unified merged.yaml that combines all downloaded Roboflow datasets.
    This is used by the training pipeline for multi-dataset training.
    """
    merged_images = roboflow_dir / "merged" / "images"
    merged_labels = roboflow_dir / "merged" / "labels"
    merged_images.mkdir(parents=True, exist_ok=True)
    merged_labels.mkdir(parents=True, exist_ok=True)

    # Unified class mapping (maps Roboflow class IDs across all datasets)
    unified_classes = {
        "fire": 0,
        "smoke": 1,
        "person": 2,
        "person_fallen": 3,
        "track_obstruction": 4,
        "abandoned_baggage": 5,
        "crowd": 6,
        "animal": 7,
    }

    total_train = 0
    total_val = 0

    for dataset_name in DATASET_REGISTRY:
        dataset_dir = roboflow_dir / dataset_name
        if not dataset_dir.exists():
            continue

        config = DATASET_REGISTRY[dataset_name]
        class_map = config.get("target_class_map", {})

        # Find train/val directories (Roboflow uses various naming)
        for split in ["train", "valid", "val"]:
            split_img_dir = dataset_dir / split / "images"
            split_lbl_dir = dataset_dir / split / "labels"

            if not split_img_dir.exists():
                continue

            # Determine target split directory
            target_split = "val" if split in ["valid", "val"] else "train"
            target_img = merged_images / target_split
            target_lbl = merged_labels / target_split
            target_img.mkdir(parents=True, exist_ok=True)
            target_lbl.mkdir(parents=True, exist_ok=True)

            # Source dataset's class names from its data.yaml
            src_class_names = _read_class_names(dataset_dir / "data.yaml")

            images = list(split_img_dir.glob("*.jpg")) + list(split_img_dir.glob("*.png"))
            for img_path in images:
                lbl_path = split_lbl_dir / (img_path.stem + ".txt")

                # Copy image with dataset prefix to avoid collisions
                prefixed_name = f"{dataset_name}_{img_path.name}"
                shutil.copy2(str(img_path), str(target_img / prefixed_name))

                if lbl_path.exists():
                    # Remap class IDs from source dataset to unified classes
                    remapped = _remap_labels(
                        lbl_path.read_text(),
                        src_class_names,
                        class_map,
                        unified_classes,
                    )
                    (target_lbl / f"{dataset_name}_{lbl_path.stem}.txt").write_text(remapped)
                else:
                    (target_lbl / f"{dataset_name}_{lbl_path.stem}.txt").write_text("")

                if target_split == "train":
                    total_train += 1
                else:
                    total_val += 1

    # Write unified YAML
    yaml_content = f"""# RailGuard AI — Unified Roboflow Dataset
# Auto-generated by download_roboflow_datasets.py

path: {(roboflow_dir / 'merged').as_posix()}
train: images/train
val: images/val

nc: {len(unified_classes)}
names: {list(unified_classes.keys())}
"""
    yaml_path = roboflow_dir / "merged" / "roboflow_merged.yaml"
    yaml_path.write_text(yaml_content)

    print(f"\n{'='*60}")
    print(f"  UNIFIED ROBOFLOW DATASET BUILT")
    print(f"  Train: {total_train} images")
    print(f"  Val  : {total_val} images")
    print(f"  Classes: {list(unified_classes.keys())}")
    print(f"  YAML: {yaml_path}")
    print(f"{'='*60}")

    return yaml_path


def _read_class_names(yaml_path: Path) -> list:
    """Extract class names from a YOLO data.yaml file."""
    if not yaml_path.exists():
        return []
    content = yaml_path.read_text()
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("names:"):
            # Could be: names: [a, b] or names:\n- a\n- b
            if "[" in line:
                return [n.strip().strip("'\"") for n in line.split("[")[1].split("]")[0].split(",")]
            else:
                # Multi-line format
                names = []
                for sub in content.splitlines()[content.splitlines().index(line) + 1:]:
                    sub = sub.strip()
                    if sub.startswith("-"):
                        names.append(sub.lstrip("- ").strip())
                    elif names:
                        break
                return names
    return []


def _remap_labels(
    label_text: str,
    src_classes: list,
    class_map: dict,
    unified_classes: dict,
) -> str:
    """
    Remap YOLO label file class IDs from source dataset IDs to unified IDs.
    Uses class_map (source_name -> target_name) and unified_classes (target_name -> id).
    """
    if not label_text.strip() or not src_classes:
        return label_text

    lines = []
    for line in label_text.strip().splitlines():
        parts = line.split()
        if len(parts) < 5:
            continue
        src_id = int(parts[0])
        bbox = parts[1:]

        if src_id >= len(src_classes):
            continue

        src_name = src_classes[src_id]
        target_name = class_map.get(src_name)

        if target_name and target_name in unified_classes:
            unified_id = unified_classes[target_name]
            lines.append(f"{unified_id} {' '.join(bbox)}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Download railway surveillance datasets from Roboflow Universe"
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=os.environ.get("ROBOFLOW_API_KEY", ""),
        help="Roboflow API key (or set ROBOFLOW_API_KEY env var)",
    )
    parser.add_argument(
        "--datasets",
        type=str,
        nargs="*",
        default=None,
        help=f"Specific datasets to download. Choices: {list(DATASET_REGISTRY.keys())}. Default: all",
    )
    parser.add_argument(
        "--no-merge",
        action="store_true",
        help="Skip building the unified merged dataset",
    )
    args = parser.parse_args()

    if not args.api_key:
        print("=" * 60)
        print("  ROBOFLOW API KEY REQUIRED")
        print("=" * 60)
        print()
        print("  Option 1: Pass via --api-key flag")
        print("    python backend/scripts/download_roboflow_datasets.py --api-key YOUR_KEY")
        print()
        print("  Option 2: Set environment variable")
        print("    $env:ROBOFLOW_API_KEY='YOUR_KEY'")
        print()
        print("  Get your key at: https://app.roboflow.com/settings/api")
        print()
        print("  Available datasets (will download all if none specified):")
        for name, cfg in DATASET_REGISTRY.items():
            print(f"    - {name}: {cfg['description']}")
        print()
        print("  To download without SDK (manual), visit the Roboflow Universe links:")
        for name, cfg in DATASET_REGISTRY.items():
            print(f"    - https://universe.roboflow.com/{cfg['workspace']}/{cfg['project']}")
        sys.exit(1)

    # Determine which datasets to download
    if args.datasets:
        targets = {k: v for k, v in DATASET_REGISTRY.items() if k in args.datasets}
        missing = set(args.datasets) - set(targets.keys())
        if missing:
            print(f"[WARN] Unknown datasets: {missing}")
            print(f"       Available: {list(DATASET_REGISTRY.keys())}")
    else:
        targets = DATASET_REGISTRY

    DATASETS_DIR.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"  RAILGUARD AI — ROBOLOW DATASET DOWNLOADER")
    print(f"  Downloading {len(targets)} datasets")
    print(f"  Output: {DATASETS_DIR}")
    print(f"{'='*60}")

    success = 0
    failed = 0
    for name, config in targets.items():
        if download_dataset(args.api_key, name, config):
            success += 1
        else:
            failed += 1

    print(f"\n{'='*60}")
    print(f"  DOWNLOAD SUMMARY")
    print(f"  Success: {success} | Failed: {failed}")
    print(f"{'='*60}")

    # Build unified merged dataset
    if not args.no_merge and success > 0:
        generate_unified_yaml(DATASETS_DIR)

    print(f"\n  Next step: python backend/scripts/build_merged_dataset.py")
    print(f"  Then: python backend/scripts/train_robust_model.py --data datasets/merged/merged.yaml")


if __name__ == "__main__":
    main()
