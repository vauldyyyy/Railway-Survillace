"""
Remote GPU Bridge Client
Handles communication between the local backend and a remote Colab GPU worker.
Falls back gracefully to local inference if the bridge is unavailable.
"""
import os
import time
import threading
import cv2
import numpy as np

try:
    import requests
    _REQUESTS_AVAILABLE = True
except ImportError:
    _REQUESTS_AVAILABLE = False
    print("[RemoteClient] Warning: 'requests' not installed. Remote inference disabled.")


class RemoteInferenceClient:
    """
    HTTP client that sends frames to the Colab GPU bridge for inference.
    Provides automatic health checking, latency tracking, and graceful fallback.
    """

    def __init__(self):
        self.remote_url = os.environ.get("REMOTE_INFERENCE_URL", "").strip()
        self.mode = os.environ.get("INFERENCE_MODE", "local").strip().lower()
        self.is_connected = False
        self.latency_ms = 0.0
        self.last_health_check = 0
        self.health_check_interval = 10  # seconds
        self._consecutive_failures = 0
        self._max_failures = 3  # fallback after 3 consecutive failures
        self._lock = threading.Lock()

        if self.mode == "remote" and self.remote_url and _REQUESTS_AVAILABLE:
            print(f"[RemoteClient] Configured for REMOTE inference: {self.remote_url}")
            self._start_health_monitor()
        else:
            if self.mode == "remote" and not self.remote_url:
                print("[RemoteClient] REMOTE mode set but no REMOTE_INFERENCE_URL configured. Using local.")
            print("[RemoteClient] Running in LOCAL inference mode.")
            self.mode = "local"

    def _start_health_monitor(self):
        """Background thread that periodically pings the remote bridge."""
        def _monitor():
            while True:
                self._check_health()
                time.sleep(self.health_check_interval)

        t = threading.Thread(target=_monitor, daemon=True)
        t.start()

    def _check_health(self):
        """Ping the /health endpoint of the remote bridge."""
        if not self.remote_url or not _REQUESTS_AVAILABLE:
            return

        try:
            start = time.time()
            resp = requests.get(f"{self.remote_url}/health", timeout=5)
            elapsed = (time.time() - start) * 1000

            if resp.status_code == 200:
                data = resp.json()
                with self._lock:
                    self.is_connected = True
                    self.latency_ms = round(elapsed, 1)
                    self._consecutive_failures = 0
                    self.last_health_check = time.time()
                return True
        except Exception as e:
            pass

        with self._lock:
            self.is_connected = False
            self.latency_ms = 0.0
        return False

    def detect_remote(self, frame, condition="normal"):
        """
        Send a frame to the remote GPU bridge for inference.
        Returns a list of detection dicts compatible with the local pipeline format,
        or None if the remote bridge is unavailable (signaling local fallback).
        """
        if self.mode != "remote" or not self.is_connected or not _REQUESTS_AVAILABLE:
            return None

        try:
            # Encode frame as JPEG for efficient transfer
            _, jpg_buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            jpg_bytes = jpg_buf.tobytes()

            start = time.time()
            resp = requests.post(
                f"{self.remote_url}/detect",
                files={"file": ("frame.jpg", jpg_bytes, "image/jpeg")},
                data={"condition": condition},
                timeout=10,
            )
            elapsed = (time.time() - start) * 1000

            if resp.status_code == 200:
                data = resp.json()
                with self._lock:
                    self.latency_ms = round(elapsed, 1)
                    self._consecutive_failures = 0
                return data.get("detections", [])
            else:
                self._handle_failure()
                return None

        except requests.exceptions.Timeout:
            print("[RemoteClient] Request timed out, falling back to local.")
            self._handle_failure()
            return None
        except Exception as e:
            print(f"[RemoteClient] Error: {e}")
            self._handle_failure()
            return None

    def _handle_failure(self):
        """Track consecutive failures and disable remote if threshold exceeded."""
        with self._lock:
            self._consecutive_failures += 1
            if self._consecutive_failures >= self._max_failures:
                print(f"[RemoteClient] {self._max_failures} consecutive failures. Falling back to LOCAL.")
                self.is_connected = False

    def get_status(self):
        """Return a status dict for the frontend GPU Bridge indicator."""
        with self._lock:
            return {
                "mode": self.mode,
                "connected": self.is_connected,
                "latency_ms": self.latency_ms,
                "remote_url": self.remote_url if self.mode == "remote" else None,
            }


# Global singleton
remote_client = RemoteInferenceClient()
