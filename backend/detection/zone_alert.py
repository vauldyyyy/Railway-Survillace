"""
zone_alert.py — Track intrusion detection using defined polygons.
"""
import cv2
import numpy as np

class ZoneIntrusionDetector:
    def __init__(self, polygons=None):
        if polygons is None:
            # Massive default polygon for the tracks area covering bottom 70% of 1080p screen
            self.track_zone = np.array([[0, 250], [1920, 250], [1920, 1080], [0, 1080]], dtype=np.int32)
        else:
            self.track_zone = np.array(polygons, dtype=np.int32)

    def check_intrusion(self, ltrb):
        x1, y1, x2, y2 = [int(x) for x in ltrb]
        # Bottom-center point represents feet
        cx, cy = (x1 + x2) // 2, y2
        
        # Returns +1 if inside, 0 if on edge, -1 if outside
        return cv2.pointPolygonTest(self.track_zone, (cx, cy), False) >= 0

    def draw(self, frame):
        cv2.polylines(frame, [self.track_zone], True, (0, 0, 255), 2)
        cv2.putText(frame, "RESTRICTED ZONE", (self.track_zone[0][0], self.track_zone[0][1] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

    def update_zone(self, polygons):
        self.track_zone = np.array(polygons, dtype=np.int32)