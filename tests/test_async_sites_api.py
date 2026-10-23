"""Tests for the async Sites API functionality."""

import httpx
import pytest
import respx

from plausible_client import AsyncClient


@respx.mock
@pytest.mark.asyncio
async def test_async_list_sites() -> None:
    """Test listing sites with async client."""
    respx.get("https://plausible.io/api/v1/sites").mock(
        return_value=httpx.Response(
            200,
            json={
                "sites": [
                    {"domain": "example.com", "timezone": "America/New_York"},
                    {"domain": "test.com", "timezone": "Europe/London"},
                ],
                "meta": {"after": None, "before": None, "limit": 100},
            },
        )
    )

    async with AsyncClient(api_key="test-key") as client:
        sites, meta = await client.list_sites()

        assert len(sites) == 2
        assert sites[0].domain == "example.com"
        assert sites[0].timezone == "America/New_York"


@respx.mock
@pytest.mark.asyncio
async def test_async_list_teams() -> None:
    """Test listing teams with async client."""
    respx.get("https://plausible.io/api/v1/sites/teams").mock(
        return_value=httpx.Response(
            200,
            json={
                "teams": [
                    {"id": "team-1", "name": "My Team", "api_available": True},
                ],
                "meta": {},
            },
        )
    )

    async with AsyncClient(api_key="test-key") as client:
        teams, meta = await client.list_teams()

        assert len(teams) == 1
        assert teams[0].id == "team-1"
        assert teams[0].name == "My Team"


@respx.mock
@pytest.mark.asyncio
async def test_async_get_site() -> None:
    """Test getting a specific site with async client."""
    respx.get("https://plausible.io/api/v1/sites/example.com").mock(
        return_value=httpx.Response(
            200,
            json={
                "domain": "example.com",
                "timezone": "America/New_York",
                "custom_properties": ["author"],
            },
        )
    )

    async with AsyncClient(api_key="test-key") as client:
        site = await client.get_site("example.com")

        assert site.domain == "example.com"
        assert site.timezone == "America/New_York"


@respx.mock
@pytest.mark.asyncio
async def test_async_create_site() -> None:
    """Test creating a new site with async client."""
    respx.post("https://plausible.io/api/v1/sites").mock(
        return_value=httpx.Response(
            200,
            json={
                "domain": "newsite.com",
                "timezone": "Europe/London",
                "custom_properties": [],
            },
        )
    )

    async with AsyncClient(api_key="test-key") as client:
        site = await client.create_site(
            domain="newsite.com",
            timezone="Europe/London",
        )

        assert site.domain == "newsite.com"


@respx.mock
@pytest.mark.asyncio
async def test_async_update_site() -> None:
    """Test updating a site with async client."""
    respx.put("https://plausible.io/api/v1/sites/old-domain.com").mock(
        return_value=httpx.Response(
            200,
            json={
                "domain": "new-domain.com",
                "timezone": "UTC",
                "custom_properties": [],
            },
        )
    )

    async with AsyncClient(api_key="test-key") as client:
        site = await client.update_site("old-domain.com", domain="new-domain.com")

        assert site.domain == "new-domain.com"


@respx.mock
@pytest.mark.asyncio
async def test_async_delete_site() -> None:
    """Test deleting a site with async client."""
    respx.delete("https://plausible.io/api/v1/sites/example.com").mock(
        return_value=httpx.Response(200, json={"deleted": "true"})
    )

    async with AsyncClient(api_key="test-key") as client:
        result = await client.delete_site("example.com")

        assert result is True


@respx.mock
@pytest.mark.asyncio
async def test_async_list_goals() -> None:
    """Test listing goals with async client."""
    respx.get("https://plausible.io/api/v1/sites/goals").mock(
        return_value=httpx.Response(
            200,
            json={
                "goals": [
                    {
                        "id": "1",
                        "goal_type": "event",
                        "display_name": "Signup",
                        "event_name": "Signup",
                        "page_path": None,
                        "custom_props": {},
                    },
                ],
                "meta": {},
            },
        )
    )

    async with AsyncClient(api_key="test-key") as client:
        goals, meta = await client.list_goals("example.com")

        assert len(goals) == 1
        assert goals[0].event_name == "Signup"


