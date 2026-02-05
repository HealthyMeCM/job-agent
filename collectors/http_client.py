"""HTTP client wrapper with rate limiting and retries."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)


@dataclass
class FetchResult:
    """Result of an HTTP fetch."""

    url: str
    status_code: int
    content: bytes
    headers: dict[str, str]
    content_type: str | None
    duration_ms: float
    success: bool
    error: str | None = None
    retry_count: int = 0


@dataclass
class RateLimiter:
    """Simple rate limiter using token bucket."""

    rate: float  # requests per second
    _last_request: float = field(default=0.0, init=False)

    async def acquire(self) -> None:
        """Wait if needed to respect rate limit."""
        if self.rate <= 0:
            return

        min_interval = 1.0 / self.rate
        now = time.monotonic()
        elapsed = now - self._last_request

        if elapsed < min_interval:
            await asyncio.sleep(min_interval - elapsed)

        self._last_request = time.monotonic()


class HttpClient:
    """HTTP client with rate limiting and retry support."""

    def __init__(
        self,
        timeout: int = 30,
        rate_limit: float = 1.0,
        max_retries: int = 3,
        user_agent: str | None = None,
    ):
        self.timeout = timeout
        self.max_retries = max_retries
        self.rate_limiter = RateLimiter(rate=rate_limit)
        self.user_agent = user_agent or "JobAgent/1.0 (Lead Discovery Bot)"

        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> HttpClient:
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout),
            headers={"User-Agent": self.user_agent},
            follow_redirects=True,
        )
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    async def fetch(self, url: str) -> FetchResult:
        """Fetch a URL with rate limiting and retries."""
        await self.rate_limiter.acquire()

        start_time = time.monotonic()
        retry_count = 0

        try:
            result = await self._fetch_with_retry(url)
            duration_ms = (time.monotonic() - start_time) * 1000

            return FetchResult(
                url=url,
                status_code=result.status_code,
                content=result.content,
                headers=dict(result.headers),
                content_type=result.headers.get("content-type"),
                duration_ms=duration_ms,
                success=result.is_success,
                retry_count=retry_count,
            )

        except Exception as e:
            duration_ms = (time.monotonic() - start_time) * 1000
            return FetchResult(
                url=url,
                status_code=0,
                content=b"",
                headers={},
                content_type=None,
                duration_ms=duration_ms,
                success=False,
                error=str(e),
                retry_count=retry_count,
            )

    async def _fetch_with_retry(self, url: str) -> httpx.Response:
        """Internal fetch with retry logic."""
        if not self._client:
            raise RuntimeError("Client not initialized. Use 'async with' context.")

        @retry(
            stop=stop_after_attempt(self.max_retries),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        )
        async def _do_fetch() -> httpx.Response:
            return await self._client.get(url)  # type: ignore

        return await _do_fetch()
