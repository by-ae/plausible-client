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
def test_send_event_debug_returns_the_ip_plausible_will_use() -> None:
    """X-Debug-Request returns HTTP 200 text/plain and does not record the event."""
    route = respx.post("https://plausible.io/api/event").mock(
        return_value=httpx.Response(
            200, text="203.0.113.5\n", headers={"content-type": "text/plain"}
        )
    )

    client = Client(api_key="test-key")
    result = client.send_event(
        domain="example.com",
        name="pageview",
        url="https://example.com/docs",
        x_forwarded_for="203.0.113.5",
        debug=True,
    )

    assert result == EventResult(dropped=False, ip="203.0.113.5")
    assert route.calls.last.request.headers["X-Debug-Request"] == "true"


@respx.mock
def test_send_event_omits_debug_header_by_default() -> None:
    """A normal event is not marked as a debug request."""
    route = respx.post("https://plausible.io/api/event").mock(
        return_value=httpx.Response(202, text="ok")
    )

    client = Client(api_key="test-key")
    result = client.send_event(
        domain="example.com",
        name="pageview",
        url="https://example.com/docs",
    )

    assert result.ip is None
    assert "x-debug-request" not in route.calls.last.request.headers


@respx.mock
def test_debug_request_ignored_by_the_server_leaves_ip_unset() -> None:
    """HTTP 202 means the header was ignored and the event was recorded."""
    respx.post("https://plausible.io/api/event").mock(return_value=httpx.Response(202, text="ok"))

    client = Client(api_key="test-key")
    result = client.send_event(
        domain="example.com",
        name="pageview",
        url="https://example.com/docs",
        debug=True,
    )

    assert result.ip is None
    assert result.dropped is False


@pytest.mark.asyncio
@respx.mock
async def test_async_send_event_debug_returns_the_ip() -> None:
    """The async client reads the same debug response."""
    route = respx.post("https://plausible.io/api/event").mock(
        return_value=httpx.Response(200, text="198.51.100.9")
    )

    client = AsyncClient(api_key="test-key")
    result = await client.send_event(
        domain="example.com",
        name="pageview",
        url="https://example.com/docs",
        cf_connecting_ip="198.51.100.9",
        debug=True,
    )

    assert result.ip == "198.51.100.9"
    assert route.calls.last.request.headers["X-Debug-Request"] == "true"
    await client.close()


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


@respx.mock
def test_send_engagement_event_sends_scroll_depth_and_time() -> None:
    """engagement events carry sd and e, the fields the tracker sends."""
    route = respx.post("https://plausible.io/api/event").mock(
        return_value=httpx.Response(202, text="ok")
    )

    client = Client(api_key="test-key")
    result = client.send_event(
        domain="example.com",
        name="engagement",
        url="https://example.com/docs",
        scroll_depth=0,
        engagement_time=12_000,
    )

    assert result.dropped is False
    body = json.loads(route.calls.last.request.content)
    assert body["name"] == "engagement"
    assert body["sd"] == 0
    assert body["e"] == 12_000
    assert "scroll_depth" not in body
    assert "engagement_time" not in body


def test_send_engagement_event_requires_a_value_the_api_keeps() -> None:
    """The API returns 400 when scroll depth and engagement time are both missing."""
    client = Client(api_key="test-key")

    with pytest.raises(ValueError, match="engagement"):
        client.send_event(
            domain="example.com",
            name="engagement",
            url="https://example.com/docs",
        )

    with pytest.raises(ValueError, match="engagement_time of 0"):
        client.send_event(
            domain="example.com",
            name="engagement",
            url="https://example.com/docs",
            engagement_time=0,
        )


@pytest.mark.parametrize(
    ("scroll_depth", "engagement_time"),
    [
        (101, None),
        (-1, None),
        (True, None),
        (None, 30 * 24 * 60 * 60 * 1000),
        (None, -5),
        (None, False),
    ],
)
def test_send_engagement_event_rejects_values_the_api_will_not_store(
    scroll_depth: object,
    engagement_time: object,
) -> None:
    """Values above 100 are stored as 100, and a huge time is ignored."""
    client = Client(api_key="test-key")

    with pytest.raises(ValueError):
        client.send_event(
            domain="example.com",
            name="engagement",
            url="https://example.com/docs",
            scroll_depth=scroll_depth,  # type: ignore[arg-type]
            engagement_time=engagement_time,  # type: ignore[arg-type]
        )


