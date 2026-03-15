"""Request middleware for rate limiting, body size enforcement, and access logging."""

from __future__ import annotations

import hashlib
import json
import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from config import (
    MAX_BODY_BYTES,
    RATE_LIMIT_READ_RPM,
    RATE_LIMIT_REGISTER_RPH,
    RATE_LIMIT_WRITE_RPM,
)

logger = logging.getLogger("nexus.access")


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _classify_request(method: str, path: str) -> tuple[str, int, int]:
    """Return (category, limit, window_seconds) for rate limiting."""
    if method == "POST" and path.rstrip("/") == "/institutes":
        return "register", RATE_LIMIT_REGISTER_RPH, 3600
    if method == "POST":
        return "write", RATE_LIMIT_WRITE_RPM, 60
    return "read", RATE_LIMIT_READ_RPM, 60


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Fixed-window IP-based rate limiter with per-category limits."""

    def __init__(self, app):
        super().__init__(app)
        self._buckets: dict[tuple[str, str], tuple[int, float]] = {}
        self._last_cleanup = 0.0

    def _cleanup(self, now: float) -> None:
        if now - self._last_cleanup < 120:
            return
        self._last_cleanup = now
        self._buckets = {
            k: v for k, v in self._buckets.items() if now - v[1] < 7200
        }

    async def dispatch(self, request: Request, call_next):
        if request.scope.get("type") != "http":
            return await call_next(request)

        now = time.monotonic()
        self._cleanup(now)

        ip = _client_ip(request)
        category, limit, window = _classify_request(
            request.method, request.url.path
        )

        key = (ip, category)
        count, window_start = self._buckets.get(key, (0, now))

        if now - window_start >= window:
            count = 0
            window_start = now

        count += 1
        self._buckets[key] = (count, window_start)

        if count > limit:
            retry_after = int(window - (now - window_start)) + 1
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded"},
                headers={"Retry-After": str(retry_after)},
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(max(0, limit - count))
        return response


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject requests whose Content-Length exceeds the configured cap."""

    async def dispatch(self, request: Request, call_next):
        cl = request.headers.get("content-length")
        if cl and int(cl) > MAX_BODY_BYTES:
            return JSONResponse(
                status_code=413,
                content={
                    "detail": f"Request body too large (max {MAX_BODY_BYTES} bytes)"
                },
            )
        return await call_next(request)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Structured JSON access log emitted after each request."""

    async def dispatch(self, request: Request, call_next):
        start = time.monotonic()
        response = await call_next(request)
        elapsed_ms = round((time.monotonic() - start) * 1000, 1)

        ip = _client_ip(request)
        ip_hash = hashlib.sha256(ip.encode()).hexdigest()[:12]

        logger.info(
            json.dumps(
                {
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "latency_ms": elapsed_ms,
                    "ip_hash": ip_hash,
                    "content_length": request.headers.get("content-length", "0"),
                }
            )
        )
        return response
