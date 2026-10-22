"""Data models for Plausible API requests and responses."""

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Literal


@dataclass
class DateRange:
    """Date range for queries."""

    start_date: date
    end_date: date

    def to_dict(self) -> dict[str, list[str]]:
        """Convert to API format."""
        return {
            "date_range": [
                self.start_date.isoformat(),
                self.end_date.isoformat(),
            ]
        }


@dataclass
class Filter:
    """Filter for queries."""

    dimension: str
    operator: Literal["is", "is_not", "contains", "does_not_contain"]
    value: str | list[str]

    def to_dict(self) -> list[str | list[str]]:
        """Convert to API format."""
        return [self.dimension, self.operator, self.value]


@dataclass
class OrderBy:
    """Ordering specification for queries."""

    metric: str
    direction: Literal["asc", "desc"] = "desc"

    def to_dict(self) -> dict[str, str]:
        """Convert to API format."""
        return {"metric": self.metric, "direction": self.direction}


class Metric:
    """Common metrics for the Stats API."""

    VISITORS = "visitors"
    VISITS = "visits"
    PAGEVIEWS = "pageviews"
    VIEWS_PER_VISIT = "views_per_visit"
    BOUNCE_RATE = "bounce_rate"
    VISIT_DURATION = "visit_duration"
    EVENTS = "events"
    CONVERSION_RATE = "conversion_rate"


class Dimension:
    """Common dimensions for the Stats API."""

    EVENT_NAME = "event:name"
    EVENT_PAGE = "event:page"
    VISIT_SOURCE = "visit:source"
    VISIT_REFERRER = "visit:referrer"
    VISIT_UTM_MEDIUM = "visit:utm_medium"
    VISIT_UTM_SOURCE = "visit:utm_source"
    VISIT_UTM_CAMPAIGN = "visit:utm_campaign"
    VISIT_UTM_CONTENT = "visit:utm_content"
    VISIT_UTM_TERM = "visit:utm_term"
    VISIT_DEVICE = "visit:device"
    VISIT_BROWSER = "visit:browser"
    VISIT_BROWSER_VERSION = "visit:browser_version"
    VISIT_OS = "visit:os"
    VISIT_OS_VERSION = "visit:os_version"
    VISIT_COUNTRY = "visit:country"
    VISIT_REGION = "visit:region"
    VISIT_CITY = "visit:city"


@dataclass
class QueryResult:
    """Result from a Stats API query."""

    results: list[dict[str, Any]]
    meta: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_response(cls, data: dict[str, Any]) -> "QueryResult":
        """Create from API response."""
        return cls(results=data.get("results", []), meta=data.get("meta", {}))
