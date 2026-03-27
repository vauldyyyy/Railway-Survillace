"""
download_targeted_videos.py
Downloads specific "hard-case" YouTube videos for railway robustness (night, fog, weather).
Uses yt-dlp to download and organizes into backend/datasets/youtube_targeted.
"""

import os
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR  = BASE_DIR / "datasets" / "youtube_targeted"

# Targeted URLs from user recommendation
VIDEOS = {
    "night_fog_high_robustness": "https://www.youtube.com/watch?v=Qewujk80HKg",
    "foggy_trains_india": "https://www.youtube.com/watch?v=jL_2f58zw70",
    "winter_fog_railway": "https://www.youtube.com/watch?v=lL7Mn3VBbjA",
    "perfect_crossing_4k": "https://www.youtube.com/watch?v=fWZ2wFIYRzE",
}

def download_video(url, name):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / f"{name}.mp4"
    
    print(f"\n[TARGETED] Downloading: {name} ({url})")
    cmd = [
        "yt-dlp",
        "-f", "best[height<=720][ext=mp4]/best[height<=720]/best",
        url,
        "-o", str(out_path),
        "--no-playlist",
        "--restrict-filenames",
    ]
    try:
        subprocess.run(cmd, check=True)
        print(f"   [OK] Downloaded to {out_path}")
        return out_path
    except subprocess.CalledProcessError as e:
        print(f"   [ERROR] Failed to download {name}: {e}")
        return None

def main():
    print("[START] Starting Targeted Video Acquisition...")
    for name, url in VIDEOS.items():
        download_video(url, name)
    print("\n[OK] Targeted downloads complete.")
    print(f"Output directory: {OUT_DIR}")
    print("👉 Next step: Run frame extraction on these videos.")

if __name__ == "__main__":
    main()
