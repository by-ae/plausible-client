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
from plausible_client.models import QueryResult
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
