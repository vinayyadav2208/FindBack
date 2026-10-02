"""Security middleware (MASTER_README §40, §62).

* RateLimitMiddleware   - sliding-window request limits per client IP, with a
                          stricter bucket for authentication endpoints.
* SecurityHeadersMiddleware - standard hardening headers on every response.

Both are no-ops when RATE_LIMIT_ENABLED=false (used by the test suite).
The limiter keeps no external state: restarting the server clears counters.
"""

from __future__ import annotations

import logging
import time
from collections import deque

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response
from starlette.types import ASGIApp

from app.config import settings

logger = logging.getLogger("findback.security")

# Endpoints an attacker would hammer for credential stuffing / brute force.
AUTH_PATHS = {"/login", "/auth/login", "/users", "/auth/register"}
EXEMPT_PREFIXES = ("/media",)


class SlidingWindowRateLimiter:
    """In-memory sliding window: `limit` events allowed per `window` seconds.

    Pure logic (no FastAPI types) so it can be unit-tested directly.
    """

    def __init__(self, window_seconds: float) -> None:
        self.window = float(window_seconds)
        self._hits: dict[str, deque[float]] = {}
        self._ops = 0

    def check(self, key: str, limit: int) -> tuple[bool, int]:
        """Consume one slot. Returns (allowed, retry_after_seconds)."""
        if limit <= 0:
            return True, 0
        now = time.monotonic()
        hits = self._hits.setdefault(key, deque())
        while hits and now - hits[0] >= self.window:
            hits.popleft()

        if len(hits) >= limit:
            retry_after = int(self.window - (now - hits[0])) + 1
            return False, max(1, retry_after)

        hits.append(now)
        self._ops += 1
        if self._ops % 500 == 0:
            self._purge(now)
        return True, 0

    def _purge(self, now: float) -> None:
        stale = [
            key
            for key, hits in self._hits.items()
            if not hits or now - hits[-1] >= self.window
        ]
        for key in stale:
            del self._hits[key]

    def reset(self) -> None:
        self._hits.clear()


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
        self._limiter = SlidingWindowRateLimiter(settings.RATE_LIMIT_WINDOW_SECONDS)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if not settings.RATE_LIMIT_ENABLED or request.method == "OPTIONS":
            return await call_next(request)

        path = request.url.path
        if path.startswith(EXEMPT_PREFIXES):
            return await call_next(request)

        is_auth = path in AUTH_PATHS
        limit = (
            settings.RATE_LIMIT_AUTH_PER_MINUTE
            if is_auth
            else settings.RATE_LIMIT_PER_MINUTE
        )
        ip = request.client.host if request.client else "unknown"
        bucket = f"{'auth' if is_auth else 'api'}:{ip}"

        allowed, retry_after = self._limiter.check(bucket, limit)
        if not allowed:
            logger.warning(
                "Rate limit exceeded for %s (%s %s) - retry in %ss",
                bucket, request.method, path, retry_after,
            )
            return JSONResponse(
                status_code=429,
                content={
                    "detail": (
                        "Too many requests. Please wait a moment and try again."
                        if is_auth
                        else "Too many requests. Please slow down."
                    )
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(limit),
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("Cross-Origin-Resource-Policy", "same-site")
        return response
