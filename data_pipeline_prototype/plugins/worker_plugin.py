import requests

from providers.worker import WorkerProvider


class _SyncUSGSProvider:
    """Synchronous USGS earthquake provider using requests."""

    URL = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson"

    def fetch(self):
        response = requests.get(self.URL, timeout=10)
        response.raise_for_status()
        return response.json()


def register(registry):
    registry.register_provider("usgs_worker", WorkerProvider(_SyncUSGSProvider()))
