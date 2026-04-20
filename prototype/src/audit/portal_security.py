"""
portal_security.py — Civic security audit for public crash portals.

Two audits are provided:

1. SequentialIDScanner
   Probes a portal for sequential ID enumeration vulnerabilities.
   If consecutive report IDs return valid records, the portal leaks
   the full report count and exposes every record to trivial scraping.
   Findings are scored LOW / MEDIUM / HIGH / CRITICAL.

2. PIILeakageScanner
   Inspects raw HTML from a portal response for common PII patterns
   (names, phone numbers, SSNs, DOB, email, license plates) that
   should not be machine-readable on a public page.

Usage
-----
    from src.audit.portal_security import SequentialIDScanner, PIILeakageScanner

    scanner = SequentialIDScanner(base_url="https://example.gov/crashes/report/")
    report  = scanner.run(sample_ids=["2501001", "2501002", "2501003"])

    pii = PIILeakageScanner()
    findings = pii.scan(html_text, source_url="https://example.gov/crashes/report/2501001")
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional
from urllib.parse import urlparse

import requests


# ---------------------------------------------------------------------------
# Severity levels
# ---------------------------------------------------------------------------

class Severity(str, Enum):
    INFO     = "INFO"
    LOW      = "LOW"
    MEDIUM   = "MEDIUM"
    HIGH     = "HIGH"
    CRITICAL = "CRITICAL"


# ---------------------------------------------------------------------------
# Shared finding dataclass
# ---------------------------------------------------------------------------

@dataclass
class Finding:
    severity: Severity
    category: str
    description: str
    evidence: str = ""
    url: str = ""


# ---------------------------------------------------------------------------
# 1. Sequential ID vulnerability scanner
# ---------------------------------------------------------------------------

@dataclass
class SequentialIDReport:
    portal_url: str
    ids_probed: List[str]
    hit_rate: float           # fraction of probed IDs that returned a valid response
    gap_rate: float           # fraction of consecutive pairs that are strictly sequential
    severity: Severity
    findings: List[Finding] = field(default_factory=list)
    recommendation: str = ""


class SequentialIDScanner:
    """
    Probe a public portal for sequential ID enumeration exposure.

    Parameters
    ----------
    base_url:
        URL prefix to which each report ID is appended.
        e.g. "https://example.gov/crashes/report/"
    valid_status_codes:
        HTTP status codes that indicate a record was found (default 200).
    request_delay_s:
        Seconds to wait between probes (default 1.0 — be a polite guest).
    timeout_s:
        Per-request timeout in seconds.
    """

    # Threshold fractions for severity escalation
    _HIT_MEDIUM   = 0.50
    _HIT_HIGH     = 0.75
    _HIT_CRITICAL = 0.90
    _GAP_THRESHOLD = 0.70   # if 70 %+ of pairs are sequential → enumerable

    def __init__(
        self,
        base_url: str,
        valid_status_codes: Optional[List[int]] = None,
        request_delay_s: float = 1.0,
        timeout_s: float = 15.0,
    ) -> None:
        parsed = urlparse(base_url)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError(f"base_url must be a full URL, got: {base_url!r}")
        self.base_url = base_url.rstrip("/") + "/"
        self.valid_status_codes = set(valid_status_codes or [200])
        self.request_delay_s = max(0.0, request_delay_s)
        self.timeout_s = timeout_s
        self._session = requests.Session()
        self._session.headers["User-Agent"] = (
            "CivicAuditBot/1.0 (municipal-security-research; contact: audit@example.gov)"
        )

    def run(self, sample_ids: List[str]) -> SequentialIDReport:
        """Probe each ID and return a scored report."""
        if not sample_ids:
            raise ValueError("sample_ids must not be empty")

        hits: List[str] = []
        misses: List[str] = []

        for report_id in sample_ids:
            url = self.base_url + str(report_id)
            try:
                resp = self._session.get(url, timeout=self.timeout_s, allow_redirects=True)
                if resp.status_code in self.valid_status_codes:
                    hits.append(report_id)
                else:
                    misses.append(report_id)
            except requests.RequestException:
                misses.append(report_id)
            time.sleep(self.request_delay_s)

        hit_rate = len(hits) / len(sample_ids)
        gap_rate = self._compute_gap_rate(sample_ids)
        severity = self._score(hit_rate, gap_rate)
        findings = self._build_findings(hit_rate, gap_rate, hits, severity)
        recommendation = self._recommendation(severity)

        return SequentialIDReport(
            portal_url=self.base_url,
            ids_probed=sample_ids,
            hit_rate=round(hit_rate, 4),
            gap_rate=round(gap_rate, 4),
            severity=severity,
            findings=findings,
            recommendation=recommendation,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_gap_rate(ids: List[str]) -> float:
        """
        Fraction of consecutive ID pairs that differ by exactly 1 (numeric suffix).
        High gap_rate means IDs are densely sequential → enumerable.
        """
        if len(ids) < 2:
            return 0.0

        numeric_ids: List[int] = []
        for id_str in ids:
            digits = re.sub(r"\D", "", str(id_str))
            if digits:
                numeric_ids.append(int(digits))

        if len(numeric_ids) < 2:
            return 0.0

        consecutive = sum(
            1
            for a, b in zip(numeric_ids, numeric_ids[1:])
            if abs(b - a) == 1
        )
        return consecutive / (len(numeric_ids) - 1)

    def _score(self, hit_rate: float, gap_rate: float) -> Severity:
        if hit_rate >= self._HIT_CRITICAL and gap_rate >= self._GAP_THRESHOLD:
            return Severity.CRITICAL
        if hit_rate >= self._HIT_HIGH:
            return Severity.HIGH
        if hit_rate >= self._HIT_MEDIUM:
            return Severity.MEDIUM
        if hit_rate > 0:
            return Severity.LOW
        return Severity.INFO

    def _build_findings(
        self,
        hit_rate: float,
        gap_rate: float,
        hits: List[str],
        severity: Severity,
    ) -> List[Finding]:
        findings: List[Finding] = []

        if hit_rate > 0:
            findings.append(Finding(
                severity=severity,
                category="Sequential ID Enumeration",
                description=(
                    f"{hit_rate:.0%} of probed IDs returned valid records. "
                    "An attacker can enumerate all crash records by iterating IDs."
                ),
                evidence=f"Valid IDs confirmed: {hits[:5]}{'…' if len(hits) > 5 else ''}",
                url=self.base_url,
            ))

        if gap_rate >= self._GAP_THRESHOLD:
            findings.append(Finding(
                severity=Severity.HIGH,
                category="Predictable ID Pattern",
                description=(
                    f"{gap_rate:.0%} of consecutive IDs differ by 1. "
                    "Report IDs are strictly sequential and therefore fully predictable."
                ),
                url=self.base_url,
            ))

        return findings

    @staticmethod
    def _recommendation(severity: Severity) -> str:
        mapping = {
            Severity.CRITICAL: (
                "URGENT: Implement token-based access control. Replace sequential IDs with "
                "non-guessable UUIDs. Add authentication for full-record retrieval. "
                "Consider rate-limiting and CAPTCHA on the search form."
            ),
            Severity.HIGH: (
                "Replace sequential numeric report IDs with opaque tokens or UUIDs. "
                "Add per-IP rate limiting and an audit log for bulk enumeration attempts."
            ),
            Severity.MEDIUM: (
                "Monitor for bulk access patterns. Consider switching to non-sequential IDs "
                "and adding rate limiting to the search endpoint."
            ),
            Severity.LOW: (
                "Low enumeration risk detected. Monitor access logs for sequential request "
                "patterns and review whether all returned fields are intended for public access."
            ),
            Severity.INFO: (
                "No enumeration vulnerability detected in this sample. Re-test with a larger "
                "ID range to confirm."
            ),
        }
        return mapping[severity]


# ---------------------------------------------------------------------------
# 2. PII leakage scanner
# ---------------------------------------------------------------------------

# PII patterns (compiled once at module load)
_PII_PATTERNS: Dict[str, re.Pattern] = {
    "SSN": re.compile(
        r"\b(?!000|666|9\d{2})\d{3}[-\s](?!00)\d{2}[-\s](?!0000)\d{4}\b"
    ),
    "Phone": re.compile(
        r"(?:\+?1[-.\s]?)?(?:\(\d{3}\)[-.\s]?|\d{3}[-.\s])\d{3}[-.\s]\d{4}"
    ),
    "Email": re.compile(
        r"\b[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}\b"
    ),
    "Date of Birth": re.compile(
        r"\b(?:DOB|Date of Birth|Born)[:\s]+\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}\b",
        re.IGNORECASE,
    ),
    "Driver License": re.compile(
        r"\b(?:DL|License)[#\s:]+[A-Z0-9]{6,12}\b",
        re.IGNORECASE,
    ),
    "License Plate": re.compile(
        r"\b[A-Z]{1,3}[-\s]?\d{3,4}[-\s]?[A-Z]{0,3}\b"
    ),
    "Full Name (labeled)": re.compile(
        r"\b(?:Driver|Owner|Name)[:\s]+[A-Z][a-z]+\s[A-Z][a-z]+\b",
        re.IGNORECASE,
    ),
}


@dataclass
class PIIFinding:
    pattern_name: str
    severity: Severity
    match_count: int
    sample_matches: List[str]
    source_url: str = ""


class PIILeakageScanner:
    """
    Scan raw HTML (or plain text) from a portal response for PII patterns
    that should not appear on a publicly accessible page.

    Parameters
    ----------
    redact_samples:
        If True, partial-redact sample matches in findings (default True).
        Set to False only in a secure, non-logged audit environment.
    """

    _SEVERITY_MAP: Dict[str, Severity] = {
        "SSN":                  Severity.CRITICAL,
        "Phone":                Severity.HIGH,
        "Email":                Severity.MEDIUM,
        "Date of Birth":        Severity.HIGH,
        "Driver License":       Severity.HIGH,
        "License Plate":        Severity.MEDIUM,
        "Full Name (labeled)":  Severity.MEDIUM,
    }

    def __init__(self, redact_samples: bool = True) -> None:
        self.redact_samples = redact_samples

    def scan(self, text: str, source_url: str = "") -> List[PIIFinding]:
        """Return PII findings for the given text. Empty list = clean."""
        findings: List[PIIFinding] = []

        for name, pattern in _PII_PATTERNS.items():
            matches = pattern.findall(text)
            if not matches:
                continue

            samples = list(dict.fromkeys(matches))[:3]  # deduplicated, max 3
            if self.redact_samples:
                samples = [self._redact(m) for m in samples]

            findings.append(PIIFinding(
                pattern_name=name,
                severity=self._SEVERITY_MAP.get(name, Severity.MEDIUM),
                match_count=len(matches),
                sample_matches=samples,
                source_url=source_url,
            ))

        # Sort by severity descending
        order = [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW, Severity.INFO]
        findings.sort(key=lambda f: order.index(f.severity))
        return findings

    @staticmethod
    def _redact(value: str) -> str:
        """Partially redact a string, preserving only the first and last characters."""
        if len(value) <= 4:
            return "*" * len(value)
        return value[0] + "*" * (len(value) - 2) + value[-1]

    def summary(self, findings: List[PIIFinding]) -> str:
        if not findings:
            return "No PII patterns detected."
        lines = [f"PII Scan — {len(findings)} finding(s):"]
        for f in findings:
            lines.append(
                f"  [{f.severity.value:8s}] {f.pattern_name}: "
                f"{f.match_count} match(es) — e.g. {f.sample_matches}"
            )
        return "\n".join(lines)
