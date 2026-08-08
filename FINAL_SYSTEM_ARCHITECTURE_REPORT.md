# 🏗️ RailGuard AI: System Architecture & Technical Implementation
**Official Technical Overview: Cyber Dome 2026 Hackathon**

The **RailGuard AI** system is a next-generation railway surveillance platform built on a distributed, high-performance architecture. It is designed to provide "Zero-Miss" threat detection across multiple non-overlapping camera feeds while maintaining extreme dashboard responsiveness.

---

## 1. Core Technology Stack
Our architecture leverages modern, high-concurrency frameworks to handle real-time video and AI data.

*   **Frontend**: React 18 + Vite (SPA)
    *   **State Management**: Zustand (Lightweight, frictionless global store).
    *   **Styling**: Tailwind CSS + Custom Cyber-Glassmorphism UI.
    *   **Data Ingest**: Real-time WebSockets (Alerts, Metrics, Heatmaps).
*   **Backend**: FastAPI (Python 3.10+)
    *   **Streaming**: Thread-safe Multi-MJPEG concurrent emitters.
    *   **Concurrency**: Asynchronous event loop for WebSocket orchestration.
    *   **Security**: AES-256-GCM Encrypted SQLite Incident Database.
*   **AI Engine**: YOLOv8s + OSNet Re-Identification
    *   **Logic**: Custom State Machine for "Baggage Ownership" and "Track Intrusion."

---

## 2. Distributed Inference Pipeline (The Hybrid Bridge)
To ensure high-performance AI on any hardware, we implemented a proprietary **Hybrid Inference Bridge**.

*   **Remote GPU Offloading**: The system can securely relay frames to a remote **NVIDIA T4 GPU** (via Google Colab/Ngrok) for complex foundation-model tasks.
*   **Intelligent Failover**: The backend actively monitors latency. If the Remote Bridge fails or exceeds 400ms latency, the system **instantly fallbacks to Local CPU** inference to ensure zero downtime.
*   **Zero-Shot Awareness**: Utilizing **YOLO-World**, the system can detect objects it has never seen in its training set (e.g., "stagnant bag") via natural language prompting.

---

## 3. High-Fidelity Intelligence Layers
Beyond simple object detection, RailGuard implements multiple "Smart Layers" to filter noise and enhance security.

### 🛡️ Layer 1: Temporal Filtering
Detects must persist for multiple consecutive frames before an alert is fired. This eliminates "ghost" detections and flickering caused by lighting changes.

### 🛡️ Layer 2: Zone-Based Threat Assessment
The system maps physical "Danger Zones" (e.g., the tracks). A detection only escalates to a **CRITICAL** alert if it intersects with these coordinate-mapped polygons.

### 🛡️ Layer 3: 5s Separation Heuristic (Baggage)
Precisely tracks the spatial proximity between a person and their bag. If the separation distance exceeds 2.5 meters for more than **5 seconds**, the item is classified as "Unattended Baggage."

---

## 4. Privacy & Forensic Security
*   **ReID Privacy**: To comply with data safety standards, our Re-Identification (ReID) vectors use **Differential Privacy** (noise injection). This allows tracking individuals across cameras without storing sensitive biometric templates.
*   **Encrypted Incident Logs**: Every alert, snapshot, and tracking event is stored in an encrypted vault. Only authorized SOC operators with the decryption key can view historical incident data.

---
**Developed by BitsGoa for Cyber Dome 2026**
**Presented on 31st March 2026**
