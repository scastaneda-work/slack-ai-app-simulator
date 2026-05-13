"""Retry decorator for Slack API calls that hit `ratelimited`.

Slack signals rate limits with HTTP 429 + a `Retry-After` header. The slack_sdk
surfaces these as SlackApiError with response['error'] == 'ratelimited' and
the wait time on response.headers['Retry-After'] (seconds).

This decorator retries up to `attempts` times, sleeping for the server-provided
wait (clamped to a sane max). All other SlackApiErrors propagate.
"""
from __future__ import annotations

import functools
import time
from typing import Any, Callable, TypeVar

from slack_sdk.errors import SlackApiError

F = TypeVar("F", bound=Callable[..., Any])

DEFAULT_ATTEMPTS = 3
MAX_BACKOFF_SECONDS = 30
DEFAULT_BACKOFF_SECONDS = 1


def retry_on_rate_limit(
    attempts: int = DEFAULT_ATTEMPTS,
    sleep: Callable[[float], None] = time.sleep,
) -> Callable[[F], F]:
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            for attempt in range(1, attempts + 1):
                try:
                    return func(*args, **kwargs)
                except SlackApiError as e:
                    if e.response.get("error") != "ratelimited" or attempt == attempts:
                        raise
                    sleep(_retry_after_seconds(e))
            raise RuntimeError("retry_on_rate_limit exhausted without returning")  # pragma: no cover

        return wrapper  # type: ignore[return-value]

    return decorator


def _retry_after_seconds(error: SlackApiError) -> float:
    headers = getattr(error.response, "headers", {}) or {}
    raw = headers.get("Retry-After") or headers.get("retry-after")
    try:
        seconds = float(raw) if raw is not None else DEFAULT_BACKOFF_SECONDS
    except (TypeError, ValueError):
        seconds = DEFAULT_BACKOFF_SECONDS
    return min(max(seconds, 0), MAX_BACKOFF_SECONDS)
