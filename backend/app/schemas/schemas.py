from datetime import datetime

from pydantic import BaseModel


class CameraBase(BaseModel):
    id: str
    location_zone: str
    is_active: bool


class CameraCreate(CameraBase):
    pass


class CameraResponse(CameraBase):
    model_config = {"from_attributes": True}


class IncidentBase(BaseModel):
    threat_type: str
    camera_id: str
    is_resolved: bool


class IncidentCreate(BaseModel):
    threat_type: str
    camera_id: str


class IncidentResponse(IncidentBase):
    id: int
    timestamp: datetime
    model_config = {"from_attributes": True}


class TrackedPersonBase(BaseModel):
    timestamp: datetime
    obfuscated_embedding: str
    camera_id: str


class TrackedPersonCreate(BaseModel):
    timestamp: datetime
    obfuscated_embedding: str
    camera_id: str


class TrackedPersonResponse(TrackedPersonBase):
    id: int
    model_config = {"from_attributes": True}


class CrowdMetricBase(BaseModel):
    timestamp: datetime
    platform_id: str
    density_count: int


class CrowdMetricCreate(CrowdMetricBase):
    pass


class CrowdMetricResponse(CrowdMetricBase):
    id: int
    model_config = {"from_attributes": True}
