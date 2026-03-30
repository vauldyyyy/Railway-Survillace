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

        # Sort: draw BASE entities first, then escalated on top
        base_entities = [e for e in entities if e.current_state == EntityState.BASE]
        escalated = [e for e in entities if e.current_state != EntityState.BASE]

        for entity in base_entities:
            self._draw_entity(annotated, entity)

        for entity in escalated:
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

        # ── CROWD ZONE: Semi-transparent overlay ──
        if entity.base_class == EntityClass.CROWD and entity.current_state == EntityState.OVERCROWDING:
            self._draw_crowd_zone(frame, entity)
            return

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
        if entity.current_state != EntityState.BASE:
            # Escalated: show state label + entity ID + confidence
            label_text = f"{label} [{entity.id}] {entity.confidence:.0%}"
        else:
            # Base: show class + entity ID + confidence
            label_text = f"{label} [{entity.id}] {entity.confidence:.0%}"

        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.40
        (tw, th), baseline = cv2.getTextSize(label_text, font, font_scale, 1)

        # Label position: above box, or below if near top edge
        label_y = y1 - 6 if y1 > th + 10 else y2 + th + 6
        label_x = x1

        # Background rectangle
        cv2.rectangle(
            frame,
            (label_x, label_y - th - 4),
            (label_x + tw + 4, label_y + 2),
            color, -1
        )
        # Text
        cv2.putText(
            frame, label_text,
            (label_x + 2, label_y - 2),
            font, font_scale,
            (255, 255, 255), 1, cv2.LINE_AA
        )

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
        """Draw crowd zone as semi-transparent red overlay."""
        x1, y1, x2, y2 = [int(v) for v in entity.box]
        overlay = frame.copy()

        # Semi-transparent red fill
        cv2.rectangle(overlay, (x1, y1), (x2, y2), (0, 0, 200), -1)
        cv2.addWeighted(overlay, 0.2, frame, 0.8, 0, frame)

        # Solid red border
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 3)

        # Label
        label = f"OVERCROWDING ZONE [{entity.id}]"
        font = cv2.FONT_HERSHEY_SIMPLEX
        (tw, th), _ = cv2.getTextSize(label, font, 0.55, 2)
        cx = (x1 + x2) // 2 - tw // 2
        cy = y1 - 10 if y1 > th + 15 else y2 + th + 10

        cv2.rectangle(frame, (cx - 4, cy - th - 4), (cx + tw + 4, cy + 4), (0, 0, 200), -1)
        cv2.putText(frame, label, (cx, cy), font, 0.55, (255, 255, 255), 2, cv2.LINE_AA)

    def _draw_hud(self, frame: np.ndarray, stats: dict, w: int, h: int):
        """Draw bottom HUD bar with pipeline statistics."""
        hud_h = 38
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, h - hud_h), (w, h), (10, 10, 15), -1)
        cv2.addWeighted(overlay, 0.85, frame, 0.15, 0, frame)

        font = cv2.FONT_HERSHEY_SIMPLEX

        # Left: Pipeline status
        src_tag = stats.get("inference_source", "LOCAL").upper()
        if src_tag == "REMOTE":
            src_tag = "GPU BRIDGE"
        else:
            src_tag = "LOCAL CPU"

        status_text = f"ENTITY-STATE ENGINE V4.0 | {src_tag}"
        cv2.putText(frame, status_text, (15, h - 12), font, 0.40,
                    (255, 191, 0), 1, cv2.LINE_AA)

        # Right: Stats
        fps = stats.get("fps", 0)
        latency = stats.get("latency", 0)
        persons = stats.get("person_count", 0)
        threats = stats.get("threat_count", 0)
        entities_total = stats.get("entity_count", 0)

        right_text = (
            f"LAT:{latency:.0f}ms | AI:{fps:.1f}FPS | "
            f"ENT:{entities_total} | PRSN:{persons} | THREATS:{threats}"
        )
        (rw, _), _ = cv2.getTextSize(right_text, font, 0.40, 1)
        cv2.putText(frame, right_text, (w - rw - 15, h - 12), font, 0.40,
                    (220, 220, 220), 1, cv2.LINE_AA)

        # Alert pulse indicator (top-left corner for active alerts)
        if threats > 0:
            pulse = abs((self._frame_counter % 30) - 15) / 15.0
            pulse_color = (0, int(50 + 205 * pulse), 255)
            cv2.circle(frame, (w - 20, h - hud_h + 10), 5, pulse_color, -1)
