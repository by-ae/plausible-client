"""Retry logic with exponential backoff."""

import asyncio
import math
import time
from collections.abc import Callable
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any

import httpx

from plausible_client.errors import RateLimitError, ServerError, message_from_payload


def should_retry(response: httpx.Response) -> bool:
    """Check if a response should be retried."""
    return response.status_code == 429 or 500 <= response.status_code < 600


def should_retry_exception(exc: Exception) -> bool:
    """
    Check if an exception should be retried.

    Timeouts are NOT retried as they indicate the server is too slow,
    not temporarily unavailable. Connection errors and other network
    issues are retried.
    """
    return not isinstance(exc, httpx.TimeoutException)


def _parse_retry_after_seconds(value: str) -> float | None:
    """Parse a Retry-After header into seconds.

    RFC 9110 allows either a non-negative delay in seconds or an HTTP-date.
    Unparseable values return None so the caller can fall back to backoff.
    """
    try:
        seconds = float(value)
    except ValueError:
        seconds = None

    if seconds is not None:
        if not math.isfinite(seconds):
            return None
        return seconds

    try:
        retry_at = parsedate_to_datetime(value)
    except (TypeError, ValueError, IndexError, OverflowError):
        return None
    if retry_at is None:
        return None
    if retry_at.tzinfo is None:
        retry_at = retry_at.replace(tzinfo=timezone.utc)
    return (retry_at - datetime.now(timezone.utc)).total_seconds()


def _normalize_retry_after(seconds: float) -> int | float:
    """Keep whole-second delays as ints so callers can compare with ``== 60``."""
    if seconds.is_integer():
        return int(seconds)
    return seconds


def parsed_retry_after(response: httpx.Response) -> int | float | None:
    """Return the Retry-After delay in seconds, or None if it cannot be used."""
    if response.status_code != 429:
        return None
    header = response.headers.get("Retry-After")
    if header is None:
        return None
    parsed = _parse_retry_after_seconds(header.strip())
    if parsed is None:
        return None
    return _normalize_retry_after(max(0.0, parsed))


def get_retry_after(response: httpx.Response, attempt: int) -> float:
    """Get the retry delay in seconds.

    A usable ``Retry-After`` value (delay-seconds or HTTP-date) is honoured.
    Anything else falls back to exponential backoff capped at 60 seconds.
    """
    parsed = parsed_retry_after(response)
    if parsed is not None:
        return float(parsed)
    return float(min(2**attempt, 60))


def _rate_limit_message(response: httpx.Response) -> str:
    """Use the API error string when the 429 body includes one."""
    default = "Rate limit exceeded"
    try:
        payload = response.json()
    except Exception:
        return default
    return message_from_payload(payload, default)


def retry_sync(
    func: Callable[..., httpx.Response], *args: Any, max_retries: int = 3, **kwargs: Any
) -> httpx.Response:
    """Execute a sync function with retry logic."""
    last_exception: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            response = func(*args, **kwargs)

            if not should_retry(response):
                return response

            if attempt < max_retries:
                delay = get_retry_after(response, attempt)
                time.sleep(delay)
            else:
                if response.status_code == 429:
                    raise RateLimitError(
                        _rate_limit_message(response),
                        retry_after=parsed_retry_after(response),
                    )
                else:
                    raise ServerError(
                        f"Server error: {response.status_code}", status_code=response.status_code
                    )

        except httpx.HTTPError as e:
            last_exception = e
            if attempt < max_retries and should_retry_exception(e):
                delay = 2**attempt
                time.sleep(delay)
            else:
                raise

    if last_exception:
        raise last_exception

    raise RuntimeError("Unexpected retry loop exit")


async def retry_async(
    func: Callable[..., Any], *args: Any, max_retries: int = 3, **kwargs: Any
) -> httpx.Response:
    """Execute an async function with retry logic."""
    last_exception: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            response: httpx.Response = await func(*args, **kwargs)

            if not should_retry(response):
                return response

            if attempt < max_retries:
                delay = get_retry_after(response, attempt)
                await asyncio.sleep(delay)
            else:
                if response.status_code == 429:
                    raise RateLimitError(
                        _rate_limit_message(response),
                        retry_after=parsed_retry_after(response),
                    )
                else:
                    raise ServerError(
                        f"Server error: {response.status_code}", status_code=response.status_code
                    )

        except httpx.HTTPError as e:
            last_exception = e
            if attempt < max_retries and should_retry_exception(e):
                delay = 2**attempt
                await asyncio.sleep(delay)
            else:
                raise

    if last_exception:
        raise last_exception

    raise RuntimeError("Unexpected retry loop exit")
