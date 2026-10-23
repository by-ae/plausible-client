"""Tests for the Sites API functionality."""

import httpx
import pytest
import respx

from plausible_client import (
    AuthenticationError,
    Client,
    InvalidQueryError,
)


@respx.mock
def test_list_sites() -> None:
    """Test listing sites."""
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

    client = Client(api_key="test-key")
    sites, meta = client.list_sites()

    assert len(sites) == 2
    assert sites[0].domain == "example.com"
    assert sites[0].timezone == "America/New_York"
    assert sites[1].domain == "test.com"
    assert meta["limit"] == 100


@respx.mock
def test_list_sites_with_pagination() -> None:
    """Test listing sites with pagination parameters."""
    route = respx.get("https://plausible.io/api/v1/sites").mock(
        return_value=httpx.Response(
            200,
            json={
                "sites": [{"domain": "example.com", "timezone": "UTC"}],
                "meta": {"after": "cursor123", "before": None, "limit": 50},
            },
        )
    )

    client = Client(api_key="test-key")
    sites, meta = client.list_sites(limit=50, after="cursor123", team_id="team-123")

    assert len(sites) == 1
    assert route.calls.last.request.url.params["limit"] == "50"
    assert route.calls.last.request.url.params["after"] == "cursor123"
    assert route.calls.last.request.url.params["team_id"] == "team-123"


@respx.mock
def test_list_teams() -> None:
    """Test listing teams."""
    respx.get("https://plausible.io/api/v1/sites/teams").mock(
        return_value=httpx.Response(
            200,
            json={
                "teams": [
                    {"id": "team-1", "name": "My Team", "api_available": True},
                    {"id": "team-2", "name": "Other Team", "api_available": False},
                ],
                "meta": {},
            },
        )
    )

    client = Client(api_key="test-key")
    teams, meta = client.list_teams()

    assert len(teams) == 2
    assert teams[0].id == "team-1"
    assert teams[0].name == "My Team"
    assert teams[0].api_available is True
    assert teams[1].api_available is False


@respx.mock
def test_get_site() -> None:
    """Test getting a specific site."""
    respx.get("https://plausible.io/api/v1/sites/example.com").mock(
        return_value=httpx.Response(
            200,
            json={
                "domain": "example.com",
                "timezone": "America/New_York",
                "custom_properties": ["author", "title"],
                "tracker_script_configuration": {
                    "id": "pa-123",
                    "installation_type": "wordpress",
                    "track_404_pages": True,
                    "hash_based_routing": False,
                    "outbound_links": True,
                    "file_downloads": True,
                    "revenue_tracking": False,
                    "tagged_events": False,
                    "form_submissions": True,
                    "pageview_props": False,
                },
            },
        )
    )

    client = Client(api_key="test-key")
    site = client.get_site("example.com")

    assert site.domain == "example.com"
    assert site.timezone == "America/New_York"
    assert "author" in site.custom_properties
    assert site.tracker_script_configuration is not None
    assert site.tracker_script_configuration.id == "pa-123"
    assert site.tracker_script_configuration.track_404_pages is True
    assert site.tracker_script_configuration.outbound_links is True


@respx.mock
def test_create_site() -> None:
    """Test creating a new site."""
    route = respx.post("https://plausible.io/api/v1/sites").mock(
        return_value=httpx.Response(
            200,
            json={
                "domain": "newsite.com",
                "timezone": "Europe/London",
                "custom_properties": [],
                "tracker_script_configuration": {
                    "id": "pa-456",
                    "installation_type": None,
                    "track_404_pages": False,
                    "hash_based_routing": False,
                    "outbound_links": False,
                    "file_downloads": True,
                    "revenue_tracking": False,
                    "tagged_events": False,
                    "form_submissions": False,
                    "pageview_props": False,
                },
            },
        )
    )

    client = Client(api_key="test-key")
    site = client.create_site(
        domain="newsite.com",
        timezone="Europe/London",
        tracker_script_configuration={"file_downloads": True},
    )

    assert site.domain == "newsite.com"
    assert site.timezone == "Europe/London"
    assert route.called

    request = route.calls.last.request
    payload = request.read()
    assert b"newsite.com" in payload
    assert b"Europe/London" in payload


@respx.mock
def test_update_site() -> None:
    """Test updating a site."""
    route = respx.put("https://plausible.io/api/v1/sites/old-domain.com").mock(
        return_value=httpx.Response(
            200,
            json={
                "domain": "new-domain.com",
                "timezone": "UTC",
                "custom_properties": [],
            },
        )
    )

    client = Client(api_key="test-key")
    site = client.update_site("old-domain.com", domain="new-domain.com")

    assert site.domain == "new-domain.com"
    assert route.called


@respx.mock
def test_delete_site() -> None:
    """Test deleting a site."""
    respx.delete("https://plausible.io/api/v1/sites/example.com").mock(
        return_value=httpx.Response(200, json={"deleted": "true"})
    )

    client = Client(api_key="test-key")
    result = client.delete_site("example.com")

    assert result is True


