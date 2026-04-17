import asyncio
import random

def retry(times=3, delay=1):
    def wrapper(func):
        async def inner(*args, **kwargs):
            for i in range(times):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if i == times - 1:
                        raise
                    await asyncio.sleep(delay * (2 ** i) + random.uniform(0, 0.2))
        return inner
    return wrapper