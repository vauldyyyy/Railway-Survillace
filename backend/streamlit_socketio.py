"""
RailGuard AI — Streamlit Socket.IO Client Dashboard
=====================================================
Connects to the Socket.IO server via background thread for
zero-lag security alerts and live video display.

Run:
    streamlit run backend/streamlit_socketio.py
"""

import base64
import json
import queue
import threading
import time
from datetime import datetime

import requests
import streamlit as st

try:
    import socketio as sio_client
except ImportError:
    st.error("Install python-socketio client: `pip install python-socketio[client] websocket-client`")
    st.stop()


# ======================================================================
# Config
# ======================================================================

SERVER_URL = "http://localhost:8000"
POLL_INTERVAL = 0.5


# ======================================================================
# Session state
# ======================================================================

if "alert_queue" not in st.session_state:
    st.session_state.alert_queue = queue.Queue()

if "frame_queue" not in st.session_state:
    st.session_state.frame_queue = queue.Queue(maxsize=5)

if "sio_started" not in st.session_state:
    st.session_state.sio_started = False

if "sio_connected" not in st.session_state:
    st.session_state.sio_connected = False

if "alert_history" not in st.session_state:
    st.session_state.alert_history = []


# ======================================================================
# 4. THE STREAMLIT CLIENT — socketio.Client in background thread
# ======================================================================

def _socketio_thread(alert_q: queue.Queue, frame_q: queue.Queue) -> None:
    """Background thread running the Socket.IO client.

    Listens on default namespace for security_alert events.
    Listens on /live namespace for video_frame events.
    """
    client = sio_client.Client(
        reconnection=True,
        reconnection_attempts=0,     # infinite
        reconnection_delay=2,
    )

    # ── Default namespace handlers ──

    @client.event
    def connect():
        print("[SOCKET.IO CLIENT] Connected to server!", flush=True)
        st.session_state.sio_connected = True

    @client.event
    def disconnect():
        print("[SOCKET.IO CLIENT] Disconnected from server.", flush=True)
        st.session_state.sio_connected = False

    @client.event
    def server_info(data):
        print(f"[SOCKET.IO CLIENT] Server: {data.get('msg', '')}", flush=True)

    @client.event
    def security_alert(data):
        """Push alert into the queue for the Streamlit main thread."""
        print(f"[SOCKET.IO CLIENT] 🚨 Alert received: {data.get('msg', 'UNKNOWN')}", flush=True)
        alert_q.put(data)

    # ── /live namespace handlers ──

    @client.on("video_frame", namespace="/live")
    def on_video_frame(data):
        """Push latest frame into the frame queue (drops old frames)."""
        try:
            if frame_q.full():
                frame_q.get_nowait()
            frame_q.put_nowait(data)
        except queue.Full:
            pass

    @client.on("stream_error", namespace="/live")
    def on_stream_error(data):
        print(f"[SOCKET.IO CLIENT] Stream error: {data.get('msg', '')}", flush=True)

    @client.on("connect", namespace="/live")
    def on_live_connect():
        print("[SOCKET.IO CLIENT] /live namespace connected!", flush=True)

    # ── Connection loop ──
    while True:
        try:
            print(f"[SOCKET.IO CLIENT] Connecting to {SERVER_URL}...", flush=True)
            client.connect(SERVER_URL, namespaces=["/", "/live"])
            client.wait()
        except Exception as exc:
            print(f"[SOCKET.IO CLIENT] Error: {exc}. Retrying in 3s...", flush=True)
            time.sleep(3)


# ======================================================================
# UI
# ======================================================================

st.set_page_config(
    page_title="RailGuard AI — Live Security Dashboard",
    page_icon="🛡️",
    layout="wide",
)

