"""Query builder for Plausible Stats API v2."""

from datetime import date, datetime
from typing import Any, Literal

from plausible_client.models import DateRange, Filter, OrderBy, normalize_clauses


def _require_query_date_pair(start: date, end: date) -> None:
    """Reject ranges DateTime.from_iso8601 or the date-pair parser cannot read.

    A custom range is either two calendar dates or two timezone-aware
    datetimes. A naive datetime's ``isoformat()`` has no offset, and a mixed
    pair matches neither parser.
    """
    start_is_datetime = isinstance(start, datetime)
    end_is_datetime = isinstance(end, datetime)
    if start_is_datetime != end_is_datetime:
        raise TypeError("date_range() start and end must both be dates or both be datetimes")
    if start_is_datetime:
        _require_aware_datetime(start)
        _require_aware_datetime(end)


def _require_aware_datetime(value: date) -> None:
    if isinstance(value, datetime):
        offset = None if value.tzinfo is None else value.tzinfo.utcoffset(value)
        if offset is None:
            raise ValueError(
                "datetime date ranges must be timezone-aware. "
                "The Stats API rejects timestamps without an offset."
            )


# Named presets accepted by the Stats API date_range field.
# https://plausible.io/docs/stats-api
DATE_RANGE_PRESETS = frozenset(
    {
        "day",
        "24h",
        "7d",
        "28d",
        "30d",
        "91d",
        "month",
        "6mo",
        "12mo",
        "year",
        "all",
    }
)

# The query parser also accepts "<n>d" and "<n>mo" relative ranges.
# Bounds match Plausible.Stats.ApiQueryParser.parse_input_date_range/1.
MAX_RELATIVE_DAYS = 5000
MAX_RELATIVE_MONTHS = 100


