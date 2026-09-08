"""Security primitives for the panel: response headers, CSRF, rate limiting and safe upload paths.

The server only ever binds to 127.0.0.1, but the browser is still a hostile environment: any page the
operator has open could try to POST to localhost. Every state-changing request therefore needs the
per-process CSRF token (delivered by GET /api/session, sent back in the X-OMS-CSRF header).
"""
from __future__ import annotations

import secrets
import threading
import time
from collections import deque
from pathlib import Path

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

CSRF_HEADER = "X-OMS-CSRF"
MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

# Clip uploads: 5 files of about 8 seconds each; 300 MB is far above any realistic 1080p clip.
UPLOAD_MAX_FILE_BYTES = 300 * 1024 * 1024
UPLOAD_MAX_TOTAL_BYTES = 1200 * 1024 * 1024
UPLOAD_SCENES = range(1, 6)

CONTENT_SECURITY_POLICY = (
    "default-src 'self'; img-src 'self' data: blob:; media-src 'self' blob:; style-src 'self'; "
    "script-src 'self'; connect-src 'self'; font-src 'self'; frame-ancestors 'none'; base-uri 'none'; "
    "form-action 'self'"
)

SECURITY_HEADERS = {
    "X-Frame-Options": "DENY",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "Content-Security-Policy": CONTENT_SECURITY_POLICY,
    "Cache-Control": "no-store",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}


def new_csrf_token() -> str:
    return secrets.token_urlsafe(32)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        for name, value in SECURITY_HEADERS.items():
            response.headers.setdefault(name, value)
        return response


class CsrfMiddleware(BaseHTTPMiddleware):
    """Reject every mutating /api request that does not carry the session token."""

    def __init__(self, app, token: str):
        super().__init__(app)
        self._token = token

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.method in MUTATING_METHODS and request.url.path.startswith("/api/"):
            sent = request.headers.get(CSRF_HEADER, "")
            if not sent or not secrets.compare_digest(sent, self._token):
                return JSONResponse({"error": "csrf", "message": "Token de sessão ausente ou inválido. Recarregue a página."},
                                    status_code=403)
        return await call_next(request)


class RateLimiter:
    """Fixed-window limiter keyed by an arbitrary string (endpoint name). Thread-safe."""

    def __init__(self, limit: int, per_seconds: float, clock=time.monotonic):
        self.limit, self.per_seconds, self._clock = limit, per_seconds, clock
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def check(self, key: str) -> bool:
        now = self._clock()
        with self._lock:
            window = self._hits.setdefault(key, deque())
            while window and now - window[0] >= self.per_seconds:
                window.popleft()
            if len(window) >= self.limit:
                return False
            window.append(now)
            return True


def safe_clip_path(inbox: Path, scene: int) -> Path:
    """Server-generated destination for an uploaded clip. Never derived from the client file name."""
    if scene not in UPLOAD_SCENES:
        raise ValueError("scene must be between 1 and 5")
    root = Path(inbox).resolve()
    if root.is_symlink():
        raise ValueError("inbox must not be a symlink")
    target = (root / f"segment_{scene:02d}.mp4").resolve()
    if target.parent != root:
        raise ValueError("clip path escaped the inbox")
    return target


def is_within(path: Path, root: Path) -> bool:
    try:
        Path(path).resolve().relative_to(Path(root).resolve())
        return True
    except ValueError:
        return False