@respx.mock
@pytest.mark.asyncio
async def test_async_create_goal() -> None:
    """Test creating a goal with async client."""
    respx.put("https://plausible.io/api/v1/sites/goals").mock(
        return_value=httpx.Response(
            200,
            json={
                "id": "3",
                "goal_type": "event",
                "display_name": "Purchase",
                "event_name": "Purchase",
                "page_path": None,
                "custom_props": {},
            },
        )
    )

    async with AsyncClient(api_key="test-key") as client:
        goal = await client.create_goal(
            site_id="example.com",
            goal_type="event",
            event_name="Purchase",
        )

        assert goal.event_name == "Purchase"


@respx.mock
@pytest.mark.asyncio
async def test_async_delete_goal() -> None:
    """Test deleting a goal with async client."""
    respx.delete("https://plausible.io/api/v1/sites/goals/1").mock(
        return_value=httpx.Response(200, json={"deleted": "true"})
    )

    async with AsyncClient(api_key="test-key") as client:
        result = await client.delete_goal("example.com", "1")

        assert result is True


@respx.mock
@pytest.mark.asyncio
async def test_async_create_shared_link() -> None:
    """Test creating a shared link with async client."""
    respx.put("https://plausible.io/api/v1/sites/shared-links").mock(
        return_value=httpx.Response(
            200,
            json={
                "name": "Dashboard",
                "url": "https://plausible.io/share/example.com?auth=abc123",
            },
        )
    )

    async with AsyncClient(api_key="test-key") as client:
        link = await client.create_shared_link("example.com", "Dashboard")

        assert link.name == "Dashboard"


@respx.mock
@pytest.mark.asyncio
async def test_async_list_custom_properties() -> None:
    """Test listing custom properties with async client."""
    respx.get("https://plausible.io/api/v1/sites/custom-props").mock(
        return_value=httpx.Response(
            200,
            json={
                "custom_properties": [
                    {"property": "author"},
                ]
            },
        )
    )

    async with AsyncClient(api_key="test-key") as client:
        props = await client.list_custom_properties("example.com")

        assert len(props) == 1
        assert "author" in props


@respx.mock
@pytest.mark.asyncio
async def test_async_create_custom_property() -> None:
    """Test creating a custom property with async client."""
    respx.put("https://plausible.io/api/v1/sites/custom-props").mock(
        return_value=httpx.Response(200, json={"created": True})
    )

    async with AsyncClient(api_key="test-key") as client:
        result = await client.create_custom_property("example.com", "author")

        assert result is True


@respx.mock
@pytest.mark.asyncio
async def test_async_delete_custom_property() -> None:
    """Test deleting a custom property with async client."""
    respx.delete("https://plausible.io/api/v1/sites/custom-props/author").mock(
        return_value=httpx.Response(200, json={"deleted": True})
    )

    async with AsyncClient(api_key="test-key") as client:
        result = await client.delete_custom_property("example.com", "author")

        assert result is True


@respx.mock
@pytest.mark.asyncio
async def test_async_list_guests() -> None:
    """Test listing guests with async client."""
    respx.get("https://plausible.io/api/v1/sites/guests").mock(
        return_value=httpx.Response(
            200,
            json={
                "guests": [
                    {"email": "alice@example.com", "role": "viewer", "status": "accepted"},
                ],
                "meta": {},
            },
        )
    )

    async with AsyncClient(api_key="test-key") as client:
        guests, meta = await client.list_guests("example.com")

        assert len(guests) == 1
        assert guests[0].email == "alice@example.com"


@respx.mock
@pytest.mark.asyncio
async def test_async_invite_guest() -> None:
    """Test inviting a guest with async client."""
    respx.put("https://plausible.io/api/v1/sites/guests").mock(
        return_value=httpx.Response(
            200,
            json={"email": "charlie@example.com", "role": "editor", "status": "invited"},
        )
    )

    async with AsyncClient(api_key="test-key") as client:
        guest = await client.invite_guest("example.com", "charlie@example.com", "editor")

        assert guest.email == "charlie@example.com"


@respx.mock
@pytest.mark.asyncio
async def test_async_delete_guest() -> None:
    """Test deleting a guest with async client."""
    respx.delete("https://plausible.io/api/v1/sites/guests/alice@example.com").mock(
        return_value=httpx.Response(200, json={"deleted": "true"})
    )

    async with AsyncClient(api_key="test-key") as client:
        result = await client.delete_guest("example.com", "alice@example.com")

        assert result is True
