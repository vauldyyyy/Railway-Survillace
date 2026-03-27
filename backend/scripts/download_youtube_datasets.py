"""
download_youtube_datasets.py
Downloads top videos from 15 railway-specific YouTube search queries.
No API key needed. Uses yt-dlp.
"""

import subprocess
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR  = BASE_DIR / "datasets" / "youtube"

QUERIES = [
    "Indian railway platform CCTV footage",
    "Mumbai local train rush hour platform",
    "railway station overcrowding stampede India",
    "person trespassing railway track caught",
    "object debris on railway track India",
    "railway platform night CCTV India",
    "railway station crowd pushing",
    "abandoned bag railway station",
    "railway fire smoke incident India",
    "Howrah station crowd footage",
    "CST station rush hour",
    "New Delhi railway station platform CCTV",
    "railway track obstruction India",
    "animal on railway track India",
    "railway CCTV surveillance footage",
]

def download_query(query: str, count: int = 5):
    safe_q = query.replace(" ", "_")[:40]
    out    = OUT_DIR / safe_q
    out.mkdir(parents=True, exist_ok=True)

    print(f"\n[YT] Downloading: '{query}'")
    cmd = [
        "yt-dlp",
        f"ytsearch{count}:{query}",
        "-f", "best[height<=480][ext=mp4]/best[height<=480]/best",
        "-o", str(out / "%(title).50s.%(ext)s"),
        "--no-playlist",
        "--ignore-errors",
        "--no-warnings",
        "--quiet",
        "--progress",
        "--restrict-filenames",
        "--max-filesize", "150m",
    ]
    result = subprocess.run(cmd, timeout=300)
    files = list(out.glob("*.mp4")) + list(out.glob("*.webm"))
    print(f"   ✓ {len(files)} files → {out.relative_to(BASE_DIR)}")
    return files

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    total = 0
    for query in QUERIES:
        try:
            files = download_query(query, count=5)
            total += len(files)
        except Exception as e:
            print(f"   ✗ Failed: {e}")
    print(f"\n{'='*60}")
    print(f"✓ Total videos downloaded: {total}")
    print(f"✓ Output: {OUT_DIR}")
    print(f"  Next step: python backend/scripts/extract_frames.py")

if __name__ == "__main__":
    main()
