import cv2
import asyncio
import websockets
import base64
import json
import time

async def stream_video():
    uri = "ws://localhost:8000/ws/live_feed/CAM-01"
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    
    while True: # Infinite reconnection loop
        print(f"Attempting to connect to {uri}...")
        try:
            async with websockets.connect(uri, ping_interval=None) as websocket:
                print("Connected! Streaming stable frames...")
                while cap.isOpened():
                    ret, frame = cap.read()
                    if not ret: break

                    # Resize and Compress
                    frame = cv2.resize(frame, (400, 300))
                    _, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 30])
                    frame_b64 = base64.b64encode(buffer).decode('utf-8')

                    try:
                        await websocket.send(json.dumps({"camera_id": "CAM-01", "frame": frame_b64}))
                    except Exception as e:
                        print(f"Send failed: {e}")
                        break # Break inner loop to reconnect

                    await asyncio.sleep(0.1) # 10 FPS
        except Exception as e:
            print(f"Connection lost/failed: {e}. Retrying in 2s...")
            await asyncio.sleep(2)

if __name__ == "__main__":
    asyncio.run(stream_video())