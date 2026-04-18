from typing import Dict, Iterable, List


class RiskEngine:
    """Simple magnitude-based risk scoring for normalized records."""

    def score(self, record) -> Dict[str, object]:
        magnitude = self._safe_magnitude(record)
        score = self._score_from_magnitude(magnitude)

        return {
            "id": getattr(record, "record_id", None),
            "magnitude": magnitude,
            "risk_score": score,
            "risk_level": self._risk_level(score),
        }

    def score_many(self, records: Iterable[object]) -> List[Dict[str, object]]:
        return [self.score(record) for record in records]

    @staticmethod
    def _safe_magnitude(record) -> float:
        value = getattr(record, "magnitude", 0.0)
        if value is None:
            return 0.0

        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _score_from_magnitude(magnitude: float) -> int:
        # Map a typical earthquake magnitude range (0-10) to a 0-100 score.
        clamped = max(0.0, min(10.0, magnitude))
        return int(round((clamped / 10.0) * 100))

    @staticmethod
    def _risk_level(score: int) -> str:
        if score >= 80:
            return "critical"
        if score >= 60:
            return "high"
        if score >= 40:
            return "medium"
        return "low"