def test_scroll_depth_is_rejected_on_other_events() -> None:
    """The API only reads sd and e when the event name is engagement."""
    client = Client(api_key="test-key")

    with pytest.raises(ValueError, match="engagement"):
        client.send_event(
            domain="example.com",
            name="pageview",
            url="https://example.com/docs",
            scroll_depth=40,
        )


@pytest.mark.asyncio
async def test_async_send_engagement_event_requires_scroll_or_time() -> None:
    """The async client applies the same engagement checks."""
    client = AsyncClient(api_key="test-key")
    with pytest.raises(ValueError, match="engagement"):
        await client.send_event(
            domain="example.com",
            name="engagement",
            url="https://example.com/docs",
        )
    await client.close()


@respx.mock
@pytest.mark.parametrize(
    "revenue",
    [
        {"currency": "USD", "amount": 49.0},
        {"currency": "EUR", "amount": "1322.22"},
        {"currency": "JPY", "amount": 0},
        {"currency": "USD", "amount": "10abc"},
    ],
)
def test_send_event_keeps_revenue_the_pipeline_accepts(revenue: dict[str, object]) -> None:
    """Integers, finite floats, and numeric strings with a current code are kept."""
    route = respx.post("https://plausible.io/api/event").mock(
        return_value=httpx.Response(202, text="ok")
    )

    client = Client(api_key="test-key")
    result = client.send_event(
        domain="example.com",
        name="Purchase",
        url="https://example.com/thanks",
        revenue=revenue,
    )

    assert result.revenue_discarded is False
    assert json.loads(route.calls.last.request.content)["revenue"] == revenue


@respx.mock
@pytest.mark.parametrize(
    "revenue",
    [
        {"currency": "usd", "amount": 10},
        {"currency": "SLE", "amount": 10},
        {"currency": "USD", "amount": "nope"},
        {"currency": "USD", "amount": True},
        {"amount": 10},
        {"currency": "USD"},
    ],
)
def test_send_event_flags_revenue_the_pipeline_discards(revenue: dict[str, object]) -> None:
    """Invalid currency or amount is still HTTP 202, and the event is recorded."""
    route = respx.post("https://plausible.io/api/event").mock(
        return_value=httpx.Response(202, text="ok")
    )

    client = Client(api_key="test-key")
    result = client.send_event(
        domain="example.com",
        name="Purchase",
        url="https://example.com/thanks",
        revenue=revenue,
    )

    assert result.revenue_discarded is True
    assert result.dropped is False
    assert json.loads(route.calls.last.request.content)["revenue"] == revenue


def test_send_event_rejects_non_finite_revenue_before_sending() -> None:
    """NaN is not valid JSON, so the request parser never sees an event."""
    client = Client(api_key="test-key")

    with pytest.raises(ValueError, match="finite"):
        client.send_event(
            domain="example.com",
            name="Purchase",
            url="https://example.com/thanks",
            revenue={"currency": "USD", "amount": float("nan")},
        )


@pytest.mark.asyncio
@respx.mock
async def test_async_send_event_flags_discarded_revenue() -> None:
    """The async client reports the same revenue outcome."""
    respx.post("https://plausible.io/api/event").mock(return_value=httpx.Response(202, text="ok"))

    client = AsyncClient(api_key="test-key")
    result = await client.send_event(
        domain="example.com",
        name="Purchase",
        url="https://example.com/thanks",
        revenue={"currency": "usd", "amount": "49.00"},
    )

    assert result.revenue_discarded is True
    await client.close()


