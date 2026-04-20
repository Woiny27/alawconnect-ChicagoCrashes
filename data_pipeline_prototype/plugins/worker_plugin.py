import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from providers.usgs_earthquakes import USGSEarthquakeProvider
from providers.worker import WorkerProvider


def register(registry):
    registry.register_provider("usgs_worker", WorkerProvider(USGSEarthquakeProvider()))
