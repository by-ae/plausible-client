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


def normalize_clauses(value: str | int | list[str | int]) -> list[str | int]:
    """Wrap a single clause the way the Stats API expects a list of clauses.

    Booleans are rejected because ``bool`` is a subclass of ``int``.
    """
    if isinstance(value, bool):
        raise TypeError("filter value must be a string, an integer, or a list of those")
    if isinstance(value, (str, int)):
        return [value]
    if isinstance(value, list):
        return list(value)
    raise TypeError("filter value must be a string, an integer, or a list of those")


def validate_clauses(dimension: str, operator: str, clauses: list[str | int]) -> None:
    """Reject clause types the Stats API parser refuses.

    ``visit:city`` clauses are GeoName IDs and ``segment`` clauses are integer
    ids. Every other dimension takes strings. ``visit:country`` with ``is`` or
    ``is_not`` additionally requires a 2-letter code.
    """
    if not clauses:
        raise ValueError("filter clauses must not be empty")

    if dimension == "visit:city":
        if any(isinstance(clause, bool) or not isinstance(clause, int) for clause in clauses):
            raise ValueError(
                "visit:city filters require GeoName IDs as integers, for example 4347778"
            )
        return

    if dimension == "segment":
        if any(isinstance(clause, bool) or not isinstance(clause, int) for clause in clauses):
            raise ValueError("segment filters require integer segment ids")
        return

    if any(not isinstance(clause, str) for clause in clauses):
        raise ValueError(f"{dimension} filter clauses must be strings")

    if dimension == "visit:country" and operator in ("is", "is_not"):
        if any(not isinstance(clause, str) or len(clause) != 2 for clause in clauses):
            raise ValueError("visit:country is and is_not filters require a 2-letter country code")


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
    clauses: list[str | int]
    case_sensitive: bool | None = None

    def to_dict(self) -> list[str | list[str | int] | dict[str, bool]]:
        """
        Convert to API format: [operator, dimension, clauses] or
        [operator, dimension, clauses, {"case_sensitive": bool}].

        Maps deprecated 'does_not_contain' to 'contains_not' for API compatibility.
        The case_sensitive modifier is documented for ``is`` and ``contains`` only.
        """
        operator = self.operator
        if operator == "does_not_contain":
            operator = "contains_not"
        validate_clauses(self.dimension, self.operator, self.clauses)
        result: list[str | list[str | int] | dict[str, bool]] = [
            operator,
            self.dimension,
            self.clauses,
        ]
        if self.case_sensitive is not None:
            if operator not in ("is", "contains"):
                raise ValueError("case_sensitive is only valid for 'is' and 'contains' filters")
            result.append({"case_sensitive": self.case_sensitive})
        return result


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
    SCROLL_DEPTH = "scroll_depth"
    PERCENTAGE = "percentage"
    CONVERSION_RATE = "conversion_rate"
    GROUP_CONVERSION_RATE = "group_conversion_rate"
    AVERAGE_REVENUE = "average_revenue"
    TOTAL_REVENUE = "total_revenue"
    TIME_ON_PAGE = "time_on_page"


class Dimension:
    """Common dimensions for the Stats API."""

    EVENT_NAME = "event:name"
    EVENT_PAGE = "event:page"
    EVENT_GOAL = "event:goal"
    EVENT_HOSTNAME = "event:hostname"
    VISIT_ENTRY_PAGE = "visit:entry_page"
    VISIT_ENTRY_PAGE_HOSTNAME = "visit:entry_page_hostname"
    VISIT_EXIT_PAGE = "visit:exit_page"
    VISIT_EXIT_PAGE_HOSTNAME = "visit:exit_page_hostname"
    VISIT_SOURCE = "visit:source"
    VISIT_CHANNEL = "visit:channel"
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
    VISIT_COUNTRY_NAME = "visit:country_name"
    VISIT_REGION_NAME = "visit:region_name"
    VISIT_CITY_NAME = "visit:city_name"
    TIME = "time"
    TIME_HOUR = "time:hour"
    TIME_DAY = "time:day"
    TIME_WEEK = "time:week"
    TIME_MONTH = "time:month"


@dataclass(frozen=True)
class EventResult:
    """Outcome of an Events API request.

    The API returns HTTP 202 even when an event is dropped. ``dropped`` is
    true when the ``x-plausible-dropped`` header is a positive count. The
    docs use the value ``1``.
    """

    dropped: bool = False


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
