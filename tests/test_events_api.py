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


def test_send_event_rejects_values_the_parser_drops() -> None:
    """Ingestion returns 400 for these payloads, or ignores interactive=false."""
    client = Client(api_key="test-key")

    with pytest.raises(ValueError, match="domain"):
        client.send_event(domain="  ", name="pageview", url="https://example.com/")
    with pytest.raises(ValueError, match="name is required"):
        client.send_event(domain="example.com", name="", url="https://example.com/")
    with pytest.raises(ValueError, match="120"):
        client.send_event(domain="example.com", name="n" * 121, url="https://example.com/")
    with pytest.raises(ValueError, match="2000"):
        client.send_event(
            domain="example.com",
            name="pageview",
            url="https://example.com/" + "a" * 2000,
        )
    with pytest.raises(ValueError, match="data:"):
        client.send_event(
            domain="example.com",
            name="pageview",
            url="DATA:text/html,hi",
        )
    with pytest.raises(ValueError, match="pageview"):
        client.send_event(
            domain="example.com",
            name="pageview",
            url="https://example.com/",
            interactive=False,
        )
    with pytest.raises(ValueError, match="File Download"):
        client.send_event(
            domain="example.com",
            name="File Download",
            url="https://example.com/file",
            interactive=False,
        )
    with pytest.raises(ValueError, match="300 bytes"):
        client.send_event(
            domain="example.com",
            name="signup",
            url="https://example.com/",
            props={"é" * 151: "ok"},
        )
    with pytest.raises(ValueError, match="2000 bytes"):
        client.send_event(
            domain="example.com",
            name="signup",
            url="https://example.com/",
            props={"plan": "x" * 2001},
        )


@respx.mock
def test_send_event_accepts_parser_limits() -> None:
    """Values at the documented limits are still sent."""
    route = respx.post("https://plausible.io/api/event").mock(
        return_value=httpx.Response(202, text="ok")
    )
    prefix = "https://example.com/"
    url = prefix + "a" * (2000 - len(prefix.encode()))
    assert len(url.encode()) == 2000

    client = Client(api_key="test-key")
    client.send_event(
        domain="example.com",
        name="n" * 120,
        url=url,
        props={"k" * 300: "v" * 2000, "flag": False},
        interactive=True,
    )

    body = json.loads(route.calls.last.request.content)
    assert body["name"] == "n" * 120
    assert body["url"] == url
    assert body["interactive"] is True
    assert body["props"]["flag"] is False


@pytest.mark.asyncio
async def test_async_send_event_rejects_noninteractive_pageview() -> None:
    """The async client applies the same ingestion checks."""
    client = AsyncClient(api_key="test-key")
    with pytest.raises(ValueError, match="pageview"):
        await client.send_event(
            domain="example.com",
            name="pageview",
            url="https://example.com/",
            interactive=False,
        )
    await client.close()
