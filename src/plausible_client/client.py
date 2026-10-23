"""Synchronous Plausible API client."""

from typing import Any

import httpx

from plausible_client._retry import retry_sync
from plausible_client.errors import (
    AuthenticationError,
    InvalidQueryError,
    PlausibleError,
    ServerError,
)
from plausible_client.models import Goal, Guest, QueryResult, SharedLink, Site, Team
from plausible_client.query import QueryBuilder


class Client:
    """Synchronous client for Plausible Analytics API."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://plausible.io",
        timeout: float = 30.0,
    ) -> None:
        """
        Initialize the Plausible client.

        Args:
            api_key: Plausible API key
            base_url: Base URL for the Plausible instance (for self-hosted)
            timeout: Request timeout in seconds
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client = httpx.Client(
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout,
        )

    def __enter__(self) -> "Client":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()

    def query(self, query_builder: QueryBuilder) -> QueryResult:
        """
        Execute a Stats API v2 query.

        Args:
            query_builder: QueryBuilder instance with the query configuration

        Returns:
            QueryResult with the API response

        Raises:
            AuthenticationError: If authentication fails
            InvalidQueryError: If the query is invalid
            RateLimitError: If rate limit is exceeded
            ServerError: If server returns 5xx error
        """
        payload = query_builder.build()
        response = retry_sync(
            self._client.post,
            f"{self.base_url}/api/v2/query",
            json=payload,
        )
        result = self._handle_response(response, QueryResult)
        assert result is not None
        return result

    def query_all(self, query_builder: QueryBuilder, page_size: int = 1000) -> QueryResult:
        """
        Execute a Stats API v2 query and automatically fetch all pages.

        This method handles pagination automatically by making multiple requests
        until all results are retrieved. The QueryBuilder's limit/offset settings
        are overridden.

        Args:
            query_builder: QueryBuilder instance with the query configuration
            page_size: Number of results per page (1 to 10000, default 1000)

        Returns:
            QueryResult with all results combined

        Raises:
            ValueError: If page_size is not between 1 and 10000
            AuthenticationError: If authentication fails
            InvalidQueryError: If the query is invalid
            RateLimitError: If rate limit is exceeded
            ServerError: If server returns 5xx error
        """
        if not 1 <= page_size <= 10000:
            raise ValueError(f"page_size must be between 1 and 10000, got {page_size}")

        all_results: list[dict[str, Any]] = []
        offset = 0
        combined_meta: dict[str, Any] = {}

        while True:
            page_query = query_builder.copy()
            page_query._limit = page_size
            page_query._offset = offset
            page_query._include["total_rows"] = True

            result = self.query(page_query)

            if not result.results:
                break

            all_results.extend(result.results)

            if not combined_meta:
                combined_meta = result.meta.copy()
            else:
                combined_meta.update(result.meta)

            total_rows = result.meta.get("total_rows")
            if total_rows is None or offset + page_size >= total_rows:
                break

            offset += page_size

        combined_meta["total_rows"] = len(all_results)
        return QueryResult(results=all_results, meta=combined_meta)

    def send_event(
        self,
        domain: str,
        name: str,
        url: str,
        user_agent: str | None = None,
        x_forwarded_for: str | None = None,
        props: dict[str, str | int | float | bool] | None = None,
        revenue: dict[str, Any] | None = None,
    ) -> None:
        """
        Send a custom event or pageview to Plausible.

        Args:
            domain: Domain of the site (e.g., "example.com")
            name: Event name (use "pageview" for pageviews)
            url: Full URL where the event occurred
            user_agent: User-Agent header from the visitor (recommended)
            x_forwarded_for: X-Forwarded-For header for visitor IP (recommended)
            props: Custom properties (max 30 properties)
            revenue: Revenue data with amount and currency

        Raises:
            AuthenticationError: If authentication fails
            InvalidQueryError: If the event data is invalid
            RateLimitError: If rate limit is exceeded
            ServerError: If server returns 5xx error
        """
        headers: dict[str, str] = {}
        if user_agent:
            headers["User-Agent"] = user_agent
        if x_forwarded_for:
            headers["X-Forwarded-For"] = x_forwarded_for

        payload: dict[str, Any] = {
            "domain": domain,
            "name": name,
            "url": url,
        }

        if props:
            payload["props"] = props

        if revenue:
            payload["revenue"] = revenue

        response = retry_sync(
            self._client.post,
            f"{self.base_url}/api/event",
            json=payload,
            headers=headers,
        )
        self._handle_response(response)

    def list_sites(
        self,
        limit: int = 100,
        after: str | None = None,
        before: str | None = None,
        team_id: str | None = None,
    ) -> tuple[list[Site], dict[str, Any]]:
        """
        List sites accessible to this API key.

        Args:
            limit: Maximum number of sites to return (default 100)
            after: Pagination cursor for next page
            before: Pagination cursor for previous page
            team_id: Filter by team ID

        Returns:
            Tuple of (list of Site objects, pagination metadata)

        Raises:
            AuthenticationError: If authentication fails
            ServerError: If server returns 5xx error
        """
        params: dict[str, Any] = {"limit": limit}
        if after:
            params["after"] = after
        if before:
            params["before"] = before
        if team_id:
            params["team_id"] = team_id

        response = retry_sync(
            self._client.get,
            f"{self.base_url}/api/v1/sites",
            params=params,
        )
        data = self._handle_json_response(response)
        sites = [Site.from_dict(site_data) for site_data in data["sites"]]
        return sites, data.get("meta", {})

    def list_teams(
        self,
        limit: int = 100,
        after: str | None = None,
        before: str | None = None,
    ) -> tuple[list[Team], dict[str, Any]]:
        """
        List teams accessible to this API key.

        Args:
            limit: Maximum number of teams to return (default 100)
            after: Pagination cursor for next page
            before: Pagination cursor for previous page

        Returns:
            Tuple of (list of Team objects, pagination metadata)

        Raises:
            AuthenticationError: If authentication fails
            ServerError: If server returns 5xx error
        """
        params: dict[str, Any] = {"limit": limit}
        if after:
            params["after"] = after
        if before:
            params["before"] = before

        response = retry_sync(
            self._client.get,
            f"{self.base_url}/api/v1/sites/teams",
            params=params,
        )
        data = self._handle_json_response(response)
        teams = [Team.from_dict(team_data) for team_data in data["teams"]]
        return teams, data.get("meta", {})

    def get_site(self, site_id: str) -> Site:
        """
        Get details of a specific site.

        Args:
            site_id: Domain of the site

        Returns:
            Site object with full details

        Raises:
            AuthenticationError: If authentication fails
            ServerError: If server returns 5xx error
        """
        response = retry_sync(
            self._client.get,
            f"{self.base_url}/api/v1/sites/{site_id}",
        )
        data = self._handle_json_response(response)
        return Site.from_dict(data)

    def create_site(
        self,
        domain: str,
        timezone: str = "Etc/UTC",
        team_id: str | None = None,
        tracker_script_configuration: dict[str, Any] | None = None,
    ) -> Site:
        """
        Create a new site in Plausible.

        Args:
            domain: Domain of the site (must be globally unique)
            timezone: IANA timezone name (default: Etc/UTC)
            team_id: ID of the team to create the site under
            tracker_script_configuration: Optional tracker configuration

        Returns:
            Created Site object

        Raises:
            AuthenticationError: If authentication fails
            InvalidQueryError: If the domain is already taken or data is invalid
            ServerError: If server returns 5xx error
        """
        payload: dict[str, Any] = {
            "domain": domain,
            "timezone": timezone,
        }
        if team_id:
            payload["team_id"] = team_id
        if tracker_script_configuration:
            payload["tracker_script_configuration"] = tracker_script_configuration

        response = retry_sync(
            self._client.post,
            f"{self.base_url}/api/v1/sites",
            json=payload,
        )
        data = self._handle_json_response(response)
        return Site.from_dict(data)

    def update_site(
        self,
        site_id: str,
        domain: str | None = None,
        tracker_script_configuration: dict[str, Any] | None = None,
    ) -> Site:
        """
        Update an existing site.

        Args:
            site_id: Current domain of the site
            domain: New domain (optional)
            tracker_script_configuration: Updated tracker configuration (optional)

        Returns:
            Updated Site object

        Raises:
            AuthenticationError: If authentication fails
            InvalidQueryError: If the new domain is already taken
            ServerError: If server returns 5xx error
        """
        payload: dict[str, Any] = {}
        if domain:
            payload["domain"] = domain
        if tracker_script_configuration:
            payload["tracker_script_configuration"] = tracker_script_configuration

        response = retry_sync(
            self._client.put,
            f"{self.base_url}/api/v1/sites/{site_id}",
            json=payload,
        )
        data = self._handle_json_response(response)
        return Site.from_dict(data)

    def delete_site(self, site_id: str) -> bool:
        """
        Delete a site from Plausible.

        Args:
            site_id: Domain of the site to delete

        Returns:
            True if deletion was successful

        Raises:
            AuthenticationError: If authentication fails
            ServerError: If server returns 5xx error
        """
        response = retry_sync(
            self._client.delete,
            f"{self.base_url}/api/v1/sites/{site_id}",
        )
        data = self._handle_json_response(response)
        return data.get("deleted") == "true"

    def list_goals(
        self,
        site_id: str,
        limit: int = 100,
        after: str | None = None,
        before: str | None = None,
    ) -> tuple[list[Goal], dict[str, Any]]:
        """
        List goals for a site.

        Args:
            site_id: Domain of the site
            limit: Maximum number of goals to return (default 100)
            after: Pagination cursor for next page
            before: Pagination cursor for previous page

        Returns:
            Tuple of (list of Goal objects, pagination metadata)

        Raises:
            AuthenticationError: If authentication fails
            ServerError: If server returns 5xx error
        """
        params: dict[str, Any] = {"site_id": site_id, "limit": limit}
        if after:
            params["after"] = after
        if before:
            params["before"] = before

        response = retry_sync(
            self._client.get,
            f"{self.base_url}/api/v1/sites/goals",
            params=params,
        )
        data = self._handle_json_response(response)
        goals = [Goal.from_dict(goal_data) for goal_data in data["goals"]]
        return goals, data.get("meta", {})

    def create_goal(
        self,
        site_id: str,
        goal_type: str,
        event_name: str | None = None,
        page_path: str | None = None,
        display_name: str | None = None,
        custom_props: dict[str, Any] | None = None,
    ) -> Goal:
        """
        Create or find a goal for a site (idempotent).

        Args:
            site_id: Domain of the site
            goal_type: Type of goal ("event" or "page")
            event_name: Event name (required if goal_type is "event")
            page_path: Page path (required if goal_type is "page")
            display_name: Display name for the goal (optional)
            custom_props: Custom properties for the goal (optional)

        Returns:
            Goal object

        Raises:
            AuthenticationError: If authentication fails
            InvalidQueryError: If the goal data is invalid
            ServerError: If server returns 5xx error
        """
        payload: dict[str, Any] = {
            "site_id": site_id,
            "goal_type": goal_type,
        }
        if event_name:
            payload["event_name"] = event_name
        if page_path:
            payload["page_path"] = page_path
        if display_name:
            payload["display_name"] = display_name
        if custom_props:
            payload["custom_props"] = custom_props

        response = retry_sync(
            self._client.put,
            f"{self.base_url}/api/v1/sites/goals",
            json=payload,
        )
        data = self._handle_json_response(response)
        return Goal.from_dict(data)

    def delete_goal(self, site_id: str, goal_id: str) -> bool:
        """
        Delete a goal from a site.

        Args:
            site_id: Domain of the site
            goal_id: ID of the goal to delete

        Returns:
            True if deletion was successful

        Raises:
            AuthenticationError: If authentication fails
            ServerError: If server returns 5xx error
        """
        response = retry_sync(
            self._client.request,
            "DELETE",
            f"{self.base_url}/api/v1/sites/goals/{goal_id}",
            json={"site_id": site_id},
        )
        data = self._handle_json_response(response)
        return data.get("deleted") == "true"

    def create_shared_link(self, site_id: str, name: str) -> SharedLink:
        """
        Create or find a shared link for a site (idempotent).

        Args:
            site_id: Domain of the site
            name: Name for the shared link

        Returns:
            SharedLink object

        Raises:
            AuthenticationError: If authentication fails
            ServerError: If server returns 5xx error
        """
        response = retry_sync(
            self._client.put,
            f"{self.base_url}/api/v1/sites/shared-links",
            json={"site_id": site_id, "name": name},
        )
        data = self._handle_json_response(response)
        return SharedLink.from_dict(data)

    def list_custom_properties(self, site_id: str) -> list[str]:
        """
        List custom properties for a site.

        Args:
            site_id: Domain of the site

        Returns:
            List of custom property names

        Raises:
            AuthenticationError: If authentication fails
            ServerError: If server returns 5xx error
        """
        response = retry_sync(
            self._client.get,
            f"{self.base_url}/api/v1/sites/custom-props",
            params={"site_id": site_id},
        )
        data = self._handle_json_response(response)
        return [prop["property"] for prop in data["custom_properties"]]

    def create_custom_property(self, site_id: str, property_name: str) -> bool:
        """
        Create a custom property for a site (idempotent).

        Args:
            site_id: Domain of the site
            property_name: Name of the custom property

        Returns:
            True if creation was successful

        Raises:
            AuthenticationError: If authentication fails
            ServerError: If server returns 5xx error
        """
        response = retry_sync(
            self._client.put,
            f"{self.base_url}/api/v1/sites/custom-props",
            data={"site_id": site_id, "property": property_name},
        )
        data = self._handle_json_response(response)
        return data.get("created") is True

    def delete_custom_property(self, site_id: str, property_name: str) -> bool:
        """
        Delete a custom property from a site.

        Args:
            site_id: Domain of the site
            property_name: Name of the custom property

        Returns:
            True if deletion was successful

        Raises:
            AuthenticationError: If authentication fails
            ServerError: If server returns 5xx error
        """
        response = retry_sync(
            self._client.request,
            "DELETE",
            f"{self.base_url}/api/v1/sites/custom-props/{property_name}",
            data={"site_id": site_id},
        )
        data = self._handle_json_response(response)
        return data.get("deleted") is True

    def list_guests(
        self,
        site_id: str,
        limit: int = 100,
        after: str | None = None,
        before: str | None = None,
    ) -> tuple[list[Guest], dict[str, Any]]:
        """
        List guests for a site.

        Args:
            site_id: Domain of the site
            limit: Maximum number of guests to return (default 100)
            after: Pagination cursor for next page
            before: Pagination cursor for previous page

        Returns:
            Tuple of (list of Guest objects, pagination metadata)

        Raises:
            AuthenticationError: If authentication fails
            ServerError: If server returns 5xx error
        """
        params: dict[str, Any] = {"site_id": site_id, "limit": limit}
        if after:
            params["after"] = after
        if before:
            params["before"] = before

        response = retry_sync(
            self._client.get,
            f"{self.base_url}/api/v1/sites/guests",
            params=params,
        )
        data = self._handle_json_response(response)
        guests = [Guest.from_dict(guest_data) for guest_data in data["guests"]]
        return guests, data.get("meta", {})

    def invite_guest(self, site_id: str, email: str, role: str) -> Guest:
        """
        Invite a guest to a site or find existing invitation (idempotent).

        Args:
            site_id: Domain of the site
            email: Email address of the guest
            role: Role for the guest ("viewer" or "editor")

        Returns:
            Guest object

        Raises:
            AuthenticationError: If authentication fails
            InvalidQueryError: If the role is invalid
            ServerError: If server returns 5xx error
        """
        response = retry_sync(
            self._client.put,
            f"{self.base_url}/api/v1/sites/guests",
            json={"site_id": site_id, "email": email, "role": role},
        )
        data = self._handle_json_response(response)
        return Guest.from_dict(data)

    def delete_guest(self, site_id: str, email: str) -> bool:
        """
        Delete a guest or invitation from a site.

        Args:
            site_id: Domain of the site
            email: Email address of the guest

        Returns:
            True if deletion was successful

        Raises:
            AuthenticationError: If authentication fails
            ServerError: If server returns 5xx error
        """
        response = retry_sync(
            self._client.delete,
            f"{self.base_url}/api/v1/sites/guests/{email}",
            params={"site_id": site_id},
        )
        data = self._handle_json_response(response)
        return data.get("deleted") == "true"

    def _handle_json_response(self, response: httpx.Response) -> dict[str, Any]:
        """Handle JSON API response and raise appropriate errors."""
        if response.status_code in (200, 201, 202):
            data: dict[str, Any] = response.json()
            return data

        if response.status_code == 401:
            raise AuthenticationError("Invalid API key")

        if response.status_code == 400:
            try:
                error_data = response.json()
                message = error_data.get("error", "Invalid request")
                errors = error_data if isinstance(error_data, dict) else None
                raise InvalidQueryError(message, errors=errors)
            except Exception as e:
                if isinstance(e, InvalidQueryError):
                    raise
                raise InvalidQueryError("Invalid request") from None

        if response.status_code >= 500:
            raise ServerError(
                f"Server error: {response.status_code}", status_code=response.status_code
            )

        raise PlausibleError(
            f"Unexpected error: {response.status_code}", status_code=response.status_code
        )

    def _handle_response(
        self, response: httpx.Response, result_class: type[QueryResult] | None = None
    ) -> QueryResult | None:
        """Handle API response and raise appropriate errors."""
        if response.status_code == 200 or response.status_code == 202:
            if result_class:
                return result_class.from_response(response.json())
            return None

        if response.status_code == 401:
            raise AuthenticationError("Invalid API key")

        if response.status_code == 400:
            try:
                error_data = response.json()
                message = error_data.get("error", "Invalid query")
                errors = error_data if isinstance(error_data, dict) else None
                raise InvalidQueryError(message, errors=errors)
            except Exception as e:
                if isinstance(e, InvalidQueryError):
                    raise
                raise InvalidQueryError("Invalid query") from None

        if response.status_code >= 500:
            raise ServerError(
                f"Server error: {response.status_code}", status_code=response.status_code
            )

        raise PlausibleError(
            f"Unexpected error: {response.status_code}", status_code=response.status_code
        )
