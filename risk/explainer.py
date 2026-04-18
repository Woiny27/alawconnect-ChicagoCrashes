from typing import Dict


class RiskExplainer:
    """Generate human-readable explanations for risk scores."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key

    async def explain(self, record, score: Dict[str, object]) -> str:
        score_value = self._safe_int(score.get("risk_score", 0))
        level = str(score.get("risk_level", "low"))
        magnitude = self._safe_float(score.get("magnitude", getattr(record, "magnitude", 0.0)))

        return self._build_explanation(level, score_value, magnitude)

    @staticmethod
    def _safe_int(value) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _safe_float(value) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _build_explanation(level: str, score: int, magnitude: float) -> str:
        base = (
            f"Risk level is {level} with score {score}/100 based on "
            f"earthquake magnitude {magnitude:.1f}."
        )

        if level == "critical":
            return base + " Immediate monitoring and response planning are recommended."
        if level == "high":
            return base + " Elevated preparedness and active monitoring are recommended."
        if level == "medium":
            return base + " Continue routine monitoring and review trends regularly."
        return base + " Current impact appears limited, maintain baseline monitoring."
