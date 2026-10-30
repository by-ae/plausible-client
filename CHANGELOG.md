# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `list_all_sites()`, `list_all_goals()`, `list_all_guests()`, and `list_all_teams()` follow the Sites API `after` cursor until it is null. Page size must be from 1 to 100, because a larger `limit` is ignored
- `Dimension.VISIT_SCREEN` (`visit:screen`) for screen-size breakdowns
- `QueryBuilder.include(trim_relative_date_range=True)` drops empty time after the current moment for `day`, `month`, and `year` date ranges
- `QueryBuilder.where()` plus `filter_clause()`, `any_of()`, `all_of()`, and `negate()` for the Stats API `or`, `and`, and `not` filters. `has_done()` and `has_not_done()` build behavioral filters, which only accept an event dimension and cannot be nested
- `Dimension.event_property()` for the documented `event:props:<name>` custom-property dimension
- `send_event(cf_connecting_ip=...)` sets the `CF-Connecting-IP` header. The Events API uses that address instead of `X-Forwarded-For` when the header is present, which matters for requests that pass through Cloudflare
- `PaymentRequiredError` exception for 402 Payment Required responses
- `NotFoundError` for 404 responses and `ForbiddenError` for 403 responses, using the API `error` message when the body includes one
- Events API `referrer` and `interactive` fields on `send_event()`
- Stats API date-range presets (`"7d"`, `"month"`, `"all"`, and the other documented presets) on `QueryBuilder.date_range()`
- `case_sensitive` filter modifier for `is` and `contains`
- Metric and dimension constants that the Stats API documents and this client previously omitted, including revenue, scroll depth, time on page, goals, channel, place names, and time buckets
- `EventResult` from `send_event()`, with `dropped` set from the `x-plausible-dropped` response header. The Events API returns HTTP 202 even when an event is discarded
- Python 3.13 to CI test matrix
- Improved timeout and network error handling with specific retry logic

### Changed

- Timeout exceptions (ConnectTimeout, ReadTimeout, etc.) are no longer retried
- Connection errors and other network failures continue to be retried with exponential backoff

### Added

- Automatic pagination with `query_all()` method for Stats API queries
- `include()` method on `QueryBuilder` for imports, time_labels, and total_rows options
- Support for fetching all results across multiple pages automatically
- `QueryBuilder.copy()` helper method for creating independent query copies
- Support for `contains_not`, `matches`, and `matches_not` filter operators
- Full Sites API (v1) support for programmatic site management
- Site operations: list, get, create, update, delete sites
- Team management: list accessible teams and check API availability
- Goal management: create, list, and delete custom event and pageview goals
- Shared link management: create idempotent shared dashboard links
- Custom property management: create, list, and delete custom event properties
- Guest management: invite, list, and remove site guests and invitations
- New typed models: `Site`, `Team`, `Goal`, `SharedLink`, `Guest`, and `TrackerScriptConfiguration`
- All Sites API methods available in both `Client` and `AsyncClient`

### Fixed

- `send_event()` sets `EventResult.revenue_discarded` when the revenue currency is not a current ISO 4217 code Plausible accepts, or the amount is not a number or numeric string. The event is still sent, matching the API, which records it and drops the revenue. A non-finite amount is rejected before the request
- `QueryBuilder.build()` rejects `order_by` entries that are not selected metrics or dimensions, `include.time_labels` without a time dimension, and metric or dimension combinations the stats query builder refuses. `event:goal` and `event:hostname` filters are rejected when nested
- 402 responses keep the API `error` string, such as a site limit or a plan that does not include shared links or custom properties
- `send_event()` rejects blank domains, empty or 120+ character event names, URLs longer than 2000 bytes, and `data:` URLs. Property keys longer than 300 bytes and values longer than 2000 bytes are rejected. `interactive=False` is rejected for system events such as `pageview`, because the ingestion pipeline ignores the flag and still counts them as interactive
- Time dimensions are rejected in filters. `event:goal` filters only accept `is` and `contains`, and `segment` filters only accept `is`. `order_by` rejects `event:goal` and `segment`. `limit()` must be from 1 to 10000, `offset()` must be zero or greater, and duplicate metrics or dimensions are rejected. The query schema refuses those payloads
- `QueryBuilder.date_range()` accepts relative ranges such as `"14d"` and `"3mo"`. The Stats API parser allows 1 to 5000 days and 1 to 100 months. Values outside those bounds are rejected before the request
- Stats API filters now use the clause types the query parser accepts. A single `visit:city` GeoName ID or `segment` id is sent as a one-element list of integers. String city or segment ids, integer clauses on other dimensions, and `visit:country` `is` / `is_not` values that are not 2 characters are rejected before the request
- `QueryBuilder.date_range()` rejects naive datetimes and mixed date/datetime pairs. The Stats API accepts calendar dates or timestamps that include an offset, and a mixed pair matches neither form
- Sites API deletion checks accept the boolean `true` the server returns, as well as the string `"true"` shown in the docs examples. `delete_site()`, `delete_goal()`, and `delete_guest()` no longer report failure after a successful delete
- Goal ids from the Sites API are coerced to strings, matching the documented id format
- 400 responses that use an `errors` object (Events API validation) include those details in `InvalidQueryError`
- 429 responses honour `Retry-After` delay-seconds and HTTP-date values, including fractional seconds. A non-numeric header no longer raises `ValueError` after retries; it falls back to exponential backoff and leaves `RateLimitError.retry_after` unset
- `RateLimitError` uses the JSON `error` message from a 429 body when one is present
- Stats API v2 payload format now matches API specification at https://plausible.io/docs/stats-api
- Pagination sent as nested `{"pagination": {"limit": N, "offset": M}}` object (was top-level keys)
- `order_by` sent as list of `[metric, direction]` pairs (was list of dict objects)
- Filters sent as `[operator, dimension, clauses]` with clauses always a list (was `[dimension, operator, value]`)
- Default pagination values (limit: 10000, offset: 0) now match API defaults
- `query_all()` validates page_size is between 1 and 10000 (raises ValueError otherwise)
- `query_all()` guards against infinite loops by breaking on empty result pages
- Deprecated `does_not_contain` operator now correctly maps to `contains_not`

## [0.1.0] - 2026-10-22

### Added

- Initial release of plausible-client
- `Client` and `AsyncClient` with httpx backend
- Support for Plausible Stats API v2 with typed query builder
- Support for Plausible Events API for pageviews and custom events
- Comprehensive error types (AuthenticationError, RateLimitError, InvalidQueryError, ServerError)
- Automatic retry with exponential backoff on 429/5xx errors
- Full type annotations with py.typed marker
- Support for self-hosted Plausible instances
- Python 3.10-3.13 compatibility
