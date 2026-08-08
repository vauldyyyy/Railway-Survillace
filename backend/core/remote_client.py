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
    Self-heals automatically by polling for the bridge at high frequency when offline.
    """

    def __init__(self):
        # ULTIMATE OVERRIDE FOR HACKATHON DEMO: Bypass .env race conditions
        self.remote_url = "https://railguard-bitsgoa.loca.lt"
        self.mode = "remote"
        
        self.is_connected = False
        self.latency_ms = 0.0
        self.last_health_check = 0
        self._consecutive_failures = 0
        self._lock = threading.Lock()

        print(f"🚀 [ULTIMATE BRIDGE] Target: {self.remote_url} (Waking up in background...)")
        # Do NOT check health synchronously at startup (prevents hanging)
        self._start_health_monitor()

    def _start_health_monitor(self):
        """Background thread that periodically pings the remote bridge with adaptive frequency."""
        def _monitor():
            while True:
                connected = self._check_health()
                # Poll faster (2s) if we aren't connected yet to catch the bridge ASAP
                # Poll slower (10s) if we are stable to save bandwidth
                interval = 2 if not connected else 10
                time.sleep(interval)

        t = threading.Thread(target=_monitor, daemon=True)
        t.start()

    def _check_health(self):
        """Ping the /health endpoint of the remote bridge."""
        if not self.remote_url or not _REQUESTS_AVAILABLE:
            return False

        try:
            start = time.time()
            # Bypassing SSL for Hackathon WiFi security blocks + Localtunnel Interstitial
            headers = {"Bypass-Tunnel-Reminder": "true"}
            resp = requests.get(f"{self.remote_url}/health", timeout=10, verify=False, headers=headers)
            elapsed = (time.time() - start) * 1000

            if resp.status_code == 200:
                with self._lock:
                    if not self.is_connected:
                        print(f" [OK] GPU Bridge Connected! ({self.remote_url})")
                    self.is_connected = True
                    self.latency_ms = round(elapsed, 1)
                    self._consecutive_failures = 0
                    self.last_health_check = time.time()
                return True
        except Exception as e:
            if self.is_connected:
                print(f" [!!] GPU Health Check Error: {e}")
            pass

        with self._lock:
            if self.is_connected:
                print(" [!!] GPU Bridge Disconnected. Retrying in background...")
            self.is_connected = False
            self.latency_ms = 0.0
        return False

    def detect_remote(self, frame, condition="normal"):
        """
        Send a frame to the remote GPU bridge for inference.
        Returns a list of detection dicts or None if currently disconnected.
        """
        if self.mode != "remote" or not _REQUESTS_AVAILABLE:
            return None

        # Optimistic check: if not connected, try a 2s fast-timeout once
        # If connected, use the standard 5s timeout
        request_timeout = 5 if self.is_connected else 2

        try:
            _, jpg_buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            jpg_bytes = jpg_buf.tobytes()

            start = time.time()
            # Adding the Localtunnel bypass header to skip the "Tunnel Reminder" interstitial
            headers = {"Bypass-Tunnel-Reminder": "true"}
            
            resp = requests.post(
                f"{self.remote_url}/detect",
                files={"image": ("frame.jpg", jpg_bytes, "image/jpeg")},
                data={"condition": condition},
                headers=headers,
                timeout=request_timeout,
                verify=False
            )
            elapsed = (time.time() - start) * 1000

            if resp.status_code == 200:
                data = resp.json()
                with self._lock:
                    if not self.is_connected:
                        print(f" [OK] GPU Bridge Re-Established via Inference Path.")
                    self.is_connected = True
                    self.latency_ms = round(elapsed, 1)
                    self._consecutive_failures = 0
                return data.get("detections", [])
            else:
                self._handle_failure()
                return None

        except Exception:
            self._handle_failure()
            return None

    def _handle_failure(self):
        """Track failures and ensure is_connected is false so background polling resumes."""
        with self._lock:
            self._consecutive_failures += 1
            if self.is_connected:
                print(f"[RemoteClient] Connection lost (Failure #{self._consecutive_failures}). Searching for bridge...")
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