class QueryBuilder:
    """Builder for constructing Stats API v2 queries."""

    def __init__(self, site_id: str) -> None:
        self.site_id = site_id
        self._metrics: list[str] = []
        self._dimensions: list[str] = []
        self._filters: list[list[Any]] = []
        self._date_range: dict[str, Any] | None = None
        self._order_by: list[list[str]] = []
        self._limit: int = 10000
        self._offset: int = 0
        self._include: dict[str, Any] = {}

    def metrics(self, *metrics: str) -> "QueryBuilder":
        """Add metrics to the query."""
        _reject_duplicates(self._metrics, metrics, "metric")
        self._metrics.extend(metrics)
        return self

    def dimensions(self, *dimensions: str) -> "QueryBuilder":
        """Add dimensions to the query."""
        _reject_duplicates(self._dimensions, dimensions, "dimension")
        self._dimensions.extend(dimensions)
        return self

    def filter(
        self,
        dimension: str,
        operator: Literal[
            "is",
            "is_not",
            "contains",
            "contains_not",
            "matches",
            "matches_not",
            "does_not_contain",
        ],
        value: str | int | list[str | int],
        *,
        case_sensitive: bool | None = None,
    ) -> "QueryBuilder":
        """
        Add a filter to the query.

        Args:
            dimension: The dimension to filter on
            operator: Filter operator (does_not_contain is deprecated, use contains_not)
            value: Single value or list of values to filter by.
                ``visit:city`` takes GeoName IDs as integers. ``segment`` takes
                integer segment ids. Other dimensions take strings.
                ``visit:country`` with ``is`` or ``is_not`` takes 2-letter codes.
            case_sensitive: Case-sensitivity modifier for ``is`` and ``contains``.
                The Stats API only documents this modifier for those two operators.
        """
        clauses = normalize_clauses(value)
        filter_obj = Filter(
            operator=operator,
            dimension=dimension,
            clauses=clauses,
            case_sensitive=case_sensitive,
        )
        self._filters.append(filter_obj.to_dict())
        return self

    def where(self, *expressions: list[Any]) -> "QueryBuilder":
        """
        Append logical or behavioral filter expressions.

        Top-level filters are combined with an implicit ``and``. Build
        expressions with ``filter_clause``, ``any_of``, ``all_of``,
        ``negate``, ``has_done``, and ``has_not_done``.
        """
        if not expressions:
            raise TypeError("where() requires at least one filter expression")
        for expression in expressions:
            _require_filter_expression(expression)
            self._filters.append(expression)
        return self

    def date_range(self, start_date: date | str, end_date: date | None = None) -> "QueryBuilder":
        """
        Set the date range for the query.

        The Stats API requires ``date_range``. Pass one documented preset
        (``"day"``, ``"24h"``, ``"7d"``, ``"28d"``, ``"30d"``, ``"91d"``,
        ``"month"``, ``"6mo"``, ``"12mo"``, ``"year"``, ``"all"``), a
        relative range (``"14d"`` for 1 to 5000 days, ``"3mo"`` for 1 to
        100 months), or a start and end ``date`` or timezone-aware
        ``datetime``. Naive datetimes and mixed date/datetime pairs are
        rejected.
        """
        if isinstance(start_date, str):
            if end_date is not None:
                raise TypeError("preset date ranges do not take an end date")
            if start_date not in DATE_RANGE_PRESETS and not _is_relative_date_range(start_date):
                presets = ", ".join(sorted(DATE_RANGE_PRESETS))
                raise ValueError(
                    f"unknown date range preset {start_date!r}. "
                    f"Expected one of: {presets}, or a relative range such as "
                    f"'14d' (1 to {MAX_RELATIVE_DAYS}) or '3mo' (1 to {MAX_RELATIVE_MONTHS})"
                )
            self._date_range = {"date_range": start_date}
            return self

        if end_date is None:
            raise TypeError("date_range() requires an end date when the start is a date")

        _require_query_date_pair(start_date, end_date)
        date_range_obj = DateRange(start_date=start_date, end_date=end_date)
        self._date_range = date_range_obj.to_dict()
        return self

    def order_by(self, metric: str, direction: Literal["asc", "desc"] = "desc") -> "QueryBuilder":
        """Add ordering to the query."""
        if metric == "event:goal":
            raise ValueError(
                "event:goal cannot be used in order_by. Order goal breakdowns by a metric instead."
            )
        if metric == "segment":
            raise ValueError("segment cannot be used in order_by")
        order_obj = OrderBy(metric=metric, direction=direction)
        self._order_by.append(order_obj.to_list())
        return self

    def limit(self, limit: int) -> "QueryBuilder":
        """Set the result limit. The query schema allows 1 to 10000."""
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 10000:
            raise ValueError(f"limit must be an integer from 1 to 10000, got {limit!r}")
        self._limit = limit
        return self

    def offset(self, offset: int) -> "QueryBuilder":
        """Set the result offset for pagination. The query schema requires zero or greater."""
        if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
            raise ValueError(
                f"offset must be an integer greater than or equal to 0, got {offset!r}"
            )
        self._offset = offset
        return self

    def include(
        self,
        imports: bool = False,
        time_labels: bool = False,
        total_rows: bool = False,
        trim_relative_date_range: bool = False,
    ) -> "QueryBuilder":
        """
        Set include options for additional data.

        Args:
            imports: Try to include imported data in the result
            time_labels: Include all time labels valid for the date range (requires time dimension)
            total_rows: Include total row count for pagination
            trim_relative_date_range: Drop empty time after the current moment for
                ``day``, ``month``, and ``year`` date ranges
        """
        if imports:
            self._include["imports"] = True
        if time_labels:
            self._include["time_labels"] = True
        if total_rows:
            self._include["total_rows"] = True
        if trim_relative_date_range:
            self._include["trim_relative_date_range"] = True
        return self

    def copy(self) -> "QueryBuilder":
        """Create a copy of this QueryBuilder."""
        new_qb = QueryBuilder(self.site_id)
        new_qb._metrics = self._metrics.copy()
        new_qb._dimensions = self._dimensions.copy()
        new_qb._filters = self._filters.copy()
        new_qb._date_range = self._date_range
        new_qb._order_by = self._order_by.copy()
        new_qb._limit = self._limit
        new_qb._offset = self._offset
        new_qb._include = self._include.copy()
        return new_qb

    def build(self) -> dict[str, Any]:
        """Build the query payload."""
        payload: dict[str, Any] = {"site_id": self.site_id}

        if self._metrics:
            payload["metrics"] = self._metrics

        if self._dimensions:
            payload["dimensions"] = self._dimensions

        if self._filters:
            payload["filters"] = self._filters

        if self._date_range:
            payload.update(self._date_range)

        if self._order_by:
            payload["order_by"] = self._order_by

        if self._limit != 10000 or self._offset != 0:
            payload["pagination"] = {"limit": self._limit, "offset": self._offset}

        if self._include:
            payload["include"] = self._include

        return payload


