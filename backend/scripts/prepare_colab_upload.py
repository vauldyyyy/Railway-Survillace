import shutil
import os
from pathlib import Path

# ── Configuration ──
SOURCE_DIR = Path("backend/datasets/auto_labeled")
OUTPUT_ZIP = Path("railguard_augmented_dataset.zip")

def prepare_zip():
    print(f"[*] Preparing {OUTPUT_ZIP} from {SOURCE_DIR}...")
    
    if not SOURCE_DIR.exists():
        print(f"[✗] Source directory {SOURCE_DIR} not found.")
        return

    # Count files
    img_count = len(list(SOURCE_DIR.rglob("*.jpg")))
    lbl_count = len(list(SOURCE_DIR.rglob("*.txt")))
    
    print(f"[*] Ready to zip {img_count} images and {lbl_count} labels.")
    
    # We will zip the directory structure
    shutil.make_archive(OUTPUT_ZIP.stem, 'zip', SOURCE_DIR)
    
    size_mb = os.path.getsize(OUTPUT_ZIP) / (1024 * 1024)
    print(f"[✓] Zip complete: {OUTPUT_ZIP} ({size_mb:.1f} MB)")
    print(f"[!] Upload this file to your Google Drive for Colab training.")

if __name__ == "__main__":
    prepare_zip()
