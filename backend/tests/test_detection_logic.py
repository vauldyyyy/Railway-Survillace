"""Unit tests for RailGuard's tracking and alert logic (no GPU, torch or model weights needed)."""
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from detection.reid import EMBED_DIM, ReIDTracker  # noqa: E402
from detection.temporal_filter import TemporalFilter  # noqa: E402
from detection.unattended import UnattendedBaggageTracker  # noqa: E402
from detection.zone_alert import ZoneIntrusionDetector  # noqa: E402

_PROJ = np.random.default_rng(0).normal(size=(24, EMBED_DIM)).astype(np.float32)


def colour_extractor(crop):
    """Stand-in for the CNN: colour histogram projected to the real embedding size."""
    hist = np.concatenate([np.histogram(crop[:, :, c], bins=8, range=(0, 256))[0] for c in range(3)])
    return (hist / max(hist.sum(), 1)).astype(np.float32) @ _PROJ


def frame_with(*people, size=(480, 640)):
    """people: (box, bgr colour). Returns the frame and the boxes."""
    f = np.zeros((*size, 3), dtype=np.uint8)
    for (x1, y1, x2, y2), colour in people:
        f[y1:y2, x1:x2] = colour
    return f, [b for b, _ in people]


class FakeClock:
    def __init__(self, t=1000.0):
        self.t = t

    def __call__(self):
        return self.t


RED, BLUE = (0, 0, 220), (220, 0, 0)


# --------------------------------------------------------------------------- re-ID
def test_same_person_keeps_identity_across_frames_and_cameras():
    clock = FakeClock()
    r = ReIDTracker(extractor=colour_extractor, clock=clock, seed=1, store_thumbnails=False)
    ids = set()
    for i, cam in enumerate(["CAM-1", "CAM-1", "CAM-2", "CAM-3"]):
        clock.t += 1
        f, (box,) = frame_with(((50 + 20 * i, 60, 130 + 20 * i, 260), RED))
        pid, path = r.update(f, box, cam)
        ids.add(pid)
    assert len(ids) == 1 and [p["camera"] for p in path] == ["CAM-1", "CAM-1", "CAM-2", "CAM-3"]


def test_different_people_get_different_identities():
    r = ReIDTracker(extractor=colour_extractor, seed=1, store_thumbnails=False)
    f, (a, b) = frame_with(((50, 60, 130, 260), RED), ((300, 60, 380, 260), BLUE))
    assert r.update(f, a, "CAM-1")[0] != r.update(f, b, "CAM-1")[0]


def test_two_lookalikes_in_one_frame_are_not_merged():
    r = ReIDTracker(extractor=colour_extractor, seed=1, store_thumbnails=False)
    f, (a, b) = frame_with(((50, 60, 130, 260), RED), ((300, 60, 380, 260), RED))
    assert r.update(f, a, "CAM-1")[0] != r.update(f, b, "CAM-1")[0]


def test_default_noise_preserves_matching_but_old_noise_scale_destroyed_it():
    """Regression test for the bug this module fixes."""

    def identities(sigma):
        clock = FakeClock()
        r = ReIDTracker(extractor=colour_extractor, noise_sigma=sigma, clock=clock, seed=3,
                        store_thumbnails=False, max_identities=1000)
        out = set()
        for _ in range(30):
            clock.t += 1
            f, (box,) = frame_with(((50, 60, 130, 260), RED))  # a new video frame each time
            out.add(r.update(f, box, "CAM-1")[0])
        return len(out)

    assert identities(0.01) == 1
    assert identities(0.12) > 20  # the previous setting: nearly every sighting a "new person"


def test_tiny_crops_are_skipped_and_gallery_is_purged_and_bounded():
    clock = FakeClock()
    r = ReIDTracker(extractor=colour_extractor, clock=clock, reset_minutes=1, max_identities=2,
                    seed=1, store_thumbnails=False)
    f, _ = frame_with(((0, 0, 10, 10), RED))
    assert r.update(f, (0, 0, 10, 10), "CAM-1") == (None, [])
    for colour, x in [(RED, 50), (BLUE, 200), ((0, 220, 0), 400)]:
        clock.t += 1
        f, (box,) = frame_with(((x, 60, x + 80, 260), colour))
        r.update(f, box, "CAM-1")
    assert len(r.gallery) == 2  # oldest evicted
    clock.t += 120
    f, (box,) = frame_with(((50, 60, 130, 260), RED))
    r.update(f, box, "CAM-1")
    assert len(r.gallery) == 1  # purge after reset_minutes


# --------------------------------------------------------------------------- baggage
def bag(x=300, y=300):
    return {"id": "bag-1", "class_id": 24, "box": [x, y, x + 40, y + 40]}


def person(x, y=200, h=180):
    return {"id": "p-1", "class_id": 0, "box": [x, y, x + 60, y + h]}


def test_alert_once_after_threshold_then_cooldown():
    t = UnattendedBaggageTracker(threshold_seconds=15, cooldown_seconds=30)
    alerts = [a for s in range(0, 40) for a in t.update(None, [bag()], "CAM-1", now=float(s))]
    assert len(alerts) == 1 and alerts[0]["details"]["duration_s"] == 16
    later = [a for s in range(40, 60) for a in t.update(None, [bag()], "CAM-1", now=float(s))]
    assert len(later) == 1  # one reminder after the 30 s cooldown


def test_owner_nearby_prevents_alert_and_rearms():
    t = UnattendedBaggageTracker(threshold_seconds=5)
    for s in range(20):
        assert t.update(None, [bag(), person(290)], "CAM-1", now=float(s)) == []


def test_proximity_scales_with_person_size():
    near_far_camera = [bag(300, 300), person(300 + 150, h=400)]   # tall person 150px away: near
    small_far = [bag(300, 300), person(300 + 150, h=60)]           # small person 150px away: not near
    t1, t2 = UnattendedBaggageTracker(threshold_seconds=1), UnattendedBaggageTracker(threshold_seconds=1)
    a1 = [a for s in range(5) for a in t1.update(None, near_far_camera, "C", now=float(s))]
    a2 = [a for s in range(5) for a in t2.update(None, small_far, "C", now=float(s))]
    assert a1 == [] and len(a2) == 1


# --------------------------------------------------------------------------- temporal filter / zone
def test_temporal_filter_confirms_after_min_hits_and_expires():
    tf = TemporalFilter(min_hits=3, max_age=2)
    assert tf.update([7]) == set() and tf.update([7]) == set()
    assert tf.update([7]) == {7}
    tf.update([])
    assert tf.update([]) == set()


def test_zone_intrusion_uses_feet_position():
    z = ZoneIntrusionDetector([[0, 300], [640, 300], [640, 480], [0, 480]])
    assert z.check_intrusion([100, 200, 150, 350])       # feet at y=350, inside
    assert not z.check_intrusion([100, 50, 150, 250])    # feet at y=250, outside
