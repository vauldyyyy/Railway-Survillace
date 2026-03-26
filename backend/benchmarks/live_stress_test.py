import cv2
import sys
import time
import random
from pathlib import Path
import numpy as np

# Add backend to path so we can heavily import the main surveillance pipeline
sys.path.append(str(Path(__file__).resolve().parent.parent))
from detection.pipeline import pipeline

import albumentations as A
import argparse

LIVE_SOURCES = {
    "webcam": 0,
    "ryde": "https://www.mangolinkworld.com/webcams/transport/ryde-bus-station.html",
    "kyoto": "https://www.skylinewebcams.com/en/webcam/japan/kansai/kyoto/bus-terminal.html",
}

class LiveStressTester:
    def __init__(self, source_key="webcam"):
        print(f"[StressTest] Initializing OpenCV VideoCapture for source: {source_key}...")
        
        # If the source is a URL, yt-dlp might be needed to extract the direct m3u8 stream,
        # but OpenCV can handle some direct http video feeds. 
        # For skylinewebcams or youtube, we usually extract the true URL first.
        stream_path = LIVE_SOURCES.get(source_key, 0)
        
        if source_key in ["ryde", "kyoto", "yt"]:
            print(f"[StressTest] Resolving live m3u8 stream for {source_key} via yt-dlp...")
            import subprocess
            try:
                result = subprocess.run(
                    ['yt-dlp', '-f', 'best[height<=480]', '--get-url', str(stream_path)],
                    capture_output=True, text=True, check=True
                )
                stream_path = result.stdout.strip()
            except Exception as e:
                print(f"[StressTest] yt-dlp failed to extract stream. Falling back to raw URL. Error: {e}")

        self.cap = cv2.VideoCapture(stream_path)
        
        # Phase 6: Define severe real-world corruption kernels using Albumentations
        print("[StressTest] Compiling Albumentations corruption kernels...")
        self.rain_transform = A.RandomRain(brightness_coefficient=0.9, drop_width=1, blur_value=3, p=1.0)
        self.fog_transform = A.RandomFog(fog_coef_lower=0.4, fog_coef_upper=0.7, alpha_coef=0.08, p=1.0)
        self.blur_transform = A.MotionBlur(blur_limit=15, p=1.0)
        self.night_transform = A.RandomBrightnessContrast(brightness_limit=-0.6, contrast_limit=0.4, p=1.0)
        self.noise_transform = A.ISONoise(intensity=(0.5, 1.0), p=1.0)
        
        # State Tracker
        self.active_corruption = "None"
        self.simulate_drops = False
        
    def _apply_corruption(self, frame):
        """Intercepts the raw frame and destroys its high-frequency texture dataset bias."""
        if self.active_corruption == "Rain":
            return self.rain_transform(image=frame)["image"]
        elif self.active_corruption == "Fog":
            return self.fog_transform(image=frame)["image"]
        elif self.active_corruption == "Motion Blur":
            return self.blur_transform(image=frame)["image"]
        elif self.active_corruption == "Night / Low Light":
            return self.night_transform(image=frame)["image"]
        elif self.active_corruption == "ISO Noise":
            return self.noise_transform(image=frame)["image"]
        return frame

    def run(self):
        print("\n=============================================")
        print("🚀 STARTING LIVE DOMAIN STRESS TEST HARNESS ")
        print("=============================================")
        print("Hackathon Judge Controls:")
        print("  1: Induce Heavy Rain   | 2: Induce Density Fog    | 3: Induce Motion Blur")
        print("  4: Simulate Night Mode | 5: Simulate ISO Noise    | 0: Restore Clear Vision")
        print("  D: Toggle Network UDP Packet Drop Simulation")
        print("  Q: Terminate Stress Test")
        print("=============================================\n")
        
        while self.cap.isOpened():
            ret, frame = self.cap.read()
            if not ret: break
            
            frame = cv2.resize(frame, (640, 480))
            
            # --- PHASE 6: STRESS INJECTION (NETWORK FAILURE) ---
            if self.simulate_drops and random.random() < 0.2:
                # 20% Packet Loss Simulation - Trackers (ByteTrack) MUST survive this via Kalman velocities
                continue 
                
            # --- PHASE 6: STRESS INJECTION (SENSORY DEGRADATION) ---
            corrupted_frame = self._apply_corruption(frame)
            
            # Run the heavy Inference Pipeline
            t0 = time.time()
            out_frame, alerts, stats = pipeline.run(corrupted_frame.copy(), "stress_test_cam")
            latency = (time.time() - t0) * 1000
            
            # Draw UI Diagnostics Overlay
            cv2.putText(out_frame, f"Domain Shift: {self.active_corruption}", (10, 30), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255) if self.active_corruption != "None" else (0, 255, 0), 2)
            
            if self.simulate_drops:
                cv2.putText(out_frame, "UDP PACKET LOSS: DETECTED", (10, 60), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                            
            cv2.putText(out_frame, f"Infer FPS: {stats['fps']} | Total Lat: {latency:.1f}ms", (10, out_frame.shape[0]-20), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                        
            cv2.imshow("RailGuard Safety Critical - Live Validation", out_frame)
            
            # Keyboard Listeners for Hackathon Interactive Demo
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'): break
            elif key == ord('1'): self.active_corruption = "Rain"
            elif key == ord('2'): self.active_corruption = "Fog"
            elif key == ord('3'): self.active_corruption = "Motion Blur"
            elif key == ord('4'): self.active_corruption = "Night / Low Light"
            elif key == ord('5'): self.active_corruption = "ISO Noise"
            elif key == ord('0'): self.active_corruption = "None"
            elif key == ord('d'): self.simulate_drops = not self.simulate_drops

        self.cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RailGuard Live Domain Stress Test")
    parser.add_argument("--source", type=str, default="webcam", choices=["webcam", "ryde", "kyoto"], 
                        help="Select the live video stream source")
    args = parser.parse_args()
    
    tester = LiveStressTester(source_key=args.source) 
    tester.run()
