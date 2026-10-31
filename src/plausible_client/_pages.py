"""Cursor pagination for Sites API list endpoints.

The list responses put the next cursor in ``meta.after``. ``null`` means
there is no next page, and every request in a walk has to send the same
limit. ``Plausible.Pagination`` ignores a limit above 100 and keeps the
default page size, so callers cannot ask for a larger page.
"""

from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from plausible_client.errors import PlausibleError

T = TypeVar("T")

MAX_PAGE_SIZE = 100


def _check_bound(value: int, *, maximum: int, label: str) -> None:
    """Reject values ``Plausible.Pagination`` will not use as the page size.

    ``to_pagination_opts/1`` keeps a limit only when it is an integer from
    1 to 100. ``true`` and ``1.5`` are not integers, and a larger limit is
    dropped so the default page size is used instead.
    """
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= maximum:
        raise ValueError(f"{label} must be an integer from 1 to {maximum}, got {value!r}")


def check_page_size(page_size: int) -> None:
    """Reject a page size the Sites API pagination helper will not apply."""
    _check_bound(page_size, maximum=MAX_PAGE_SIZE, label="page_size")


def check_list_limit(limit: int) -> None:
    """Reject a ``limit`` the Sites API list endpoints will ignore."""
    _check_bound(limit, maximum=MAX_PAGE_SIZE, label="limit")


def collect_pages(
    fetch: Callable[[str | None], tuple[list[T], dict[str, Any]]],
) -> list[T]:
    """Follow ``meta.after`` until it is null."""
    return _collect(fetch)


async def collect_pages_async(
    fetch: Callable[[str | None], Awaitable[tuple[list[T], dict[str, Any]]]],
) -> list[T]:
    """Async form of :func:`collect_pages`."""
    collected: list[T] = []
    after: str | None = None
    seen: set[str] = set()
    while True:
        page, meta = await fetch(after)
        collected.extend(page)
        after = _advance(meta, seen)
        if after is None:
            return collected


def _collect(fetch: Callable[[str | None], tuple[list[T], dict[str, Any]]]) -> list[T]:
    collected: list[T] = []
    after: str | None = None
    seen: set[str] = set()
    while True:
        page, meta = fetch(after)
        collected.extend(page)
        after = _advance(meta, seen)
        if after is None:
            return collected


def _advance(meta: dict[str, Any], seen: set[str]) -> str | None:
    cursor = meta.get("after")
    if cursor is None:
        return None
    if not isinstance(cursor, str) or cursor == "":
        raise PlausibleError("Sites API pagination cursor must be a string or null")
    if cursor in seen:
        raise PlausibleError("Sites API pagination cursor did not advance")
    seen.add(cursor)
    return cursor
