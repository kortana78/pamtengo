"""Simple in-memory fixed-window rate limiter (single process, dev grade).

Production plan: replace with Redis-backed token bucket (e.g. slowapi +
redis or an ingress rule) so limits are shared across replicas. Documented in
docs/threat-model.md.
"""

import time
from collections import defaultdict

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings

_hits: dict[str, list[float]] = defaultdict(list)


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in ("/health", "/openapi.json", "/docs", "/redoc"):
            return await call_next(request)
        limit = settings.rate_limit_per_minute
        key = request.client.host if request.client else "unknown"
        now = time.monotonic()
        window = [t for t in _hits[key] if now - t < 60]
        window.append(now)
        _hits[key] = window
        if len(window) > limit:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Try again shortly."},
            )
        return await call_next(request)


def reset_rate_limiter() -> None:
    _hits.clear()
