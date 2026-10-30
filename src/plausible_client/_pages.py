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


def check_page_size(page_size: int) -> None:
    """Reject a page size the Sites API pagination helper will not apply."""
    if (
        isinstance(page_size, bool)
        or not isinstance(page_size, int)
        or not 1 <= page_size <= MAX_PAGE_SIZE
    ):
        raise ValueError(
            f"page_size must be an integer from 1 to {MAX_PAGE_SIZE}, got {page_size!r}"
        )


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
