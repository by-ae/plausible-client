"""Checks for Events API payloads the ingestion request parser rejects."""

import math
import re
from typing import Any
from urllib.parse import urlsplit

from plausible_client._currencies import CURRENT_CURRENCIES

# The request parser measures the whole URL with byte_size/1.
MAX_URL_BYTES = 2000
# Ecto validate_length on event_name, counted in characters.
MAX_EVENT_NAME_LENGTH = 120
# Plausible.Props.max_prop_key_length/0 and max_prop_value_length/0.
# The ingestion parser compares those limits with byte_size/1 after
# stringifying each value.
MAX_PROP_KEY_BYTES = 300
MAX_PROP_VALUE_BYTES = 2000
# Plausible.Ingestion.Request @max_props. Extra keys are dropped after
# blank and nested values are removed.
MAX_PROPS = 30
# Plausible.Event.SystemEvents.events_with_path_prop/0. When "path" is
# not already present, the pathname is inserted before the 30 cap.
PATH_PROP_EVENTS = frozenset({"404", "WP Form Completions", "Form: Submission"})

# Plausible.Event.SystemEvents.events_with_interactive_always_true/0.
# interactive: false is ignored for these names.
ALWAYS_INTERACTIVE_EVENTS = frozenset(
    {
        "pageview",
        "engagement",
        "Outbound Link: Click",
        "Cloaked Link: Click",
        "File Download",
        "404",
        "WP Form Completions",
        "Form: Submission",
    }
)

PropValue = str | int | float | bool

# Plausible.Ingestion.Request stores scroll depth 0..100 and clamps anything
# larger to 100. Engagement time is milliseconds. Values at or above
# :timer.hours(30 * 24) are ignored. Erlang timer:hours/1 returns milliseconds.
MAX_SCROLL_DEPTH = 100
MAX_ENGAGEMENT_TIME_MS = 30 * 24 * 60 * 60 * 1000


def validate_event(
    *,
    domain: str,
    name: str,
    url: str,
    interactive: bool | None,
    props: dict[str, PropValue] | None,
    scroll_depth: int | None = None,
    engagement_time: int | None = None,
) -> None:
    """Raise ValueError when the ingestion parser would reject the event."""
    if not isinstance(domain, str) or not domain.strip():
        raise ValueError("domain is required")
    if not isinstance(name, str) or name == "":
        raise ValueError("name is required")
    if len(name) > MAX_EVENT_NAME_LENGTH:
        raise ValueError(f"name must be at most {MAX_EVENT_NAME_LENGTH} characters")
    if not isinstance(url, str) or url == "":
        raise ValueError("url is required")
    if len(url.encode("utf-8")) > MAX_URL_BYTES:
        raise ValueError(f"url must be at most {MAX_URL_BYTES} bytes")
    if urlsplit(url).scheme.lower() == "data":
        raise ValueError("data: URLs are not supported by the Events API")
    if interactive is False and name in ALWAYS_INTERACTIVE_EVENTS:
        raise ValueError(
            f"interactive=false has no effect on {name!r}. "
            "The Events API only honours it for custom events; "
            "pageview and other system events stay interactive."
        )
    if props:
        _validate_props(props)
    engagement_fields(name=name, scroll_depth=scroll_depth, engagement_time=engagement_time)


def engagement_fields(
    *,
    name: str,
    scroll_depth: int | None,
    engagement_time: int | None,
) -> dict[str, int]:
    """Return the ``sd`` and ``e`` fields for an engagement event.

    The ingestion request only reads those keys when the event name is
    ``engagement``. Both missing, or an engagement time of 0 with no scroll
    depth, is the pair the server rejects with a 400.
    """
    if scroll_depth is None and engagement_time is None:
        if name == "engagement":
            raise ValueError(
                "engagement events require scroll_depth from 0 to "
                f"{MAX_SCROLL_DEPTH} or engagement_time from 1 to "
                f"{MAX_ENGAGEMENT_TIME_MS - 1} milliseconds. "
                "The Events API rejects the event when both are missing."
            )
        return {}

    if name != "engagement":
        raise ValueError(
            "scroll_depth and engagement_time are only recorded for an "
            "engagement event. The Events API ignores them on other names."
        )

    payload: dict[str, int] = {}
    if scroll_depth is not None:
        payload["sd"] = _require_scroll_depth(scroll_depth)
    if engagement_time is not None:
        payload["e"] = _require_engagement_time(engagement_time)

    time_counts = payload.get("e", 0) > 0
    if "sd" not in payload and not time_counts:
        raise ValueError(
            "engagement events require scroll_depth from 0 to "
            f"{MAX_SCROLL_DEPTH} or engagement_time from 1 to "
            f"{MAX_ENGAGEMENT_TIME_MS - 1} milliseconds. "
            "An engagement_time of 0 does not count on its own."
        )
    return payload


