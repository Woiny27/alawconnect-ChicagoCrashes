"""Tests for dataset_stats.py."""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

from src.utils.dataset_stats import (
    CityDatasetStats,
    DatasetStatsCollector,
    MultiCityStatsReport,
)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

def _now_iso(delta_days: int = 0) -> str:
    dt = datetime.now(tz=timezone.utc) - timedelta(days=delta_days)
    return dt.isoformat()


def _make_df(rows) -> pd.DataFrame:
    return pd.DataFrame(rows)


GOOD_ROWS = [
    {
        "crash_join_id":        f"ID{i:04d}",
        "crash_date":           _now_iso(i),
        "date_police_notified": _now_iso(i - 1),   # notified 1 day before crash (data quirk)
        "latitude":             41.85 + i * 0.001,
        "longitude":            -87.65 - i * 0.001,
        "injuries_total":       i % 3,
    }
    for i in range(1, 21)
]

SPARSE_ROWS = [
    {
        "crash_join_id": f"S{i:03d}",
        "crash_date":    _now_iso(i),
        "latitude":      None,
        "longitude":     None,
        "injuries_total": None,
    }
    for i in range(1, 6)
]


# ---------------------------------------------------------------------------
# CityDatasetStats — dataclass contract
# ---------------------------------------------------------------------------

class TestCityDatasetStats:
    def test_as_dict_has_all_fields(self):
        s = CityDatasetStats(
            city="Chicago", total_records=100,
            missing_fields_pct=5.0, duplicate_rate=0.01,
            avg_ingestion_delay_days=2.0, data_source_type="api",
        )
        d = s.as_dict()
        assert d["city"] == "Chicago"
        assert "quality_score" in d
        assert "flagged_issues" in d

    def test_summary_contains_city_name(self):
        s = CityDatasetStats(
            city="Detroit", total_records=50,
            missing_fields_pct=10.0, duplicate_rate=0.0,
            avg_ingestion_delay_days=0.5, data_source_type="api",
        )
        assert "Detroit" in s.summary()

    def test_summary_lists_issues(self):
        s = CityDatasetStats(
            city="X", total_records=10,
            missing_fields_pct=5.0, duplicate_rate=0.0,
            avg_ingestion_delay_days=1.0, data_source_type="portal",
            flagged_issues=["High missing-field rate: 55.0%"],
        )
        assert "High missing-field rate" in s.summary()


# ---------------------------------------------------------------------------
# DatasetStatsCollector — empty DataFrame
# ---------------------------------------------------------------------------

class TestCollectorEmpty:
    def test_empty_df_returns_zero_records(self):
        stats = DatasetStatsCollector("Chicago").collect(pd.DataFrame())
        assert stats.total_records == 0

    def test_empty_df_has_issue(self):
        stats = DatasetStatsCollector("Chicago").collect(pd.DataFrame())
        assert any("empty" in i.lower() for i in stats.flagged_issues)

    def test_empty_df_quality_score_zero(self):
        stats = DatasetStatsCollector("Chicago").collect(pd.DataFrame())
        assert stats.quality_score == 0.0


# ---------------------------------------------------------------------------
# DatasetStatsCollector — healthy data
# ---------------------------------------------------------------------------

class TestCollectorGoodData:
    def setup_method(self):
        self.df = _make_df(GOOD_ROWS)
        self.stats = DatasetStatsCollector("Chicago", data_source_type="api").collect(self.df)

    def test_total_records(self):
        assert self.stats.total_records == 20

    def test_data_source_type(self):
        assert self.stats.data_source_type == "api"

    def test_missing_pct_is_low(self):
        # All critical fields populated → missing should be low
        assert self.stats.missing_fields_pct < 30

    def test_duplicate_rate_zero(self):
        assert self.stats.duplicate_rate == 0.0

    def test_quality_score_in_range(self):
        assert 0 <= self.stats.quality_score <= 100

    def test_injury_completeness_100(self):
        assert self.stats.injury_completeness_pct == 100.0

    def test_staleness_under_25_days(self):
        # Oldest row is 20 days ago; staleness = days since newest (1 day ago)
        assert self.stats.staleness_days < 5


# ---------------------------------------------------------------------------
# DatasetStatsCollector — sparse / bad data
# ---------------------------------------------------------------------------

class TestCollectorSparseData:
    def setup_method(self):
        self.df = _make_df(SPARSE_ROWS)
        self.stats = DatasetStatsCollector("St. Louis", data_source_type="portal").collect(self.df)

    def test_missing_pct_is_high(self):
        assert self.stats.missing_fields_pct > 20

    def test_critical_null_pct_is_high(self):
        # lat + lon are missing
        assert self.stats.critical_fields_null_pct > 20

    def test_injury_completeness_zero(self):
        assert self.stats.injury_completeness_pct == 0.0

    def test_flagged_missing_issue(self):
        assert any("missing" in i.lower() for i in self.stats.flagged_issues)

    def test_quality_score_lower_than_good(self):
        good = DatasetStatsCollector("Chicago").collect(_make_df(GOOD_ROWS))
        assert self.stats.quality_score < good.quality_score


