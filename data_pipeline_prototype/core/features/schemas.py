from pydantic import BaseModel
from typing import Optional


class RawCrashRecord(BaseModel):
    """Schema for a raw record coming in from Chicago Open Data."""
    crash_record_id: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    timestamp: Optional[str] = None
    crash_type: Optional[str] = None
    injuries_total: Optional[float] = None
    damage: Optional[str] = None
    weather_condition: Optional[str] = None
    lighting_condition: Optional[str] = None
    road_defect: Optional[str] = None


class EngineeredFeatures(BaseModel):
    """Schema for the output of the feature pipeline."""
    crash_record_id: Optional[str] = None

    # Cleaned location
    lat: Optional[float] = None
    lon: Optional[float] = None

    # Time features
    hour: Optional[int] = None
    is_night: int = 0

    # Missing data signals
    missing_location: int = 0


class Entity(BaseModel):
    """Represents an external entity (org, agency, data source) with a risk score."""
    entity_id: str
    type: str
    name: str
    contact_channel: Optional[str] = None
    risk_score: float = 0.0
