"""Tests for the QueryBuilder."""

from datetime import date

from plausible_client import Dimension, Metric, QueryBuilder


def test_query_builder_basic() -> None:
    """Test basic query building."""
    query = QueryBuilder("example.com").metrics(Metric.VISITORS)

    payload = query.build()

    assert payload["site_id"] == "example.com"
    assert payload["metrics"] == [Metric.VISITORS]


def test_query_builder_multiple_metrics() -> None:
    """Test query with multiple metrics."""
    query = QueryBuilder("example.com").metrics(
        Metric.VISITORS, Metric.PAGEVIEWS, Metric.BOUNCE_RATE
    )

    payload = query.build()

    assert len(payload["metrics"]) == 3


def test_query_builder_with_dimensions() -> None:
    """Test query with dimensions."""
    query = (
        QueryBuilder("example.com")
        .metrics(Metric.VISITORS)
        .dimensions(Dimension.EVENT_PAGE, Dimension.VISIT_SOURCE)
    )

    payload = query.build()

    assert len(payload["dimensions"]) == 2
    assert Dimension.EVENT_PAGE in payload["dimensions"]


def test_query_builder_with_filter() -> None:
    """Test query with single filter."""
    query = (
        QueryBuilder("example.com")
        .metrics(Metric.VISITORS)
        .filter(Dimension.VISIT_SOURCE, "is", "Google")
    )

    payload = query.build()

    assert len(payload["filters"]) == 1
    assert payload["filters"][0] == [Dimension.VISIT_SOURCE, "is", "Google"]


def test_query_builder_with_multiple_filters() -> None:
    """Test query with multiple filters."""
    query = (
        QueryBuilder("example.com")
        .metrics(Metric.VISITORS)
        .filter(Dimension.VISIT_SOURCE, "is", "Google")
        .filter(Dimension.VISIT_COUNTRY, "is_not", "US")
    )

    payload = query.build()

    assert len(payload["filters"]) == 2


def test_query_builder_filter_with_list() -> None:
    """Test query with filter using list value."""
    query = (
        QueryBuilder("example.com")
        .metrics(Metric.VISITORS)
        .filter(Dimension.VISIT_COUNTRY, "is", ["US", "UK", "CA"])
    )

    payload = query.build()

    assert payload["filters"][0][2] == ["US", "UK", "CA"]


def test_query_builder_with_date_range() -> None:
    """Test query with date range."""
    query = (
        QueryBuilder("example.com")
        .metrics(Metric.VISITORS)
        .date_range(date(2024, 1, 1), date(2024, 1, 31))
    )

    payload = query.build()

    assert "date_range" in payload
    assert payload["date_range"] == ["2024-01-01", "2024-01-31"]


def test_query_builder_with_order_by() -> None:
    """Test query with ordering."""
    query = (
        QueryBuilder("example.com")
        .metrics(Metric.VISITORS, Metric.PAGEVIEWS)
        .order_by(Metric.VISITORS, "desc")
    )

    payload = query.build()

    assert len(payload["order_by"]) == 1
    assert payload["order_by"][0]["metric"] == Metric.VISITORS
    assert payload["order_by"][0]["direction"] == "desc"


def test_query_builder_with_pagination() -> None:
    """Test query with limit and offset."""
    query = QueryBuilder("example.com").metrics(Metric.VISITORS).limit(10).offset(20)

    payload = query.build()

    assert payload["limit"] == 10
    assert payload["offset"] == 20


def test_query_builder_full_example() -> None:
    """Test query with all features combined."""
    query = (
        QueryBuilder("example.com")
        .metrics(Metric.VISITORS, Metric.PAGEVIEWS)
        .dimensions(Dimension.EVENT_PAGE)
        .filter(Dimension.VISIT_SOURCE, "contains", "google")
        .date_range(date(2024, 1, 1), date(2024, 1, 31))
        .order_by(Metric.VISITORS, "desc")
        .limit(50)
    )

    payload = query.build()

    assert payload["site_id"] == "example.com"
    assert len(payload["metrics"]) == 2
    assert len(payload["dimensions"]) == 1
    assert len(payload["filters"]) == 1
    assert "date_range" in payload
    assert len(payload["order_by"]) == 1
    assert payload["limit"] == 50
