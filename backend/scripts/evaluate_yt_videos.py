import cv2
import sys
import time
from pathlib import Path

backend_dir = str(Path(__file__).resolve().parent.parent)
sys.path.append(backend_dir)
from detection.yolo_world import ZeroShotDetector

def test_video(detector, video_path, target_classes, conf_threshold=0.10):
    detector.set_classes(target_classes)
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Could not open {video_path}")
        return False
        
    frames_read = 0
    detected_frames = 0
    
    while True:
        ret, frame = cap.read()
        if not ret or frames_read > 200:
            break
            
        dets = detector.detect(frame, conf_threshold=conf_threshold)
        
        # Check if *any* target class (other than just 'person') is detected
        # Unless target is just person, but the user wants specific threats
        threat_detected = False
        for d in dets:
            if d['class_name'] in target_classes and d['class_name'] != "person":
                threat_detected = True
                break
                
        if threat_detected:
            detected_frames += 1
            
        frames_read += 1
        
    cap.release()
    if frames_read == 0:
        return False
        
    acc = (detected_frames / frames_read) * 100
    print(f"[{Path(video_path).name}] Accuracy (frames with threat / total 200 max): {acc:.1f}% ({detected_frames}/{frames_read})")
    return True

if __name__ == "__main__":
    detector = ZeroShotDetector()
    
    videos = [
        ("test_videos/person_on_track.mp4", ["person", "person on railway track", "fallen person on track"]),
        ("test_videos/unattended_baggage.mp4", ["person", "luggage", "unattended baggage", "backpack"]),
        ("test_videos/fire_smoke.mp4", ["person", "fire", "smoke", "flames"])
    ]
    
    project_root = Path(backend_dir).parent
    for vid_rel_path, classes in videos:
        full_vid_path = str(project_root / vid_rel_path)
        print(f"\nEvaluating: {vid_rel_path}")
        test_video(detector, full_vid_path, classes, conf_threshold=0.15)
