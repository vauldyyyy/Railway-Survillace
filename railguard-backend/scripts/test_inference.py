import cv2
import sys
import time
from pathlib import Path
import os

# Link into backend context
backend_dir = str(Path(__file__).resolve().parent.parent)
sys.path.append(backend_dir)
from detection.pipeline import SurveillancePipeline

def process_video(input_path, output_path, max_frames=300):
    print("===================================================")
    print(" [RAILGUARD] OFFLINE VIDEO INFERENCE TEST ")
    print("===================================================")
    
    pipe = SurveillancePipeline()
    cap = cv2.VideoCapture(input_path)
    
    if not cap.isOpened():
        print(f"⚠ Failed to open source video at: {input_path}")
        return
        
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    if fps == 0: fps = 30
    
    # Use standard mp4v codec for cross-platform playback natively in OpenCV
    fourcc = cv2.VideoWriter_fourcc(*'mp4v') 
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    count = 0
    print(f"\nProcessing {input_path}...")
    print(f"Encoding output at {width}x{height} @ {fps}fps")
    
    start_t = time.time()
    while cap.isOpened() and count < max_frames:
        ret, frame = cap.read()
        if not ret: break
        
        # ── CORE INFERENCE ── (YOLO-World -> Person Crop -> OSNet -> Diff Privacy UUID)
        ann_frame, alerts, _ = pipe.run(frame, camera_id="Offline_Test")
        out.write(ann_frame)
        
        # Console Telemetry
        if count % 30 == 0:
            sys.stdout.write(f"\rRendered Frame {count}/{max_frames} | Active Tracking Nodes: {len(pipe.reid.gallery)}")
            sys.stdout.flush()
            if alerts:
                # Log the first severe alert detected in this 30-frame window
                print(f"\n   [System Alert] {alerts[0]['type']}: {alerts[0].get('severity')} | Confidence: {alerts[0].get('confidence')}")
                
        count += 1
        
    cap.release()
    out.release()
    t_elapsed = time.time() - start_t
    print(f"\n\n✅ Target Acquired. Successfully processed {count} frames in {t_elapsed:.2f}s.")
    print(f"The neural-annotated output video has been saved to: \n-> {output_path}")
    print("Open this file in VS Code or VLC to visually verify the Zero-Shot / ReID Tracking Engine.")

if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parent.parent.parent
    
    # We use the raw dataset video we harvested via yt-dlp earlier today
    input_vid = str(base_dir / "datasets" / "raw_videos" / "track_incident_1.mp4")
    output_vid = str(base_dir / "demo_output.mp4")
    
    if os.path.exists(input_vid):
        process_video(input_vid, output_vid)
    else:
        print(f"Source video not found: {input_vid}. Searching for fallback `test_video.mp4`...")
        fallback = str(base_dir / "test_video.mp4")
        if os.path.exists(fallback):
            process_video(fallback, output_vid)
        else:
            print("No test videos found. Please manually populate the directory.")
