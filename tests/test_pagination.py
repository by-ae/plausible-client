"""Tests for pagination functionality."""

from datetime import date

import httpx
import respx
from respx import MockRouter

from plausible_client import AsyncClient, Client, Metric, QueryBuilder


@respx.mock
def test_query_all_single_page(respx_mock: MockRouter) -> None:
    """Test query_all with results fitting in a single page."""
    client = Client(api_key="test-key")

    results = [
        {"dimensions": ["US"], "metrics": [100]},
        {"dimensions": ["UK"], "metrics": [50]},
    ]

    respx_mock.post("https://plausible.io/api/v2/query").mock(
        return_value=httpx.Response(
            200,
            json={
                "results": results,
                "meta": {"total_rows": 2},
            },
        )
    )

    query = QueryBuilder("example.com").metrics(Metric.VISITORS).date_range(
        date(2024, 1, 1), date(2024, 1, 31)
    )

    result = client.query_all(query, page_size=1000)

    assert len(result.results) == 2
    assert result.results == results
    assert result.meta["total_rows"] == 2
    assert len(respx_mock.calls) == 1


@respx.mock
def test_query_all_multiple_pages(respx_mock: MockRouter) -> None:
    """Test query_all with results spanning multiple pages."""
    client = Client(api_key="test-key")

    page1_results = [{"dimensions": [f"Country{i}"], "metrics": [100]} for i in range(100)]
    page2_results = [{"dimensions": [f"Country{i}"], "metrics": [100]} for i in range(100, 150)]

    call_count = 0

    def mock_response(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1

        if call_count == 1:
            return httpx.Response(
                200,
                json={
                    "results": page1_results,
                    "meta": {"total_rows": 150},
                },
            )
        else:
            return httpx.Response(
                200,
                json={
                    "results": page2_results,
                    "meta": {"total_rows": 150},
                },
            )

    respx_mock.post("https://plausible.io/api/v2/query").mock(side_effect=mock_response)

    query = QueryBuilder("example.com").metrics(Metric.VISITORS).date_range(
        date(2024, 1, 1), date(2024, 1, 31)
    )

    result = client.query_all(query, page_size=100)

    assert len(result.results) == 150
    assert result.results == page1_results + page2_results
    assert result.meta["total_rows"] == 150
    assert len(respx_mock.calls) == 2


@respx.mock
def test_query_all_custom_page_size(respx_mock: MockRouter) -> None:
    """Test query_all with a custom page size."""
    client = Client(api_key="test-key")

    results = [{"dimensions": [f"Page{i}"], "metrics": [10]} for i in range(5)]

    respx_mock.post("https://plausible.io/api/v2/query").mock(
        return_value=httpx.Response(
            200,
            json={
                "results": results,
                "meta": {"total_rows": 5},
            },
        )
    )

    query = QueryBuilder("example.com").metrics(Metric.PAGEVIEWS).date_range(
        date(2024, 1, 1), date(2024, 1, 31)
    )

    result = client.query_all(query, page_size=50)

    assert len(result.results) == 5
    request = respx_mock.calls.last.request
    import json

    body = json.loads(request.content)
    assert body["limit"] == 50


@respx.mock
def test_query_all_preserves_query_options(respx_mock: MockRouter) -> None:
    """Test that query_all preserves filters, dimensions, and ordering."""
    client = Client(api_key="test-key")

    respx_mock.post("https://plausible.io/api/v2/query").mock(
        return_value=httpx.Response(
            200,
            json={
                "results": [],
                "meta": {"total_rows": 0},
            },
        )
    )

    query = (
        QueryBuilder("example.com")
        .metrics(Metric.VISITORS, Metric.PAGEVIEWS)
        .dimensions("visit:country")
        .filter("visit:source", "is", "Google")
        .date_range(date(2024, 1, 1), date(2024, 1, 31))
        .order_by(Metric.VISITORS, "desc")
    )

    result = client.query_all(query)

    assert result.results == []
    request = respx_mock.calls.last.request
    import json

    body = json.loads(request.content)
    assert body["metrics"] == ["visitors", "pageviews"]
    assert body["dimensions"] == ["visit:country"]
    assert body["filters"] == [["visit:source", "is", "Google"]]
    assert "include" in body
    assert body["include"]["total_rows"] is True


@respx.mock
async def test_async_query_all_single_page(respx_mock: MockRouter) -> None:
    """Test async query_all with results fitting in a single page."""
    async with AsyncClient(api_key="test-key") as client:
        results = [
            {"dimensions": ["US"], "metrics": [100]},
            {"dimensions": ["UK"], "metrics": [50]},
        ]

        respx_mock.post("https://plausible.io/api/v2/query").mock(
            return_value=httpx.Response(
                200,
                json={
                    "results": results,
                    "meta": {"total_rows": 2},
                },
            )
        )

        query = QueryBuilder("example.com").metrics(Metric.VISITORS).date_range(
            date(2024, 1, 1), date(2024, 1, 31)
        )

        result = await client.query_all(query, page_size=1000)

        assert len(result.results) == 2
        assert result.results == results
        assert result.meta["total_rows"] == 2


@respx.mock
async def test_async_query_all_multiple_pages(respx_mock: MockRouter) -> None:
    """Test async query_all with results spanning multiple pages."""
    async with AsyncClient(api_key="test-key") as client:
        page1_results = [{"dimensions": [f"Country{i}"], "metrics": [100]} for i in range(50)]
        page2_results = [
            {"dimensions": [f"Country{i}"], "metrics": [100]} for i in range(50, 75)
        ]

        call_count = 0

        def mock_response(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1

            if call_count == 1:
                return httpx.Response(
                    200,
                    json={
                        "results": page1_results,
                        "meta": {"total_rows": 75},
                    },
                )
            else:
                return httpx.Response(
                    200,
                    json={
                        "results": page2_results,
                        "meta": {"total_rows": 75},
                    },
                )

        respx_mock.post("https://plausible.io/api/v2/query").mock(side_effect=mock_response)

        query = QueryBuilder("example.com").metrics(Metric.VISITORS).date_range(
            date(2024, 1, 1), date(2024, 1, 31)
        )

        result = await client.query_all(query, page_size=50)

        assert len(result.results) == 75
        assert result.results == page1_results + page2_results
        assert result.meta["total_rows"] == 75


@respx.mock
def test_query_builder_include_options(respx_mock: MockRouter) -> None:
    """Test QueryBuilder include options."""
    client = Client(api_key="test-key")

    respx_mock.post("https://plausible.io/api/v2/query").mock(
        return_value=httpx.Response(
            200,
            json={
                "results": [],
                "meta": {
                    "total_rows": 0,
                    "imports_included": True,
                    "time_labels": ["2024-01-01", "2024-01-02"],
                },
            },
        )
    )

    query = (
        QueryBuilder("example.com")
        .metrics(Metric.VISITORS)
        .date_range(date(2024, 1, 1), date(2024, 1, 2))
        .include(imports=True, time_labels=True, total_rows=True)
    )

    result = client.query(query)

    request = respx_mock.calls.last.request
    import json

    body = json.loads(request.content)
    assert body["include"]["imports"] is True
    assert body["include"]["time_labels"] is True
    assert body["include"]["total_rows"] is True
    assert result.meta["imports_included"] is True
    assert result.meta["time_labels"] == ["2024-01-01", "2024-01-02"]


@respx.mock
def test_query_builder_include_partial(respx_mock: MockRouter) -> None:
    """Test QueryBuilder include with only some options enabled."""
    client = Client(api_key="test-key")

    respx_mock.post("https://plausible.io/api/v2/query").mock(
        return_value=httpx.Response(
            200,
            json={
                "results": [],
                "meta": {"total_rows": 0},
            },
        )
    )

    query = (
        QueryBuilder("example.com")
        .metrics(Metric.VISITORS)
        .date_range(date(2024, 1, 1), date(2024, 1, 2))
        .include(total_rows=True)
    )

    client.query(query)

    request = respx_mock.calls.last.request
    import json

    body = json.loads(request.content)
    assert body["include"]["total_rows"] is True
    assert "imports" not in body["include"]
    assert "time_labels" not in body["include"]
