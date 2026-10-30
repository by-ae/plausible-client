"""Reject Stats API queries the query builder turns into QueryError.

Schema checks happen first. These rules run afterwards in
Plausible.Stats.QueryBuilder and Plausible.Stats.TableDecider.
"""

from typing import Any

# Session-only metrics. visitors and visits are not in this set.
_SESSION_METRICS = frozenset({"bounce_rate", "visit_duration", "views_per_visit"})
# Event metrics other than revenue. Revenue is allowed with session dimensions.
_EVENT_METRICS = frozenset({"scroll_depth", "pageviews", "events", "time_on_page"})
_SESSION_DIMENSIONS = frozenset(
    {
        "visit:entry_page",
        "visit:entry_page_hostname",
        "visit:exit_page",
        "visit:exit_page_hostname",
    }
)
_PAGE_DIMENSION_EXCEPTION = frozenset({"event:page", "event:hostname"})
_TOPLEVEL_ONLY = frozenset({"event:goal", "event:hostname"})
_UNARY_OPERATORS = frozenset({"not", "has_done", "has_not_done"})
_BEHAVIORAL_OPERATORS = frozenset({"has_done", "has_not_done"})
_BRANCH_OPERATORS = frozenset({"and", "or"})


def validate_query(
    *,
    metrics: list[str],
    dimensions: list[str],
    filters: list[Any],
    order_by: list[list[str]],
    include: dict[str, Any],
) -> None:
    """Raise ValueError when the stats query builder would reject the query."""
    _validate_order_by(metrics, dimensions, order_by)
    _validate_time_labels(dimensions, include)
    _validate_metric_requirements(metrics, dimensions, filters)
    _validate_metric_dimension_conflict(metrics, dimensions)
    _validate_toplevel_filters(filters)


def _validate_order_by(
    metrics: list[str], dimensions: list[str], order_by: list[list[str]]
) -> None:
    selected = set(metrics)
    selected.update(dimensions)
    for entry in order_by:
        key = entry[0]
        if key not in selected:
            raise ValueError(
                f"order_by entry {key!r} is not a queried metric or dimension. "
                "The stats query builder rejects it."
            )


def _validate_time_labels(dimensions: list[str], include: dict[str, Any]) -> None:
    if not include.get("time_labels"):
        return
    if any(dimension.startswith("time") for dimension in dimensions):
        return
    raise ValueError("include.time_labels requires a time dimension")


def _validate_metric_requirements(
    metrics: list[str], dimensions: list[str], filters: list[Any]
) -> None:
    page_dimension = "event:page" in dimensions
    goal_dimension = "event:goal" in dimensions
    page_filter = _filters_on(filters, "event:page")
    goal_filter = _filters_on(filters, "event:goal")
    non_time_dimensions = [
        dimension for dimension in dimensions if not dimension.startswith("time")
    ]

    if "scroll_depth" in metrics and not (page_dimension or _toplevel_page_filter(filters)):
        raise ValueError("scroll_depth can only be queried with an event:page filter or dimension")
    if "time_on_page" in metrics and not (page_dimension or page_filter):
        raise ValueError("time_on_page can only be queried with an event:page filter or dimension")
    for metric in ("conversion_rate", "group_conversion_rate"):
        if metric in metrics and not (goal_dimension or goal_filter):
            raise ValueError(f"{metric} can only be queried with an event:goal filter or dimension")
    if "views_per_visit" in metrics:
        if page_filter:
            raise ValueError("views_per_visit cannot be queried with a filter on event:page")
        if non_time_dimensions:
            raise ValueError("views_per_visit cannot be queried with non-time dimensions")


def _validate_metric_dimension_conflict(metrics: list[str], dimensions: list[str]) -> None:
    event_dimensions = [dimension for dimension in dimensions if dimension.startswith("event:")]
    session_dimensions = [dimension for dimension in dimensions if dimension in _SESSION_DIMENSIONS]
    session_metrics = [metric for metric in metrics if metric in _SESSION_METRICS]
    event_metrics = [metric for metric in metrics if metric in _EVENT_METRICS]

    page_breakdown = "event:page" in event_dimensions and all(
        dimension in _PAGE_DIMENSION_EXCEPTION for dimension in event_dimensions
    )
    if session_metrics and event_dimensions and not page_breakdown:
        raise ValueError(
            f"{_join(session_metrics)} cannot be queried along with "
            f"event dimension {_join(event_dimensions)}"
        )
    if event_metrics and session_dimensions:
        raise ValueError(
            f"{_join(event_metrics)} cannot be queried along with "
            f"session dimension {_join(session_dimensions)}"
        )


def _validate_toplevel_filters(filters: list[Any]) -> None:
    for leaf, depth, behavioral in _iter_leaves(filters):
        if behavioral or depth < 1 or len(leaf) < 2:
            continue
        dimension = leaf[1]
        if isinstance(dimension, str) and dimension in _TOPLEVEL_ONLY:
            raise ValueError(f"{dimension} can only be filtered at the top level")


def _filters_on(filters: list[Any], dimension: str) -> bool:
    """True when a non-behavioral filter uses this dimension at any depth."""
    for leaf, _depth, behavioral in _iter_leaves(filters):
        if behavioral or len(leaf) < 2:
            continue
        if leaf[1] == dimension:
            return True
    return False


def _toplevel_page_filter(filters: list[Any]) -> bool:
    """Match get_toplevel_filter(query, "event:page"), which is prefix-based."""
    for item in filters:
        if (
            isinstance(item, list)
            and len(item) >= 2
            and isinstance(item[1], str)
            and item[1].startswith("event:page")
        ):
            return True
    return False


def _iter_leaves(
    filters: list[Any], *, depth: int = 0, behavioral: bool = False
) -> list[tuple[list[Any], int, bool]]:
    """Walk filters the way Plausible.Stats.Filters.traverse/3 does."""
    leaves: list[tuple[list[Any], int, bool]] = []
    for item in filters:
        if not isinstance(item, list) or not item or not isinstance(item[0], str):
            continue
        operator = item[0]
        if operator in _UNARY_OPERATORS and len(item) == 2 and isinstance(item[1], list):
            leaves.extend(
                _iter_leaves(
                    [item[1]],
                    depth=depth + 1,
                    behavioral=behavioral or operator in _BEHAVIORAL_OPERATORS,
                )
            )
            continue
        if operator in _BRANCH_OPERATORS and len(item) == 2 and isinstance(item[1], list):
            leaves.extend(_iter_leaves(item[1], depth=depth + 1, behavioral=behavioral))
            continue
        leaves.append((item, depth, behavioral))
    return leaves


def _join(values: list[str]) -> str:
    return ", ".join(values)
