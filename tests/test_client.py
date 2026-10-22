"""Tests for the synchronous Plausible client."""

from datetime import date

import httpx
import pytest
import respx

from plausible_client import (
    AuthenticationError,
    Client,
    Dimension,
    InvalidQueryError,
    Metric,
    QueryBuilder,
    RateLimitError,
    ServerError,
)


@respx.mock
def test_client_query_success() -> None:
    """Test successful query execution."""
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

    client = Client(api_key="test-key")
    query = QueryBuilder("example.com").metrics(Metric.VISITORS, Metric.PAGEVIEWS)

    result = client.query(query)

    assert len(result.results) == 1
    assert result.results[0]["metrics"] == [100, 200]
    assert result.meta["total"] == 1
    assert route.called


@respx.mock
def test_client_query_with_filters() -> None:
    """Test query with filters and dimensions."""
    route = respx.post("https://plausible.io/api/v2/query").mock(
        return_value=httpx.Response(
            200,
            json={
                "results": [
                    {"dimensions": ["/home"], "metrics": [50]},
                    {"dimensions": ["/about"], "metrics": [30]},
                ],
            },
        )
    )

    client = Client(api_key="test-key")
    query = (
        QueryBuilder("example.com")
        .metrics(Metric.VISITORS)
        .dimensions(Dimension.EVENT_PAGE)
        .filter(Dimension.VISIT_SOURCE, "is", "Google")
        .date_range(date(2024, 1, 1), date(2024, 1, 31))
        .limit(10)
    )

    result = client.query(query)

    assert len(result.results) == 2
    assert route.called

    request = route.calls.last.request
    payload = request.read()
    assert b"example.com" in payload
    assert b"Google" in payload


@respx.mock
def test_client_authentication_error() -> None:
    """Test authentication error handling."""
    respx.post("https://plausible.io/api/v2/query").mock(
        return_value=httpx.Response(401, json={"error": "Invalid API key"})
    )

    client = Client(api_key="invalid-key")
    query = QueryBuilder("example.com").metrics(Metric.VISITORS)

    with pytest.raises(AuthenticationError):
        client.query(query)


@respx.mock
def test_client_invalid_query_error() -> None:
    """Test invalid query error handling."""
    respx.post("https://plausible.io/api/v2/query").mock(
        return_value=httpx.Response(
            400, json={"error": "Invalid metric", "details": {"metric": "unknown"}}
        )
    )

    client = Client(api_key="test-key")
    query = QueryBuilder("example.com").metrics("invalid_metric")

    with pytest.raises(InvalidQueryError) as exc_info:
        client.query(query)

    assert "Invalid metric" in str(exc_info.value)


@respx.mock
def test_client_rate_limit_error() -> None:
    """Test rate limit error handling."""
    respx.post("https://plausible.io/api/v2/query").mock(
        return_value=httpx.Response(429, headers={"Retry-After": "60"})
    )

    client = Client(api_key="test-key")
    query = QueryBuilder("example.com").metrics(Metric.VISITORS)

    with pytest.raises(RateLimitError) as exc_info:
        client.query(query)

    assert exc_info.value.retry_after == 60


@respx.mock
def test_client_server_error() -> None:
    """Test server error handling."""
    respx.post("https://plausible.io/api/v2/query").mock(
        return_value=httpx.Response(503)
    )

    client = Client(api_key="test-key")
    query = QueryBuilder("example.com").metrics(Metric.VISITORS)

    with pytest.raises(ServerError):
        client.query(query)


@respx.mock
def test_client_retry_on_500() -> None:
    """Test retry logic on 500 errors."""
    route = respx.post("https://plausible.io/api/v2/query").mock(
        side_effect=[
            httpx.Response(500),
            httpx.Response(500),
            httpx.Response(200, json={"results": [], "meta": {}}),
        ]
    )

    client = Client(api_key="test-key")
    query = QueryBuilder("example.com").metrics(Metric.VISITORS)

    result = client.query(query)

    assert result.results == []
    assert route.call_count == 3


@respx.mock
def test_send_event_pageview() -> None:
    """Test sending a pageview event."""
    route = respx.post("https://plausible.io/api/event").mock(
        return_value=httpx.Response(202)
    )

    client = Client(api_key="test-key")
    client.send_event(
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


@respx.mock
def test_send_event_custom_with_props() -> None:
    """Test sending a custom event with properties."""
    route = respx.post("https://plausible.io/api/event").mock(
        return_value=httpx.Response(202)
    )

    client = Client(api_key="test-key")
    client.send_event(
        domain="example.com",
        name="signup",
        url="https://example.com/signup",
        props={"plan": "premium", "trial": True},
        revenue={"amount": 99.99, "currency": "USD"},
    )

    assert route.called


@respx.mock
def test_self_hosted_base_url() -> None:
    """Test using a self-hosted Plausible instance."""
    route = respx.post("https://analytics.company.com/api/v2/query").mock(
        return_value=httpx.Response(200, json={"results": []})
    )

    client = Client(api_key="test-key", base_url="https://analytics.company.com/")
    query = QueryBuilder("example.com").metrics(Metric.VISITORS)

    client.query(query)

    assert route.called


def test_client_context_manager() -> None:
    """Test client as context manager."""
    with Client(api_key="test-key") as client:
        assert client._client is not None

    assert client._client.is_closed
