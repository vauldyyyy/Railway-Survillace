import time
import datetime
from typing import List, Dict, Optional, Any

class ThreatEngine:
    def __init__(self):
        # camera_id -> track_id -> metadata
        self.registry = {}
        # Cooldown: {camera_id: {alert_type: last_ts}}
        self.cooldowns = {}
        self.COOLDOWN_SECONDS = 30

    def _get_operational_mapping(self, threat_type: str, level: str, cam_id: str):
        """Strict mapping as per Railway Safety Directive (Sr. Architect)."""
        mappings = {
            "Person Fallen on Track": {
                "command": f"STOP_ALL_TRAINS_ON_TRACK_{cam_id[-1] if cam_id[-1].isdigit() else '01'}",
                "notify": ["Station Master", "Control Room", "RPF"],
                "escalation": ["Medical Emergency Unit"]
            },
            "Person on Track": {
                "command": "ISSUE_IMMEDIATE_PA_WARNING",
                "notify": ["Platform Security"],
                "escalation": ["RPF"]
            },
            "Baggage Unattended": {
                "command": "ISOLATE_AREA_5M_RADIUS",
                "notify": ["Station Security", "RPF"],
                "escalation": ["Bomb Detection Squad"] if level == "CRITICAL" else []
            },
            "Smoke": {
                "command": "VERIFY_WITH_SECONDARY_CAMERA" if level == "MEDIUM" else "ACTIVATE_FIRE_RESPONSE_PROTOCOL",
                "notify": ["Fire Department", "Station Master"],
                "escalation": []
            },
            "Fire": {
                "command": "ACTIVATE_FIRE_SUPPRESSION",
                "notify": ["Fire Department", "Emergency Control"],
                "escalation": []
            },
            "Crowd Detected": {
                "command": "RESTRICT_ENTRY_GATE",
                "notify": ["Crowd Control Team"],
                "escalation": []
            }
        }
        return mappings.get(threat_type, {
            "command": "MONITOR_SITUATION",
            "notify": ["Security Monitor"],
            "escalation": []
        })

    def process_observations(self, camera_id: str, observations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        observations: [{
            "id": "uuid",
            "class": "person", 
            "box": [x1, y1, x2, y2], 
            "confidence": 0.9,
            "is_intrusion": bool,
            "is_fallen_pose": bool,
            "is_motionless": bool,
            "is_unattended": bool,
            "duration_s": float (if coming from existing trackers)
        }]
        """
        now = time.time()
        now_iso = datetime.datetime.now().isoformat()
        
        if camera_id not in self.registry:
            self.registry[camera_id] = {}
        if camera_id not in self.cooldowns:
            self.cooldowns[camera_id] = {}

        camera_registry = self.registry[camera_id]
        final_alerts = []

        # 1. Update Registry State
        for obs in observations:
            track_id = obs["id"]
            if track_id not in camera_registry:
                camera_registry[track_id] = {
                    "first_seen": now,
                    "last_seen": now,
                    "class": obs["class"],
                    "persistent_alert_type": None,
                    "metadata": {}
                }
            else:
                camera_registry[track_id]["last_seen"] = now
            
            entry = camera_registry[track_id]
            persist_duration = now - entry["first_seen"]
            
            threat_type = None
            level = "LOW"
            confidence = obs["confidence"]

            # --- CASE LOGIC MATRIX ---

            # 🚨 CASE 1 & 2: Person Track Logic
            if obs["class"] == "person":
                if obs.get("is_intrusion"):
                    if obs.get("is_fallen_pose") and persist_duration >= 3.0 and obs.get("is_motionless"):
                        threat_type = "Person Fallen on Track"
                        level = "CRITICAL"
                    else:
                        threat_type = "Person on Track"
                        level = "HIGH"

            # 🎒 CASE 3: Unattended Baggage (5s / 20s rules)
            elif "bag" in obs["class"] or obs["class"] in ("luggage", "backpack", "suitcase"):
                if obs.get("is_unattended"):
                    unattended_dur = obs.get("duration_s", persist_duration)
                    if unattended_dur >= 20.0:
                        threat_type = "Baggage Unattended"
                        level = "CRITICAL"
                        obs["command_override"] = "INITIATE_BOMB_PROTOCOL"
                    elif unattended_dur >= 5.0:
                        threat_type = "Baggage Unattended"
                        level = "HIGH"

            # 🌫 CASE 4 & 5: Smoke / Fire
            elif obs["class"] == "fire":
                threat_type = "Fire"
                level = "CRITICAL"
            elif obs["class"] == "smoke":
                if persist_duration >= 10.0:
                    threat_type = "Smoke"
                    level = "CRITICAL"
                elif persist_duration >= 5.0:
                    threat_type = "Smoke"
                    level = "MEDIUM"

            # 👥 CASE 6: Crowd Detected (handled as a pseudo-track from pipeline)
            elif obs["class"] == "crowd_detected":
                if persist_duration >= 10.0:
                    threat_type = "Crowd Detected"
                    level = "HIGH"

            # 2. Alert Construction & Cooldown
            if threat_type:
                # Deduplication / Cooldown
                last_alert_ts = self.cooldowns[camera_id].get(threat_type, 0)
                if (now - last_alert_ts) > self.COOLDOWN_SECONDS or level == "CRITICAL":
                    ops = self._get_operational_mapping(threat_type, level, camera_id)
                    
                    alert = {
                        "camera_id": str(camera_id).upper(),
                        "threat_type": threat_type,
                        "threat_level": level,
                        "command": obs.get("command_override") if obs.get("command_override") else ops["command"],
                        "notify": ops["notify"],
                        "escalation": ops["escalation"],
                        "timestamp": now_iso,
                        "confidence": round(float(confidence), 2)
                    }
                    final_alerts.append(alert)
                    self.cooldowns[camera_id][threat_type] = now

        # 3. Cleanup registry (stale for > 5s)
        self.registry[camera_id] = {k: v for k, v in camera_registry.items() if now - v["last_seen"] < 5.0}
        
        return final_alerts
