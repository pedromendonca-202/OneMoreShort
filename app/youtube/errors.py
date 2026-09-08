"""Translate googleapiclient HttpError into the platform's retryable / non-retryable error types."""
from __future__ import annotations

import json
from typing import Any

from app.core.errors import ExternalAPIError, RateLimited

_QUOTA_REASONS = {"quotaExceeded", "rateLimitExceeded", "userRateLimitExceeded", "dailyLimitExceeded"}


def _reasons(err: Any) -> set[str]:
    content = getattr(err, "content", b"") or b""
    try:
        data = json.loads(content.decode("utf-8") if isinstance(content, bytes) else content)
    except (ValueError, AttributeError):
        return set()
    errors = (data.get("error") or {}).get("errors") or []
    return {str(item.get("reason")) for item in errors if isinstance(item, dict)}


def map_http_error(api: str, err: Exception) -> ExternalAPIError:
    resp = getattr(err, "resp", None)
    status = int(getattr(resp, "status", 0) or 0)
    reasons = _reasons(err)
    message = f"HTTP {status}: {', '.join(sorted(reasons)) or str(err)[:200]}"
    if status == 429 or reasons & _QUOTA_REASONS:
        return RateLimited(api, message)
    if status >= 500:
        return ExternalAPIError(api, message, retryable=True)
    return ExternalAPIError(api, message, retryable=False)
