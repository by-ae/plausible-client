"""Encode values that are placed in a Sites API URL path.

httpx parses a full URL string before sending it. A ``?`` starts the query
string, a ``#`` starts a fragment that is never sent, and a bare ``%`` is an
invalid escape. The request then addresses a different site, guest, goal, or
custom property than the one the caller named.

Guest emails keep ``@`` and ``+`` as written. Both are valid in one path
segment, and the router does not treat ``+`` as a space there.

Custom property names keep ``/``. The route is ``/custom-props/*property``
and the controller joins those wildcard segments back into the name.
"""

from urllib.parse import quote


def encode_path_segment(value: str) -> str:
    """Encode one path segment, leaving ``@`` and ``+`` unchanged."""
    return quote(value, safe="@+")


def encode_property_path(value: str) -> str:
    """Encode a custom property name, leaving slashes as path separators."""
    return quote(value, safe="/")
