"""
Camera Tamper Detection — Production Grade (v3)
=================================================
Multi-signal tamper detector combining:
  1. SSIM with adaptive baseline thresholding
  2. Temporal smoothing via sliding SSIM window
  3. Dense optical flow (Farneback) for motion verification
  4. Histogram-based lighting change rejection

Designed for real-time async FastAPI pipelines.

Dependencies:
    pip install opencv-python scikit-image numpy
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import cv2
import numpy as np
from skimage.metrics import structural_similarity as ssim

logger = logging.getLogger("railguard.ai.tamper_detector")

_EXECUTOR = ThreadPoolExecutor(max_workers=2)


# ======================================================================
# Data Structures
# ======================================================================

class AlertType(str, Enum):
    FREEZE = "Freeze/Replay Detected"
    BLOCKED = "Camera Blocked"
    DEFOCUS = "Camera Defocused"


@dataclass(slots=True)
class _FrameEntry:
    gray: np.ndarray
    timestamp: float
    histogram: np.ndarray


@dataclass(slots=True)
class AnalysisResult:
    status: str              # "ok" | "alert"
    alert: str | None
    ssim: float | None
    motion_magnitude: float | None
    confidence: float        # 0.0 – 1.0 (how certain we are of the alert)
    metrics: dict[str, Any]  # raw numbers for dashboards / logging

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "alert": self.alert,
            "ssim": self.ssim,
            "motion_magnitude": self.motion_magnitude,
            "confidence": round(self.confidence, 4),
            "metrics": self.metrics,
        }


# ======================================================================
# Main detector
# ======================================================================

@dataclass
class TamperDetector:
    """Production-grade async camera tamper detector.

    New in v3
    ---------
    * **Adaptive baseline**: SSIM threshold auto-calibrates from a rolling
      median of recent scores, avoiding fixed-threshold false positives.
    * **Temporal smoothing**: alerts only fire when the *sliding window
      average* of SSIM (not a single frame) crosses the threshold.
    * **Optical flow**: Farneback dense optical flow confirms whether real
      motion exists, separating lighting flicker from actual freeze.
    * **Histogram comparison**: Rapid global illumination change (clouds,
      train headlights) is detected via histogram correlation and excluded
      from block alerts.
    * **Structured logging**: All decisions are logged at DEBUG/WARNING
      level with machine-parseable key=value pairs.
    """

    # ── Tunable parameters ──
    buffer_size: int = 30
    ssim_window_size: int = 10
    freeze_base_threshold: float = 0.98
    freeze_duration_sec: float = 10.0
    block_base_threshold: float = 0.4
    block_variance_ceil: float = 5.0
    cooldown_sec: float = 3.0
    motion_threshold: float = 0.5
    histogram_change_threshold: float = 0.7
    defocus_laplacian_threshold: float = 50.0


    # ── Internal state ──
    _buffer: deque[_FrameEntry] = field(default_factory=deque, init=False, repr=False)
    _ssim_history: deque[float] = field(default_factory=deque, init=False, repr=False)
    _freeze_start: float | None = field(default=None, init=False, repr=False)
    _last_alert_time: float = field(default=0.0, init=False, repr=False)
    _last_alert_type: str | None = field(default=None, init=False, repr=False)
    _baseline_ssim: float | None = field(default=None, init=False, repr=False)
    _calibration_frames: int = field(default=0, init=False, repr=False)

    def __post_init__(self) -> None:
        self._buffer = deque(maxlen=self.buffer_size)
        self._ssim_history = deque(maxlen=self.ssim_window_size)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def analyze_frame(self, current_frame: np.ndarray) -> AnalysisResult:
        """Non-blocking multi-signal analysis of a single BGR frame."""
        now = time.monotonic()
        gray = cv2.cvtColor(current_frame, cv2.COLOR_BGR2GRAY)
        hist = cv2.calcHist([gray], [0], None, [256], [0, 256]).flatten()
        hist = hist / (hist.sum() + 1e-7)  # normalise

        entry = _FrameEntry(gray=gray, timestamp=now, histogram=hist)

        # Bootstrap: need at least one previous frame
        if len(self._buffer) == 0:
            self._buffer.append(entry)
            logger.debug("tamper_detector frame=first action=buffered")
            return _ok()

        prev = self._buffer[-1]

        # ── Offload heavy compute to thread pool ──
        loop = asyncio.get_running_loop()
        score, flow_mag, laplacian_var = await loop.run_in_executor(
            _EXECUTOR,
            _compute_signals,
            gray,
            prev.gray,
        )

        # ── Update sliding window ──
        self._ssim_history.append(score)
        smoothed_ssim = float(np.median(self._ssim_history))

        # ── Adaptive baseline calibration (first 60 frames ≈ 2 s @ 30 fps) ──
        self._calibration_frames += 1
        if self._calibration_frames <= 60:
            self._baseline_ssim = smoothed_ssim
            self._buffer.append(entry)
            logger.debug(
                "tamper_detector calibrating frame=%d baseline_ssim=%.4f",
                self._calibration_frames, smoothed_ssim,
            )
            return _ok(ssim_score=score, motion=flow_mag)

        # Adapt thresholds relative to baseline
        freeze_thresh = max(
            self.freeze_base_threshold,
            (self._baseline_ssim or 0.95) + 0.005,
        )
        block_thresh = min(
            self.block_base_threshold,
            (self._baseline_ssim or 0.80) - 0.3,
        )

        # ── Histogram change check (lighting rejection) ──
        hist_corr = float(cv2.compareHist(
            prev.histogram.astype(np.float32),
            hist.astype(np.float32),
            cv2.HISTCMP_CORREL,
        ))
        is_lighting_change = hist_corr < self.histogram_change_threshold and score > block_thresh

        metrics = {
            "raw_ssim": round(score, 6),
            "smoothed_ssim": round(smoothed_ssim, 6),
            "flow_magnitude": round(flow_mag, 4),
            "laplacian_var": round(laplacian_var, 2),
            "histogram_corr": round(hist_corr, 4),
            "adaptive_freeze_thresh": round(freeze_thresh, 4),
            "adaptive_block_thresh": round(block_thresh, 4),
            "is_lighting_change": is_lighting_change,
        }

        logger.debug("tamper_detector %s", " ".join(f"{k}={v}" for k, v in metrics.items()))

        # ── 1. Freeze / Replay (SSIM high + no optical flow) ──
        if smoothed_ssim >= freeze_thresh and flow_mag < self.motion_threshold:
            if self._freeze_start is None:
                self._freeze_start = now
            elapsed = now - self._freeze_start
            if elapsed >= self.freeze_duration_sec:
                confidence = min(1.0, elapsed / (self.freeze_duration_sec * 2))
                self._buffer.append(entry)
                return self._emit(
                    AlertType.FREEZE, score, flow_mag, confidence, metrics, now
                )
        else:
            self._freeze_start = None

        # ── 2. Camera Blocked / Blinded ──
        if smoothed_ssim < block_thresh and not is_lighting_change:
            variance = float(np.var(gray.astype(np.float32)))
            if variance <= self.block_variance_ceil:
                confidence = min(1.0, (block_thresh - smoothed_ssim) / block_thresh)
                self._buffer.append(entry)
                return self._emit(
                    AlertType.BLOCKED, score, flow_mag, confidence, metrics, now
                )

        # ── 3. Defocus / Spray (low Laplacian variance) ──
        if laplacian_var < self.defocus_laplacian_threshold and flow_mag < self.motion_threshold:
            confidence = min(1.0, (self.defocus_laplacian_threshold - laplacian_var) / self.defocus_laplacian_threshold)
            if confidence > 0.6:
                self._buffer.append(entry)
                return self._emit(
                    AlertType.DEFOCUS, score, flow_mag, confidence, metrics, now
                )

        self._buffer.append(entry)
        return _ok(ssim_score=score, motion=flow_mag, metrics=metrics)

    def reset(self) -> None:
        self._buffer.clear()
        self._ssim_history.clear()
        self._freeze_start = None
        self._last_alert_time = 0.0
        self._last_alert_type = None
        self._baseline_ssim = None
        self._calibration_frames = 0
        logger.info("tamper_detector state=reset")

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _emit(
        self,
        alert_type: AlertType,
        ssim_score: float,
        motion: float,
        confidence: float,
        metrics: dict,
        now: float,
    ) -> AnalysisResult:
        if (
            self._last_alert_type == alert_type.value
            and (now - self._last_alert_time) < self.cooldown_sec
        ):
            logger.debug("tamper_detector alert=%s suppressed=cooldown", alert_type.value)
            return _ok(ssim_score=ssim_score, motion=motion, metrics=metrics)

        self._last_alert_time = now
        self._last_alert_type = alert_type.value
        logger.warning(
            "tamper_detector ALERT=%s ssim=%.4f motion=%.4f confidence=%.4f",
            alert_type.value, ssim_score, motion, confidence,
        )
        return AnalysisResult(
            status="alert",
            alert=alert_type.value,
            ssim=ssim_score,
            motion_magnitude=motion,
            confidence=confidence,
            metrics=metrics,
        )


# ======================================================================
# CPU-bound helpers (run in thread pool)
# ======================================================================

def _compute_signals(
    gray_curr: np.ndarray,
    gray_prev: np.ndarray,
) -> tuple[float, float, float]:
    """Return (ssim_score, optical_flow_magnitude, laplacian_variance)."""
    # 1. SSIM
    score = float(ssim(gray_curr, gray_prev))

    # 2. Dense optical flow (Farneback)
    flow = cv2.calcOpticalFlowFarneback(
        gray_prev, gray_curr,
        None,  # type: ignore[arg-type]
        pyr_scale=0.5, levels=3, winsize=15,
        iterations=3, poly_n=5, poly_sigma=1.2,
        flags=0,
    )
    magnitude, _ = cv2.cartToPolar(flow[..., 0], flow[..., 1])
    flow_mag = float(np.mean(magnitude))

    # 3. Laplacian variance (focus measure)
    laplacian_var = float(cv2.Laplacian(gray_curr, cv2.CV_64F).var())

    return score, flow_mag, laplacian_var


def _ok(
    ssim_score: float | None = None,
    motion: float | None = None,
    metrics: dict | None = None,
) -> AnalysisResult:
    return AnalysisResult(
        status="ok",
        alert=None,
        ssim=ssim_score,
        motion_magnitude=motion,
        confidence=0.0,
        metrics=metrics or {},
    )
