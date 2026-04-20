import asyncio


class WorkerProvider:
    """
    Wraps a synchronous provider and exposes an async fetch() interface.

    Runs the underlying provider's synchronous fetch() in a thread pool via
    asyncio.to_thread, allowing legacy sync providers to integrate with the
    async pipeline without blocking the event loop.
    """

    def __init__(self, provider):
        self._provider = provider

    async def fetch(self):
        return await asyncio.to_thread(self._provider.fetch)
