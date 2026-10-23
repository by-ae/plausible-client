"""Query builder for Plausible Stats API v2."""

from typing import Any, Literal

from plausible_client.models import DateRange, Filter, OrderBy


class QueryBuilder:
    """Builder for constructing Stats API v2 queries."""

    def __init__(self, site_id: str) -> None:
        self.site_id = site_id
        self._metrics: list[str] = []
        self._dimensions: list[str] = []
        self._filters: list[list[str | list[str]]] = []
        self._date_range: dict[str, Any] | None = None
        self._order_by: list[dict[str, str]] = []
        self._limit: int | None = None
        self._offset: int | None = None
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
        operator: Literal["is", "is_not", "contains", "does_not_contain"],
        value: str | list[str],
    ) -> "QueryBuilder":
        """Add a filter to the query."""
        filter_obj = Filter(dimension=dimension, operator=operator, value=value)
        self._filters.append(filter_obj.to_dict())
        return self

    def date_range(self, start_date: Any, end_date: Any) -> "QueryBuilder":
        """Set the date range for the query."""
        date_range_obj = DateRange(start_date=start_date, end_date=end_date)
        self._date_range = date_range_obj.to_dict()
        return self

    def order_by(self, metric: str, direction: Literal["asc", "desc"] = "desc") -> "QueryBuilder":
        """Add ordering to the query."""
        order_obj = OrderBy(metric=metric, direction=direction)
        self._order_by.append(order_obj.to_dict())
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

        if self._limit is not None:
            payload["limit"] = self._limit

        if self._offset is not None:
            payload["offset"] = self._offset

        if self._include:
            payload["include"] = self._include

        return payload
