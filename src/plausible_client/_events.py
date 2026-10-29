"""Checks for Events API payloads the ingestion request parser rejects."""

from urllib.parse import urlsplit

# The request parser measures the whole URL with byte_size/1.
MAX_URL_BYTES = 2000
# Ecto validate_length on event_name, counted in characters.
MAX_EVENT_NAME_LENGTH = 120
# Plausible.Props.max_prop_key_length/0 and max_prop_value_length/0.
# The ingestion parser compares those limits with byte_size/1 after
# stringifying each value.
MAX_PROP_KEY_BYTES = 300
MAX_PROP_VALUE_BYTES = 2000

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


def validate_event(
    *,
    domain: str,
    name: str,
    url: str,
    interactive: bool | None,
    props: dict[str, PropValue] | None,
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


def _validate_props(props: dict[str, PropValue]) -> None:
    for key, value in props.items():
        if len(key.encode("utf-8")) > MAX_PROP_KEY_BYTES:
            raise ValueError(f"property key {key!r} is longer than {MAX_PROP_KEY_BYTES} bytes")
        stored = _stored_prop_text(value)
        if len(stored.encode("utf-8")) > MAX_PROP_VALUE_BYTES:
            raise ValueError(f"property {key!r} is longer than {MAX_PROP_VALUE_BYTES} bytes")


def _stored_prop_text(value: PropValue) -> str:
    """Return the string the ingestion parser stores for a property value."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return value
    return str(value)
