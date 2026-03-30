import subprocess
import os
import sys

# Define searches for the remaining 3 use-cases
# We use length restrictions and search multiple results to find a short clip natively.
queries = {
    "cam2": "ytsearch5:night security camera rain",  # Night / Rain
    "cam3": "ytsearch5:cctv factory smoke fire",     # Smoke / Industrial
    "cam4": "ytsearch5:airport cctv luggage"         # Baggage / Concourse
}

os.makedirs("test_data", exist_ok=True)

for cam, query in queries.items():
    output_path = f"test_data/{cam}.mp4"
    if os.path.exists(output_path):
        print(f"[{cam}] Already exists.")
        continue
        
    print(f"\n--- Downloading {cam} ---")
    try:
        # -f bestvideo[ext=mp4]: Gets only the video stream (no audio) so ffmpeg isn't needed
        # --match-filter: Ensures we don't accidentally download a 10 hr live stream
        subprocess.run([
            "yt-dlp",
            "-f", "bestvideo[height<=720][ext=mp4]/best[ext=mp4]",
            "--match-filter", "duration < 300 & !is_live",
            "--max-downloads", "1",
            "--no-warnings",
            "-o", f"test_data/{cam}.mp4.temp",
            query
        ], check=True)
        
        # yt-dlp might append an ID or extension if not careful, so let's find the downloaded file
        # Since we forced mp4, it should be pretty close to our intended name
        for file in os.listdir("test_data"):
            if file.startswith(f"{cam}.mp4.temp"):
                os.rename(os.path.join("test_data", file), output_path)
                print(f"[{cam}] Successfully saved as {output_path}")
                break
    except Exception as e:
        print(f"[{cam}] Download failed: {e}")
