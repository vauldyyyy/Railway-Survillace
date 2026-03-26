"""
unattended.py — Tracks person + bag associations across frames using DeepSORT.
"""
import time
import cv2
import numpy as np
from deep_sort_realtime.deepsort_tracker import DeepSort

class UnattendedBaggageTracker:
    def __init__(self, threshold_seconds=15):
        self.threshold_seconds = threshold_seconds
        self.tracker = DeepSort(max_age=30, n_init=3, nms_max_overlap=1.0)
        # bag_id -> {"box": [], "first_seen": ts, "last_person_near": ts, "last_seen": ts}
        self.bag_registry = {}

    def update(self, frame, detections_for_tracker, camera_id):
        alerts = []
        now = time.time()
        
        # detections_for_tracker = [([x, y, w, h], conf, class_id), ...]
        tracks = self.tracker.update_tracks(detections_for_tracker, frame=frame)
        
        persons = []
        bags = []
        
        for track in tracks:
            if not track.is_confirmed() or track.time_since_update > 1:
                continue
            
            track_id = track.track_id
            class_id = track.det_class
            ltrb = track.to_ltrb() # x1, y1, x2, y2
            
            if class_id == 0: # person
                persons.append(ltrb)
            else: # bag
                bags.append((track_id, ltrb))

        # Update registry
        for bag_id, ltrb in bags:
            bx1, by1, bx2, by2 = ltrb
            bcx, bcy = (bx1 + bx2) / 2, (by1 + by2) / 2
            
            if bag_id not in self.bag_registry:
                self.bag_registry[bag_id] = {
                    "box": ltrb, "first_seen": now, "last_person_near": now, "last_seen": now
                }
            else:
                self.bag_registry[bag_id]["box"] = ltrb
                self.bag_registry[bag_id]["last_seen"] = now

            # Check if any person is near
            person_nearby = False
            for px1, py1, px2, py2 in persons:
                pcx, pcy = (px1 + px2) / 2, (py1 + py2) / 2
                dist = np.sqrt((bcx - pcx)**2 + (bcy - pcy)**2)
                if dist < 120:  # ~120 pixel radius threshold
                    person_nearby = True
                    break
            
            if person_nearby:
                self.bag_registry[bag_id]["last_person_near"] = now
            else:
                duration = now - self.bag_registry[bag_id]["last_person_near"]
                if duration > self.threshold_seconds:
                    alerts.append({
                        "type": "Unattended Baggage",
                        "severity": "warning",
                        "camera": camera_id,
                        "details": {"duration_s": int(duration), "box": [int(x) for x in ltrb]},
                        "ts": now
                    })

        # Cleanup old entries (not seen for > 2 seconds)
        self.bag_registry = {k: v for k, v in self.bag_registry.items() if now - v["last_seen"] < 2}
        
        return tracks, alerts