import cv2
import os
import sys
import time
import numpy as np
from pathlib import Path

# ── Configuration ──
BASE_DIR = Path(__file__).resolve().parent.parent
DATASETS_DIR = BASE_DIR / "datasets"
YOUTUBE_RAW  = DATASETS_DIR / "youtube_raw"
LIVE_STREAMS = DATASETS_DIR / "live_streams"
OUT_DIR      = DATASETS_DIR / "frames_master"

VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".webm", ".flv"}

def extract_frames(video_path: Path, out_dir: Path, fps: float = 1.0, max_frames: int = 200):
    """Extract frames from a video at 1 FPS (to avoid redundancy)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    
    cap     = cv2.VideoCapture(str(video_path))
    vid_fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    interval = max(1, int(vid_fps / fps))
    count    = 0
    saved    = 0
    
    video_id = video_path.stem.replace(" ", "_")[:20]

    while saved < max_frames:
        ret, frame = cap.read()
        if not ret:
            break
        if count % interval == 0:
            # Standardization to 640x640 for YOLOv8
            frame = cv2.resize(frame, (640, 640), interpolation=cv2.INTER_AREA)
            fname = out_dir / f"{video_id}_fr{saved:04d}.jpg"
            cv2.imwrite(str(fname), frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            saved += 1
        count += 1
    
    cap.release()
    return saved

def main():
    print("=== RailGuard Global Frame Extraction Engine ===")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    
    total_videos  = 0
    total_frames  = 0
    
    # Process YouTube Mass Downloads + Live Stream Caps
    roots = [YOUTUBE_RAW, LIVE_STREAMS]
    
    for root in roots:
        if not root.exists(): continue
        print(f"\n[*] Scanning: {root}")
        
        # Scans all subdirectories (e.g., datasets/youtube_raw/night_01/*.mp4)
        for video_path in sorted(root.rglob("*")):
            if video_path.suffix.lower() not in VIDEO_EXTENSIONS:
                continue
            
            # Group into category folders
            category = video_path.parent.name
            target_dir = OUT_DIR / category
            
            print(f"  [+] Extracting: {video_path.name[:40]}...", end="\r")
            n = extract_frames(video_path, target_dir)
            
            total_videos += 1
            total_frames += n
            
    print(f"\n\n{'='*40}")
    print(f"EXTRACTION SUMMARY")
    print(f"{'='*40}")
    print(f"  Videos processed: {total_videos}")
    print(f"  Total frames:     {total_frames}")
    print(f"  Output Dir:       {OUT_DIR}")
    print(f"\nNext step: python backend/scripts/diverse_sampling.py (then auto_label.py)")

if __name__ == "__main__":
    main()
