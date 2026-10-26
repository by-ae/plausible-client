"""Tests for Retry-After handling on 429 responses."""

from datetime import datetime, timedelta, timezone
from email.utils import format_datetime

import httpx
import pytest
import respx

from plausible_client import AsyncClient, Client, Metric, QueryBuilder, RateLimitError


def _patch_sync_sleep(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    slept: list[float] = []
    monkeypatch.setattr("plausible_client._retry.time.sleep", slept.append)
    return slept


def _patch_async_sleep(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    slept: list[float] = []

    async def record_sleep(delay: float) -> None:
        slept.append(delay)

    monkeypatch.setattr("plausible_client._retry.asyncio.sleep", record_sleep)
    return slept


@respx.mock
def test_fractional_retry_after_is_honoured(monkeypatch: pytest.MonkeyPatch) -> None:
    """A decimal Retry-After must not crash when retries are exhausted."""
    slept = _patch_sync_sleep(monkeypatch)
    respx.post("https://plausible.io/api/v2/query").mock(
        return_value=httpx.Response(429, headers={"Retry-After": "1.5"})
    )

    client = Client(api_key="test-key")
    query = QueryBuilder("example.com").metrics(Metric.VISITORS)

    with pytest.raises(RateLimitError) as exc_info:
        client.query(query)

    assert exc_info.value.retry_after == 1.5
    assert exc_info.value.status_code == 429
    assert slept == [1.5, 1.5, 1.5]


@respx.mock
def test_http_date_retry_after_is_honoured(monkeypatch: pytest.MonkeyPatch) -> None:
    """HTTP-date Retry-After values are converted into a wait."""
    slept = _patch_sync_sleep(monkeypatch)
    retry_at = datetime.now(timezone.utc) + timedelta(seconds=90)
    header = format_datetime(retry_at, usegmt=True)
    respx.post("https://plausible.io/api/v2/query").mock(
        return_value=httpx.Response(429, headers={"Retry-After": header})
    )

    client = Client(api_key="test-key")
    query = QueryBuilder("example.com").metrics(Metric.VISITORS)

    with pytest.raises(RateLimitError) as exc_info:
        client.query(query)

    assert exc_info.value.retry_after == pytest.approx(90, abs=2)
    assert len(slept) == 3
    assert slept == pytest.approx([90, 90, 90], abs=2)


@respx.mock
def test_unparseable_retry_after_falls_back_to_backoff(monkeypatch: pytest.MonkeyPatch) -> None:
    """Garbage Retry-After values use exponential backoff and still raise RateLimitError."""
    slept = _patch_sync_sleep(monkeypatch)
    respx.post("https://plausible.io/api/v2/query").mock(
        return_value=httpx.Response(429, headers={"Retry-After": "soon"})
    )

    client = Client(api_key="test-key")
    query = QueryBuilder("example.com").metrics(Metric.VISITORS)

    with pytest.raises(RateLimitError) as exc_info:
        client.query(query)

    assert exc_info.value.retry_after is None
    assert str(exc_info.value) == "Rate limit exceeded"
    assert slept == [1.0, 2.0, 4.0]


@respx.mock
def test_rate_limit_error_includes_response_message(monkeypatch: pytest.MonkeyPatch) -> None:
    """429 bodies that include an error string are surfaced on the exception."""
    _patch_sync_sleep(monkeypatch)
    respx.post("https://plausible.io/api/v2/query").mock(
        return_value=httpx.Response(
            429,
            headers={"Retry-After": "0"},
            json={"error": "Too many requests"},
        )
    )

    client = Client(api_key="test-key")
    query = QueryBuilder("example.com").metrics(Metric.VISITORS)

    with pytest.raises(RateLimitError) as exc_info:
        client.query(query)

    assert str(exc_info.value) == "Too many requests"
    assert exc_info.value.retry_after == 0


@respx.mock
def test_retry_after_delay_used_before_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """A later success still waits for the Retry-After from the 429."""
    slept = _patch_sync_sleep(monkeypatch)
    respx.post("https://plausible.io/api/v2/query").mock(
        side_effect=[
            httpx.Response(429, headers={"Retry-After": "2"}),
            httpx.Response(200, json={"results": [{"metrics": [1]}], "meta": {}}),
        ]
    )

    client = Client(api_key="test-key")
    result = client.query(QueryBuilder("example.com").metrics(Metric.VISITORS))

    assert result.results == [{"metrics": [1]}]
    assert slept == [2.0]


@pytest.mark.asyncio
@respx.mock
async def test_async_fractional_retry_after(monkeypatch: pytest.MonkeyPatch) -> None:
    """Async retries honour fractional Retry-After values too."""
    slept = _patch_async_sleep(monkeypatch)
    respx.post("https://plausible.io/api/v2/query").mock(
        return_value=httpx.Response(
            429,
            headers={"Retry-After": "0.5"},
            json={"error": "Slow down"},
        )
    )

    client = AsyncClient(api_key="test-key")
    query = QueryBuilder("example.com").metrics(Metric.VISITORS)

    with pytest.raises(RateLimitError) as exc_info:
        await client.query(query)

    assert exc_info.value.retry_after == 0.5
    assert str(exc_info.value) == "Slow down"
    assert slept == [0.5, 0.5, 0.5]
    await client.close()
