import cv2
import sys
import time
from pathlib import Path

backend_dir = str(Path(__file__).resolve().parent.parent)
sys.path.append(backend_dir)
from detection.pipeline import SurveillancePipeline

def run_demo():
    print("=====================================================")
    print(" [RAILGUARD AI] OSNET CROSS-CAMERA RE-ID TRACKER ")
    print("=====================================================")
    print("Booting Core Pipeline (YOLO-World + Torchreid OSNet)...")
    
    pipe = SurveillancePipeline()
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("⚠ FATAL: No webcam found at cv2.VideoCapture(0).")
        return

    print("\n[LIVE INSTRUCTIONS]")
    print("   -> Walk across the LEFT half of the frame (Camera A).")
    print("   -> Walk into the RIGHT half of the frame (Camera B).")
    print("   -> Watch the Neural UUID perfectly persist across the virtual blind-spot.\n")
    
    while True:
        ret, frame = cap.read()
        if not ret: break
        
        # Simulate Multi-Camera Topology by slicing the webcam in half
        h, w = frame.shape[:2]
        mid = w // 2
        frame_a = frame[:, :mid]
        frame_b = frame[:, mid:]
        
        # Run isolated environments
        ann_a, alerts_a, _ = pipe.run(frame_a, camera_id="East Gate (Cam A)")
        ann_b, alerts_b, _ = pipe.run(frame_b, camera_id="Concourse (Cam B)")
        
        # Stitch back together with absolute visual barrier
        merged = cv2.hconcat([ann_a, ann_b])
        cv2.line(merged, (mid, 0), (mid, h), (0, 0, 0), 25) # Black blind spot
        
        cv2.putText(merged, "EAST GATE - CAM A", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,255,255), 2)
        cv2.putText(merged, "CONCOURSE - CAM B", (mid + 10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,255,255), 2)
        
        # Log active trajectories to presentation terminal
        for alert in alerts_a + alerts_b:
            if alert["type"] == "ReID_Track":
                path_str = " -> ".join([p["camera"] for p in alert["path"]])
                print(f"[{time.strftime('%H:%M:%S')}] ⚠ Suspect UUID {alert['uuid'][:8]} Trajectory: {path_str}")
                
        cv2.imshow("Multi-Camera ReID Persistent Tracking", merged)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
            
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    run_demo()
