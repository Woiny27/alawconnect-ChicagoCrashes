import httpx
from core.retry import retry

class AsyncClient:

    @retry(times=3)
    async def get(self, url: str):
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(url)
            r.raise_for_status()
            return r.json()