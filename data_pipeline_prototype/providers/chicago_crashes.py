import httpx


class ChicagoCrashProvider:
    """Provider for fetching Chicago crash data from City of Chicago Open Data."""
    
    def __init__(self):
        self.url = "https://data.cityofchicago.org/resource/85ca-t3if.json"
    
    async def fetch(self):
        """Fetch crash data from the Chicago Open Data API."""
        async with httpx.AsyncClient() as client:
            res = await client.get(self.url)
            return res.json()
    
    async def fetch_with_limit(self, limit: int = 100):
        """Fetch crash data with a limit on records."""
        async with httpx.AsyncClient() as client:
            res = await client.get(self.url, params={"$limit": limit})
            return res.json()
