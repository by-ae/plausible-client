"""Tests for data models."""

from datetime import date

from plausible_client.models import DateRange, Filter, OrderBy, QueryResult


def test_date_range_to_dict() -> None:
    """Test DateRange conversion to dict."""
    dr = DateRange(start_date=date(2024, 1, 1), end_date=date(2024, 1, 31))
    result = dr.to_dict()

    assert result == {"date_range": ["2024-01-01", "2024-01-31"]}


def test_filter_to_dict_single_value() -> None:
    """Test Filter conversion with single value."""
    f = Filter(dimension="event:page", operator="is", value="/home")
    result = f.to_dict()

    assert result == ["event:page", "is", "/home"]


def test_filter_to_dict_list_value() -> None:
    """Test Filter conversion with list value."""
    f = Filter(dimension="visit:country", operator="is", value=["US", "UK"])
    result = f.to_dict()

    assert result == ["visit:country", "is", ["US", "UK"]]


def test_order_by_to_dict() -> None:
    """Test OrderBy conversion to dict."""
    ob = OrderBy(metric="visitors", direction="desc")
    result = ob.to_dict()

    assert result == {"metric": "visitors", "direction": "desc"}


def test_order_by_default_direction() -> None:
    """Test OrderBy with default direction."""
    ob = OrderBy(metric="pageviews")
    result = ob.to_dict()

    assert result["direction"] == "desc"


def test_query_result_from_response() -> None:
    """Test QueryResult creation from API response."""
    response_data = {
        "results": [
            {"dimensions": [], "metrics": [100, 200]},
            {"dimensions": [], "metrics": [150, 250]},
        ],
        "meta": {"total": 2, "offset": 0},
    }

    result = QueryResult.from_response(response_data)

    assert len(result.results) == 2
    assert result.meta["total"] == 2


def test_query_result_empty_response() -> None:
    """Test QueryResult with empty response."""
    result = QueryResult.from_response({})

    assert result.results == []
    assert result.meta == {}
