import subprocess
import sys
import os

vids = {
    "cam2": "ytsearch1:train night rain cctv",
    "cam3": "ytsearch1:warehouse fire smoke cctv",
    "cam4": "ytsearch1:airport cctv abandoned luggage"
}

for k, v in vids.items():
    if not os.path.exists(f"test_data/{k}.mp4"):
        print(f"Downloading {k}...")
        try:
            subprocess.run([
                "yt-dlp", "-f", "best[height<=720][ext=mp4]/best",
                "--download-sections", "*00:00:00-00:01:00",
                "--force-keyframes", "-o", f"test_data/{k}.mp4", v
            ])
        except Exception as e:
            print(f"Failed {k}: {e}")
