"""
temporal_filter.py — Multi-frame detection hardening layer.

Requires min_hits consecutive detections before confirming a track.
Prevents single-frame noise from generating alerts.

V2 fixes: min_hits raised from 1→3 (was instantly confirming everything).
"""
import collections
import time


class TemporalFilter:
    def __init__(self, min_hits=3, max_age=8):
        self.min_hits = min_hits
        self.max_age = max_age
        self.track_history = collections.defaultdict(int)
        self.track_age = collections.defaultdict(int)
        self.confirmed_tracks = set()

    def update(self, current_track_ids):
        """
        Updates track history. Returns set of confirmed active track IDs.
        A track must be seen in min_hits frames to be confirmed.
        """
        active_ids = set(current_track_ids)

        for tid in active_ids:
            self.track_history[tid] += 1
            self.track_age[tid] = 0

            if self.track_history[tid] >= self.min_hits:
                self.confirmed_tracks.add(tid)

        stale = []
        for tid in list(self.track_history.keys()):
            if tid not in active_ids:
                self.track_age[tid] += 1
                if self.track_age[tid] >= self.max_age:
                    self.confirmed_tracks.discard(tid)
                    stale.append(tid)

        for tid in stale:
            del self.track_history[tid]
            del self.track_age[tid]

        return self.confirmed_tracks

    def reset(self):
        self.track_history.clear()
        self.track_age.clear()
        self.confirmed_tracks.clear()
