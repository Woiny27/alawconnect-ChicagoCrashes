from dataclasses import dataclass


@dataclass
class EarthquakeSchema:
    id: str
    magnitude: float
    timestamp: int
    location: list
