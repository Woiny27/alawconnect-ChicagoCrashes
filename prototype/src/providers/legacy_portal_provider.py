import asyncio
from typing import TYPE_CHECKING, Any, Dict, Iterable, List, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import BaseProvider
from src.utils.limiter import RateLimiter

if TYPE_CHECKING:
    import aiohttp


class LegacyPortalProvider(BaseProvider):
    """Automates form-based lookup flows used by legacy crash portals."""

    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = dict(config)
        self.search_url = str(self.config.get("search_url", "")).strip()
        if not self.search_url:
            raise ValueError("config.search_url is required")

        self.search_path = str(self.config.get("search_path", "search"))
        self.report_field_name = str(self.config.get("report_field_name", "report_id"))
        self.csrf_field_name = str(self.config.get("csrf_field_name", "csrf_token"))
        self.agency = str(self.config.get("agency", "Legacy Portal"))
        self.default_ids: List[str] = [
            str(value).strip()
            for value in self.config.get("accident_ids", [])
            if str(value).strip()
        ]

        # High-volume safe extraction: smooth request spikes.
        self.limiter = RateLimiter(tokens_per_second=float(self.config.get("tokens_per_second", 2)))

    def fetch(self, limit: Optional[int] = None) -> List[Dict[str, str]]:
        """BaseProvider-compatible sync wrapper over async batch lookup."""
        ids = self.default_ids[:limit] if limit else self.default_ids
        if not ids:
            return []

        rows = asyncio.run(self.check_ids(ids))
        return [row for row in rows if isinstance(row, dict)]

    async def check_ids(self, accident_ids: Iterable[str]) -> List[Dict[str, Any]]:
        """Run sequential ID checks with shared session/cookies."""
        import aiohttp

        timeout = aiohttp.ClientTimeout(total=float(self.config.get("timeout_seconds", 30)))
        results: List[Dict[str, Any]] = []

        async with aiohttp.ClientSession(timeout=timeout) as session:
            for accident_id in accident_ids:
                row = await self.check_id(str(accident_id), session=session)
                if row:
                    results.append(row)

        return results

    async def check_id(
        self,
        accident_id: str,
        *,
        session: Optional[Any] = None,
    ) -> Optional[Dict[str, Any]]:
        """Automate a form-based ID lookup for one report ID."""
        await self.limiter.wait()

        if session is None:
            import aiohttp

            timeout = aiohttp.ClientTimeout(total=float(self.config.get("timeout_seconds", 30)))
            async with aiohttp.ClientSession(timeout=timeout) as owned_session:
                return await self._check_id_with_session(accident_id, owned_session)

        return await self._check_id_with_session(accident_id, session)

    async def _check_id_with_session(
        self,
        accident_id: str,
        session: Any,
    ) -> Optional[Dict[str, Any]]:
        async with session.get(self.search_url) as response:
            if response.status >= 400:
                return None
            html = await response.text()

        token = self._extract_token(html)
        payload: Dict[str, Any] = {self.report_field_name: accident_id}
        if token is not None:
            payload[self.csrf_field_name] = token

        payload.update(self.config.get("extra_payload", {}))

        post_url = urljoin(f"{self.search_url.rstrip('/')}/", self.search_path.lstrip("/"))
        async with session.post(post_url, data=payload) as post_response:
            if post_response.status != 200:
                return None

            return self.normalize(await post_response.text())

    def _extract_token(self, html: str) -> Optional[str]:
        soup = BeautifulSoup(html, "html.parser")
        field = soup.find("input", {"name": self.csrf_field_name})
        if field is None:
            return None
        value = field.get("value")
        return str(value) if value is not None else None

    def normalize(self, raw_html: str) -> Dict[str, Any]:
        """Map legacy HTML lookup results into crash_join_id schema."""
        soup = BeautifulSoup(raw_html, "html.parser")

        report_node = soup.find(id="report_num")
        report_id = report_node.get_text(strip=True) if report_node is not None else ""

        involved_party = soup.find(id="involved_party")

        return {
            "crash_join_id": report_id,
            "agency": self.agency,
            "contact_found": involved_party is not None,
        }