st.markdown("""
<div style="background: linear-gradient(135deg, #0B0F19 0%, #1a1f2e 100%);
            padding: 1.5rem 2rem; border-radius: 12px; margin-bottom: 1.5rem;
            border: 1px solid rgba(6,182,212,0.2);">
    <h1 style="color: #06b6d4; margin: 0; font-size: 1.8rem;">
        🛡️ RailGuard AI — Socket.IO Live Dashboard
    </h1>
    <p style="color: #94a3b8; margin: 0.25rem 0 0 0; font-size: 0.9rem;">
        Real-time alerts via Socket.IO · Camera Gateway · Data Shield · Logic Gate
    </p>
</div>
""", unsafe_allow_html=True)


# ── Start background thread ──
if not st.session_state.sio_started:
    t = threading.Thread(
        target=_socketio_thread,
        args=(st.session_state.alert_queue, st.session_state.frame_queue),
        daemon=True,
    )
    t.start()
    st.session_state.sio_started = True


# ── Status bar ──
col1, col2, col3 = st.columns(3)
with col1:
    icon = "🟢" if st.session_state.sio_connected else "🔴"
    st.metric("Socket.IO", f"{icon} {'Connected' if st.session_state.sio_connected else 'Disconnected'}")
with col2:
    st.metric("Alerts Received", len(st.session_state.alert_history))
with col3:
    try:
        h = requests.get(f"{SERVER_URL}/health", timeout=2).json()
        st.metric("Server", f"🟢 {h.get('transport', 'socket.io')}")
    except Exception:
        st.metric("Server", "🔴 Offline")

st.divider()


# ── Live video frame display ──
video_col, alert_col = st.columns([2, 1])

with video_col:
    st.subheader("📹 Live Camera Feed")
    video_placeholder = st.empty()

    try:
        frame_data = st.session_state.frame_queue.get_nowait()
        b64 = frame_data.get("data", "")
        if b64:
            img_bytes = base64.b64decode(b64)
            video_placeholder.image(img_bytes, channels="BGR", use_container_width=True)
    except queue.Empty:
        video_placeholder.info("No live feed active. Start stream from server.")


# ── Drain alert queue ──
with alert_col:
    st.subheader("🚨 Live Alerts")

    while not st.session_state.alert_queue.empty():
        try:
            alert = st.session_state.alert_queue.get_nowait()
            msg = alert.get("msg", "UNKNOWN")
            camera = alert.get("camera_id", "—")
            ts = datetime.fromtimestamp(alert.get("timestamp", time.time())).strftime("%H:%M:%S")

            if msg == "TAMPER_DETECTED":
                st.error(f"🚨 **TAMPER DETECTED** — `{camera}` at {ts}")
                st.toast(f"🔴 Camera {camera} tampered!", icon="🚨")
            elif msg == "INJECTION_ATTEMPT":
                st.error(f"🛑 **INJECTION BLOCKED** — `{camera}` at {ts}")
                st.toast(f"🛑 Injection attempt!", icon="🛑")
            else:
                st.warning(f"⚠️ **{msg}** — `{camera}` at {ts}")
                st.toast(f"⚠️ {msg}", icon="⚠️")

            st.session_state.alert_history.append({
                "Time": ts,
                "Type": msg,
                "Camera": camera,
                "Detail": str(alert.get("alert_type", alert.get("risk_score", "")))[:60],
            })

        except queue.Empty:
            break

    if not st.session_state.alert_history:
        st.info("Monitoring for events…")


# ── Incident table ──
st.divider()
st.subheader("📋 Incident Log")

if st.session_state.alert_history:
    display = list(reversed(st.session_state.alert_history[-50:]))
    st.dataframe(display, use_container_width=True, height=250)

with st.expander("📂 Database Incidents (from API)", expanded=False):
    try:
        incidents = requests.get(f"{SERVER_URL}/incidents", timeout=2).json()
        if incidents:
            st.dataframe(incidents, use_container_width=True)
        else:
            st.info("No incidents in database.")
    except Exception as exc:
        st.warning(f"Could not fetch: {exc}")


# ── Auto-refresh ──
time.sleep(POLL_INTERVAL)
st.rerun()
