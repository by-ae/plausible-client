"""Shared handling of Plausible HTTP responses."""

from typing import Any, NoReturn

import httpx

from plausible_client.errors import (
    AuthenticationError,
    ForbiddenError,
    InvalidQueryError,
    NotFoundError,
    PaymentRequiredError,
    PlausibleError,
    ServerError,
    message_from_payload,
)


def json_object(response: httpx.Response) -> dict[str, Any] | None:
    """Return a JSON object body, or None when the body is not one."""
    try:
        payload = response.json()
    except Exception:
        return None
    if isinstance(payload, dict):
        return payload
    return None


def raise_for_status(response: httpx.Response, *, invalid_message: str) -> NoReturn:
    """Raise the typed error for a non-success Plausible response."""
    if response.status_code == 401:
        raise AuthenticationError("Invalid API key")

    if response.status_code == 402:
        raise PaymentRequiredError("Payment required to access this resource")

    if response.status_code == 403:
        raise ForbiddenError(message_from_payload(json_object(response), "Forbidden"))

    if response.status_code == 404:
        raise NotFoundError(message_from_payload(json_object(response), "Resource not found"))

    if response.status_code == 400:
        payload = json_object(response)
        raise InvalidQueryError(message_from_payload(payload, invalid_message), errors=payload)

    if response.status_code >= 500:
        raise ServerError(f"Server error: {response.status_code}", status_code=response.status_code)

    raise PlausibleError(
        f"Unexpected error: {response.status_code}", status_code=response.status_code
    )


def was_deleted(payload: dict[str, Any]) -> bool:
    """Return whether a Sites API delete response reports success.

    The API encodes the flag as JSON ``true``. The published examples for
    site, goal, and guest deletion also show the string ``"true"``.
    """
    deleted = payload.get("deleted")
    return deleted is True or deleted == "true"
