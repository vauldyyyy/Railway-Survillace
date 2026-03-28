"""
extract_frames.py
Scans all videos in datasets/youtube/ and datasets/pexels/ 
Extracts frames at 2 FPS, resized to 640x640, saves as JPG.
Also creates stub YOLO label files via zero-shot YOLO-World inference.
"""

import cv2
import os
import sys
import time
import numpy as np
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATASETS_DIR = BASE_DIR / "datasets"
FRAMES_DIR   = DATASETS_DIR / "frames"

VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".webm", ".flv"}


def extract_frames(video_path: Path, out_dir: Path, fps: float = 2.0, max_frames: int = 500):
    """Extract frames from a video at specified FPS."""
    out_dir.mkdir(parents=True, exist_ok=True)
    
    cap     = cv2.VideoCapture(str(video_path))
    vid_fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    interval = max(1, int(vid_fps / fps))
    count    = 0
    saved    = 0
    
    while saved < max_frames:
        ret, frame = cap.read()
        if not ret:
            break
        if count % interval == 0:
            frame = cv2.resize(frame, (640, 640), interpolation=cv2.INTER_AREA)
            fname = out_dir / f"frame_{saved:05d}.jpg"
            cv2.imwrite(str(fname), frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            saved += 1
        count += 1
    
    cap.release()
    return saved


def scan_and_extract():
    total_videos  = 0
    total_frames  = 0
    category_stats = {}

    # Scan all subdirectories under datasets/youtube, datasets/youtube_targeted and datasets/pexels
    for search_root in [DATASETS_DIR / "youtube", DATASETS_DIR / "youtube_targeted", DATASETS_DIR / "pexels"]:
        if not search_root.exists():
            continue
        for video_path in sorted(search_root.rglob("*")):
            if video_path.suffix.lower() not in VIDEO_EXTENSIONS:
                continue

            # Category = parent folder name (search query)
            category = video_path.parent.name[:30]
            out_dir  = FRAMES_DIR / category

            t0 = time.time()
            n  = extract_frames(video_path, out_dir)
            dt = time.time() - t0

            total_videos += 1
            total_frames += n
            category_stats[category] = category_stats.get(category, 0) + n

            print(f"  [{total_videos}] {video_path.name[:50]:<50} -> {n:3d} frames  ({dt:.1f}s)")

    return total_videos, total_frames, category_stats


def print_summary(total_videos, total_frames, stats):
    print(f"\n{'='*60}")
    print(f"FRAME EXTRACTION COMPLETE")
    print(f"{'='*60}")
    print(f"  Videos processed : {total_videos}")
    print(f"  Total frames     : {total_frames}")
    print(f"\n  Breakdown by category:")
    for cat, n in sorted(stats.items(), key=lambda x: -x[1]):
        print(f"    {cat:<35} {n:5d} frames")
    print(f"\n  Output: {FRAMES_DIR}")
    print(f"\n  Next step: python backend/scripts/auto_label.py")


def main():
    print(f"Scanning for videos in: {DATASETS_DIR}")
    total_videos, total_frames, stats = scan_and_extract()
    print_summary(total_videos, total_frames, stats)


if __name__ == "__main__":
    main()
