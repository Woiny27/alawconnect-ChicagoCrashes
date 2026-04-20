"""
civic_alerts.py — Crash cluster detection and victim support triggers.

Two capabilities:

1. CrashClusterDetector
   Groups crash records by road segment (street + block) and flags
   segments that exceed a configurable density or injury threshold as
   high-risk "crash clusters" requiring immediate municipal attention.
   Output is suitable for direct export to a city road-repair work order
   or dashboard alert feed.

2. VictimSupportTrigger
   Evaluates each crash row and, where injury indicators are present,
   generates a structured support alert linking the victim to:
     • Emergency medical / trauma support referrals
     • Legal aid and insurance guidance
     • City infrastructure complaint filing links
     • Language-appropriate resource URLs

Usage
-----
    from src.audit.civic_alerts import CrashClusterDetector, VictimSupportTrigger
    import pandas as pd

    df = pd.read_csv("data/merged_output.csv")

    clusters = CrashClusterDetector().detect(df)
    alerts   = VictimSupportTrigger().evaluate(df)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import pandas as pd


# ---------------------------------------------------------------------------
# Support resource registry
# ---------------------------------------------------------------------------

SUPPORT_RESOURCES: Dict[str, Dict[str, str]] = {
    "chicago": {
        "trauma":        "https://www.chicago.gov/city/en/depts/cdph/supp_info/behavioral-health/trauma-informed-care.html",
        "legal_aid":     "https://www.illinoislegalaid.org/",
        "road_complaint": "https://311.chicago.gov/s/",
        "insurance_help": "https://insurance.illinois.gov/consumer/InjuredInAnAccident.html",
        "victim_services": "https://www.chicago.gov/city/en/depts/fss/supp_info/victim-services.html",
    },
    "default": {
        "trauma":         "https://www.samhsa.gov/find-help/national-helpline",
        "legal_aid":      "https://www.lawhelp.org/",
        "road_complaint":  "https://www.usa.gov/local-governments",
        "insurance_help":  "https://www.naic.org/consumer_alert_auto.htm",
        "victim_services": "https://ovc.ojp.gov/help-for-crime-victims/find-help",
    },
}


# ---------------------------------------------------------------------------
# 1. Crash cluster detection
# ---------------------------------------------------------------------------

@dataclass
class ClusterAlert:
    segment_key: str          # e.g. "1200 N MICHIGAN AVE"
    street_name: str
    street_no_block: str      # rounded to nearest 100
    crash_count: int
    injury_count: int
    fatal_count: int
    risk_score: float         # 0–100
    severity_label: str       # "MONITOR" | "ELEVATED" | "HIGH RISK" | "CRITICAL"
    contributing_causes: List[str] = field(default_factory=list)
    road_defects: List[str] = field(default_factory=list)
    recommendation: str = ""


class CrashClusterDetector:
    """
    Identify road segments with disproportionate crash concentrations.

    Parameters
    ----------
    min_crashes:
        Minimum number of crashes on a segment to be flagged (default 3).
    block_size:
        Round street_no to this granularity for segment grouping (default 100).
    injury_weight:
        Points added to risk score per injured person (default 8).
    fatal_weight:
        Points added to risk score per fatality (default 25).
    """

    _SEVERITY_THRESHOLDS = [
        (75, "CRITICAL"),
        (50, "HIGH RISK"),
        (25, "ELEVATED"),
        (0,  "MONITOR"),
    ]

    def __init__(
        self,
        min_crashes: int = 3,
        block_size: int = 100,
        injury_weight: float = 8.0,
        fatal_weight: float = 25.0,
    ) -> None:
        self.min_crashes = min_crashes
        self.block_size = block_size
        self.injury_weight = injury_weight
        self.fatal_weight = fatal_weight

    def detect(self, df: pd.DataFrame) -> List[ClusterAlert]:
        """
        Analyse a crashes DataFrame and return sorted ClusterAlert objects.

        Required columns: street_no, street_name
        Optional (used if present): injuries_total, injuries_fatal,
            prim_contributory_cause, road_defect
        """
        if df.empty:
            return []

        work = df.copy()

        # Normalise street_no to block-level (round down to nearest block_size)
        work["_block"] = (
            pd.to_numeric(work.get("street_no", pd.Series(dtype=float)), errors="coerce")
            .fillna(0)
            .astype(int)
            .apply(lambda n: (n // self.block_size) * self.block_size)
        )
        work["_street"] = (
            work.get("street_name", pd.Series("UNKNOWN", index=work.index))
            .fillna("UNKNOWN")
            .str.upper()
            .str.strip()
        )
        work["_segment"] = work["_block"].astype(str) + " " + work["_street"]

        groups = work.groupby("_segment")
        alerts: List[ClusterAlert] = []

        for segment_key, group in groups:
            crash_count = len(group)
            if crash_count < self.min_crashes:
                continue

            injury_count = int(
                pd.to_numeric(group.get("injuries_total", pd.Series(dtype=float)), errors="coerce")
                .fillna(0)
                .sum()
            )
            fatal_count = int(
                pd.to_numeric(group.get("injuries_fatal", pd.Series(dtype=float)), errors="coerce")
                .fillna(0)
                .sum()
            )

            risk_score = self._score(crash_count, injury_count, fatal_count)
            severity_label = self._label(risk_score)

            cause_col = "prim_contributory_cause"
            causes: List[str] = []
            if cause_col in group.columns:
                causes = (
                    group[cause_col]
                    .dropna()
                    .value_counts()
                    .head(3)
                    .index.tolist()
                )

            defect_col = "road_defect"
            defects: List[str] = []
            if defect_col in group.columns:
                defects = (
                    group[defect_col]
                    .dropna()
                    .loc[lambda s: ~s.str.upper().isin({"NO DEFECTS", "UNKNOWN", ""})]
                    .value_counts()
                    .head(3)
                    .index.tolist()
                )

            block_str = str(group["_block"].iloc[0])
            street_str = str(group["_street"].iloc[0])

            alerts.append(ClusterAlert(
                segment_key=str(segment_key),
                street_name=street_str,
                street_no_block=block_str,
                crash_count=crash_count,
                injury_count=injury_count,
                fatal_count=fatal_count,
                risk_score=round(risk_score, 1),
                severity_label=severity_label,
                contributing_causes=causes,
                road_defects=defects,
                recommendation=self._recommend(severity_label, defects),
            ))

        alerts.sort(key=lambda a: a.risk_score, reverse=True)
        return alerts

    def to_dataframe(self, alerts: List[ClusterAlert]) -> pd.DataFrame:
        """Convert a list of ClusterAlerts to a flat DataFrame for CSV export."""
        return pd.DataFrame([
            {
                "segment":              a.segment_key,
                "street_name":          a.street_name,
                "block":                a.street_no_block,
                "crash_count":          a.crash_count,
                "injury_count":         a.injury_count,
                "fatal_count":          a.fatal_count,
                "risk_score":           a.risk_score,
                "severity":             a.severity_label,
                "top_causes":           " | ".join(a.contributing_causes),
                "road_defects":         " | ".join(a.road_defects),
                "recommendation":       a.recommendation,
            }
            for a in alerts
        ])

    def _score(self, crashes: int, injuries: int, fatals: int) -> float:
        base = math.log1p(crashes) * 15
        return min(100.0, base + injuries * self.injury_weight + fatals * self.fatal_weight)

    @staticmethod
    def _label(score: float) -> str:
        if score >= 75:
            return "CRITICAL"
        if score >= 50:
            return "HIGH RISK"
        if score >= 25:
            return "ELEVATED"
        return "MONITOR"

    @staticmethod
    def _recommend(severity: str, defects: List[str]) -> str:
        base = {
            "CRITICAL":  "Immediate engineering review required. Deploy traffic safety improvements (signals, barriers, repaving) within 30 days.",
            "HIGH RISK": "Schedule engineering assessment within 60 days. Review signal timing and sight-line obstructions.",
            "ELEVATED":  "Flag for next quarterly road inspection cycle. Review posted speed limits.",
            "MONITOR":   "Add to monthly monitoring list. No immediate action required.",
        }.get(severity, "Review with city traffic engineering team.")
        if defects:
            base += f" Known road defects: {', '.join(defects)}."
        return base


# ---------------------------------------------------------------------------
# 2. Victim support trigger
# ---------------------------------------------------------------------------

# Injury severity levels that warrant a support alert
_INJURY_FLAGS = {
    "FATAL",
    "INCAPACITATING INJURY",
    "NONINCAPACITATING INJURY",
    "REPORTED, NOT EVIDENT",
}


@dataclass
class SupportAlert:
    crash_join_id: str
    crash_date: str
    injury_severity: str
    location_desc: str
    contact_name: str           # driver_name from contacts if available
    contact_phone: str          # driver_phone, cleaned
    resources: Dict[str, str]   # category → URL
    notes: str = ""


class VictimSupportTrigger:
    """
    Scan each crash row and generate a SupportAlert for injured parties.

    Parameters
    ----------
    city:
        Resource registry key. "chicago" picks city-specific URLs;
        anything else falls back to "default".
    min_severity:
        Only generate alerts for injury levels at this rank or above.
        Rank order: FATAL > INCAPACITATING > NONINCAPACITATING > REPORTED_NOT_EVIDENT
    """

    _SEVERITY_RANK = {
        "FATAL":                       4,
        "INCAPACITATING INJURY":        3,
        "NONINCAPACITATING INJURY":     2,
        "REPORTED, NOT EVIDENT":        1,
        "NO INDICATION OF INJURY":      0,
    }

    def __init__(self, city: str = "chicago", min_severity_rank: int = 1) -> None:
        self.city = city.lower()
        self.min_severity_rank = min_severity_rank
        self.resources = SUPPORT_RESOURCES.get(self.city, SUPPORT_RESOURCES["default"])

    def evaluate(self, df: pd.DataFrame) -> List[SupportAlert]:
        """
        Return one SupportAlert per crash row where injury level meets threshold.

        Expected columns: crash_join_id, most_severe_injury
        Optional: crash_date, street_no, street_direction, street_name,
                  driver_name, driver_phone
        """
        alerts: List[SupportAlert] = []

        for _, row in df.iterrows():
            severity_raw = str(row.get("most_severe_injury", "")).strip().upper()
            rank = self._SEVERITY_RANK.get(severity_raw, 0)
            if rank < self.min_severity_rank:
                continue

            alerts.append(SupportAlert(
                crash_join_id=str(row.get("crash_join_id", "")),
                crash_date=str(row.get("crash_date", "")),
                injury_severity=severity_raw,
                location_desc=self._location(row),
                contact_name=str(row.get("driver_name", "")).strip(),
                contact_phone=str(row.get("driver_phone", "")).strip(),
                resources=dict(self.resources),
                notes=self._notes(row),
            ))

        return alerts

    def to_dataframe(self, alerts: List[SupportAlert]) -> pd.DataFrame:
        """Flatten support alerts for CSV or dashboard export."""
        rows = []
        for a in alerts:
            base: Dict[str, Any] = {
                "crash_join_id":   a.crash_join_id,
                "crash_date":      a.crash_date,
                "injury_severity": a.injury_severity,
                "location":        a.location_desc,
                "contact_name":    a.contact_name,
                "contact_phone":   a.contact_phone,
                "notes":           a.notes,
            }
            base.update({f"resource_{k}": v for k, v in a.resources.items()})
            rows.append(base)
        return pd.DataFrame(rows)

    @staticmethod
    def _location(row: pd.Series) -> str:
        parts = [
            str(row.get("street_no", "")).strip(),
            str(row.get("street_direction", "")).strip(),
            str(row.get("street_name", "")).strip(),
        ]
        return " ".join(p for p in parts if p and p.lower() != "nan")

    @staticmethod
    def _notes(row: pd.Series) -> str:
        notes = []
        if str(row.get("hit_and_run_i", "")).strip().upper() == "Y":
            notes.append("Hit-and-run — victim may need additional legal support.")
        if str(row.get("road_defect", "")).strip().upper() not in {"", "NO DEFECTS", "UNKNOWN", "NAN"}:
            notes.append(f"Road defect recorded: {row.get('road_defect')}.")
        if str(row.get("device_condition", "")).strip().upper() not in {"", "FUNCTIONING PROPERLY", "NAN"}:
            notes.append(f"Traffic device condition: {row.get('device_condition')}.")
        return " ".join(notes)
