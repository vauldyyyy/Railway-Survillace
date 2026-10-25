"""
reid.py — cross-frame / cross-camera person re-identification.

Embeddings: global-average-pooled MobileNetV3-Small features (576-d, ImageNet
weights), L2-normalised. Matching: cosine similarity against an in-memory gallery
with an exponential moving average per identity, one-to-one within a frame.

Privacy: embeddings are perturbed with small Gaussian noise before they are stored
and the gallery is purged on a timer. This is a practical safeguard, NOT a formal
differential-privacy guarantee. Earlier versions advertised "ε=1.2 DP" while adding
noise with σ=0.12 per dimension to a unit vector — noise norm ≈2.7 vs signal 1.0 —
so no two crops of the same person could reach the match threshold and every
detection became a new identity. `noise_sigma` defaults to 0.01, which keeps the
cosine similarity between two noisy copies of the same embedding near 0.95.
"""
from __future__ import annotations

import base64
import time
import uuid
import warnings
import weakref

import numpy as np

EMBED_DIM = 576
MIN_CROP_AREA = 400


class MobileNetExtractor:
    """ImageNet MobileNetV3-Small trunk + global average pooling. Loads torch lazily."""

    dim = EMBED_DIM

    def __init__(self):
        import torch
        from torchvision import models, transforms

        self.torch = torch
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        backbone = models.mobilenet_v3_small(weights="MobileNet_V3_Small_Weights.DEFAULT")
        self.model = torch.nn.Sequential(backbone.features, torch.nn.AdaptiveAvgPool2d(1),
                                         torch.nn.Flatten()).to(self.device).eval()
        self.preprocess = transforms.Compose([
            transforms.ToPILImage(),
            transforms.Resize((256, 128)),  # standard person re-ID aspect ratio
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])

    def __call__(self, crop_bgr: np.ndarray) -> np.ndarray:
        rgb = np.ascontiguousarray(crop_bgr[:, :, ::-1])
        with self.torch.no_grad():
            x = self.preprocess(rgb).unsqueeze(0).to(self.device)
            return self.model(x).view(-1).cpu().numpy().astype(np.float32)


def _normalise(v: np.ndarray) -> np.ndarray:
    n = float(np.linalg.norm(v))
    return v / n if n > 0 else v


class ReIDTracker:
    def __init__(self, threshold: float = 0.75, noise_sigma: float = 0.01, reset_minutes: float = 60,
                 max_identities: int = 150, ema_alpha: float = 0.2, extractor=None, clock=time.time,
                 store_thumbnails: bool = True, seed: int | None = None, epsilon: float | None = None):
        if epsilon is not None:
            warnings.warn("ReIDTracker(epsilon=...) is ignored: the old noise scale destroyed matching. "
                          "Use noise_sigma.", DeprecationWarning, stacklevel=2)
        self.threshold = threshold
        self.noise_sigma = noise_sigma
        self.reset_minutes = reset_minutes
        self.max_identities = max_identities
        self.ema_alpha = ema_alpha
        self.clock = clock
        self.store_thumbnails = store_thumbnails
        self.rng = np.random.default_rng(seed)
        self._extractor = extractor
        self.gallery: dict[str, dict] = {}
        self.last_reset = clock()
        self._frame_ref = None
        self._frame_cam = None
        self._claimed: set[str] = set()

    @property
    def extractor(self):
        if self._extractor is None:
            self._extractor = MobileNetExtractor()
        return self._extractor

    # ------------------------------------------------------------------ embedding
    def embed(self, crop: np.ndarray) -> np.ndarray:
        vec = _normalise(np.asarray(self.extractor(crop), dtype=np.float32))
        if self.noise_sigma > 0:
            vec = _normalise(vec + self.rng.normal(0, self.noise_sigma, vec.shape).astype(np.float32))
        return vec

    def _best_match(self, emb: np.ndarray):
        ids = [k for k in self.gallery if k not in self._claimed]
        if not ids:
            return None, -1.0
        mat = np.stack([self.gallery[k]["embedding"] for k in ids])
        sims = mat @ emb
        i = int(np.argmax(sims))
        return ids[i], float(sims[i])

    # ------------------------------------------------------------------ update
    def update(self, frame: np.ndarray, box, camera_id: str):
        """Match one person box. Returns (identity, path) or (None, []) for tiny crops."""
        now = self.clock()
        if (now - self.last_reset) > self.reset_minutes * 60:
            self.gallery.clear()
            self.last_reset = now

        # Identities matched earlier in this same frame cannot be matched again.
        same_frame = (self._frame_ref is not None and self._frame_ref() is frame
                      and self._frame_cam == camera_id)
        if not same_frame:
            self._frame_ref, self._frame_cam, self._claimed = weakref.ref(frame), camera_id, set()

        h, w = frame.shape[:2]
        x1, y1, x2, y2 = (int(v) for v in box)
        x1, y1, x2, y2 = max(0, x1), max(0, y1), min(w, x2), min(h, y2)
        if (x2 - x1) * (y2 - y1) < MIN_CROP_AREA:
            return None, []
        crop = frame[y1:y2, x1:x2]
        emb = self.embed(crop)

        record = {"camera": camera_id, "time": time.strftime("%H:%M:%S", time.localtime(now)),
                  "center": ((x1 + x2) // 2, (y1 + y2) // 2)}
        best, score = self._best_match(emb)
        if best is not None and score >= self.threshold:
            g = self.gallery[best]
            g["embedding"] = _normalise((1 - self.ema_alpha) * g["embedding"] + self.ema_alpha * emb)
            g["path"].append(record)
            g["last_seen"] = now
            g["last_similarity"] = round(score, 4)
            self._claimed.add(best)
            return best, g["path"]

        if len(self.gallery) >= self.max_identities:
            oldest = min(self.gallery, key=lambda k: self.gallery[k]["last_seen"])
            del self.gallery[oldest]
        new_id = f"TRK-{uuid.uuid4().hex[:8].upper()}"
        self.gallery[new_id] = {"embedding": emb, "path": [record], "last_seen": now,
                                "status": "NORMAL",
                                "image": self._thumbnail(crop) if self.store_thumbnails else ""}
        self._claimed.add(new_id)
        return new_id, self.gallery[new_id]["path"]

    @staticmethod
    def _thumbnail(crop: np.ndarray) -> str:
        import cv2
        ok, buf = cv2.imencode(".jpg", crop, [cv2.IMWRITE_JPEG_QUALITY, 70])
        return "data:image/jpeg;base64," + base64.b64encode(buf.tobytes()).decode() if ok else ""
