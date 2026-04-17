import asyncio
from core.registry import PluginRegistry
from core.pipeline import Pipeline
from storage.sqlite import SQLiteStorage

async def main():
    registry = PluginRegistry()
    registry.load_plugins()

    provider = registry.providers["usgs"]
    storage = SQLiteStorage()

    pipeline = Pipeline(provider, storage)
    count = await pipeline.run()

    print(f"Processed {count} records")

if __name__ == "__main__":
    asyncio.run(main())