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

    operator: Literal[
        "is",
        "is_not",
        "contains",
        "contains_not",
        "matches",
        "matches_not",
        "does_not_contain",
    ]
    dimension: str
    clauses: list[str]

    def to_dict(self) -> list[str | list[str]]:
        """
        Convert to API format: [operator, dimension, clauses].

        Maps deprecated 'does_not_contain' to 'contains_not' for API compatibility.
        """
        operator = self.operator
        if operator == "does_not_contain":
            operator = "contains_not"
        return [operator, self.dimension, self.clauses]


@dataclass
class OrderBy:
    """Ordering specification for queries."""

    metric: str
    direction: Literal["asc", "desc"] = "desc"

    def to_list(self) -> list[str]:
        """Convert to API format: [metric, direction]."""
        return [self.metric, self.direction]


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


@dataclass
class TrackerScriptConfiguration:
    """Tracker script configuration for a site."""

    id: str | None = None
    installation_type: str | None = None
    track_404_pages: bool = False
    hash_based_routing: bool = False
    outbound_links: bool = False
    file_downloads: bool = False
    revenue_tracking: bool = False
    tagged_events: bool = False
    form_submissions: bool = False
    pageview_props: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to API format."""
        result: dict[str, Any] = {}
        if self.installation_type is not None:
            result["installation_type"] = self.installation_type
        result["track_404_pages"] = self.track_404_pages
        result["hash_based_routing"] = self.hash_based_routing
        result["outbound_links"] = self.outbound_links
        result["file_downloads"] = self.file_downloads
        result["revenue_tracking"] = self.revenue_tracking
        result["tagged_events"] = self.tagged_events
        result["form_submissions"] = self.form_submissions
        result["pageview_props"] = self.pageview_props
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TrackerScriptConfiguration":
        """Create from API response."""
        return cls(
            id=data.get("id"),
            installation_type=data.get("installation_type"),
            track_404_pages=data.get("track_404_pages", False),
            hash_based_routing=data.get("hash_based_routing", False),
            outbound_links=data.get("outbound_links", False),
            file_downloads=data.get("file_downloads", False),
            revenue_tracking=data.get("revenue_tracking", False),
            tagged_events=data.get("tagged_events", False),
            form_submissions=data.get("form_submissions", False),
            pageview_props=data.get("pageview_props", False),
        )


@dataclass
class Site:
    """A site in Plausible."""

    domain: str
    timezone: str
    custom_properties: list[str] = field(default_factory=list)
    tracker_script_configuration: TrackerScriptConfiguration | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Site":
        """Create from API response."""
        tracker_config = None
        if "tracker_script_configuration" in data:
            tracker_config = TrackerScriptConfiguration.from_dict(
                data["tracker_script_configuration"]
            )

        return cls(
            domain=data["domain"],
            timezone=data["timezone"],
            custom_properties=data.get("custom_properties", []),
            tracker_script_configuration=tracker_config,
        )


@dataclass
class Team:
    """A team in Plausible."""

    id: str
    name: str
    api_available: bool

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Team":
        """Create from API response."""
        return cls(
            id=data["id"],
            name=data["name"],
            api_available=data["api_available"],
        )


@dataclass
class Goal:
    """A goal in Plausible."""

    id: str
    goal_type: str
    display_name: str
    event_name: str | None = None
    page_path: str | None = None
    custom_props: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Goal":
        """Create from API response."""
        return cls(
            id=str(data["id"]),
            goal_type=data["goal_type"],
            display_name=data["display_name"],
            event_name=data.get("event_name"),
            page_path=data.get("page_path"),
            custom_props=data.get("custom_props", {}),
        )


@dataclass
class SharedLink:
    """A shared link for a site."""

    name: str
    url: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SharedLink":
        """Create from API response."""
        return cls(name=data["name"], url=data["url"])


@dataclass
class Guest:
    """A guest or invitation for a site."""

    email: str
    role: str
    status: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Guest":
        """Create from API response."""
        return cls(
            email=data["email"],
            role=data["role"],
            status=data["status"],
        )
