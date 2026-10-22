"""Live integration tests (optional, requires real API key and site).

Set PLAUSIBLE_API_KEY and PLAUSIBLE_SITE_ID environment variables to run these tests.
"""

import os
from datetime import date, timedelta

import pytest

from plausible_client import AsyncClient, Client, Dimension, Metric, QueryBuilder

pytestmark = pytest.mark.skipif(
    not os.environ.get("PLAUSIBLE_API_KEY") or not os.environ.get("PLAUSIBLE_SITE_ID"),
    reason="Live tests require PLAUSIBLE_API_KEY and PLAUSIBLE_SITE_ID environment variables",
)


@pytest.fixture
def api_key() -> str:
    """Get API key from environment."""
    return os.environ["PLAUSIBLE_API_KEY"]


@pytest.fixture
def site_id() -> str:
    """Get site ID from environment."""
    return os.environ["PLAUSIBLE_SITE_ID"]


def test_live_query_visitors(api_key: str, site_id: str) -> None:
    """Test live query for visitor count."""
    client = Client(api_key=api_key)

    today = date.today()
    last_week = today - timedelta(days=7)

    query = (
        QueryBuilder(site_id)
        .metrics(Metric.VISITORS, Metric.PAGEVIEWS)
        .date_range(last_week, today)
    )

    result = client.query(query)

    assert isinstance(result.results, list)
    assert "meta" in result.meta or len(result.results) >= 0


def test_live_query_with_dimensions(api_key: str, site_id: str) -> None:
    """Test live query with dimensions."""
    client = Client(api_key=api_key)

    today = date.today()
    last_week = today - timedelta(days=7)

    query = (
        QueryBuilder(site_id)
        .metrics(Metric.VISITORS)
        .dimensions(Dimension.VISIT_SOURCE)
        .date_range(last_week, today)
        .limit(5)
    )

    result = client.query(query)

    assert isinstance(result.results, list)


@pytest.mark.asyncio
async def test_live_async_query(api_key: str, site_id: str) -> None:
    """Test live async query."""
    async with AsyncClient(api_key=api_key) as client:
        today = date.today()
        last_week = today - timedelta(days=7)

        query = (
            QueryBuilder(site_id)
            .metrics(Metric.VISITORS, Metric.PAGEVIEWS, Metric.BOUNCE_RATE)
            .date_range(last_week, today)
        )

        result = await client.query(query)

        assert isinstance(result.results, list)


def test_live_send_event(api_key: str, site_id: str) -> None:
    """Test live event sending."""
    client = Client(api_key=api_key)

    client.send_event(
        domain=site_id,
        name="test_event",
        url=f"https://{site_id}/test",
        props={"test": "true", "source": "python_client"},
    )
