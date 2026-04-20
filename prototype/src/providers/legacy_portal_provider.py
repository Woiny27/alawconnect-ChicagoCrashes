import asyncio
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Iterable, List, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import BaseProvider
from src.utils.limiter import RateLimiter

if TYPE_CHECKING:
    import aiohttp


class LegacyPortalProvider(BaseProvider):
    """Automates form-based lookup flows used by legacy crash portals."""

    @classmethod
    def from_profile(
        cls,
        profile_key: str,
        *,
        config_path: Optional[Path] = None,
    ) -> "LegacyPortalProvider":
        """
        Construct provider from a machine-readable jurisdiction profile.

        The expected structure is `jurisdictions.<key>.providers.legacy_portal`.
        """
        import yaml

        path = config_path or (Path(__file__).resolve().parents[2] / "jurisdictions.yaml")
        if not path.exists():
            raise FileNotFoundError(f"Jurisdiction config file not found: {path}")

        with path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}

        jurisdictions = data.get("jurisdictions", {})
        if profile_key not in jurisdictions:
            raise KeyError(f"Unknown profile key: {profile_key}")

        profile = jurisdictions[profile_key]
        provider_config = profile.get("providers", {}).get("legacy_portal")
        if not isinstance(provider_config, dict):
            raise KeyError(f"Profile '{profile_key}' has no legacy_portal provider config")

        merged = dict(provider_config)
        merged.setdefault("agency", profile.get("agency", profile_key))

        seeds = profile.get("manual_test_seeds", [])
        if seeds and "accident_ids" not in merged:
            merged["accident_ids"] = [
                str(seed.get("report_id", "")).strip()
                for seed in seeds
                if isinstance(seed, dict) and str(seed.get("report_id", "")).strip()
            ]

        return cls(merged)

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

        post_url, payload, report_field_name = self._extract_form_metadata(html, self.search_url)

        token = self._extract_token(html)
        if token is not None and self.csrf_field_name not in payload:
            payload[self.csrf_field_name] = token

        payload.update(self.config.get("extra_payload", {}))
        payload[report_field_name] = accident_id

        async with session.post(post_url, data=payload) as post_response:
            if post_response.status != 200:
                return None

            return self.normalize(await post_response.text())

    def _extract_form_metadata(self, html: str, current_url: str) -> tuple[str, Dict[str, Any], str]:
        """Extract form action/default fields and detect the best report-id input."""
        soup = BeautifulSoup(html, "html.parser")
        form = soup.find("form")
        if form is None:
            fallback_url = urljoin(f"{self.search_url.rstrip('/')}/", self.search_path.lstrip("/"))
            return fallback_url, {}, self.report_field_name

        action = form.get("action") or self.search_path
        action_url = urljoin(current_url, action)

        payload: Dict[str, Any] = {}
        text_candidates: List[str] = []

        for field in form.find_all(["input", "select", "textarea"]):
            name = field.get("name")
            if not name:
                continue

            if field.name == "input":
                input_type = str(field.get("type", "text")).lower()
                if input_type in {"submit", "button", "reset", "file", "image"}:
                    continue
                if input_type in {"checkbox", "radio"} and not field.has_attr("checked"):
                    continue

                payload[name] = field.get("value", "")
                if input_type in {"text", "search", "number", "tel", "email"}:
                    text_candidates.append(name)
                continue

            if field.name == "select":
                selected = field.find("option", selected=True)
                if selected is not None:
                    payload[name] = selected.get("value", "")
                else:
                    first = field.find("option")
                    payload[name] = first.get("value", "") if first is not None else ""
                continue

            payload[name] = field.get_text(strip=True) if field.name == "textarea" else ""

        report_field_name = self.report_field_name
        if report_field_name not in payload:
            likely_names = [
                "IncidentNumber",
                "report_id",
                "reportId",
                "ReportId",
                "caseNumber",
                "CaseNumber",
                "cadnumber",
            ]
            for candidate in likely_names:
                if candidate in payload:
                    report_field_name = candidate
                    break
            else:
                if text_candidates:
                    report_field_name = text_candidates[0]

        return action_url, payload, report_field_name

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
