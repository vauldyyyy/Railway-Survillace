import cv2
import sys
from pathlib import Path

# Connect to backend modules
backend_dir = str(Path(__file__).resolve().parent.parent)
sys.path.append(backend_dir)
from detection.yolo_world import ZeroShotDetector

def run_demo():
    print("=====================================================")
    print(" [RAILGUARD AI] ZERO-SHOT FOUNDATION DETECTOR DEMO ")
    print("=====================================================")
    print("Booting Vision-Language Model... (yolov8s-worldv2.pt)")
    
    detector = ZeroShotDetector()
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("⚠ FATAL: No webcam found at cv2.VideoCapture(0). Ensure camera is attached!")
        return

    print("\n[LIVE INSTRUCTIONS]")
    print("   -> Press 'T' to suspend feed and type a new THREAT PROMPT.")
    print("   -> Press 'Q' to Terminate.\n")
    
    while True:
        ret, frame = cap.read()
        if not ret: break
        
        # 1. Zero-Shot Inference
        detections = detector.detect(frame, 0.15)
        
        # 2. Render Scene
        for det in detections:
            x1, y1, x2, y2 = det["box"]
            cls_name = det["class_name"]
            color = (0, 0, 255) if det["severity"] == "critical" else (0, 255, 255)
            
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, cls_name, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            
        cv2.putText(frame, "[T] Input New Threat Prompts  |  [Q] Exit", (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    
        cv2.imshow("Zero-Shot Tactical Overview", frame)
        
        # 3. Handle Live Text Prompt Re-mapping without Rebooting
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('t'):
            print("\n" + "="*50)
            new_threat = input("✍ ENTER NEW THREAT PROMPT (e.g. 'person holding umbrella'): ")
            print("="*50)
            # Retain default criticals, but append new user query
            detector.set_classes(detector.default_classes + [new_threat])
            print(">>> ✅ Neural Weights re-aligned to new vocabulary instantly!")
            
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    run_demo()
