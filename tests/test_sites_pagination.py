"""Tests for walking Sites API cursor pages."""

import httpx
import pytest
import respx

from plausible_client import AsyncClient, Client, PlausibleError


def _page(items_key: str, items: list[dict[str, object]], after: str | None) -> httpx.Response:
    return httpx.Response(
        200, json={items_key: items, "meta": {"after": after, "before": None, "limit": 1}}
    )


@respx.mock
def test_list_all_sites_follows_after_cursor() -> None:
    """A second page is requested with the same limit and the after cursor."""
    route = respx.get("https://plausible.io/api/v1/sites").mock(
        side_effect=[
            _page("sites", [{"domain": "a.example", "timezone": "Etc/UTC"}], "cursor-1"),
            _page("sites", [{"domain": "b.example", "timezone": "Europe/Tallinn"}], None),
        ]
    )

    client = Client(api_key="test-key")
    sites = client.list_all_sites(page_size=1, team_id="team-1")

    assert [site.domain for site in sites] == ["a.example", "b.example"]
    assert len(route.calls) == 2
    first = route.calls[0].request.url.params
    second = route.calls[1].request.url.params
    assert first["limit"] == "1"
    assert second["limit"] == "1"
    assert "after" not in first
    assert second["after"] == "cursor-1"
    assert first["team_id"] == "team-1"
    assert second["team_id"] == "team-1"


@respx.mock
def test_list_all_sites_stops_on_a_single_page() -> None:
    """after: null means the list is complete."""
    respx.get("https://plausible.io/api/v1/sites").mock(
        return_value=_page("sites", [{"domain": "only.example", "timezone": "Etc/UTC"}], None)
    )

    client = Client(api_key="test-key")

    sites = client.list_all_sites()

    assert [site.domain for site in sites] == ["only.example"]


@respx.mock
def test_list_all_sites_rejects_a_repeated_cursor() -> None:
    """The same after cursor would request the same page forever."""
    respx.get("https://plausible.io/api/v1/sites").mock(
        return_value=_page("sites", [{"domain": "a.example", "timezone": "Etc/UTC"}], "stuck")
    )

    client = Client(api_key="test-key")

    with pytest.raises(PlausibleError, match="did not advance"):
        client.list_all_sites(page_size=1)


@pytest.mark.parametrize("page_size", [0, 101, True])
def test_list_all_sites_rejects_page_sizes_the_api_ignores(page_size: int) -> None:
    """Limits above 100 are dropped by the pagination helper and become the default."""
    client = Client(api_key="test-key")

    with pytest.raises(ValueError, match="page_size"):
        client.list_all_sites(page_size=page_size)


@respx.mock
def test_list_all_goals_and_guests_and_teams() -> None:
    """Goals, guests, and teams use the same after cursor."""
    respx.get("https://plausible.io/api/v1/sites/goals").mock(
        side_effect=[
            _page(
                "goals",
                [{"id": 1, "goal_type": "event", "display_name": "Signup"}],
                "g2",
            ),
            _page(
                "goals",
                [{"id": "2", "goal_type": "page", "display_name": "Visit /"}],
                None,
            ),
        ]
    )
    respx.get("https://plausible.io/api/v1/sites/guests").mock(
        return_value=_page(
            "guests",
            [{"email": "viewer@example.com", "role": "viewer", "status": "invited"}],
            None,
        )
    )
    respx.get("https://plausible.io/api/v1/sites/teams").mock(
        return_value=_page("teams", [{"id": "team-1", "name": "Team", "api_available": True}], None)
    )

    client = Client(api_key="test-key")

    goals = client.list_all_goals("example.com", page_size=1)
    guests = client.list_all_guests("example.com")
    teams = client.list_all_teams()

    assert [goal.id for goal in goals] == ["1", "2"]
    assert guests[0].email == "viewer@example.com"
    assert teams[0].api_available is True


@pytest.mark.asyncio
@respx.mock
async def test_async_list_all_sites_follows_after_cursor() -> None:
    """The async client walks the same cursor."""
    respx.get("https://plausible.io/api/v1/sites").mock(
        side_effect=[
            _page("sites", [{"domain": "a.example", "timezone": "Etc/UTC"}], "cursor-1"),
            _page("sites", [{"domain": "b.example", "timezone": "Etc/UTC"}], None),
        ]
    )

    async with AsyncClient(api_key="test-key") as client:
        sites = await client.list_all_sites(page_size=1)

    assert [site.domain for site in sites] == ["a.example", "b.example"]