@respx.mock
def test_list_goals() -> None:
    """Test listing goals for a site."""
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
                    {
                        "id": "2",
                        "goal_type": "page",
                        "display_name": "Visit /register",
                        "event_name": None,
                        "page_path": "/register",
                        "custom_props": {},
                    },
                ],
                "meta": {},
            },
        )
    )

    client = Client(api_key="test-key")
    goals, meta = client.list_goals("example.com")

    assert len(goals) == 2
    assert goals[0].goal_type == "event"
    assert goals[0].event_name == "Signup"
    assert goals[1].goal_type == "page"
    assert goals[1].page_path == "/register"


@respx.mock
def test_create_goal() -> None:
    """Test creating a goal."""
    route = respx.put("https://plausible.io/api/v1/sites/goals").mock(
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

    client = Client(api_key="test-key")
    goal = client.create_goal(
        site_id="example.com",
        goal_type="event",
        event_name="Purchase",
        display_name="Purchase",
    )

    assert goal.goal_type == "event"
    assert goal.event_name == "Purchase"
    assert route.called


@respx.mock
def test_delete_goal() -> None:
    """Test deleting a goal."""
    respx.delete("https://plausible.io/api/v1/sites/goals/1").mock(
        return_value=httpx.Response(200, json={"deleted": "true"})
    )

    client = Client(api_key="test-key")
    result = client.delete_goal("example.com", "1")

    assert result is True


@respx.mock
def test_create_shared_link() -> None:
    """Test creating a shared link."""
    respx.put("https://plausible.io/api/v1/sites/shared-links").mock(
        return_value=httpx.Response(
            200,
            json={
                "name": "Dashboard",
                "url": "https://plausible.io/share/example.com?auth=abc123",
            },
        )
    )

    client = Client(api_key="test-key")
    link = client.create_shared_link("example.com", "Dashboard")

    assert link.name == "Dashboard"
    assert "example.com" in link.url


@respx.mock
def test_list_custom_properties() -> None:
    """Test listing custom properties."""
    respx.get("https://plausible.io/api/v1/sites/custom-props").mock(
        return_value=httpx.Response(
            200,
            json={
                "custom_properties": [
                    {"property": "author"},
                    {"property": "category"},
                ]
            },
        )
    )

    client = Client(api_key="test-key")
    props = client.list_custom_properties("example.com")

    assert len(props) == 2
    assert "author" in props
    assert "category" in props


@respx.mock
def test_create_custom_property() -> None:
    """Test creating a custom property."""
    respx.put("https://plausible.io/api/v1/sites/custom-props").mock(
        return_value=httpx.Response(200, json={"created": True})
    )

    client = Client(api_key="test-key")
    result = client.create_custom_property("example.com", "author")

    assert result is True


@respx.mock
def test_delete_custom_property() -> None:
    """Test deleting a custom property."""
    respx.delete("https://plausible.io/api/v1/sites/custom-props/author").mock(
        return_value=httpx.Response(200, json={"deleted": True})
    )

    client = Client(api_key="test-key")
    result = client.delete_custom_property("example.com", "author")

    assert result is True


@respx.mock
def test_list_guests() -> None:
    """Test listing guests for a site."""
    respx.get("https://plausible.io/api/v1/sites/guests").mock(
        return_value=httpx.Response(
            200,
            json={
                "guests": [
                    {"email": "alice@example.com", "role": "viewer", "status": "accepted"},
                    {"email": "bob@example.com", "role": "editor", "status": "invited"},
                ],
                "meta": {},
            },
        )
    )

    client = Client(api_key="test-key")
    guests, meta = client.list_guests("example.com")

    assert len(guests) == 2
    assert guests[0].email == "alice@example.com"
    assert guests[0].role == "viewer"
    assert guests[0].status == "accepted"
    assert guests[1].status == "invited"


@respx.mock
def test_invite_guest() -> None:
    """Test inviting a guest."""
    respx.put("https://plausible.io/api/v1/sites/guests").mock(
        return_value=httpx.Response(
            200,
            json={"email": "charlie@example.com", "role": "editor", "status": "invited"},
        )
    )

    client = Client(api_key="test-key")
    guest = client.invite_guest("example.com", "charlie@example.com", "editor")

    assert guest.email == "charlie@example.com"
    assert guest.role == "editor"
    assert guest.status == "invited"


@respx.mock
def test_delete_guest() -> None:
    """Test deleting a guest."""
    respx.delete("https://plausible.io/api/v1/sites/guests/alice@example.com").mock(
        return_value=httpx.Response(200, json={"deleted": "true"})
    )

    client = Client(api_key="test-key")
    result = client.delete_guest("example.com", "alice@example.com")

    assert result is True


@respx.mock
def test_sites_api_authentication_error() -> None:
    """Test authentication error in Sites API."""
    respx.get("https://plausible.io/api/v1/sites").mock(
        return_value=httpx.Response(401, json={"error": "Invalid API key"})
    )

    client = Client(api_key="invalid-key")

    with pytest.raises(AuthenticationError):
        client.list_sites()


@respx.mock
def test_sites_api_invalid_request() -> None:
    """Test invalid request error in Sites API."""
    respx.post("https://plausible.io/api/v1/sites").mock(
        return_value=httpx.Response(400, json={"error": "Domain already exists", "domain": "taken"})
    )

    client = Client(api_key="test-key")

    with pytest.raises(InvalidQueryError) as exc_info:
        client.create_site("taken.com")

    assert "Domain already exists" in str(exc_info.value)
