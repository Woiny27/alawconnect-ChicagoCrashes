from fastapi import APIRouter
from core.registry import PluginRegistry
from core.pipeline import Pipeline
from storage.sqlite import SQLiteStorage
from api.schemas import (
    USGSEarthquakeAnalysisRequest,
    RiskAnalysisResponse,
    RiskScoreResponse,
)
from risk.engine import RiskEngine
from risk.explainer import RiskExplainer

router = APIRouter()

registry = PluginRegistry()
registry.load_plugins()

risk_engine = RiskEngine()
risk_explainer = RiskExplainer()


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/providers")
def list_providers():
    return list(registry.providers.keys())


@router.post("/run/{provider_name}")
async def run_pipeline(provider_name: str):
    if provider_name not in registry.providers:
        return {"error": "provider not found"}

    provider = registry.providers[provider_name]
    storage = SQLiteStorage()

    pipeline = Pipeline(provider, storage)
    count = await pipeline.run()

    return {
        "provider": provider_name,
        "processed_records": count
    }


@router.post("/risk/analyze/usgs", response_model=RiskAnalysisResponse)
async def analyze_usgs_earthquake(request: USGSEarthquakeAnalysisRequest):
    """Analyze USGS earthquake data for risk and provide explanation."""
    
    # Create a simple record object to work with the risk engine
    class Record:
        def __init__(self, record_id: str, magnitude: float):
            self.record_id = record_id
            self.magnitude = magnitude
    
    record = Record(request.record_id, request.magnitude)
    
    # Score the earthquake
    score = risk_engine.score(record)
    
    # Generate explanation
    explanation = await risk_explainer.explain(record, score)
    
    # Format response
    risk_score = RiskScoreResponse(
        id=score["id"],
        magnitude=score["magnitude"],
        risk_score=score["risk_score"],
        risk_level=score["risk_level"]
    )
    
    return RiskAnalysisResponse(
        record_id=request.record_id,
        risk_score=risk_score,
        explanation=explanation
    )