"""Tests for Events API fields and dropped-event reporting."""

import json

import httpx
import pytest
import respx

from plausible_client import AsyncClient, Client, EventResult


@respx.mock
def test_send_event_referrer_and_interactive() -> None:
    """referrer and interactive are optional Events API body fields."""
    route = respx.post("https://plausible.io/api/event").mock(
        return_value=httpx.Response(202, text="ok")
    )

    client = Client(api_key="test-key")
    result = client.send_event(
        domain="example.com",
        name="signup",
        url="https://example.com/signup",
        referrer="https://news.ycombinator.com/item?id=1",
        interactive=False,
    )

    assert result == EventResult(dropped=False)
    body = json.loads(route.calls.last.request.content)
    assert body["referrer"] == "https://news.ycombinator.com/item?id=1"
    assert body["interactive"] is False
    assert body["domain"] == "example.com"
    assert body["name"] == "signup"
    assert body["url"] == "https://example.com/signup"


@respx.mock
def test_send_event_sets_cf_connecting_ip() -> None:
    """Cloudflare's CF-Connecting-IP overrides X-Forwarded-For, so it must be set too."""
    route = respx.post("https://plausible.io/api/event").mock(
        return_value=httpx.Response(202, text="ok")
    )

    client = Client(api_key="test-key")
    client.send_event(
        domain="example.com",
        name="pageview",
        url="https://example.com/home",
        x_forwarded_for="203.0.113.5",
        cf_connecting_ip="203.0.113.5",
    )

    headers = route.calls.last.request.headers
    assert headers["X-Forwarded-For"] == "203.0.113.5"
    assert headers["CF-Connecting-IP"] == "203.0.113.5"


@respx.mock
def test_send_event_omits_cf_connecting_ip_by_default() -> None:
    """Existing callers do not start sending a Cloudflare header."""
    route = respx.post("https://plausible.io/api/event").mock(
        return_value=httpx.Response(202, text="ok")
    )

    client = Client(api_key="test-key")
    client.send_event(
        domain="example.com",
        name="pageview",
        url="https://example.com/home",
        x_forwarded_for="203.0.113.5",
    )

    assert "cf-connecting-ip" not in route.calls.last.request.headers


@pytest.mark.asyncio
@respx.mock
async def test_async_send_event_sets_cf_connecting_ip() -> None:
    """The async client forwards the same Cloudflare header."""
    route = respx.post("https://plausible.io/api/event").mock(
        return_value=httpx.Response(202, text="ok")
    )

    client = AsyncClient(api_key="test-key")
    await client.send_event(
        domain="example.com",
        name="pageview",
        url="https://example.com/home",
        cf_connecting_ip="2001:db8::1",
    )

    assert route.calls.last.request.headers["CF-Connecting-IP"] == "2001:db8::1"
    await client.close()


@respx.mock
def test_send_event_omits_unset_optional_fields() -> None:
    """Unset referrer and interactive stay out of the payload."""
    route = respx.post("https://plausible.io/api/event").mock(
        return_value=httpx.Response(202, text="ok")
    )

    client = Client(api_key="test-key")
    client.send_event(
        domain="example.com",
        name="pageview",
        url="https://example.com/home",
    )

    body = json.loads(route.calls.last.request.content)
    assert "referrer" not in body
    assert "interactive" not in body


@respx.mock
@pytest.mark.parametrize(
    ("header", "dropped"),
    [
        (None, False),
        ("0", False),
        ("1", True),
        ("2", True),
    ],
)
def test_dropped_header(header: str | None, dropped: bool) -> None:
    """x-plausible-dropped is a count. The docs use 1. 202 still means accepted."""
    headers = {} if header is None else {"x-plausible-dropped": header}
    respx.post("https://plausible.io/api/event").mock(
        return_value=httpx.Response(202, headers=headers, text="ok")
    )

    client = Client(api_key="test-key")
    result = client.send_event(
        domain="example.com",
        name="pageview",
        url="https://example.com/home",
    )

    assert result.dropped is dropped


@pytest.mark.asyncio
@respx.mock
async def test_async_send_event_referrer_and_dropped() -> None:
    """Async send_event reports the same fields and dropped flag."""
    route = respx.post("https://plausible.io/api/event").mock(
        return_value=httpx.Response(202, headers={"x-plausible-dropped": "1"}, text="ok")
    )

    client = AsyncClient(api_key="test-key")
    result = await client.send_event(
        domain="example.com",
        name="scroll",
        url="https://example.com/docs",
        referrer="https://example.com/blog",
        interactive=False,
    )

    assert result.dropped is True
    body = json.loads(route.calls.last.request.content)
    assert body["referrer"] == "https://example.com/blog"
    assert body["interactive"] is False
    await client.close()