def _require_scroll_depth(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= MAX_SCROLL_DEPTH:
        raise ValueError(
            "scroll_depth must be an integer from 0 to "
            f"{MAX_SCROLL_DEPTH}. The Events API stores a larger value as 100."
        )
    return value


def _require_engagement_time(value: object) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < 0
        or value >= MAX_ENGAGEMENT_TIME_MS
    ):
        raise ValueError(
            "engagement_time must be an integer from 0 to "
            f"{MAX_ENGAGEMENT_TIME_MS - 1} milliseconds. "
            "A larger value is ignored and stored as no time."
        )
    return value


def _validate_props(props: dict[str, PropValue]) -> None:
    if not isinstance(props, dict):
        raise ValueError("props must be an object")
    for key, value in props.items():
        if not isinstance(key, str):
            raise ValueError("property keys must be strings")
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError(
                f"property {key!r} must be a finite number. "
                "A non-finite value is not valid JSON and the event is not recorded."
            )
        if value is None:
            raise ValueError(f"property {key!r} must be a string, number, or boolean")
        if isinstance(value, (list, dict, tuple)):
            # Valid JSON. Ingestion drops these keys and still records the event.
            continue
        if not isinstance(value, (str, int, float)):
            raise ValueError(f"property {key!r} must be a string, number, or boolean")
        if not _prop_is_stored(key, value):
            continue
        if len(key.encode("utf-8")) > MAX_PROP_KEY_BYTES:
            raise ValueError(f"property key {key!r} is longer than {MAX_PROP_KEY_BYTES} bytes")
        stored = _stored_prop_text(value)
        if len(stored.encode("utf-8")) > MAX_PROP_VALUE_BYTES:
            raise ValueError(f"property {key!r} is longer than {MAX_PROP_VALUE_BYTES} bytes")


def props_discarded(name: str, props: dict[str, PropValue] | None) -> bool:
    """Return whether ingestion will store the event without some properties.

    Blank keys and values are removed. Lists and objects are removed.
    At most 30 properties are kept. ``404``, ``WP Form Completions``, and
    ``Form: Submission`` also receive a ``path`` property copied from the
    URL when the caller did not send one, and that counts toward the 30.
    """
    if not props:
        return False
    kept = 0
    saw_path = False
    dropped = False
    for key, value in props.items():
        if isinstance(key, str) and _prop_is_stored(key, value):
            kept += 1
            if key == "path":
                saw_path = True
        else:
            dropped = True
    if name in PATH_PROP_EVENTS and not saw_path:
        kept += 1
    return dropped or kept > MAX_PROPS


def _prop_is_stored(key: str, value: object) -> bool:
    """Return whether filter_bad_props/2 keeps this pair.

    A value is blank when ``String.trim_leading(to_string(value))`` is empty.
    ``false`` and ``0`` are kept. Nested values are not.
    """
    if _leading_blank(key):
        return False
    if isinstance(value, bool):
        return True
    if isinstance(value, str):
        return not _leading_blank(value)
    if isinstance(value, (int, float)):
        return True
    return False


def _leading_blank(value: str) -> bool:
    return value.lstrip() == ""


# Decimal.parse/1 succeeds when a numeric prefix is present and ignores the rest.
_DECIMAL_PREFIX = re.compile(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?")
_MISSING = object()


def revenue_discarded(revenue: Any) -> bool:
    """Return whether ingestion will store the event without this revenue.

    A revenue object needs ``currency`` and ``amount``. ``currency`` has to
    be one of the current ISO 4217 codes Plausible accepts. ``amount`` has
    to be an integer, a finite float, or a string with a numeric prefix.
    Anything else is ignored. The event is still recorded and the response
    is HTTP 202, with no header for the discarded revenue.

    A non-finite amount is not valid JSON, so the whole event would fail
    to parse. That case raises ValueError instead of being sent.
    """
    if revenue is None:
        return False
    if not isinstance(revenue, dict):
        return True
    amount = revenue.get("amount", _MISSING)
    currency = revenue.get("currency", _MISSING)
    if amount is _MISSING or currency is _MISSING:
        return True
    if not isinstance(currency, str) or currency not in CURRENT_CURRENCIES:
        return True
    return not _amount_kept(amount)


def _amount_kept(amount: Any) -> bool:
    if isinstance(amount, bool):
        return False
    if isinstance(amount, int):
        return True
    if isinstance(amount, float):
        if not math.isfinite(amount):
            raise ValueError(
                "revenue amount must be a finite number. "
                "A non-finite value is not valid JSON and the event is not recorded."
            )
        return True
    if isinstance(amount, str):
        return _DECIMAL_PREFIX.match(amount) is not None
    return False


def _stored_prop_text(value: PropValue) -> str:
    """Return the string the ingestion parser stores for a property value."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return value
    return str(value)
