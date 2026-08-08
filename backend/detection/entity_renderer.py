"""
entity_renderer.py — Entity-State-Aware Visual Rendering Engine
================================================================
Reads entity state from the EntityRegistry and draws:
  - Color-coded bounding boxes per entity state
  - Entity ID labels (P_145, B_032, S_001)
  - State transition labels (PERSON ON TRACK, UNATTENDED BAGGAGE)
  - Flashing effect for CRITICAL states
  - Crowd zone overlay (semi-transparent red boundary)
  - Professional HUD bar with pipeline statistics

Design Rule: This module ONLY draws. It NEVER modifies entity state.
"""

import cv2
import numpy as np
import time
from typing import List, Tuple

from detection.entity_state import (
    Entity, EntityClass, EntityState,
    BASE_COLORS, STATE_COLORS, STATE_LABELS,
)


class EntityRenderer:
    """Stateless renderer — reads Entity objects, draws on frame."""

    def __init__(self):
        self._frame_counter = 0

    def render(self, frame: np.ndarray, entities: List[Entity],
               pipeline_stats: dict = None) -> np.ndarray:
        """
        Draw all entities on the frame.
        Returns the annotated frame.
        """
        self._frame_counter += 1
        annotated = frame.copy()
        h, w = annotated.shape[:2]

        # Layer 1: Environmental Awareness (CROWD zones) - background
        for entity in entities:
            if entity.base_class == EntityClass.CROWD:
                self._draw_entity(annotated, entity)

        # Layer 2: Object-level Intel (PERSON, BAGGAGE, etc.) - foreground
        # This ensures 'Blue Persons' are always crisp and on top of any red areas.
        for entity in entities:
            if entity.base_class != EntityClass.CROWD:
                self._draw_entity(annotated, entity)

        # Draw Depositor Bag Linkages
        for entity in entities:
            if entity.base_class == EntityClass.BAGGAGE and hasattr(entity, 'owner_id') and entity.owner_id:
                owner = next((e for e in entities if e.id == entity.owner_id), None)
                if owner:
                    # Draw dashed/dotted line effect by overlapping
                    cv2.line(annotated, entity.centroid, owner.centroid, (0, 210, 80), 2)
                    mid_x = (entity.centroid[0] + owner.centroid[0]) // 2
                    mid_y = (entity.centroid[1] + owner.centroid[1]) // 2
                    
                    # Highlight if separated
                    dist_color = (0, 0, 255) if entity.current_state != EntityState.BASE else (0, 210, 80)
                    dist_text = f"Depositor {owner.id}"
                    cv2.putText(annotated, dist_text, (mid_x, mid_y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, dist_color, 1, cv2.LINE_AA)

        # Draw HUD bar
        if pipeline_stats:
            self._draw_hud(annotated, pipeline_stats, w, h)

        return annotated

    def _draw_entity(self, frame: np.ndarray, entity: Entity):
        """Draw a single entity with its current visual state."""
        # ── TEMPORAL SMOOTHING ──
        if hasattr(entity, 'box_history') and len(entity.box_history) >= 2:
            # Simple weighted average for 60FPS-like gliding motion
            boxes = np.array(entity.box_history)
            weights = np.linspace(0.4, 1.0, len(boxes))
            weights /= weights.sum()
            smooth_box = np.sum(boxes * weights[:, None], axis=0).astype(int)
            x1, y1, x2, y2 = smooth_box
        else:
            x1, y1, x2, y2 = [int(v) for v in entity.box]

        color = entity.color
        thickness = entity.thickness
        label = entity.label

        # Flashing effect for CRITICAL states (fire, bomb protocol)
        if entity.current_state in (
            EntityState.FIRE_DETECTED,
            EntityState.BAGGAGE_BOMB,
            EntityState.PERSON_FALLEN,
        ):
            if self._frame_counter % 6 < 3:
                color = (255, 255, 255)  # Flash white every 3 frames

        # ── CROWD ZONE: Semi-transparent red overlay ──
        if entity.base_class == EntityClass.CROWD and entity.current_state in (EntityState.OVERCROWDING, EntityState.STAMPEDE_RISK):
            self._draw_crowd_zone(frame, entity)
            return

        # ── SEGMENTATION MASK (Direct precision fix) ──
        if entity.mask is not None:
            mask_overlay = frame.copy()
            # Draw translucent filled polygon
            cv2.fillPoly(mask_overlay, [entity.mask], color)
            cv2.addWeighted(mask_overlay, 0.35, frame, 0.65, 0, frame)
            # Draw glowing boundary
            cv2.polylines(frame, [entity.mask], True, color, thickness + 1, cv2.LINE_AA)

        # ── BOUNDING BOX ──
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)

        # ── CORNER BRACKETS (professional look) ──
        bracket_len = min(20, (x2 - x1) // 4, (y2 - y1) // 4)
        if bracket_len > 5:
            # Top-left
            cv2.line(frame, (x1, y1), (x1 + bracket_len, y1), color, thickness + 1)
            cv2.line(frame, (x1, y1), (x1, y1 + bracket_len), color, thickness + 1)
            # Top-right
            cv2.line(frame, (x2, y1), (x2 - bracket_len, y1), color, thickness + 1)
            cv2.line(frame, (x2, y1), (x2, y1 + bracket_len), color, thickness + 1)
            # Bottom-left
            cv2.line(frame, (x1, y2), (x1 + bracket_len, y2), color, thickness + 1)
            cv2.line(frame, (x1, y2), (x1, y2 - bracket_len), color, thickness + 1)
            # Bottom-right
            cv2.line(frame, (x2, y2), (x2 - bracket_len, y2), color, thickness + 1)
            cv2.line(frame, (x2, y2), (x2, y2 - bracket_len), color, thickness + 1)

        # ── LABEL BACKGROUND ──
        is_hazard = entity.current_state in (EntityState.FIRE_DETECTED, EntityState.SMOKE_CRITICAL)
        
        if entity.current_state != EntityState.BASE:
            # Escalated: show state label + entity ID + confidence
            label_text = f"{label} [{entity.id}] {entity.confidence:.0%}"
        else:
            # Base: show class + entity ID + confidence
            label_text = f"{label} [{entity.id}] {entity.confidence:.0%}"

        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.50 if is_hazard else 0.40 # Thicker font for hazards
        (tw, th), baseline = cv2.getTextSize(label_text, font, font_scale, 2 if is_hazard else 1)

        # Label position: above box, or below if near top edge
        label_y = y1 - 6 if y1 > th + 10 else y2 + th + 6
        label_x = x1

        # Background rectangle (High contrast for hazards)
        cv2.rectangle(
            frame,
            (label_x, label_y - th - 6),
            (label_x + tw + 6, label_y + 4),
            color, -1
        )
        # Text
        text_color = (255, 255, 255)
        cv2.putText(
            frame, label_text,
            (label_x + 3, label_y - 3),
            font, font_scale,
            text_color, 2 if is_hazard else 1, cv2.LINE_AA
        )

        # ── PRECISION HIT (Target symbol on centroid for Jurors) ──
        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
        cv2.drawMarker(frame, (cx, cy), color, cv2.MARKER_CROSS, 8, 1)

        # ── THREAT LEVEL BADGE (for escalated states) ──
        if entity.threat_level in ("CRITICAL", "HIGH"):
            badge_text = entity.threat_level
            badge_color = (0, 0, 255) if entity.threat_level == "CRITICAL" else (0, 128, 255)
            (bw, bh), _ = cv2.getTextSize(badge_text, font, 0.30, 1)
            badge_x = x2 - bw - 6
            badge_y = y1 + bh + 8
            cv2.rectangle(frame, (badge_x - 2, badge_y - bh - 2), (badge_x + bw + 2, badge_y + 2), badge_color, -1)
            cv2.putText(frame, badge_text, (badge_x, badge_y), font, 0.30, (255, 255, 255), 1, cv2.LINE_AA)

    def _draw_crowd_zone(self, frame: np.ndarray, entity: Entity):
        """Draw crowd zone as semi-transparent red overlay with dynamic intensity."""
        x1, y1, x2, y2 = [int(v) for v in entity.box]
        overlay = frame.copy()

        # Dynamic intensity: STAMPEDE_RISK is much darker/more intense
        if entity.current_state == EntityState.STAMPEDE_RISK:
            opacity = 0.45
            border_thick = 4
            label = "STAMPEDE RISK - TAKE ACTION"
            # Flash border for stampede risk
            border_color = (0, 0, 255) if self._frame_counter % 10 < 5 else (255, 255, 255)
        else:
            opacity = 0.20
            border_thick = 2
            border_color = (0, 0, 255)
            label = "OVERCROWDING DETECTED"

        # Semi-transparent red fill
        cv2.rectangle(overlay, (x1, y1), (x2, y2), (0, 0, 180), -1)
        cv2.addWeighted(overlay, opacity, frame, 1.0 - opacity, 0, frame)

        # Border
        cv2.rectangle(frame, (x1, y1), (x2, y2), border_color, border_thick)

        # Label
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.6 if entity.current_state == EntityState.STAMPEDE_RISK else 0.5
        (tw, th), _ = cv2.getTextSize(label, font, font_scale, 2)
        
        # Center label top
        lx = (x1 + x2) // 2 - tw // 2
        ly = y1 - 12 if y1 > th + 15 else y2 + th + 12
        
        cv2.rectangle(frame, (lx - 5, ly - th - 5), (lx + tw + 5, ly + 5), (0, 0, 200), -1)
        cv2.putText(frame, label, (lx, ly), font, font_scale, (255, 255, 255), 2, cv2.LINE_AA)

    def _draw_hud(self, frame: np.ndarray, stats: dict, w: int, h: int):
        """Draw bottom HUD bar with pipeline statistics."""
        hud_h = 35
        # Draw background bar
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, h - hud_h), (w, h), (15, 10, 5), -1)
        cv2.addWeighted(overlay, 0.88, frame, 0.12, 0, frame)

        font = cv2.FONT_HERSHEY_SIMPLEX
        
        # Left: Camera ID + Pipeline status
        cam_id = stats.get("camera_id", "CAM_X")
        src_tag = stats.get("inference_source", "LOCAL").upper()
        if "REMOTE" in src_tag:
            src_tag = "GPU BRIDGE"
            src_color = (255, 191, 0) # Cyan-blue
        else:
            src_tag = "LOCAL CPU"
            src_color = (200, 200, 200) # Gray
            
        status_text = f"{cam_id} | {src_tag}"
        cv2.putText(frame, status_text, (15, h - 12), font, 0.42, src_color, 1, cv2.LINE_AA)

        # Right: All Stats + Confidence
        fps = stats.get("fps", 0)
        latency = stats.get("latency", 0)
        conf = stats.get("confidence", 0.0)
        threats = stats.get("threat_count", 0)
        
        # Confidence color coding
        conf_color = (0, 255, 0) if conf > 0.8 else (0, 255, 255) if conf > 0.5 else (0, 0, 255)
        
        right_text = (
            f"LAT:{latency:.0f}ms | AI:{fps:.1f}FPS | "
            f"CONFIDENCE: {conf:.0%} "
        )
        (rw, _), _ = cv2.getTextSize(right_text, font, 0.40, 1)
        
        # Draw a small confidence bar
        bar_w = 40
        bar_x = w - rw - bar_w - 25
        cv2.rectangle(frame, (bar_x, h - 22), (bar_x + bar_w, h - 14), (40, 40, 40), -1)
        cv2.rectangle(frame, (bar_x, h - 22), (bar_x + int(bar_w * conf), h - 14), conf_color, -1)

        cv2.putText(frame, right_text, (w - rw - 15, h - 12), font, 0.40, (220, 220, 220), 1, cv2.LINE_AA)

        # Alert pulse indicator (top-left corner for active alerts)
        if threats > 0:
            pulse = abs((self._frame_counter % 30) - 15) / 15.0
            pulse_color = (0, int(50 + 205 * pulse), 255)
            cv2.circle(frame, (w - 20, h - hud_h + 10), 5, pulse_color, -1)
