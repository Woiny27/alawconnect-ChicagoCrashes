from core.async_client import AsyncClient

class USGSProvider:
    URL = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson"

    def __init__(self):
        self.client = AsyncClient()

    async def fetch(self):
        return await self.client.get(self.URL)


def register(registry):
    registry.register_provider("usgs", USGSProvider())
