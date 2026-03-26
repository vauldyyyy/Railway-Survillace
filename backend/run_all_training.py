"""
run_all_training.py
Automates the execution of RailFOD, UAV, and LSTM training.
Handles the migration of best.pt weights to the models directory.
"""

import subprocess
import shutil
import os
from pathlib import Path

def run_script(script_path):
    print(f"\n{'='*60}")
    print(f"EXECUTING: {script_path.name}")
    print(f"{'='*60}")
    # We use a shell-like execution to ensure environmental variables/paths are inherited
    process = subprocess.Popen(["python", str(script_path)], stdout=None, stderr=None)
    process.wait()
    
    if process.returncode != 0:
        print(f"[ERROR] {script_path.name} failed with return code {process.returncode}")
        return False
    return True

def main():
    backend_dir = Path(__file__).resolve().parent
    models_dir = backend_dir / "models"
    models_dir.mkdir(exist_ok=True)

    # 1. Run All Training Scripts
    training_scripts = [
        backend_dir / "train_railfod.py",
        backend_dir / "train_uav.py",
        backend_dir / "train_lstm.py"
    ]

    for script in training_scripts:
        if not run_script(script):
            print("Stopping automation due to script failure.")
            return

    # 2. Migration of Weights
    # Ultralytics saves runs in the current working directory's 'runs' folder
    runs_dir = Path.cwd() / "runs" / "detect"
    
    weight_maps = {
        runs_dir / "railfod_cpu_run" / "weights" / "best.pt": models_dir / "railfod_best.pt",
        runs_dir / "uav_cpu_run" / "weights" / "best.pt": models_dir / "uav_best.pt"
    }

    for src, dst in weight_maps.items():
        if src.exists():
            shutil.copy(src, dst)
            print(f"[SUCCESS] Migrated {src.parent.parent.parent.name} weights to {dst}")
        else:
            print(f"[WARNING] Could not find weights at {src}")

    print(f"\n{'='*60}\nALL TRAINING AND MIGRATION COMPLETED.\n{'='*60}")

if __name__ == "__main__":
    main()