"""Tests for portal_security.py and civic_alerts.py."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.audit.portal_security import (
    PIILeakageScanner,
    SequentialIDScanner,
    Severity,
)
from src.audit.civic_alerts import (
    ClusterAlert,
    CrashClusterDetector,
    SupportAlert,
    VictimSupportTrigger,
)


# ==========================================================================
# SequentialIDScanner
# ==========================================================================

def _mock_response(status: int):
    r = MagicMock()
    r.status_code = status
    return r


class TestSequentialIDScanner:
    BASE = "https://example.gov/crashes/report/"

    def _scanner(self):
        return SequentialIDScanner(self.BASE, request_delay_s=0)

    def test_rejects_invalid_base_url(self):
        with pytest.raises(ValueError):
            SequentialIDScanner("not-a-url")

    def test_all_hits_scores_high_or_critical(self):
        scanner = self._scanner()
        with patch.object(scanner._session, "get", return_value=_mock_response(200)):
            report = scanner.run(["2501001", "2501002", "2501003", "2501004", "2501005"])
        assert report.hit_rate == 1.0
        assert report.severity in {Severity.HIGH, Severity.CRITICAL}

    def test_all_misses_scores_info(self):
        scanner = self._scanner()
        with patch.object(scanner._session, "get", return_value=_mock_response(404)):
            report = scanner.run(["2501001", "2501002"])
        assert report.hit_rate == 0.0
        assert report.severity == Severity.INFO

    def test_gap_rate_all_sequential(self):
        rate = SequentialIDScanner._compute_gap_rate(["100", "101", "102", "103"])
        assert rate == 1.0

    def test_gap_rate_non_sequential(self):
        rate = SequentialIDScanner._compute_gap_rate(["100", "200", "300"])
        assert rate == 0.0

    def test_report_has_recommendation(self):
        scanner = self._scanner()
        with patch.object(scanner._session, "get", return_value=_mock_response(200)):
            report = scanner.run(["1", "2", "3"])
        assert len(report.recommendation) > 10

    def test_empty_ids_raises(self):
        with pytest.raises(ValueError):
            self._scanner().run([])


# ==========================================================================
# PIILeakageScanner
# ==========================================================================

CLEAN_HTML = "<html><body><p>No crash details here.</p></body></html>"

PII_HTML = """
<html><body>
  <p>Driver: John Smith</p>
  <p>SSN: 123-45-6789</p>
  <p>Phone: (555) 202-1234</p>
  <p>Email: jsmith@example.com</p>
