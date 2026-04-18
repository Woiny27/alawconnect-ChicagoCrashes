from risk.engine import RiskEngine
from risk.explainer import RiskExplainer

risk_engine = RiskEngine()
explainer = RiskExplainer(api_key="YOUR_KEY")


async def process(records):
    results = []

    for r in records:
        score = risk_engine.score(r)
        explanation = await explainer.explain(r, score)

        results.append(
            {
                "record": r,
                "risk_score": score,
                "explanation": explanation,
            }
        )

    return results
