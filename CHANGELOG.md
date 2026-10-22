# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
