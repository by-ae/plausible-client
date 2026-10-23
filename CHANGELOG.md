# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Full Sites API (v1) support for programmatic site management
- Site operations: list, get, create, update, delete sites
- Team management: list accessible teams and check API availability
- Goal management: create, list, and delete custom event and pageview goals
- Shared link management: create idempotent shared dashboard links
- Custom property management: create, list, and delete custom event properties
- Guest management: invite, list, and remove site guests and invitations
- New typed models: `Site`, `Team`, `Goal`, `SharedLink`, `Guest`, and `TrackerScriptConfiguration`
- All Sites API methods available in both `Client` and `AsyncClient`

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
