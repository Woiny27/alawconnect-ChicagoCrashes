from dataclasses import dataclass
from typing import List, Optional
from pydantic import BaseModel


@dataclass
class EarthquakeSchema:
    id: str
    magnitude: float
    timestamp: int
    location: list


class USGSEarthquakeAnalysisRequest(BaseModel):
    """Request model for USGS earthquake risk analysis."""
    record_id: str
    magnitude: float
    latitude: float
    longitude: float
    depth: Optional[float] = None
    timestamp: int


class RiskScoreResponse(BaseModel):
    """Risk score for an earthquake."""
    id: str
    magnitude: float
    risk_score: int
    risk_level: str


class RiskAnalysisResponse(BaseModel):
    """Full risk analysis response."""
    record_id: str
    risk_score: RiskScoreResponse
    explanation: str
