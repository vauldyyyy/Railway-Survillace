import os
import subprocess
from pathlib import Path

# Targeted Video Collection for Audit Closure
VIDEO_TARGETS = [
    {"url": "https://www.youtube.com/watch?v=06OLEi9v_Gw", "category": "night_fog", "desc": "High quality night/fog"},
    {"url": "https://www.youtube.com/watch?v=L2G57361_G4", "category": "drone_uav", "desc": "Railway Drone Overhead 4K"},
    {"url": "https://www.youtube.com/watch?v=4pG_v2jS6f4", "category": "indian_fog", "desc": "Dense Fog Indian Railway Action"},
]

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = BASE_DIR / "datasets" / "youtube_targeted"

def download_videos():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"--- Starting Targeted Data Acquisition (Task 2) ---")
    
    for i, target in enumerate(VIDEO_TARGETS):
        url = target["url"]
        cat = target["category"]
        print(f"[Downloading {i+1}/3] {cat}: {url}")
        
        output_tmpl = str(OUT_DIR / f"{cat}_%(id)s.%(ext)s")
        
        try:
            # Use -f "best[height<=720]" to keep it fast but good quality
            subprocess.run([
                "yt-dlp", "-f", "best[height<=720][ext=mp4]", 
                "-o", output_tmpl, url
            ], check=True)
            print(f"  OK: {cat} downloaded.")
        except Exception as e:
            print(f"  FAIL: {cat} failed: {e}")

if __name__ == "__main__":
    download_videos()
