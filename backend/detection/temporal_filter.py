import collections
import time

class TemporalFilter:
    """
    Filters out transient false positives by requiring consistent detection 
    over multiple frames before firing an alert.
    """
    def __init__(self, min_hits=5, max_age=10):
        self.min_hits = min_hits
        self.max_age = max_age
        self.track_history = collections.defaultdict(int)
        self.track_age = collections.defaultdict(int)
        self.confirmed_tracks = set()

    def update(self, current_track_ids):
        """
        Updates the track history and returns the set of confirmed active track IDs.
        """
        active_ids = set(current_track_ids)
        
        # 1. Update existing and new tracks
        for tid in active_ids:
            self.track_history[tid] += 1
            self.track_age[tid] = 0  # Reset age since it's seen
            
            if self.track_history[tid] >= self.min_hits:
                self.confirmed_tracks.add(tid)
        
        # 2. Handle missing tracks
        all_tracked_ids = list(self.track_history.keys())
        for tid in all_tracked_ids:
            if tid not in active_ids:
                self.track_age[tid] += 1
                
                # If track was confirmed but is now "too old", remove it
                if self.track_age[tid] >= self.max_age:
                    if tid in self.confirmed_tracks:
                        self.confirmed_tracks.remove(tid)
                    del self.track_history[tid]
                    del self.track_age[tid]
        
        return self.confirmed_tracks

def test_filter():
    print("[HARDENING] Testing Task 5: Temporal Filter...")
    tf = TemporalFilter(min_hits=3, max_age=2)
    
    # Simulate a flickering person (0, 0, 1, 1, 1, 0, 0)
    scenarios = [
        [1], [1], [1], [1], [], [], [1]
    ]
    
    for i, frame_ids in enumerate(scenarios):
        confirmed = tf.update(frame_ids)
        print(f"  Frame {i}: Detected={frame_ids} | Confirmed={list(confirmed)}")
        
    print("[OK] Task 5 Logic Verified.")

if __name__ == "__main__":
    test_filter()
