from __future__ import annotations

import random
from datetime import datetime

from app.core.database import SessionLocal
from app import models


def seed() -> None:
    db = SessionLocal()
    try:
        existing_cameras = db.query(models.Camera).first()
        if existing_cameras is None:
            cameras = [
                models.Camera(id="CAM-01", location_zone="Platform 1", is_active=True),
                models.Camera(id="CAM-02", location_zone="Platform 2 North", is_active=True),
                models.Camera(id="CAM-03", location_zone="Main Concourse", is_active=True),
            ]
            db.add_all(cameras)
            db.flush()

        incidents = [
            models.Incident(threat_type="Unattended Baggage", camera_id="CAM-01"),
            models.Incident(threat_type="Track Intrusion", camera_id="CAM-02"),
            models.Incident(threat_type="Crowd Surge", camera_id="CAM-03"),
        ]
        db.add_all(incidents)

        now = datetime.utcnow()
        crowd_metrics = [
            models.CrowdMetric(
                timestamp=now,
                platform_id="Platform 1",
                density_count=random.randint(50, 500),
            ),
            models.CrowdMetric(
                timestamp=now,
                platform_id="Platform 2 North",
                density_count=random.randint(50, 500),
            ),
            models.CrowdMetric(
                timestamp=now,
                platform_id="Main Concourse",
                density_count=random.randint(50, 500),
            ),
        ]
        db.add_all(crowd_metrics)

        db.commit()
        print("Seeded cameras, incidents, and crowd metrics.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
