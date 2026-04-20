"""
dataset_stats.py — City dataset quality profiling.

Provides:
  CityDatasetStats        — dataclass holding per-city quality metrics
  DatasetStatsCollector   — computes stats from a DataFrame + metadata
  MultiCityStatsReport    — aggregates stats across multiple cities
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Dict, List, Optional, Sequence

import pandas as pd


# ---------------------------------------------------------------------------
# Core dataclass (user-supplied, extended with helpers)
# ---------------------------------------------------------------------------

@dataclass
class CityDatasetStats:
    city: str
    total_records: int
    missing_fields_pct: float        # 0–100: mean % of fields missing per row
    duplicate_rate: float            # 0–1: fraction of rows that are exact duplicates
    avg_ingestion_delay_days: float  # mean days between crash_date and date_police_notified
    data_source_type: str            # "api" | "vendor" | "portal"

    # Extended quality dimensions
    critical_fields_null_pct: float = 0.0   # nulls in must-have columns (lat, lon, date)
    injury_completeness_pct: float = 100.0  # % of rows where injuries_total is present
    staleness_days: float = 0.0             # days since the most recent record
    quality_score: float = 0.0             # 0–100 composite score (higher = better)
    flagged_issues: List[str] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    def as_dict(self) -> Dict:
        return asdict(self)

    def summary(self) -> str:
        lines = [
            f"=== {self.city} ({self.data_source_type.upper()}) ===",
            f"  Records          : {self.total_records:,}",
            f"  Quality score    : {self.quality_score:.1f} / 100",
            f"  Missing fields   : {self.missing_fields_pct:.1f}%",
            f"  Duplicate rate   : {self.duplicate_rate:.1%}",
            f"  Ingestion delay  : {self.avg_ingestion_delay_days:.1f} days avg",
            f"  Staleness        : {self.staleness_days:.0f} days since last record",
            f"  Critical nulls   : {self.critical_fields_null_pct:.1f}%",
            f"  Injury complete  : {self.injury_completeness_pct:.1f}%",
        ]
        if self.flagged_issues:
            lines.append("  Issues:")
            for issue in self.flagged_issues:
                lines.append(f"    ⚠  {issue}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Collector — derives a CityDatasetStats from a DataFrame
# ---------------------------------------------------------------------------

# Fields that must be present for a record to be usable downstream.
_CRITICAL_FIELDS = ["crash_date", "latitude", "longitude", "crash_join_id"]

# Thresholds that trigger a flagged issue.
_WARN_MISSING_PCT      = 20.0   # >20 % overall missing → warn
_WARN_DUPLICATE_RATE   = 0.05   # >5 % duplicates → warn
_WARN_DELAY_DAYS       = 14.0   # >14 days avg ingestion delay → warn
_WARN_STALENESS_DAYS   = 30.0   # last record >30 days old → warn
_WARN_CRITICAL_NULL    = 5.0    # >5 % critical-field nulls → warn


class DatasetStatsCollector:
    """
    Compute CityDatasetStats from a crash DataFrame.

    Parameters
    ----------
    city : str
        Human-readable city / jurisdiction label.
    data_source_type : str
        One of "api", "vendor", "portal".
    crash_date_col : str
        Column containing crash timestamp (ISO string or datetime).
    notified_date_col : str
        Column containing the police-notified timestamp, used to compute
        ingestion delay.  Pass None to skip delay computation.
    dedup_subset : Sequence[str] | None
        Columns to use for duplicate detection.  Defaults to all columns.
    """

    def __init__(
        self,
        city: str,
        data_source_type: str = "api",
        crash_date_col: str = "crash_date",
        notified_date_col: Optional[str] = "date_police_notified",
        dedup_subset: Optional[Sequence[str]] = None,
    ) -> None:
        self.city = city
        self.data_source_type = data_source_type.lower().strip()
        self.crash_date_col = crash_date_col
        self.notified_date_col = notified_date_col
        self.dedup_subset = list(dedup_subset) if dedup_subset else None

    def collect(self, df: pd.DataFrame) -> CityDatasetStats:
        """Analyse *df* and return a fully populated CityDatasetStats."""
        if df.empty:
            return CityDatasetStats(
                city=self.city,
                total_records=0,
                missing_fields_pct=100.0,
                duplicate_rate=0.0,
                avg_ingestion_delay_days=0.0,
                data_source_type=self.data_source_type,
                quality_score=0.0,
                flagged_issues=["Dataset is empty"],
            )

        total = len(df)
        missing_pct      = self._missing_pct(df)
        dup_rate         = self._duplicate_rate(df)
        delay_days       = self._avg_delay(df)
        critical_null    = self._critical_null_pct(df)
        injury_complete  = self._injury_completeness(df)
        staleness        = self._staleness_days(df)
        issues           = self._flag_issues(
            missing_pct, dup_rate, delay_days, critical_null, staleness
        )
        score            = self._quality_score(
            missing_pct, dup_rate, delay_days, critical_null, injury_complete
        )

        return CityDatasetStats(
            city=self.city,
            total_records=total,
            missing_fields_pct=round(missing_pct, 2),
            duplicate_rate=round(dup_rate, 4),
            avg_ingestion_delay_days=round(delay_days, 2),
            data_source_type=self.data_source_type,
            critical_fields_null_pct=round(critical_null, 2),
            injury_completeness_pct=round(injury_complete, 2),
            staleness_days=round(staleness, 1),
            quality_score=round(score, 1),
            flagged_issues=issues,
        )

    # ------------------------------------------------------------------
    # Individual metric helpers
    # ------------------------------------------------------------------

    def _missing_pct(self, df: pd.DataFrame) -> float:
        """Mean percentage of missing values per row, across all columns."""
        return float(df.isnull().mean(axis=1).mean() * 100)

    def _duplicate_rate(self, df: pd.DataFrame) -> float:
        """Fraction of rows that are exact duplicates (keep=False)."""
        subset = self.dedup_subset
        # Only use subset columns that exist in df
        if subset:
            subset = [c for c in subset if c in df.columns] or None
        dup_mask = df.duplicated(subset=subset, keep=False)
        return float(dup_mask.sum() / len(df))

    def _avg_delay(self, df: pd.DataFrame) -> float:
        """Mean days between crash_date and date_police_notified."""
        if (
            self.notified_date_col is None
            or self.crash_date_col not in df.columns
            or self.notified_date_col not in df.columns
        ):
            return 0.0

        crash_dt    = pd.to_datetime(df[self.crash_date_col],    errors="coerce", utc=True)
        notified_dt = pd.to_datetime(df[self.notified_date_col], errors="coerce", utc=True)
        delta = (notified_dt - crash_dt).dt.total_seconds() / 86400
        valid = delta.dropna()
        valid = valid[valid >= 0]   # ignore data-entry reversals
        return float(valid.mean()) if not valid.empty else 0.0

    def _critical_null_pct(self, df: pd.DataFrame) -> float:
        """Percentage of critical-field cells that are null."""
        present = [c for c in _CRITICAL_FIELDS if c in df.columns]
        if not present:
            return 100.0
        return float(df[present].isnull().mean(axis=1).mean() * 100)

    def _injury_completeness(self, df: pd.DataFrame) -> float:
        """% of rows where injuries_total is non-null."""
        col = "injuries_total"
        if col not in df.columns:
            return 0.0
        return float(df[col].notna().mean() * 100)

    def _staleness_days(self, df: pd.DataFrame) -> float:
        """Days since the most recent crash_date in the dataset."""
        if self.crash_date_col not in df.columns:
            return 0.0
        dates = pd.to_datetime(df[self.crash_date_col], errors="coerce", utc=True)
        latest = dates.max()
        if pd.isnull(latest):
            return 0.0
        now = datetime.now(tz=timezone.utc)
        return max(0.0, (now - latest).total_seconds() / 86400)

    @staticmethod
    def _flag_issues(
        missing_pct: float,
        dup_rate: float,
        delay_days: float,
        critical_null: float,
        staleness: float,
    ) -> List[str]:
        issues: List[str] = []
        if missing_pct > _WARN_MISSING_PCT:
            issues.append(f"High missing-field rate: {missing_pct:.1f}% of cells are null.")
        if dup_rate > _WARN_DUPLICATE_RATE:
            issues.append(f"Duplicate rate {dup_rate:.1%} exceeds {_WARN_DUPLICATE_RATE:.0%} threshold.")
        if delay_days > _WARN_DELAY_DAYS:
            issues.append(f"Avg ingestion delay {delay_days:.1f} days — data may lag real events.")
        if critical_null > _WARN_CRITICAL_NULL:
            issues.append(f"Critical fields (lat/lon/date/id) have {critical_null:.1f}% nulls.")
        if staleness > _WARN_STALENESS_DAYS:
            issues.append(f"Most recent record is {staleness:.0f} days old — feed may have stalled.")
        return issues

    @staticmethod
    def _quality_score(
        missing_pct: float,
        dup_rate: float,
        delay_days: float,
        critical_null: float,
        injury_complete: float,
    ) -> float:
        """
        Composite quality score 0–100.

        Weighted penalties:
          missing_pct      → up to -30 pts  (weight 0.30)
          critical_null    → up to -30 pts  (weight 0.30)
          dup_rate (0-1)   → up to -20 pts  (weight 0.20)
          delay days (/30) → up to -10 pts  (weight 0.10)
          injury_complete  → up to -10 pts  (weight 0.10)
        """
        score = 100.0
        score -= min(missing_pct, 100)       * 0.30
        score -= min(critical_null, 100)     * 0.30
        score -= min(dup_rate * 100, 100)    * 0.20
        score -= min(delay_days / 30, 1) * 100 * 0.10
        score -= (100 - min(injury_complete, 100)) * 0.10
        return max(0.0, score)


# ---------------------------------------------------------------------------
# Multi-city aggregation
# ---------------------------------------------------------------------------

@dataclass
class MultiCityStatsReport:
    """Aggregated quality stats across multiple cities."""
    stats: List[CityDatasetStats]

    def to_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame([s.as_dict() for s in self.stats])

    def ranked(self) -> List[CityDatasetStats]:
        """Return cities sorted by quality_score descending."""
        return sorted(self.stats, key=lambda s: s.quality_score, reverse=True)

    def summary(self) -> str:
        ranked = self.ranked()
        lines = [f"Multi-City Dataset Quality Report ({len(ranked)} cities)\n"]
        lines.append(f"{'City':<30} {'Source':<8} {'Records':>8} {'Score':>6} {'Issues':>6}")
        lines.append("-" * 65)
        for s in ranked:
            lines.append(
                f"{s.city:<30} {s.data_source_type:<8} {s.total_records:>8,} "
                f"{s.quality_score:>5.1f}  {len(s.flagged_issues):>5}"
            )
        return "\n".join(lines)
