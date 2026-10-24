"""Tests for timeout and network error handling."""

import httpx
import pytest
import respx

from plausible_client import AsyncClient, Client, Metric, QueryBuilder


@respx.mock
def test_timeout_not_retried() -> None:
    """Test that timeout exceptions are not retried."""
    route = respx.post("https://plausible.io/api/v2/query").mock(
        side_effect=httpx.ReadTimeout("Request timed out")
    )

    client = Client(api_key="test-key", timeout=5.0)
    query = QueryBuilder("example.com").metrics(Metric.VISITORS)

    with pytest.raises(httpx.ReadTimeout):
        client.query(query)

    # Should only be called once (no retries)
    assert route.call_count == 1


@respx.mock
def test_connect_timeout_not_retried() -> None:
    """Test that connect timeout exceptions are not retried."""
    route = respx.post("https://plausible.io/api/v2/query").mock(
        side_effect=httpx.ConnectTimeout("Connection timed out")
    )

    client = Client(api_key="test-key", timeout=5.0)
    query = QueryBuilder("example.com").metrics(Metric.VISITORS)

    with pytest.raises(httpx.ConnectTimeout):
        client.query(query)

    # Should only be called once (no retries)
    assert route.call_count == 1


@respx.mock
def test_connection_error_retried() -> None:
    """Test that connection errors (non-timeout) are retried."""
    route = respx.post("https://plausible.io/api/v2/query").mock(
        side_effect=[
            httpx.ConnectError("Connection refused"),
            httpx.ConnectError("Connection refused"),
            httpx.Response(200, json={"results": [], "meta": {}}),
        ]
    )

    client = Client(api_key="test-key")
    query = QueryBuilder("example.com").metrics(Metric.VISITORS)

    result = client.query(query)

    assert result.results == []
    # Should be called 3 times (2 retries + success)
    assert route.call_count == 3


@pytest.mark.asyncio
@respx.mock
async def test_async_timeout_not_retried() -> None:
    """Test that async timeout exceptions are not retried."""
    route = respx.post("https://plausible.io/api/v2/query").mock(
        side_effect=httpx.ReadTimeout("Request timed out")
    )

    client = AsyncClient(api_key="test-key", timeout=5.0)
    query = QueryBuilder("example.com").metrics(Metric.VISITORS)

    with pytest.raises(httpx.ReadTimeout):
        await client.query(query)

    # Should only be called once (no retries)
    assert route.call_count == 1
    await client.close()


@pytest.mark.asyncio
@respx.mock
async def test_async_connection_error_retried() -> None:
    """Test that async connection errors (non-timeout) are retried."""
    route = respx.post("https://plausible.io/api/v2/query").mock(
        side_effect=[
            httpx.ConnectError("Connection refused"),
            httpx.Response(200, json={"results": [], "meta": {}}),
        ]
    )

    client = AsyncClient(api_key="test-key")
    query = QueryBuilder("example.com").metrics(Metric.VISITORS)

    result = await client.query(query)

    assert result.results == []
    # Should be called 2 times (1 retry + success)
    assert route.call_count == 2
    await client.close()
