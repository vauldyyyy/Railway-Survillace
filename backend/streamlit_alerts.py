"""
RailGuard AI — Streamlit Alert Dashboard (Frontend Bridge)
============================================================
Persistent WebSocket listener + real-time notifications + incident log.

Run:
    streamlit run backend/streamlit_alerts.py
"""

import json
import queue
import threading
import time
from datetime import datetime

import requests
import streamlit as st

try:
    import websocket  # pip install websocket-client
except ImportError:
    st.error("Install websocket-client: `pip install websocket-client`")
    st.stop()

# ======================================================================
# Config
# ======================================================================

API_BASE = "http://localhost:8000"
WS_URL = "ws://localhost:8000/ws/alerts"
POLL_INTERVAL = 1.0

# ======================================================================
# Session state init
# ======================================================================

if "alert_queue" not in st.session_state:
    st.session_state.alert_queue = queue.Queue()

if "ws_thread_started" not in st.session_state:
    st.session_state.ws_thread_started = False

if "alert_history" not in st.session_state:
    st.session_state.alert_history = []

if "ws_connected" not in st.session_state:
    st.session_state.ws_connected = False


# ======================================================================
# Background WebSocket listener thread
# ======================================================================

def _ws_listener(q: queue.Queue) -> None:
    """Background thread — auto-reconnects on failure."""
    while True:
        try:
            ws = websocket.WebSocket()
            ws.connect(WS_URL)
            ws.settimeout(1.0)
            st.session_state.ws_connected = True
            print("[STREAMLIT] WebSocket connected.", flush=True)

            while True:
                try:
                    raw = ws.recv()
                    if raw:
                        data = json.loads(raw)
                        if data.get("event") == "security_alert":
                            q.put(data)
                except websocket.WebSocketTimeoutException:
                    try:
                        ws.send("ping")
                    except Exception:
                        break

        except Exception as exc:
            st.session_state.ws_connected = False
            print(f"[STREAMLIT] WS error: {exc}. Reconnecting in 3s…", flush=True)
            time.sleep(3)


# ======================================================================
# UI
# ======================================================================

st.set_page_config(page_title="RailGuard AI — Security Dashboard", page_icon="🛡️", layout="wide")

# -- Header --
st.markdown("""
<div style="background: linear-gradient(135deg, #0B0F19 0%, #1a1f2e 100%);
            padding: 1.5rem 2rem; border-radius: 12px; margin-bottom: 1.5rem;
            border: 1px solid rgba(6,182,212,0.2);">
    <h1 style="color: #06b6d4; margin: 0; font-size: 1.8rem;">🛡️ RailGuard AI — Live Security Dashboard</h1>
    <p style="color: #94a3b8; margin: 0.25rem 0 0 0; font-size: 0.9rem;">
        Real-time alerts from Camera Gateway · Data Shield · Logic Gate
    </p>
</div>
""", unsafe_allow_html=True)

# -- Start background listener --
if not st.session_state.ws_thread_started:
    t = threading.Thread(
        target=_ws_listener,
        args=(st.session_state.alert_queue,),
        daemon=True,
    )
    t.start()
    st.session_state.ws_thread_started = True

# -- Status bar --
col1, col2, col3 = st.columns(3)
with col1:
    ws_icon = "🟢" if st.session_state.ws_connected else "🔴"
    st.metric("WebSocket", f"{ws_icon} {'Connected' if st.session_state.ws_connected else 'Disconnected'}")
with col2:
    st.metric("Alerts Received", len(st.session_state.alert_history))
with col3:
    try:
        health = requests.get(f"{API_BASE}/health", timeout=2).json()
        st.metric("Server", f"🟢 {health.get('websocket_clients', '?')} WS clients")
    except Exception:
        st.metric("Server", "🔴 Offline")

st.divider()

# -- Drain alert queue --
new_alerts = 0
while not st.session_state.alert_queue.empty():
    try:
        alert = st.session_state.alert_queue.get_nowait()
        new_alerts += 1

        msg = alert.get("msg", "UNKNOWN")
        detail = alert.get("detail", "")
        camera = alert.get("camera_id", "—")
        ts = datetime.fromtimestamp(alert.get("timestamp", time.time())).strftime("%H:%M:%S")

        # Visual notification
        if msg == "CAMERA_TAMPERED":
            st.error(f"🚨 **CAMERA TAMPERED** — `{camera}` | Detail: `{detail}`")
            st.toast(f"🔴 Camera {camera} tampered!", icon="🚨")
        elif msg == "INJECTION_ATTEMPT":
            st.error(f"🛑 **PROMPT INJECTION BLOCKED** — Source: `{camera}`")
            st.toast(f"🛑 Injection attempt from {camera}!", icon="🛑")
        else:
            st.warning(f"⚠️ **{msg}** — `{camera}`")
            st.toast(f"⚠️ {msg}", icon="⚠️")

        st.session_state.alert_history.append({
            "Time": ts,
            "Type": msg,
            "Detail": str(detail)[:80] if isinstance(detail, (str, dict)) else str(detail)[:80],
            "Camera": camera,
        })

    except queue.Empty:
        break

# -- Incident Logs table (auto-refreshed) --
st.subheader("📋 Live Incident Log")

if st.session_state.alert_history:
    # Show most recent first
    display_data = list(reversed(st.session_state.alert_history[-50:]))
    st.dataframe(display_data, use_container_width=True, height=300)
else:
    st.info("No incidents yet. Monitoring for events…")

# -- Fetch DB incidents --
with st.expander("📂 Database Incident History (from API)", expanded=False):
    try:
        incidents = requests.get(f"{API_BASE}/incidents", timeout=2).json()
        if incidents:
            st.dataframe(incidents, use_container_width=True)
        else:
            st.info("No incidents in database.")
    except Exception as exc:
        st.warning(f"Could not fetch incidents: {exc}")

# -- Auto-refresh --
time.sleep(POLL_INTERVAL)
st.rerun()
