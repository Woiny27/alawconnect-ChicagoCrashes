from fastapi import APIRouter
from core.registry import PluginRegistry
from core.pipeline import Pipeline
from storage.sqlite import SQLiteStorage

router = APIRouter()

registry = PluginRegistry()
registry.load_plugins()

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