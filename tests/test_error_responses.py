"""Tests for Sites API success flags and previously uncovered error paths."""

import httpx
import pytest
import respx

from plausible_client import (
    AsyncClient,
    Client,
    ForbiddenError,
    InvalidQueryError,
    Metric,
    NotFoundError,
    PlausibleError,
    QueryBuilder,
)


@respx.mock
def test_delete_site_accepts_boolean_true() -> None:
    """The Sites API returns {"deleted": true}, not the string "true"."""
    respx.delete("https://plausible.io/api/v1/sites/example.com").mock(
        return_value=httpx.Response(200, json={"deleted": True})
    )

    client = Client(api_key="test-key")

    assert client.delete_site("example.com") is True


@respx.mock
def test_delete_goal_and_guest_accept_boolean_true() -> None:
    """Goal and guest deletion use the same boolean flag."""
    respx.delete("https://plausible.io/api/v1/sites/goals/1").mock(
        return_value=httpx.Response(200, json={"deleted": True})
    )
    respx.delete("https://plausible.io/api/v1/sites/guests/alice@example.com").mock(
        return_value=httpx.Response(200, json={"deleted": True})
    )

    client = Client(api_key="test-key")

    assert client.delete_goal("example.com", "1") is True
    assert client.delete_guest("example.com", "alice@example.com") is True


@respx.mock
def test_delete_site_still_accepts_documented_string() -> None:
    """Published examples show the string "true"; keep accepting that too."""
    respx.delete("https://plausible.io/api/v1/sites/example.com").mock(
        return_value=httpx.Response(200, json={"deleted": "true"})
    )

    client = Client(api_key="test-key")

    assert client.delete_site("example.com") is True


@pytest.mark.asyncio
@respx.mock
async def test_async_delete_site_accepts_boolean_true() -> None:
    """Async deletion uses the same boolean success flag."""
    respx.delete("https://plausible.io/api/v1/sites/example.com").mock(
        return_value=httpx.Response(200, json={"deleted": True})
    )

    client = AsyncClient(api_key="test-key")

    assert await client.delete_site("example.com") is True
    await client.close()


@respx.mock
def test_get_site_not_found_includes_api_message() -> None:
    """Missing sites are 404 with an error string, not a generic unexpected error."""
    route = respx.get("https://plausible.io/api/v1/sites/missing.example").mock(
        return_value=httpx.Response(404, json={"error": "Site could not be found"})
    )

    client = Client(api_key="test-key")

    with pytest.raises(NotFoundError) as exc_info:
        client.get_site("missing.example")

    assert exc_info.value.status_code == 404
    assert str(exc_info.value) == "Site could not be found"
    assert route.call_count == 1


@pytest.mark.asyncio
@respx.mock
async def test_async_get_site_not_found() -> None:
    """Async client maps 404 the same way."""
    respx.get("https://plausible.io/api/v1/sites/missing.example").mock(
        return_value=httpx.Response(404, json={"error": "Site could not be found"})
    )

    client = AsyncClient(api_key="test-key")

    with pytest.raises(NotFoundError) as exc_info:
        await client.get_site("missing.example")

    assert str(exc_info.value) == "Site could not be found"
    await client.close()


@respx.mock
def test_create_site_forbidden_includes_api_message() -> None:
    """403 responses carry the permission error from the API."""
    respx.post("https://plausible.io/api/v1/sites").mock(
        return_value=httpx.Response(
            403, json={"error": "You can't add sites to the selected team."}
        )
    )

    client = Client(api_key="test-key")

    with pytest.raises(ForbiddenError) as exc_info:
        client.create_site("newsite.com")

    assert exc_info.value.status_code == 403
    assert "can't add sites" in str(exc_info.value)


@respx.mock
def test_non_json_400_is_invalid_query() -> None:
    """A 400 body that is not JSON still raises InvalidQueryError."""
    respx.post("https://plausible.io/api/v2/query").mock(
        return_value=httpx.Response(400, content=b"nope")
    )

    client = Client(api_key="test-key")

    with pytest.raises(InvalidQueryError) as exc_info:
        client.query(QueryBuilder("example.com").metrics(Metric.VISITORS))

    assert str(exc_info.value) == "Invalid query"
    assert exc_info.value.errors is None


@respx.mock
def test_event_validation_errors_are_included() -> None:
    """Events API validation failures use an errors object rather than error."""
    respx.post("https://plausible.io/api/event").mock(
        return_value=httpx.Response(400, json={"errors": {"url": ["can't be blank"]}})
    )

    client = Client(api_key="test-key")

    with pytest.raises(InvalidQueryError) as exc_info:
        client.send_event(domain="example.com", name="pageview", url="https://example.com")

    assert "can't be blank" in str(exc_info.value)
    assert exc_info.value.errors == {"errors": {"url": ["can't be blank"]}}


@respx.mock
def test_unexpected_status_keeps_status_code() -> None:
    """Statuses without a dedicated exception stay on PlausibleError."""
    respx.post("https://plausible.io/api/v2/query").mock(return_value=httpx.Response(418))

    client = Client(api_key="test-key")

    with pytest.raises(PlausibleError) as exc_info:
        client.query(QueryBuilder("example.com").metrics(Metric.VISITORS))

    assert type(exc_info.value) is PlausibleError
    assert exc_info.value.status_code == 418
    assert "418" in str(exc_info.value)
