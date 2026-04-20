from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from .base import BaseProvider


class LAPDProvider(BaseProvider):
    """Public LAPD/BuyCrash lookup provider using HTML form automation."""

    INVALID_MARKERS = (
        "not found",
        "no report",
        "no results",
        "invalid",
        "unable to locate",
    )

    def __init__(
        self,
        report_ids: Iterable[str],
        *,
        base_url: str = "https://buycrash.lexisnexisrisk.com",
        lookup_path: str = "/",
        report_field_name: str = "reportNumber",
        timeout_seconds: int = 30,
        extra_payload: Optional[Dict[str, str]] = None,
        session: Optional[requests.Session] = None,
    ) -> None:
        self.report_ids = [str(value).strip() for value in report_ids if str(value).strip()]
        self.base_url = base_url.rstrip("/")
        self.lookup_path = lookup_path
        self.report_field_name = report_field_name
        self.timeout_seconds = timeout_seconds
        self.extra_payload = dict(extra_payload or {})
        self.session = session or requests.Session()

    def fetch(self, limit: Optional[int] = None) -> List[Dict[str, str]]:
        """Lookup report IDs and return only records that appear valid."""
        rows: List[Dict[str, str]] = []
        ids = self.report_ids[:limit] if limit else self.report_ids

        for report_id in ids:
            payload = self.fetch_single_report(report_id)
            if payload is None:
                continue
            rows.append(self.normalize(report_id, payload))

        return rows

    def fetch_single_report(self, report_id: str) -> Optional[Dict[str, Any]]:
        """Submit one report lookup and return parsed response metadata when valid."""
        lookup_url = self._lookup_url()
        form_response = self.session.get(lookup_url, timeout=self.timeout_seconds)
        form_response.raise_for_status()

        action_url, form_data = self._extract_form(form_response.text, lookup_url)
        if not action_url:
            return None

        form_data.update(self.extra_payload)
        form_data[self.report_field_name] = report_id

        response = self.session.post(
            action_url,
            data=form_data,
            timeout=self.timeout_seconds,
            allow_redirects=True,
        )
        response.raise_for_status()

        if not self._is_valid_result(response.text):
            return None

        return {
            "status_code": response.status_code,
            "url": response.url,
            "html": response.text,
        }

    def _lookup_url(self) -> str:
        return urljoin(f"{self.base_url}/", self.lookup_path.lstrip("/"))

    @staticmethod
    def _extract_form(html: str, current_url: str) -> tuple[str, Dict[str, str]]:
        """Extract first form action and default input values from page HTML."""
        soup = BeautifulSoup(html, "html.parser")
        form = soup.find("form")
        if form is None:
            return "", {}

        action = form.get("action") or ""
        action_url = urljoin(current_url, action)

        form_data: Dict[str, str] = {}
        for field in form.find_all(["input", "select", "textarea"]):
            name = field.get("name")
            if not name:
                continue

            if field.name == "select":
                selected = field.find("option", selected=True)
                if selected is not None:
                    form_data[name] = selected.get("value", "")
                else:
                    first = field.find("option")
                    form_data[name] = first.get("value", "") if first is not None else ""
                continue

            form_data[name] = field.get("value", "")

        return action_url, form_data

    def _is_valid_result(self, html: str) -> bool:
        text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True).lower()
        return not any(marker in text for marker in self.INVALID_MARKERS)

    @staticmethod
    def normalize(report_id: str, payload: Dict[str, Any]) -> Dict[str, str]:
        """Normalize successful lookup into pipeline-friendly shape."""
        return {
            "report_id": report_id,
            "crash_join_id": report_id,
            "source": "lapd_buycrash",
            "portal_url": str(payload.get("url", "")),
            "status_code": str(payload.get("status_code", "")),
        }
