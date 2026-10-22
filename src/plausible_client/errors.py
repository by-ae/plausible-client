"""Exception types for the Plausible client."""

from typing import Any


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


class RateLimitError(PlausibleError):
    """Raised when rate limit is exceeded (429)."""

    def __init__(
        self, message: str = "Rate limit exceeded", retry_after: int | None = None
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
