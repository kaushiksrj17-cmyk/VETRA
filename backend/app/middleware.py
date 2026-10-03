import time
import uuid
from typing import Dict, List, Tuple
from collections import defaultdict
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.config import settings
from app.logging_config import logger


class InMemoryRateLimiter:
    """
    In-memory sliding window rate limiter designed for single-process deployments
    and lightweight API defense against brute-force and resource exhaustion.
    """

    def __init__(self):
        # Maps (client_ip, category) -> list of timestamp floats
        self._history: Dict[Tuple[str, str], List[float]] = defaultdict(list)
        self._last_cleanup = time.time()

    def _cleanup_old_entries(self, now: float):
        if now - self._last_cleanup > 300:  # Cleanup every 5 minutes
            cutoff = now - 3600
            empty_keys = []
            for key, timestamps in self._history.items():
                self._history[key] = [t for t in timestamps if t > cutoff]
                if not self._history[key]:
                    empty_keys.append(key)
            for k in empty_keys:
                del self._history[k]
            self._last_cleanup = now

    def is_rate_limited(self, client_ip: str, path: str, method: str) -> Tuple[bool, int]:
        """
        Check if the request exceeds configured thresholds.
        Returns:
            (is_limited: bool, retry_after_seconds: int)
        """
        if not settings.RATE_LIMIT_ENABLED:
            return False, 0

        now = time.time()
        self._cleanup_old_entries(now)

        # Classify route category and limit thresholds
        category = "general"
        limit = settings.RATE_LIMIT_REQUESTS
        window = settings.RATE_LIMIT_WINDOW_SECONDS

        if path.startswith("/auth/login") and method == "POST":
            category = "auth_login"
            limit = 10
            window = 60
        elif path.startswith("/auth/register") and method == "POST":
            category = "auth_register"
            limit = 5
            window = 60
        elif "/government-packages" in path and method == "POST":
            category = "gov_packages"
            limit = 20
            window = 60
        elif "/visual-health/analyze" in path and method == "POST":
            category = "media_analyze"
            limit = 30
            window = 60

        key = (client_ip, category)
        cutoff = now - window
        timestamps = [t for t in self._history[key] if t > cutoff]

        if len(timestamps) >= limit:
            oldest = timestamps[0]
            retry_after = max(1, int(window - (now - oldest)))
            return True, retry_after

        timestamps.append(now)
        self._history[key] = timestamps
        return False, 0


rate_limiter = InMemoryRateLimiter()


class SecurityAndObservabilityMiddleware(BaseHTTPMiddleware):
    """
    Production-grade middleware managing:
    - Request ID assignment & propagation
    - Request payload size protection
    - Rate limiting checks
    - Security headers injection
    - Structured request logging
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.perf_counter()

        # 1. Request ID assignment
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id

        # Extract real client IP (supporting reverse proxies)
        client_ip = request.headers.get("X-Forwarded-For")
        if client_ip:
            client_ip = client_ip.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "127.0.0.1"

        path = request.url.path
        method = request.method

        # 2. Payload size check
        content_length = request.headers.get("Content-Length")
        if content_length:
            try:
                length_int = int(content_length)
                max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
                if length_int > max_bytes:
                    return JSONResponse(
                        status_code=413,
                        content={
                            "error": f"Payload exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_MB} MB.",
                            "request_id": request_id
                        },
                        headers={"X-Request-ID": request_id}
                    )
            except ValueError:
                pass

        # 3. Rate limiting check
        is_limited, retry_after = rate_limiter.is_rate_limited(client_ip, path, method)
        if is_limited:
            logger.warning(
                f"Rate limit exceeded for IP: {client_ip} on path {method} {path}",
                extra={"request_id": request_id, "client_ip": client_ip, "path": path, "method": method}
            )
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Too many requests. Please try again later.",
                    "retry_after": retry_after,
                    "request_id": request_id
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-Request-ID": request_id
                }
            )

        # 4. Process Request
        try:
            response = await call_next(request)
        except Exception as exc:
            # Let global exception handler catch or handle unhandled errors safely
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.error(
                f"Unhandled error processing {method} {path}: {str(exc)}",
                extra={"request_id": request_id, "client_ip": client_ip, "path": path, "method": method, "duration_ms": duration_ms}
            )
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal server error",
                    "request_id": request_id
                },
                headers={"X-Request-ID": request_id}
            )

        # 5. Attach Request ID
        response.headers["X-Request-ID"] = request_id

        # 6. Inject Security Headers
        if settings.SECURITY_HEADERS_ENABLED:
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "SAMEORIGIN"
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
            response.headers["Permissions-Policy"] = "geolocation=(), camera=(self), microphone=()"
            response.headers["X-XSS-Protection"] = "1; mode=block"

            # Enable HSTS when running in production or over HTTPS
            if settings.APP_ENV == "production" or request.url.scheme == "https":
                response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        # 7. Structured Access Log
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        logger.info(
            f"{method} {path} {response.status_code} ({duration_ms}ms)",
            extra={
                "request_id": request_id,
                "method": method,
                "path": path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
                "client_ip": client_ip
            }
        )

        return response