</body></html>
"""


class TestPIILeakageScanner:
    def test_clean_html_returns_empty(self):
        findings = PIILeakageScanner().scan(CLEAN_HTML)
        assert findings == []

    def test_ssn_detected(self):
        findings = PIILeakageScanner().scan(PII_HTML)
        names = [f.pattern_name for f in findings]
        assert "SSN" in names

    def test_phone_detected(self):
        findings = PIILeakageScanner().scan(PII_HTML)
        names = [f.pattern_name for f in findings]
        assert "Phone" in names

    def test_ssn_is_critical(self):
        findings = PIILeakageScanner().scan(PII_HTML)
        ssn = next(f for f in findings if f.pattern_name == "SSN")
        assert ssn.severity == Severity.CRITICAL

    def test_redaction_applied_by_default(self):
        findings = PIILeakageScanner(redact_samples=True).scan(PII_HTML)
        for f in findings:
            for sample in f.sample_matches:
                # Redacted samples must contain at least one '*'
                assert "*" in sample

    def test_no_redaction_when_disabled(self):
        findings = PIILeakageScanner(redact_samples=False).scan(PII_HTML)
        phone = next((f for f in findings if f.pattern_name == "Phone"), None)
        assert phone is not None
        assert "*" not in phone.sample_matches[0]

    def test_summary_string_nonempty_when_findings(self):
        findings = PIILeakageScanner().scan(PII_HTML)
        summary = PIILeakageScanner().summary(findings)
        assert "finding" in summary.lower()

    def test_summary_clean_message(self):
        assert "No PII" in PIILeakageScanner().summary([])


# ==========================================================================
# CrashClusterDetector
# ==========================================================================

def _make_crashes(rows):
    return pd.DataFrame(rows)


CRASHES = [
    {"street_no": 1200, "street_name": "Michigan Ave", "injuries_total": 1, "injuries_fatal": 0,
     "prim_contributory_cause": "SPEEDING", "road_defect": "RUT, HOLES"},
    {"street_no": 1201, "street_name": "Michigan Ave", "injuries_total": 2, "injuries_fatal": 0,
     "prim_contributory_cause": "SPEEDING", "road_defect": "NO DEFECTS"},
    {"street_no": 1250, "street_name": "Michigan Ave", "injuries_total": 0, "injuries_fatal": 1,
     "prim_contributory_cause": "FAILING TO YIELD", "road_defect": "RUT, HOLES"},
    {"street_no": 100,  "street_name": "Oak St",       "injuries_total": 0, "injuries_fatal": 0,
     "prim_contributory_cause": "UNKNOWN", "road_defect": "NO DEFECTS"},
]


class TestCrashClusterDetector:
    def test_single_crash_not_flagged(self):
        df = _make_crashes(CRASHES[3:4])
        alerts = CrashClusterDetector(min_crashes=2).detect(df)
        assert alerts == []

    def test_cluster_detected(self):
        df = _make_crashes(CRASHES[:3])
        alerts = CrashClusterDetector(min_crashes=2).detect(df)
        assert len(alerts) >= 1

    def test_risk_score_is_positive(self):
        df = _make_crashes(CRASHES[:3])
        alerts = CrashClusterDetector(min_crashes=2).detect(df)
        assert all(a.risk_score > 0 for a in alerts)

    def test_fatal_crash_elevates_score(self):
        no_fatal = _make_crashes([
            {"street_no": 1200, "street_name": "A St", "injuries_total": 1, "injuries_fatal": 0, "prim_contributory_cause": "X", "road_defect": "NO DEFECTS"},
            {"street_no": 1200, "street_name": "A St", "injuries_total": 1, "injuries_fatal": 0, "prim_contributory_cause": "X", "road_defect": "NO DEFECTS"},
            {"street_no": 1200, "street_name": "A St", "injuries_total": 1, "injuries_fatal": 0, "prim_contributory_cause": "X", "road_defect": "NO DEFECTS"},
        ])
        with_fatal = _make_crashes([
            {"street_no": 1200, "street_name": "A St", "injuries_total": 1, "injuries_fatal": 1, "prim_contributory_cause": "X", "road_defect": "NO DEFECTS"},
            {"street_no": 1200, "street_name": "A St", "injuries_total": 1, "injuries_fatal": 0, "prim_contributory_cause": "X", "road_defect": "NO DEFECTS"},
            {"street_no": 1200, "street_name": "A St", "injuries_total": 1, "injuries_fatal": 0, "prim_contributory_cause": "X", "road_defect": "NO DEFECTS"},
        ])
        score_base  = CrashClusterDetector(min_crashes=2).detect(no_fatal)[0].risk_score
        score_fatal = CrashClusterDetector(min_crashes=2).detect(with_fatal)[0].risk_score
        assert score_fatal > score_base

    def test_sorted_by_risk_score_descending(self):
        df = _make_crashes(CRASHES)
        alerts = CrashClusterDetector(min_crashes=2).detect(df)
        scores = [a.risk_score for a in alerts]
        assert scores == sorted(scores, reverse=True)

    def test_to_dataframe_columns(self):
        df = _make_crashes(CRASHES[:3])
        alerts = CrashClusterDetector(min_crashes=2).detect(df)
        out_df = CrashClusterDetector().to_dataframe(alerts)
        assert "segment" in out_df.columns
        assert "risk_score" in out_df.columns
        assert "severity" in out_df.columns

    def test_empty_df_returns_empty(self):
        alerts = CrashClusterDetector().detect(pd.DataFrame())
        assert alerts == []


# ==========================================================================
# VictimSupportTrigger
# ==========================================================================

CRASH_ROWS = [
    {"crash_join_id": "A1", "crash_date": "2026-04-01", "most_severe_injury": "INCAPACITATING INJURY",
     "street_no": 100, "street_direction": "N", "street_name": "Michigan Ave",
     "driver_name": "Jane Doe", "driver_phone": "5551234567", "hit_and_run_i": "N",
     "road_defect": "NO DEFECTS", "device_condition": "FUNCTIONING PROPERLY"},
    {"crash_join_id": "A2", "crash_date": "2026-04-02", "most_severe_injury": "NO INDICATION OF INJURY",
     "street_no": 200, "street_direction": "S", "street_name": "State St",
     "driver_name": "", "driver_phone": "", "hit_and_run_i": "N",
     "road_defect": "NO DEFECTS", "device_condition": "FUNCTIONING PROPERLY"},
    {"crash_join_id": "A3", "crash_date": "2026-04-03", "most_severe_injury": "FATAL",
     "street_no": 300, "street_direction": "W", "street_name": "Oak St",
     "driver_name": "Bob Smith", "driver_phone": "5559876543", "hit_and_run_i": "Y",
     "road_defect": "RUT, HOLES", "device_condition": "FUNCTIONING PROPERLY"},
]


class TestVictimSupportTrigger:
    def test_no_injury_row_not_triggered(self):
        df = pd.DataFrame([CRASH_ROWS[1]])
        alerts = VictimSupportTrigger().evaluate(df)
        assert alerts == []

    def test_injury_row_triggers_alert(self):
        df = pd.DataFrame([CRASH_ROWS[0]])
        alerts = VictimSupportTrigger().evaluate(df)
        assert len(alerts) == 1
        assert alerts[0].crash_join_id == "A1"

    def test_fatal_row_triggers_alert(self):
        df = pd.DataFrame([CRASH_ROWS[2]])
        alerts = VictimSupportTrigger().evaluate(df)
        assert len(alerts) == 1
        assert alerts[0].injury_severity == "FATAL"

    def test_hit_and_run_note_added(self):
        df = pd.DataFrame([CRASH_ROWS[2]])
        alerts = VictimSupportTrigger().evaluate(df)
        assert "hit-and-run" in alerts[0].notes.lower()

    def test_road_defect_note_added(self):
        df = pd.DataFrame([CRASH_ROWS[2]])
        alerts = VictimSupportTrigger().evaluate(df)
        assert "road defect" in alerts[0].notes.lower()

    def test_resources_populated(self):
        df = pd.DataFrame([CRASH_ROWS[0]])
        alerts = VictimSupportTrigger(city="chicago").evaluate(df)
        assert "legal_aid" in alerts[0].resources
        assert alerts[0].resources["legal_aid"].startswith("http")

    def test_to_dataframe_has_resource_columns(self):
        df = pd.DataFrame(CRASH_ROWS)
        alerts = VictimSupportTrigger().evaluate(df)
        out_df = VictimSupportTrigger().to_dataframe(alerts)
        assert "resource_legal_aid" in out_df.columns
        assert "resource_trauma" in out_df.columns

    def test_multiple_rows_correct_count(self):
        df = pd.DataFrame(CRASH_ROWS)  # 2 of 3 have injuries
        alerts = VictimSupportTrigger().evaluate(df)
        assert len(alerts) == 2