# ---------------------------------------------------------------------------
# DatasetStatsCollector — duplicate detection
# ---------------------------------------------------------------------------

class TestDuplicateDetection:
    def test_duplicate_rate_detected(self):
        row = {"crash_join_id": "DUP001", "crash_date": _now_iso(1), "latitude": 41.85,
               "longitude": -87.65, "injuries_total": 0}
        df = _make_df([row, row, row])
        stats = DatasetStatsCollector("Chicago").collect(df)
        assert stats.duplicate_rate == 1.0

    def test_no_duplicates_rates_zero(self):
        rows = [{"crash_join_id": f"U{i}", "crash_date": _now_iso(i),
                 "latitude": 41.0 + i, "longitude": -87.0 + i, "injuries_total": 0}
                for i in range(5)]
        stats = DatasetStatsCollector("Chicago").collect(_make_df(rows))
        assert stats.duplicate_rate == 0.0


# ---------------------------------------------------------------------------
# DatasetStatsCollector — ingestion delay
# ---------------------------------------------------------------------------

class TestIngestionDelay:
    def test_zero_delay_when_notified_matches_crash(self):
        rows = [{"crash_join_id": f"X{i}", "crash_date": _now_iso(5),
                 "date_police_notified": _now_iso(5),
                 "latitude": 41.0, "longitude": -87.0, "injuries_total": 0}
                for i in range(3)]
        stats = DatasetStatsCollector("Chicago").collect(_make_df(rows))
        assert stats.avg_ingestion_delay_days == pytest.approx(0.0, abs=0.1)

    def test_delay_computed_correctly(self):
        # crash_date 10 days ago, notified_date 8 days ago → delay ~2 days
        rows = [{"crash_join_id": f"D{i}", "crash_date": _now_iso(10),
                 "date_police_notified": _now_iso(8),
                 "latitude": 41.0, "longitude": -87.0, "injuries_total": 0}
                for i in range(4)]
        stats = DatasetStatsCollector("Chicago").collect(_make_df(rows))
        assert stats.avg_ingestion_delay_days == pytest.approx(2.0, abs=0.1)

    def test_no_notified_col_returns_zero(self):
        rows = [{"crash_join_id": "A1", "crash_date": _now_iso(1),
                 "latitude": 41.0, "longitude": -87.0}]
        stats = DatasetStatsCollector("Chicago", notified_date_col=None).collect(_make_df(rows))
        assert stats.avg_ingestion_delay_days == 0.0


# ---------------------------------------------------------------------------
# Quality score monotonicity
# ---------------------------------------------------------------------------

class TestQualityScore:
    def test_perfect_data_scores_near_100(self):
        rows = [{"crash_join_id": f"P{i}", "crash_date": _now_iso(1),
                 "date_police_notified": _now_iso(1),
                 "latitude": 41.0, "longitude": -87.0, "injuries_total": 0}
                for i in range(10)]
        stats = DatasetStatsCollector("Chicago").collect(_make_df(rows))
        assert stats.quality_score >= 85

    def test_more_missing_lowers_score(self):
        full_rows = [{"crash_join_id": f"F{i}", "crash_date": _now_iso(1),
                      "latitude": 41.0, "longitude": -87.0, "injuries_total": 0}
                     for i in range(10)]
        sparse_rows = [{"crash_join_id": f"S{i}", "crash_date": _now_iso(1)}
                       for i in range(10)]
        full_stats   = DatasetStatsCollector("A").collect(_make_df(full_rows))
        sparse_stats = DatasetStatsCollector("B").collect(_make_df(sparse_rows))
        assert full_stats.quality_score > sparse_stats.quality_score


# ---------------------------------------------------------------------------
# MultiCityStatsReport
# ---------------------------------------------------------------------------

class TestMultiCityReport:
    def _make_stats(self, city, score):
        s = CityDatasetStats(city=city, total_records=100,
                             missing_fields_pct=5.0, duplicate_rate=0.0,
                             avg_ingestion_delay_days=1.0, data_source_type="api")
        s.quality_score = score
        return s

    def test_ranked_sorts_descending(self):
        report = MultiCityStatsReport([
            self._make_stats("C", 60),
            self._make_stats("A", 90),
            self._make_stats("B", 75),
        ])
        scores = [s.quality_score for s in report.ranked()]
        assert scores == [90, 75, 60]

    def test_to_dataframe_has_correct_columns(self):
        report = MultiCityStatsReport([self._make_stats("Chicago", 80)])
        df = report.to_dataframe()
        assert "city" in df.columns
        assert "quality_score" in df.columns
        assert "data_source_type" in df.columns

    def test_summary_lists_all_cities(self):
        report = MultiCityStatsReport([
            self._make_stats("Chicago", 80),
            self._make_stats("Detroit", 65),
        ])
        summary = report.summary()
        assert "Chicago" in summary
        assert "Detroit" in summary
