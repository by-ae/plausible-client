"""A clean, typed Python client for Plausible Analytics HTTP APIs."""

from plausible_client.async_client import AsyncClient
from plausible_client.client import Client
from plausible_client.errors import (
    AuthenticationError,
    InvalidQueryError,
    PaymentRequiredError,
    PlausibleError,
    RateLimitError,
    ServerError,
)
from plausible_client.models import (
    DateRange,
    Dimension,
    Filter,
    Goal,
    Guest,
    Metric,
    OrderBy,
    QueryResult,
    SharedLink,
    Site,
    Team,
    TrackerScriptConfiguration,
)
from plausible_client.query import QueryBuilder

__version__ = "0.1.0"

__all__ = [
    "Client",
    "AsyncClient",
    "PlausibleError",
    "AuthenticationError",
    "PaymentRequiredError",
    "RateLimitError",
    "InvalidQueryError",
    "ServerError",
    "QueryBuilder",
    "QueryResult",
    "Metric",
    "Dimension",
    "Filter",
    "DateRange",
    "OrderBy",
    "Site",
    "Team",
    "Goal",
    "SharedLink",
    "Guest",
    "TrackerScriptConfiguration",
]
