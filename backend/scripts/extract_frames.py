import cv2
import os
from pathlib import Path

def extract_frames(video_path, output_dir, fps=2, max_frames=500):
    """
    fps=2: good balance — enough diversity, not too redundant
    max_frames=500: cap per video to avoid class imbalance
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error opening video: {video_path}")
        return

    video_fps = cap.get(cv2.CAP_PROP_FPS)
    if video_fps <= 0:
        video_fps = 30 # fallback
        
    frame_interval = max(1, int(video_fps / fps))
    
    os.makedirs(output_dir, exist_ok=True)
    count = 0
    saved = 0
    
    print(f"Extracting from {video_path} at 1 frame every {frame_interval} frames...")
    
    while saved < max_frames:
        ret, frame = cap.read()
        if not ret:
            break
        if count % frame_interval == 0:
            # Resize to YOLOv8 training resolution to save disk space
            frame = cv2.resize(frame, (640, 640))
            out_path = os.path.join(output_dir, f"frame_{saved:04d}.jpg")
            cv2.imwrite(out_path, frame)
            saved += 1
        count += 1
    
    cap.release()
    print(f"✓ Extracted {saved} frames to {output_dir}")

if __name__ == "__main__":
    # Base directories
    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    DATASET_DIR = BASE_DIR / "datasets"
    VIDEO_DIR = DATASET_DIR / "raw_videos"
    FRAMES_DIR = DATASET_DIR / "frames"

    if not VIDEO_DIR.exists():
        print(f"Please place your downloaded videos in: {VIDEO_DIR}")
        VIDEO_DIR.mkdir(parents=True, exist_ok=True)
    else:
        print("Starting batch frame extraction...")
        # Process all videos
        for video in VIDEO_DIR.glob("*.mp4"):
            # Use the video filename (without extension) as the category folder
            category = video.stem.replace(" ", "_")
            extract_frames(
                str(video),
                str(FRAMES_DIR / category),
                fps=2
            )
        print("Batch extraction complete.")
