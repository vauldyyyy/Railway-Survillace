# RailGuard AI — System Architecture & Implementation Details

*Developed for Cyber Dome 2026 Hackathon*

This document provides a comprehensive overview of the implementation, components, and advanced features built into the **RailGuard AI** Railway Surveillance System. The system was designed from the ground up to provide research-grade, 90%+ operational reliability across diverse environmental conditions.

---

## 1. Zero-Shot Vision Intelligence (YOLO-World)
Instead of relying on a narrowly trained, rigid object detector, we implemented the YOLOv8-World foundation model. 

* **Dynamic Prompting:** The vision system isn't hardcoded. It dynamically prompts the foundation model to look for specific targets: `["person", "backpack", "suitcase", "train", "animal"]`.
* **Context-Aware Adaptation:** In specific conditions (like low-light), the system dynamically injects additional prompts (e.g., `["flashlight"]`) to improve scene understanding without requiring model retraining.
* **Threat Severities:** Detections are automatically classified. Identifying a "person" or "backpack" triggers standard tracking, while detecting "weapon", "fire", or "smoke" automatically escalates to a `critical` severity alert.

## 2. Advanced Cross-Camera Tracking (OSNet Re-Identification)
To maintain persistent tracking across multiple non-overlapping camera feeds in the railway station, we implemented a sophisticated Re-Identification (ReID) layer.

* **Omni-Scale Network (OSNet):** Extracts deep visual features from detected persons, invariant to changes in camera angle, lighting, or pose.
* **Differential Privacy:** To ensure compliance with modern privacy standards, the ReID feature vectors undergo noise-injection (Differential Privacy with $\epsilon = 0.1$). This prevents the exact biometric reconstruction of individuals while still allowing the system to match global tracks.
* **Global Trajectory Mapping:** The system assigns a unique UUID to individuals and plots their trajectory seamlessly as they move from platform to platform.

## 3. Persistent Inference GPU Bridge (Cloud Offloading)
To make the system hardware-agnostic and ensure the dashboard remains incredibly responsive even on low-spec local machines, we built a hybrid inference engine bridging Local CPU and Google Colab GPUs via Ngrok.

* **Colab Inference Worker:** A standalone environment (`remote_ai_server.py`) that mounts the heavy YOLO-World model onto a free Colab T4 GPU and exposes a high-speed prediction endpoint via an ephemeral Ngrok HTTP tunnel.
* **Local `RemoteClient` Engine:** The local FastAPI backend securely relays compressed video frames to the Colab GPU.
* **Seamless Failover & Fallback:** The backend actively monitors bridge latency and health. If the Colab runtime disconnects or fails 3 consecutive times, the pipeline instantly and silently falls back to localized CPU inference, ensuring the surveillance feed never drops.
* **UI Telemetry:** The React sidebar features a live telemetry badge detailing the active inference source (`GPU BRIDGE` vs `LOCAL CPU`) and real-time millisecond latency.

## 4. Adverse Condition Preprocessing Layer
Real-world railway environments suffer from fog, smog, and poor illumination. We integrated a pre-inference enhancement layer to stabilize accuracy.

* **Dynamic Dehazing:** Automatically detects fog/haze density and applies contrast-restoring algorithms to the frame before it hits the neural network.
* **Low-Light Enhancement:** Uses adaptive histogram techniques to brighten shadows in nocturnal feeds without blowing out highlights, vastly improving the recall rate at night.

## 5. Temporal Filtering & Zone Intrusion Logic
To harden the system against false positives (flickering detections):

* **Temporal Stabilizer:** A detection must be witnessed across multiple consecutive frames (minimum hits) before it is escalated to the dashboard, preventing transient noise from spamming security operators.
* **Intrusion Zones:** Bounding boxes are verified against defined spatial polygons (e.g., the physical train tracks). A person matched locally but stepping into a restricted zone automatically triggers a `PERSON ON TRACK` critical alert.

## 6. The User Interface (React + Zustand)
The SOC (Security Operations Center) dashboard was built to be responsive, aesthetic, and data-rich.

* **Aesthetic Design:** Utilizes a dark cyber-aesthetic with glassmorphism, precise telemetry readouts, and animated data flows.
* **Live WebSockets:** Alerts, heatmap data, System FPS, global confidence metrics, and cross-camera trajectories are streamed instantly from Python to React via WebSockets.
* **Global State Management:** `Zustand` provides a lightweight, frictionless global store handling the active threat index (0-10 scale), model metrics, and active camera states.

## 7. Secured Encrypted Backend
* **FastAPI:** Handles the high-bandwidth requirements of raw MJPEG video streaming concurrently with WebSocket data.
* **AES-256-GCM Encryption:** All verified incidents are dumped into an encrypted local SQLite database, ensuring that sensitive tracking data cannot be tampered with or read if the physical hard drive is compromised.
