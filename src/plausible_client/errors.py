"""Exception types for the Plausible client."""

from typing import Any


def message_from_payload(payload: Any, default: str) -> str:
    """Return a human-readable message from a Plausible error body.

    Stats and Sites API errors use ``{"error": "..."}``. The Events API
    reports validation failures as ``{"errors": ...}``.
    """
    if not isinstance(payload, dict):
        return default

    error = payload.get("error")
    if isinstance(error, str) and error:
        return error

    errors = payload.get("errors")
    if isinstance(errors, str) and errors:
        return errors
    if errors:
        return f"{default}: {errors}"
    return default


class PlausibleError(Exception):
    """Base exception for all Plausible client errors."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class AuthenticationError(PlausibleError):
    """Raised when API authentication fails (401)."""

    def __init__(self, message: str = "Authentication failed") -> None:
        super().__init__(message, status_code=401)


class PaymentRequiredError(PlausibleError):
    """Raised when subscription payment is required (402)."""

    def __init__(self, message: str = "Payment required") -> None:
        super().__init__(message, status_code=402)


class RateLimitError(PlausibleError):
    """Raised when rate limit is exceeded (429)."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: int | float | None = None,
    ) -> None:
        super().__init__(message, status_code=429)
        self.retry_after = retry_after


class InvalidQueryError(PlausibleError):
    """Raised when the query is invalid (400)."""

    def __init__(self, message: str, errors: dict[str, Any] | None = None) -> None:
        super().__init__(message, status_code=400)
        self.errors = errors


class ServerError(PlausibleError):
    """Raised when the server returns a 5xx error."""

    def __init__(self, message: str, status_code: int = 500) -> None:
        super().__init__(message, status_code=status_code)


class ForbiddenError(PlausibleError):
    """Raised when the API key is not allowed to perform the request (403)."""

    def __init__(self, message: str = "Forbidden") -> None:
        super().__init__(message, status_code=403)


class NotFoundError(PlausibleError):
    """Raised when the requested resource does not exist (404)."""

    def __init__(self, message: str = "Resource not found") -> None:
        super().__init__(message, status_code=404)
