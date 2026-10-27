"""Tests for the QueryBuilder."""

from datetime import date, datetime, timezone

import pytest

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
    assert payload["filters"][0] == ["is", Dimension.VISIT_SOURCE, ["Google"]]


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


def test_city_filter_wraps_a_geoname_id() -> None:
    """visit:city clauses are GeoName IDs, and a single id is still a list."""
    payload = QueryBuilder("example.com").filter(Dimension.VISIT_CITY, "is", 4347778).build()

    assert payload["filters"] == [["is", "visit:city", [4347778]]]


def test_city_filter_rejects_string_ids() -> None:
    """The Stats API parser accepts only integers for visit:city."""
    with pytest.raises(ValueError, match="visit:city"):
        QueryBuilder("example.com").filter(Dimension.VISIT_CITY, "is", "4347778")


def test_segment_filter_uses_integer_ids() -> None:
    """Segment filters are ["is", "segment", [<integer id>]]."""
    payload = QueryBuilder("example.com").filter("segment", "is", 123).build()

    assert payload["filters"] == [["is", "segment", [123]]]


def test_segment_filter_rejects_string_ids() -> None:
    """A string segment id is not a valid clause."""
    with pytest.raises(ValueError, match="segment"):
        QueryBuilder("example.com").filter("segment", "is", "123")


def test_country_code_must_be_two_characters() -> None:
    """is and is_not on visit:country require a 2-letter code."""
    with pytest.raises(ValueError, match="visit:country"):
        QueryBuilder("example.com").filter(Dimension.VISIT_COUNTRY, "is", "USA")


def test_country_contains_keeps_longer_strings() -> None:
    """The 2-letter check applies to is and is_not, not to contains."""
    payload = (
        QueryBuilder("example.com").filter(Dimension.VISIT_COUNTRY, "contains", "United").build()
    )

    assert payload["filters"] == [["contains", "visit:country", ["United"]]]


def test_non_city_filter_rejects_integers() -> None:
    """Other dimensions take strings. An int would be rejected by the parser."""
    with pytest.raises(ValueError, match="visit:source"):
        QueryBuilder("example.com").filter(Dimension.VISIT_SOURCE, "is", 1)


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
    assert payload["order_by"][0] == [Metric.VISITORS, "desc"]


def test_query_builder_with_pagination() -> None:
    """Test query with limit and offset."""
    query = QueryBuilder("example.com").metrics(Metric.VISITORS).limit(10).offset(20)

    payload = query.build()

    assert "pagination" in payload
    assert payload["pagination"]["limit"] == 10
    assert payload["pagination"]["offset"] == 20


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
    assert payload["pagination"]["limit"] == 50


def test_query_builder_date_range_preset() -> None:
    """Stats API presets are sent as a string, not a date pair."""
    payload = QueryBuilder("example.com").metrics(Metric.VISITORS).date_range("7d").build()

    assert payload["date_range"] == "7d"


def test_query_builder_unknown_date_preset() -> None:
    """Unknown presets fail before a request is sent."""
    with pytest.raises(ValueError, match="unknown date range preset"):
        QueryBuilder("example.com").date_range("fortnight")


def test_query_builder_preset_rejects_end_date() -> None:
    """A preset does not combine with an end date."""
    with pytest.raises(TypeError):
        QueryBuilder("example.com").date_range("7d", date(2024, 1, 1))


def test_query_builder_datetime_range() -> None:
    """Custom ranges accept timezone-aware datetimes."""
    payload = (
        QueryBuilder("example.com")
        .metrics(Metric.VISITORS)
        .date_range(
            datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
            datetime(2024, 1, 1, 15, 59, 59, tzinfo=timezone.utc),
        )
        .build()
    )

    assert payload["date_range"] == [
        "2024-01-01T12:00:00+00:00",
        "2024-01-01T15:59:59+00:00",
    ]


def test_naive_datetime_range_is_rejected() -> None:
    """DateTime.from_iso8601 rejects timestamps that have no offset."""
    with pytest.raises(ValueError, match="timezone-aware"):
        QueryBuilder("example.com").date_range(
            datetime(2024, 1, 1, 12, 0),
            datetime(2024, 1, 1, 15, 0),
        )


def test_mixed_date_and_datetime_range_is_rejected() -> None:
    """A pair must be two dates or two timestamps, not one of each."""
    with pytest.raises(TypeError, match="both be dates or both be datetimes"):
        QueryBuilder("example.com").date_range(
            date(2024, 1, 1),
            datetime(2024, 1, 1, 15, 0, tzinfo=timezone.utc),
        )


def test_query_builder_case_insensitive_filter() -> None:
    """is and contains accept the documented case_sensitive modifier."""
    payload = (
        QueryBuilder("example.com")
        .metrics(Metric.VISITORS)
        .filter(Dimension.VISIT_COUNTRY_NAME, "contains", ["united", "EST"], case_sensitive=False)
        .build()
    )

    assert payload["filters"] == [
        ["contains", "visit:country_name", ["united", "EST"], {"case_sensitive": False}]
    ]


def test_query_builder_case_sensitive_rejected_for_other_operators() -> None:
    """The modifier is not documented for operators other than is and contains."""
    with pytest.raises(ValueError, match="case_sensitive"):
        QueryBuilder("example.com").filter(
            Dimension.EVENT_PAGE, "matches", "^/user/", case_sensitive=False
        )


def test_documented_metric_and_dimension_names() -> None:
    """Constants match the Stats API metric and dimension names."""
    assert Metric.SCROLL_DEPTH == "scroll_depth"
    assert Metric.PERCENTAGE == "percentage"
    assert Metric.GROUP_CONVERSION_RATE == "group_conversion_rate"
    assert Metric.AVERAGE_REVENUE == "average_revenue"
    assert Metric.TOTAL_REVENUE == "total_revenue"
    assert Metric.TIME_ON_PAGE == "time_on_page"
    assert Dimension.EVENT_GOAL == "event:goal"
    assert Dimension.EVENT_HOSTNAME == "event:hostname"
    assert Dimension.VISIT_ENTRY_PAGE == "visit:entry_page"
    assert Dimension.VISIT_EXIT_PAGE == "visit:exit_page"
    assert Dimension.VISIT_CHANNEL == "visit:channel"
    assert Dimension.VISIT_COUNTRY_NAME == "visit:country_name"
    assert Dimension.VISIT_REGION_NAME == "visit:region_name"
    assert Dimension.VISIT_CITY_NAME == "visit:city_name"
    assert Dimension.TIME == "time"
    assert Dimension.TIME_HOUR == "time:hour"
    assert Dimension.TIME_DAY == "time:day"
    assert Dimension.TIME_WEEK == "time:week"
    assert Dimension.TIME_MONTH == "time:month"
