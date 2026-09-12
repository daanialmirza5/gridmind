"""Minimal in-memory sliding-window rate limiter for sensitive endpoints (login, AI
analyze). Adequate for a single-process demo deployment; a production deployment behind
multiple workers would move this to Redis, which is called out in docs/model_cards.md."""

import time
from collections import defaultdict, deque

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

RATE_LIMITS = {
    "/api/auth/login": (10, 60),  # 10 requests / 60s per IP
    "/api/ai/analyze": (20, 60),
}

_hits: dict[str, deque] = defaultdict(deque)


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        limit_config = RATE_LIMITS.get(request.url.path)
        if limit_config:
            max_requests, window_seconds = limit_config
            key = f"{request.url.path}:{request.client.host if request.client else 'unknown'}"
            now = time.time()
            hits = _hits[key]
            while hits and now - hits[0] > window_seconds:
                hits.popleft()
            if len(hits) >= max_requests:
                return JSONResponse(
                    status_code=429,
                    content={"error": {"code": "RATE_LIMITED", "message": "Rate limit exceeded, please slow down"}},
                )
            hits.append(now)
        return await call_next(request)
