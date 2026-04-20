"""
MissouriProvider — Missouri State Highway Patrol (MSHP) crash report lookup.

Targets the Troop-based AccidentForm portal used by field troops including
Troop C (St. Louis area). Report IDs follow the format YYMMXXXXX
(e.g. 250111396 = 2025, Troop area, sequential number).

Portal: https://www.mshp.dps.missouri.gov/HP68/AccidentForm
"""

import asyncio
import re
from typing import Any, Dict, Iterable, List, Optional

from bs4 import BeautifulSoup

from .base import BaseProvider
from src.utils.limiter import RateLimiter

# Troop codes → human-readable coverage areas.
TROOP_COVERAGE: Dict[str, str] = {
    "A": "Troop A – Lee's Summit / Kansas City area",
    "B": "Troop B – Macon",
    "C": "Troop C – Weldon Spring / St. Louis area",
    "D": "Troop D – Springfield",
    "E": "Troop E – Poplar Bluff / New Madrid area",
    "F": "Troop F – Jefferson City",
    "G": "Troop G – Willow Springs",
    "H": "Troop H – St. Joseph",
    "I": "Troop I – Rolla",
}

PORTAL_BASE = "https://www.mshp.dps.missouri.gov"
SEARCH_URL = f"{PORTAL_BASE}/HP68/AccidentForm"


class MissouriProvider(BaseProvider):
    """
    Fetch MSHP crash records by report-ID lookup from the Troop portal.

    Usage
    -----
    provider = MissouriProvider(troop="C", tokens_per_second=2)
    rows = provider.fetch(limit=10)

    Each returned row conforms to the crash_join_id schema:
        {
            "crash_join_id": "250111396",
            "source": "mshp_troop_c",
            "agency": "Missouri State Highway Patrol – Troop C",
            "troop": "C",
            "report_date": "...",
            "county": "...",
            "location": "...",
            "contact_found": True,
        }
    """

    REPORT_ID_FIELD = "accidentNumber"
    SOURCE_PREFIX = "mshp_troop"

    def __init__(
        self,
        troop: str = "C",
        accident_ids: Optional[List[str]] = None,
        tokens_per_second: float = 2.0,
        timeout_seconds: float = 30.0,
    ) -> None:
        self.troop = troop.upper().strip()
        self.default_ids: List[str] = [str(i).strip() for i in (accident_ids or []) if str(i).strip()]
        self.timeout_seconds = timeout_seconds
        self.limiter = RateLimiter(tokens_per_second=tokens_per_second)
        self.source = f"{self.SOURCE_PREFIX}_{self.troop.lower()}"
        coverage = TROOP_COVERAGE.get(self.troop, f"Troop {self.troop}")
        self.agency = f"Missouri State Highway Patrol – {coverage}"

    # ------------------------------------------------------------------
    # BaseProvider interface
    # ------------------------------------------------------------------

    def fetch(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Sync wrapper — runs the async lookup loop and returns normalized rows."""
        ids = self.default_ids[:limit] if limit else self.default_ids
        if not ids:
            return []
        rows = asyncio.run(self.check_ids(ids))
        return [row for row in rows if isinstance(row, dict)]

    # ------------------------------------------------------------------
    # Async lookup helpers
    # ------------------------------------------------------------------

    async def check_ids(self, accident_ids: Iterable[str]) -> List[Dict[str, Any]]:
        """Sequential rate-limited lookup, one shared aiohttp session."""
        import aiohttp

        timeout = aiohttp.ClientTimeout(total=self.timeout_seconds)
        results: List[Dict[str, Any]] = []

        async with aiohttp.ClientSession(timeout=timeout) as session:
            # Pre-fetch the landing page to capture any session cookies / CSRF.
            try:
                async with session.get(SEARCH_URL) as seed_response:
                    seed_html = await seed_response.text() if seed_response.status < 400 else ""
            except Exception:
                seed_html = ""

            hidden_defaults = self._extract_hidden_fields(seed_html)

            for accident_id in accident_ids:
                row = await self._lookup_one(accident_id, session, hidden_defaults)
                if row is not None:
                    results.append(row)

        return results

    async def _lookup_one(
        self,
        accident_id: str,
        session: Any,
        hidden_defaults: Dict[str, str],
    ) -> Optional[Dict[str, Any]]:
        """Rate-limited single-record POST lookup."""
        await self.limiter.wait()

        payload = dict(hidden_defaults)
        payload[self.REPORT_ID_FIELD] = accident_id
        # Troop selector — portal uses a dropdown named 'troop'.
        payload.setdefault("troop", self.troop)

        try:
            async with session.post(SEARCH_URL, data=payload) as response:
                if response.status != 200:
                    return None
                html = await response.text()
        except Exception:
            return None

        return self.normalize(html, accident_id)

    # ------------------------------------------------------------------
    # Parsing helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_hidden_fields(html: str) -> Dict[str, str]:
        """Capture hidden/default form inputs for CSRF and ViewState passthrough."""
        soup = BeautifulSoup(html, "html.parser")
        fields: Dict[str, str] = {}
        for inp in soup.find_all("input"):
            name = inp.get("name")
            if not name:
                continue
            itype = str(inp.get("type", "text")).lower()
            if itype in {"hidden", "submit", "button", "reset"}:
                fields[name] = str(inp.get("value", ""))
        return fields

    def normalize(self, html: str, accident_id: str) -> Optional[Dict[str, Any]]:
        """
        Parse the MSHP result page into the crash_join_id schema.

        Returns None if the portal returned a "not found" / error page.
        """
        soup = BeautifulSoup(html, "html.parser")
        page_text = soup.get_text(separator=" ", strip=True)

        # Heuristic: portal shows "No records found" or "invalid" on miss.
        no_result_patterns = [
            r"no records found",
            r"no accident report",
            r"not found",
            r"invalid accident number",
        ]
        for pattern in no_result_patterns:
            if re.search(pattern, page_text, re.IGNORECASE):
                return None

        # Extract structured fields from labelled table cells / definition lists.
        report_date = self._scrape_field(soup, ["Report Date", "Date of Crash", "Crash Date"])
        county = self._scrape_field(soup, ["County"])
        location = self._scrape_field(soup, ["Location", "Location of Crash"])
        troop_code = self._scrape_field(soup, ["Troop"]) or self.troop

        # Detect any contact / involved-party block.
        contact_found = bool(
            soup.find(string=re.compile(r"Driver|Owner|Pedestrian|Involved Party", re.IGNORECASE))
        )

        return {
            "crash_join_id": accident_id,
            "source": self.source,
            "agency": self.agency,
            "troop": troop_code,
            "report_date": report_date,
            "county": county,
            "location": location,
            "contact_found": contact_found,
        }

    @staticmethod
    def _scrape_field(soup: BeautifulSoup, labels: List[str]) -> str:
        """
        Find the first match of any label, then return the adjacent text value.
        Works for <th>Label</th><td>Value</td> table rows and <dt>/<dd> pairs.
        """
        for label in labels:
            # Table row pattern: <th> or <td> containing the label.
            header = soup.find(["th", "td"], string=re.compile(rf"^\s*{re.escape(label)}\s*$", re.IGNORECASE))
            if header is not None:
                sibling = header.find_next_sibling(["td", "th"])
                if sibling is not None:
                    return sibling.get_text(strip=True)

            # Definition-list pattern: <dt> → <dd>
            dt = soup.find("dt", string=re.compile(rf"^\s*{re.escape(label)}\s*$", re.IGNORECASE))
            if dt is not None:
                dd = dt.find_next_sibling("dd")
                if dd is not None:
                    return dd.get_text(strip=True)

        return ""