@respx.mock
def test_send_event_flags_properties_the_api_drops() -> None:
    """Blank, nested, and extra properties are dropped without failing the request."""
    route = respx.post("https://plausible.io/api/event").mock(
        return_value=httpx.Response(202, text="ok")
    )
    client = Client(api_key="test-key")

    blank = client.send_event(
        domain="example.com",
        name="signup",
        url="https://example.com/signup",
        props={"author": "   ", "plan": "pro"},
    )
    nested = client.send_event(
        domain="example.com",
        name="signup",
        url="https://example.com/signup",
        props={"plan": "pro", "meta": {"a": 1}},  # type: ignore[dict-item]
    )
    extra = {f"k{i}": str(i) for i in range(31)}
    overflow = client.send_event(
        domain="example.com",
        name="signup",
        url="https://example.com/signup",
        props=extra,
    )
    kept = client.send_event(
        domain="example.com",
        name="signup",
        url="https://example.com/signup",
        props={"n": 0, "flag": False, "label": "a"},
    )

    assert blank.props_discarded is True
    assert nested.props_discarded is True
    assert overflow.props_discarded is True
    assert kept.props_discarded is False
    sent = json.loads(route.calls.last.request.content)
    assert sent["props"]["n"] == 0
    assert sent["props"]["flag"] is False


@respx.mock
def test_send_event_counts_the_path_property_added_for_system_events() -> None:
    """404, form, and WP events gain a path property before the 30 cap."""
    respx.post("https://plausible.io/api/event").mock(return_value=httpx.Response(202, text="ok"))
    client = Client(api_key="test-key")

    thirty = {f"k{i}": i for i in range(30)}
    dropped = client.send_event(
        domain="example.com",
        name="404",
        url="https://example.com/missing",
        props=thirty,
    )
    kept = client.send_event(
        domain="example.com",
        name="404",
        url="https://example.com/missing",
        props={f"k{i}": i for i in range(29)},
    )
    explicit = dict(thirty)
    explicit["path"] = "/missing"
    explicit.pop("k0")
    with_path = client.send_event(
        domain="example.com",
        name="Form: Submission",
        url="https://example.com/contact",
        props=explicit,
    )

    assert dropped.props_discarded is True
    assert kept.props_discarded is False
    assert with_path.props_discarded is False
    assert len(explicit) == 30


@respx.mock
def test_send_event_drops_a_long_blank_property_instead_of_rejecting_it() -> None:
    """Length limits apply to stored values. A blank value is removed first."""
    route = respx.post("https://plausible.io/api/event").mock(
        return_value=httpx.Response(202, text="ok")
    )
    client = Client(api_key="test-key")
    result = client.send_event(
        domain="example.com",
        name="signup",
        url="https://example.com/signup",
        props={"note": " " * 2500, "plan": "pro"},
    )

    assert result.props_discarded is True
    assert "note" in json.loads(route.calls.last.request.content)["props"]


def test_send_event_rejects_property_values_that_are_not_json() -> None:
    """Null crashes property stringification, and NaN is not valid JSON."""
    client = Client(api_key="test-key")

    with pytest.raises(ValueError, match="finite"):
        client.send_event(
            domain="example.com",
            name="signup",
            url="https://example.com/signup",
            props={"score": float("nan")},
        )
    with pytest.raises(ValueError, match="boolean"):
        client.send_event(
            domain="example.com",
            name="signup",
            url="https://example.com/signup",
            props={"score": None},  # type: ignore[dict-item]
        )
    with pytest.raises(ValueError, match="keys"):
        client.send_event(
            domain="example.com",
            name="signup",
            url="https://example.com/signup",
            props={1: "a"},  # type: ignore[dict-item]
        )


@pytest.mark.asyncio
@respx.mock
async def test_async_send_event_flags_discarded_properties() -> None:
    """The async client reports the same property outcome."""
    respx.post("https://plausible.io/api/event").mock(return_value=httpx.Response(202, text="ok"))
    client = AsyncClient(api_key="test-key")
    result = await client.send_event(
        domain="example.com",
        name="signup",
        url="https://example.com/signup",
        props={"author": ""},
    )
    assert result.props_discarded is True
    await client.close()