def filter_clause(
    dimension: str,
    operator: Literal[
        "is",
        "is_not",
        "contains",
        "contains_not",
        "matches",
        "matches_not",
        "does_not_contain",
    ],
    value: str | int | list[str | int],
    *,
    case_sensitive: bool | None = None,
) -> list[Any]:
    """Build one simple filter without adding it to a query."""
    return Filter(
        operator=operator,
        dimension=dimension,
        clauses=normalize_clauses(value),
        case_sensitive=case_sensitive,
    ).to_dict()


def all_of(*filters: list[Any]) -> list[Any]:
    """Combine filters with ``and``. The result is ``["and", [filters...]]``."""
    _require_combined_filters(filters, "all_of")
    return ["and", list(filters)]


def any_of(*filters: list[Any]) -> list[Any]:
    """Combine filters with ``or``. The result is ``["or", [filters...]]``."""
    _require_combined_filters(filters, "any_of")
    return ["or", list(filters)]


def negate(expression: list[Any]) -> list[Any]:
    """Negate one filter. The result is ``["not", filter]``."""
    _require_filter_expression(expression)
    return ["not", expression]


def has_done(expression: list[Any]) -> list[Any]:
    """Keep sessions in which the event filter also matched."""
    _require_event_filter(expression)
    return ["has_done", expression]


def has_not_done(expression: list[Any]) -> list[Any]:
    """Drop sessions in which the event filter matched."""
    _require_event_filter(expression)
    return ["has_not_done", expression]


def _reject_duplicates(existing: list[str], incoming: tuple[str, ...], label: str) -> None:
    """The query schema requires metrics and dimensions to be unique."""
    seen = set(existing)
    for value in incoming:
        if value in seen:
            raise ValueError(f"duplicate {label} {value!r}")
        seen.add(value)


def _is_relative_date_range(value: str) -> bool:
    """Return whether ``value`` is an ``<n>d`` or ``<n>mo`` range the parser accepts.

    Out-of-range numbers raise, because the parser rejects them after the
    string matches the shorthand pattern.
    """
    if value.endswith("mo"):
        count_text = value[:-2]
        upper = MAX_RELATIVE_MONTHS
        unit = "month"
    elif value.endswith("d"):
        count_text = value[:-1]
        upper = MAX_RELATIVE_DAYS
        unit = "day"
    else:
        return False

    if not count_text.isdigit():
        return False

    count = int(count_text)
    if 1 <= count <= upper:
        return True
    raise ValueError(
        f"date range {value!r} is outside the Stats API limits. "
        f"A {unit} range must be from 1 to {upper}."
    )


def _require_combined_filters(filters: tuple[list[Any], ...], name: str) -> None:
    if len(filters) < 2:
        raise ValueError(f"{name}() requires at least two filters")
    for expression in filters:
        _require_filter_expression(expression)


def _require_filter_expression(expression: list[Any]) -> None:
    if not isinstance(expression, list) or not expression or not isinstance(expression[0], str):
        raise TypeError("expected a Stats API filter expression")


def _require_event_filter(expression: list[Any]) -> None:
    _require_filter_expression(expression)
    if expression[0] in ("has_done", "has_not_done"):
        raise ValueError("Behavioral filters (has_done, has_not_done) cannot be nested.")
    dimension = expression[1] if len(expression) > 1 else None
    if not isinstance(dimension, str) or not dimension.startswith("event:"):
        raise ValueError("has_done and has_not_done only accept an event dimension filter")
