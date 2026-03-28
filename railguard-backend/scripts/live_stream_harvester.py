import subprocess
import cv2
import threading
import time
import os
from pathlib import Path

# ── Configuration ──
DURATION_MINS = 5  # Capture for 5 minutes per stream (default for hackathon demo)
FPS_TARGET = 1     # 1 frame per second
OUTPUT_BASE = Path("datasets/live_streams")

LIVE_STREAMS = {
    "svr_bewdley_n":     "https://www.youtube.com/c/SeverValleyRailway/live",
    "kyoto_terminal":    "https://www.skylinewebcams.com/en/webcam/japan/kansai/kyoto/bus-terminal.html",
    "vrf_ashland":       "https://www.youtube.com/@VirtualRailfan/streams",
    "utrecht_central":   "https://railwebcams.net/utrecht-centraal/",
    "tokyo_ebisu":       "https://railwebcams.net/tokyo-ebisu-railway/",
    "oslo_central":      "https://railwebcams.net/oslo-central-railway-station/",
    "vienna_central":    "https://railwebcams.net/vienna-central-station/",
    "toronto_rail":      "https://railwebcams.net/toronto-city-railway/",
    "nyc_woodside":      "https://railwebcams.net/new-york-city-ny-woodside-railroad-subway/",
}

def get_stream_url(url):
    """Use yt-dlp to get the actual stream manifest URL."""
    try:
        # Standardize for yt-dlp
        result = subprocess.run(
            ["yt-dlp", "-f", "best[height<=480]", "--get-url", url],
            capture_output=True, text=True, timeout=20
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return url
    except Exception as e:
        print(f"[!] yt-dlp error for {url}: {e}")
        return url

def harvest_stream(name, url, duration=DURATION_MINS):
    """Capture frames from a single stream."""
    out_dir = OUTPUT_BASE / name
    out_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"[*] Starting harvest for {name}...")
    stream_url = get_stream_url(url)
    
    cap = cv2.VideoCapture(stream_url)
    if not cap.isOpened():
        print(f"[✗] Failed to open stream: {name}")
        return

    vid_fps = cap.get(cv2.CAP_PROP_FPS) or 25
    interval = max(1, int(vid_fps / FPS_TARGET))
    end_time = time.time() + (duration * 60)
    count = saved = 0

    while time.time() < end_time:
        ret, frame = cap.read()
        if not ret:
            # Try to reconnect once if the stream drops
            cap.release()
            time.sleep(5)
            cap = cv2.VideoCapture(get_stream_url(url))
            if not cap.isOpened(): break
            continue
            
        if count % interval == 0:
            # Resize for YOLO consistency
            frame = cv2.resize(frame, (640, 640))
            fname = out_dir / f"{name}_{int(time.time())}_{saved:04d}.jpg"
            cv2.imwrite(str(fname), frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            saved += 1
            
        count += 1
        # Prevent CPU pegging
        if count % 100 == 0: time.sleep(0.01)

    cap.release()
    print(f"[✓] {name}: Saved {saved} frames to {out_dir}")

def main():
    threads = []
    print(f"=== RailGuard Live Stream Harvester ===")
    print(f"Duration: {DURATION_MINS} mins | Res: 640x640 | Target: {FPS_TARGET} FPS")
    
    for name, url in LIVE_STREAMS.items():
        t = threading.Thread(target=harvest_stream, args=(name, url))
        t.start()
        threads.append(t)
        time.sleep(3)  # Stagger to avoid request rate-limiting

    for t in threads:
        t.join()

    print("\n[✓] All manual stream harvesting complete.")

if __name__ == "__main__":
    main()
