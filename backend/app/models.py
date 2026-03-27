from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, func

from app.core.database import Base


class Camera(Base):
    __tablename__ = "cameras"

    id = Column(String, primary_key=True, index=True)
    location_zone = Column(String, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)


class Incident(Base):
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    threat_type = Column(String, nullable=False)
    camera_id = Column(String, ForeignKey("cameras.id"), nullable=False)
    is_resolved = Column(Boolean, default=False, nullable=False)


class TrackedPerson(Base):
    __tablename__ = "tracked_people"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    obfuscated_embedding = Column(String, nullable=False)
    camera_id = Column(String, ForeignKey("cameras.id"), nullable=False)


class CrowdMetric(Base):
    __tablename__ = "crowd_metrics"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    platform_id = Column(String, nullable=False)
    density_count = Column(Integer, nullable=False)
