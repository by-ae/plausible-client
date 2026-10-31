"""Tests for 402 Payment Required error handling."""

import httpx
import pytest
import respx

from plausible_client import (
    AsyncClient,
    Client,
    Metric,
    PaymentRequiredError,
    QueryBuilder,
)


@respx.mock
def test_client_payment_required_error() -> None:
    """Test 402 Payment Required error handling for sync client."""
    respx.post("https://plausible.io/api/v2/query").mock(
        return_value=httpx.Response(
            402, json={"error": "Payment required. Please update your subscription."}
        )
    )

    client = Client(api_key="test-key")
    query = QueryBuilder("example.com").metrics(Metric.VISITORS)

    with pytest.raises(PaymentRequiredError) as exc_info:
        client.query(query)

    assert exc_info.value.status_code == 402
    assert str(exc_info.value) == "Payment required. Please update your subscription."


@pytest.mark.asyncio
@respx.mock
async def test_async_client_payment_required_error() -> None:
    """Test 402 Payment Required error handling for async client."""
    respx.post("https://plausible.io/api/v2/query").mock(
        return_value=httpx.Response(
            402, json={"error": "Payment required. Please update your subscription."}
        )
    )

    client = AsyncClient(api_key="test-key")
    query = QueryBuilder("example.com").metrics(Metric.VISITORS)

    with pytest.raises(PaymentRequiredError) as exc_info:
        await client.query(query)

    assert exc_info.value.status_code == 402
    assert str(exc_info.value) == "Payment required. Please update your subscription."
    await client.close()


@respx.mock
def test_sites_api_payment_required_error() -> None:
    """Test 402 Payment Required error handling for Sites API."""
    respx.get("https://plausible.io/api/v1/sites").mock(
        return_value=httpx.Response(402, json={"error": "Payment required"})
    )

    client = Client(api_key="test-key")

    with pytest.raises(PaymentRequiredError):
        client.list_sites()


@respx.mock
def test_send_event_payment_required_error() -> None:
    """Test 402 Payment Required error handling for Events API."""
    respx.post("https://plausible.io/api/event").mock(
        return_value=httpx.Response(402, json={"error": "Payment required"})
    )

    client = Client(api_key="test-key")

    with pytest.raises(PaymentRequiredError, match="Payment required"):
        client.send_event(
            domain="example.com",
            name="pageview",
            url="https://example.com/home",
        )


@respx.mock
def test_payment_required_uses_the_api_error() -> None:
    """A 402 names the plan limit. Callers need that string, not a generic one."""
    respx.post("https://plausible.io/api/v1/sites").mock(
        return_value=httpx.Response(
            402,
            json={
                "error": (
                    "Your account has reached the limit of 10 sites. "
                    "To unlock more sites, please upgrade your subscription."
                )
            },
        )
    )

    client = Client(api_key="test-key")

    with pytest.raises(PaymentRequiredError) as exc_info:
        client.create_site(domain="another.example")

    assert exc_info.value.status_code == 402
    assert exc_info.value.message == (
        "Your account has reached the limit of 10 sites. "
        "To unlock more sites, please upgrade your subscription."
    )


@respx.mock
def test_payment_required_without_json_body_keeps_the_default() -> None:
    """A 402 with no error string still raises PaymentRequiredError."""
    respx.get("https://plausible.io/api/v1/sites").mock(return_value=httpx.Response(402, text=""))

    client = Client(api_key="test-key")

    with pytest.raises(PaymentRequiredError) as exc_info:
        client.list_sites()

    assert exc_info.value.message == "Payment required to access this resource"
