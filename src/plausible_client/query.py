"""Query builder for Plausible Stats API v2."""

from datetime import date
from typing import Any, Literal

from plausible_client.models import DateRange, Filter, OrderBy, normalize_clauses

# Presets accepted by the Stats API date_range field.
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


class QueryBuilder:
    """Builder for constructing Stats API v2 queries."""

    def __init__(self, site_id: str) -> None:
        self.site_id = site_id
        self._metrics: list[str] = []
        self._dimensions: list[str] = []
        self._filters: list[list[str | list[str | int] | dict[str, bool]]] = []
        self._date_range: dict[str, Any] | None = None
        self._order_by: list[list[str]] = []
        self._limit: int = 10000
        self._offset: int = 0
        self._include: dict[str, Any] = {}

    def metrics(self, *metrics: str) -> "QueryBuilder":
        """Add metrics to the query."""
        self._metrics.extend(metrics)
        return self

    def dimensions(self, *dimensions: str) -> "QueryBuilder":
        """Add dimensions to the query."""
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

    def date_range(self, start_date: date | str, end_date: date | None = None) -> "QueryBuilder":
        """
        Set the date range for the query.

        The Stats API requires ``date_range``. Pass one documented preset
        (``"day"``, ``"24h"``, ``"7d"``, ``"28d"``, ``"30d"``, ``"91d"``,
        ``"month"``, ``"6mo"``, ``"12mo"``, ``"year"``, ``"all"``) or a
        start and end ``date`` or ``datetime``.
        """
        if isinstance(start_date, str):
            if end_date is not None:
                raise TypeError("preset date ranges do not take an end date")
            if start_date not in DATE_RANGE_PRESETS:
                presets = ", ".join(sorted(DATE_RANGE_PRESETS))
                raise ValueError(
                    f"unknown date range preset {start_date!r}. Expected one of: {presets}"
                )
            self._date_range = {"date_range": start_date}
            return self

        if end_date is None:
            raise TypeError("date_range() requires an end date when the start is a date")

        date_range_obj = DateRange(start_date=start_date, end_date=end_date)
        self._date_range = date_range_obj.to_dict()
        return self

    def order_by(self, metric: str, direction: Literal["asc", "desc"] = "desc") -> "QueryBuilder":
        """Add ordering to the query."""
        order_obj = OrderBy(metric=metric, direction=direction)
        self._order_by.append(order_obj.to_list())
        return self

    def limit(self, limit: int) -> "QueryBuilder":
        """Set the result limit."""
        self._limit = limit
        return self

    def offset(self, offset: int) -> "QueryBuilder":
        """Set the result offset for pagination."""
        self._offset = offset
        return self

    def include(
        self,
        imports: bool = False,
        time_labels: bool = False,
        total_rows: bool = False,
    ) -> "QueryBuilder":
        """
        Set include options for additional data.

        Args:
            imports: Try to include imported data in the result
            time_labels: Include all time labels valid for the date range (requires time dimension)
            total_rows: Include total row count for pagination
        """
        if imports:
            self._include["imports"] = True
        if time_labels:
            self._include["time_labels"] = True
        if total_rows:
            self._include["total_rows"] = True
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
