import requests
from providers.base import Provider

class USGSEarthquakeProvider(Provider):
    """
    Fetches earthquake data from USGS public API.
    """

    URL = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson"

    def fetch(self):
        response = requests.get(self.URL, timeout=10)
        response.raise_for_status()
        return response.json()