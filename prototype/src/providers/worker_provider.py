import os
from itertools import cycle
from typing import Any, Dict, Iterable, Optional

import requests

from src.utils.limiter import TokenBucketLimiter


DEFAULT_USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"


class WorkerProvider:
    """HTTP worker that rotates user-agents/proxies to reduce rate limiting."""

    def __init__(
        self,
        *,
        user_agents: Optional[Iterable[str]] = None,
        proxies: Optional[Iterable[str]] = None,
        session: Optional[requests.sessions.Session] = None,
        max_attempts: int = 3,
        limiter: Optional[TokenBucketLimiter] = None,
    ) -> None:
        ua_values = [value.strip() for value in (user_agents or []) if value.strip()]
        proxy_values = [value.strip() for value in (proxies or []) if value.strip()]

        if not ua_values:
            ua_values = [DEFAULT_USER_AGENT]

        self._ua_cycle = cycle(ua_values)
        self._proxy_cycle = cycle(proxy_values) if proxy_values else None
        self.session = session or requests.Session()
        self.max_attempts = max(1, max_attempts)
        self.limiter = limiter or TokenBucketLimiter(
            capacity=float(os.getenv("WORKER_RATE_LIMIT_CAPACITY", "10")),
            refill_rate=float(os.getenv("WORKER_RATE_LIMIT_TOKENS_PER_SECOND", "2")),
        )

    @classmethod
    def from_env(cls) -> "WorkerProvider":
        user_agents = os.getenv("WORKER_USER_AGENTS", "")
        proxies = os.getenv("WORKER_PROXIES", "")

        return cls(
            user_agents=user_agents.split(",") if user_agents else None,
            proxies=proxies.split(",") if proxies else None,
            max_attempts=int(os.getenv("WORKER_MAX_ATTEMPTS", "3")),
            limiter=TokenBucketLimiter(
                capacity=float(os.getenv("WORKER_RATE_LIMIT_CAPACITY", "10")),
                refill_rate=float(os.getenv("WORKER_RATE_LIMIT_TOKENS_PER_SECOND", "2")),
            ),
        )

    def _next_proxy(self) -> Optional[Dict[str, str]]:
        if self._proxy_cycle is None:
            return None
        proxy = next(self._proxy_cycle)
        return {"http": proxy, "https": proxy}

    def _build_headers(self, headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        output = dict(headers or {})
        output["User-Agent"] = next(self._ua_cycle)
        return output

    def get(self, url: str, **kwargs: Any) -> requests.Response:
        """GET with rotating identity; retries automatically on HTTP 429."""
        response: Optional[requests.Response] = None
        for _ in range(self.max_attempts):
            self.limiter.acquire()
            headers = self._build_headers(kwargs.get("headers"))
            request_kwargs = dict(kwargs)
            request_kwargs["headers"] = headers

            proxy = self._next_proxy()
            if proxy is not None:
                request_kwargs["proxies"] = proxy

            response = self.session.get(url, **request_kwargs)
            if response.status_code != 429:
                return response

        assert response is not None
        return response