# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `PaymentRequiredError` exception for 402 Payment Required responses
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
