"""Retry logic with exponential backoff."""

import asyncio
import time
from collections.abc import Callable
from typing import Any, TypeVar

import httpx

from plausible_client.errors import RateLimitError, ServerError

T = TypeVar("T")


def should_retry(response: httpx.Response) -> bool:
    """Check if a response should be retried."""
    return response.status_code == 429 or 500 <= response.status_code < 600


def get_retry_after(response: httpx.Response, attempt: int) -> float:
    """Get the retry delay in seconds."""
    if response.status_code == 429 and "Retry-After" in response.headers:
        try:
            return float(response.headers["Retry-After"])
        except ValueError:
            pass
    return float(min(2**attempt, 60))


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
                    retry_after = (
                        int(response.headers["Retry-After"])
                        if "Retry-After" in response.headers
                        else None
                    )
                    raise RateLimitError(retry_after=retry_after)
                else:
                    raise ServerError(
                        f"Server error: {response.status_code}", status_code=response.status_code
                    )

        except httpx.HTTPError as e:
            last_exception = e
            if attempt < max_retries:
                delay = 2**attempt
                time.sleep(delay)
            else:
                raise

    if last_exception:
        raise last_exception

    raise RuntimeError("Unexpected retry loop exit")


async def retry_async(
    func: Callable[..., Any], *args: Any, max_retries: int = 3, **kwargs: Any
) -> Any:
    """Execute an async function with retry logic."""
    last_exception: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            response = await func(*args, **kwargs)

            if not should_retry(response):
                return response

            if attempt < max_retries:
                delay = get_retry_after(response, attempt)
                await asyncio.sleep(delay)
            else:
                if response.status_code == 429:
                    retry_after = (
                        int(response.headers["Retry-After"])
                        if "Retry-After" in response.headers
                        else None
                    )
                    raise RateLimitError(retry_after=retry_after)
                else:
                    raise ServerError(
                        f"Server error: {response.status_code}", status_code=response.status_code
                    )

        except httpx.HTTPError as e:
            last_exception = e
            if attempt < max_retries:
                delay = 2**attempt
                await asyncio.sleep(delay)
            else:
                raise

    if last_exception:
        raise last_exception

    raise RuntimeError("Unexpected retry loop exit")
