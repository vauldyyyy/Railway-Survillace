"""
run_all_training.py
Master orchestrator for the full RailGuard AI training pipeline.
Runs all steps in order:
  1. Generate crowd CSV data
  2. Download YouTube datasets (yt-dlp)
  3. Extract frames from all videos
  4. Auto-label frames with YOLO-World
  5. Build merged dataset
  6. Train RailFOD YOLOv8s
  7. Train UAV YOLOv8n
  8. Train LSTM crowd forecaster
  9. Validate all models
"""

import subprocess
import shutil
import sys
import os
import time
from pathlib import Path

BASE_DIR    = Path(__file__).resolve().parent
SCRIPTS_DIR = BASE_DIR / "scripts"

BOLD  = "\033[1m"
GREEN = "\033[92m"
RED   = "\033[91m"
CYAN  = "\033[96m"
RESET = "\033[0m"


def banner(title: str):
    print(f"\n{CYAN}{'='*60}{RESET}")
    print(f"{BOLD}{CYAN}  {title}{RESET}")
    print(f"{CYAN}{'='*60}{RESET}")


def run(script: Path, label: str) -> bool:
    banner(f"STEP: {label}")
    t0 = time.time()
    proc = subprocess.run([sys.executable, str(script)], cwd=str(BASE_DIR))
    dt = time.time() - t0
    if proc.returncode == 0:
        print(f"{GREEN}  ✓ {label} completed in {dt:.0f}s{RESET}")
        return True
    else:
        print(f"{RED}  ✗ {label} FAILED (code {proc.returncode}){RESET}")
        return False


def migrate_weights():
    banner("STEP: Migrating weights to models/")
    models_dir = BASE_DIR / "models"
    models_dir.mkdir(exist_ok=True)

    runs_dir = BASE_DIR.parent / "runs" / "detect"
    if not runs_dir.exists():
        runs_dir = Path("runs") / "detect"

    maps = {
        "railfod_merged":    "railfod_best.pt",
        "railfod_run":       "railfod_best.pt",
        "uav_run":           "uav_best.pt",
    }

    for run_name, dest_name in maps.items():
        src = runs_dir / run_name / "weights" / "best.pt"
        dst = models_dir / dest_name
        if src.exists():
            shutil.copy(str(src), str(dst))
            print(f"  {GREEN}✓ Migrated {run_name} → {dest_name}{RESET}")


def print_final_summary():
    banner("PIPELINE COMPLETE — MODEL SUMMARY")
    models_dir = BASE_DIR / "models"
    for f in sorted(models_dir.glob("*")):
        size_mb = f.stat().st_size / 1_000_000
        print(f"  {GREEN}✓{RESET} {f.name:<30} {size_mb:.1f} MB")
    print(f"\n  {BOLD}Next step: restart the backend and check Model Dashboard.{RESET}")
    print(f"  python backend/main.py")


def main():
    banner("RailGuard AI — Full Training Pipeline")
    print(f"  Mode: CPU-optimized")
    print(f"  Start: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    steps = [
        (SCRIPTS_DIR / "generate_crowd_csv.py",      "Generate Crowd CSV Data"),
        (SCRIPTS_DIR / "download_youtube_datasets.py","Download YouTube Datasets"),
        (SCRIPTS_DIR / "extract_frames.py",           "Extract Video Frames"),
        (SCRIPTS_DIR / "auto_label.py",               "Auto-Label Frames (YOLO-World)"),
        (SCRIPTS_DIR / "build_merged_dataset.py",     "Build Merged Dataset"),
        (BASE_DIR    / "train_railfod.py",            "Train RailFOD YOLOv8s (50 epochs)"),
        (BASE_DIR    / "train_uav.py",                "Train UAV YOLOv8n (50 epochs)"),
        (BASE_DIR    / "train_lstm.py",               "Train LSTM Crowd Forecaster"),
    ]

    failed = []
    for script, label in steps:
        if not script.exists():
            print(f"\n  {RED}[SKIP] {label} — script not found: {script}{RESET}")
            continue
        ok = run(script, label)
        if not ok:
            failed.append(label)
            print(f"  {RED}[WARN] Continuing despite failure in: {label}{RESET}")

    migrate_weights()
    print_final_summary()

    if failed:
        print(f"\n  {RED}Steps that failed: {failed}{RESET}")
    else:
        print(f"\n  {GREEN}All steps completed successfully!{RESET}")


if __name__ == "__main__":
    main()