"""
unattended.py — unattended-baggage detection from tracked person and bag boxes.

A bag becomes "unattended" when no person has been near it for `threshold_seconds`.
"Near" is scale-aware: within `proximity_factor` x the nearby person's box height
(minimum `min_radius_px`), so it works for people close to and far from the camera.
Each bag raises one alert, then at most one reminder per `cooldown_seconds`.
Pass the frame timestamp as `now` when processing recorded video so durations
follow video time, not wall-clock time.
"""
from __future__ import annotations

import time

import numpy as np


class UnattendedBaggageTracker:
    def __init__(self, threshold_seconds: float = 15, proximity_factor: float = 1.0,
                 min_radius_px: float = 60, stale_seconds: float = 2.0, cooldown_seconds: float = 30,
                 clock=time.time):
        self.threshold_seconds = threshold_seconds
        self.proximity_factor = proximity_factor
        self.min_radius_px = min_radius_px
        self.stale_seconds = stale_seconds
        self.cooldown_seconds = cooldown_seconds
        self.clock = clock
        # bag_id -> {"box", "first_seen", "last_person_near", "last_seen", "last_alert"}
        self.bag_registry: dict = {}

    @staticmethod
    def _centre(b):
        x1, y1, x2, y2 = b
        return (x1 + x2) / 2.0, (y1 + y2) / 2.0

    def _person_near(self, bag_box, persons) -> bool:
        bx, by = self._centre(bag_box)
        for _, pbox in persons:
            px, py = self._centre(pbox)
            radius = max(self.min_radius_px, self.proximity_factor * (pbox[3] - pbox[1]))
            if np.hypot(bx - px, by - py) <= radius:
                return True
        return False

    def update(self, frame, tracks, camera_id, now: float | None = None):
        """tracks = [{"id": track_id, "class_id": 0 for person / other for bag, "box": [x1,y1,x2,y2]}]"""
        now = self.clock() if now is None else now
        persons, bags = [], []
        for t in tracks:
            if t.get("id") is None:
                continue
            (persons if t["class_id"] == 0 else bags).append((t["id"], t["box"]))

        alerts = []
        for bag_id, box in bags:
            entry = self.bag_registry.setdefault(bag_id, {"first_seen": now, "last_person_near": now,
                                                          "last_alert": None})
            entry["box"], entry["last_seen"] = box, now
            if self._person_near(box, persons):
                entry["last_person_near"] = now
                entry["last_alert"] = None  # owner returned: re-arm
                continue
            alone_for = now - entry["last_person_near"]
            due = entry["last_alert"] is None or now - entry["last_alert"] >= self.cooldown_seconds
            if alone_for > self.threshold_seconds and due:
                entry["last_alert"] = now
                alerts.append({"type": "Unattended Baggage", "severity": "critical", "camera": camera_id,
                               "bag_id": bag_id,
                               "details": {"duration_s": int(alone_for), "box": [int(x) for x in box]},
                               "ts": now})

        self.bag_registry = {k: v for k, v in self.bag_registry.items()
                             if now - v["last_seen"] < self.stale_seconds}
        return alerts
