"""Tests for the asynchronous Plausible client."""

from datetime import date

import httpx
import pytest
import respx

from plausible_client import (
    AsyncClient,
    AuthenticationError,
    Dimension,
    InvalidQueryError,
    Metric,
    QueryBuilder,
    RateLimitError,
    ServerError,
)


@pytest.mark.asyncio
@respx.mock
async def test_async_client_query_success() -> None:
    """Test successful async query execution."""
    route = respx.post("https://plausible.io/api/v2/query").mock(
        return_value=httpx.Response(
            200,
            json={
                "results": [
                    {"dimensions": [], "metrics": [100, 200]},
                ],
                "meta": {"total": 1},
            },
        )
    )

    client = AsyncClient(api_key="test-key")
    query = QueryBuilder("example.com").metrics(Metric.VISITORS, Metric.PAGEVIEWS)

    result = await client.query(query)

    assert len(result.results) == 1
    assert result.results[0]["metrics"] == [100, 200]
    assert result.meta["total"] == 1
    assert route.called
    await client.close()


@pytest.mark.asyncio
@respx.mock
async def test_async_client_query_with_dimensions() -> None:
    """Test async query with dimensions."""
    route = respx.post("https://plausible.io/api/v2/query").mock(
        return_value=httpx.Response(
            200,
            json={
                "results": [
                    {"dimensions": ["US"], "metrics": [1000]},
                    {"dimensions": ["UK"], "metrics": [500]},
                ],
            },
        )
    )

    client = AsyncClient(api_key="test-key")
    query = (
        QueryBuilder("example.com")
        .metrics(Metric.VISITORS)
        .dimensions(Dimension.VISIT_COUNTRY)
        .order_by(Metric.VISITORS, "desc")
    )

    result = await client.query(query)

    assert len(result.results) == 2
    assert route.called
    await client.close()


@pytest.mark.asyncio
@respx.mock
async def test_async_client_authentication_error() -> None:
    """Test async authentication error handling."""
    respx.post("https://plausible.io/api/v2/query").mock(
        return_value=httpx.Response(401, json={"error": "Invalid API key"})
    )

    client = AsyncClient(api_key="invalid-key")
    query = QueryBuilder("example.com").metrics(Metric.VISITORS)

    with pytest.raises(AuthenticationError):
        await client.query(query)

    await client.close()


@pytest.mark.asyncio
@respx.mock
async def test_async_client_rate_limit_error() -> None:
    """Test async rate limit error handling."""
    respx.post("https://plausible.io/api/v2/query").mock(
        return_value=httpx.Response(429, headers={"Retry-After": "30"})
    )

    client = AsyncClient(api_key="test-key")
    query = QueryBuilder("example.com").metrics(Metric.VISITORS)

    with pytest.raises(RateLimitError) as exc_info:
        await client.query(query)

    assert exc_info.value.retry_after == 30
    await client.close()


@pytest.mark.asyncio
@respx.mock
async def test_async_client_retry_on_429() -> None:
    """Test async retry logic on 429 errors."""
    route = respx.post("https://plausible.io/api/v2/query").mock(
        side_effect=[
            httpx.Response(500),
            httpx.Response(200, json={"results": [], "meta": {}}),
        ]
    )

    client = AsyncClient(api_key="test-key")
    query = QueryBuilder("example.com").metrics(Metric.VISITORS)

    result = await client.query(query)

    assert result.results == []
    assert route.call_count == 2
    await client.close()


@pytest.mark.asyncio
@respx.mock
async def test_async_send_event_pageview() -> None:
    """Test async sending a pageview event."""
    route = respx.post("https://plausible.io/api/event").mock(
        return_value=httpx.Response(202)
    )

    client = AsyncClient(api_key="test-key")
    await client.send_event(
        domain="example.com",
        name="pageview",
        url="https://example.com/home",
        user_agent="Mozilla/5.0",
        x_forwarded_for="192.168.1.1",
    )

    assert route.called
    request = route.calls.last.request
    assert request.headers["User-Agent"] == "Mozilla/5.0"
    assert request.headers["X-Forwarded-For"] == "192.168.1.1"
    await client.close()


@pytest.mark.asyncio
@respx.mock
async def test_async_send_event_custom_with_revenue() -> None:
    """Test async sending a custom event with revenue."""
    route = respx.post("https://plausible.io/api/event").mock(
        return_value=httpx.Response(202)
    )

    client = AsyncClient(api_key="test-key")
    await client.send_event(
        domain="example.com",
        name="purchase",
        url="https://example.com/checkout",
        props={"product": "widget", "quantity": 2},
        revenue={"amount": 199.98, "currency": "USD"},
    )

    assert route.called
    await client.close()


@pytest.mark.asyncio
@respx.mock
async def test_async_self_hosted_base_url() -> None:
    """Test async with self-hosted Plausible instance."""
    route = respx.post("https://analytics.company.com/api/v2/query").mock(
        return_value=httpx.Response(200, json={"results": []})
    )

    client = AsyncClient(api_key="test-key", base_url="https://analytics.company.com")
    query = QueryBuilder("example.com").metrics(Metric.VISITORS)

    await client.query(query)

    assert route.called
    await client.close()


@pytest.mark.asyncio
async def test_async_client_context_manager() -> None:
    """Test async client as context manager."""
    async with AsyncClient(api_key="test-key") as client:
        assert client._client is not None

    assert client._client.is_closed
