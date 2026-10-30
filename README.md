# plausible-client

[![CI](https://github.com/by-ae/plausible-client/actions/workflows/ci.yml/badge.svg)](https://github.com/by-ae/plausible-client/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/plausible-client.svg)](https://pypi.org/project/plausible-client/)
[![Python Versions](https://img.shields.io/pypi/pyversions/plausible-client.svg)](https://pypi.org/project/plausible-client/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A clean, typed Python client for [Plausible Analytics](https://plausible.io/) HTTP APIs.

## Features

- 🔒 **Fully typed** with comprehensive type hints and `py.typed` marker
- 🚀 **Both sync and async** clients built on httpx
- 📊 **Stats API v2** support with typed query builder
- 📈 **Events API** for sending pageviews and custom events
- 🏗️ **Sites API** for programmatic site and goal management
- 🔄 **Automatic retry** with exponential backoff on rate limits and server errors
- 🏢 **Self-hosted** Plausible instance support
- ✨ **Clean API** with builder pattern for queries
- 🐍 **Python 3.10+** with full 3.13 support

## Installation

```bash
pip install plausible-client
```

## Quick Start

### Stats API - Querying Analytics Data

```python
from datetime import date, timedelta
from plausible_client import Client, QueryBuilder, Metric, Dimension

# Initialize the client
client = Client(api_key="your-api-key")

# Build and execute a query
today = date.today()
last_week = today - timedelta(days=7)

query = (
    QueryBuilder("example.com")
    .metrics(Metric.VISITORS, Metric.PAGEVIEWS, Metric.BOUNCE_RATE)
    .dimensions(Dimension.VISIT_SOURCE)
    .date_range(last_week, today)
    .order_by(Metric.VISITORS, "desc")
    .limit(10)
)

result = client.query(query)

for row in result.results:
    print(f"Source: {row['dimensions']}, Visitors: {row['metrics'][0]}")
```

### Async Client

```python
import asyncio
from plausible_client import AsyncClient, QueryBuilder, Metric


async def get_stats():
    async with AsyncClient(api_key="your-api-key") as client:
        query = QueryBuilder("example.com").metrics(Metric.VISITORS).date_range("7d")
        result = await client.query(query)
        return result


stats = asyncio.run(get_stats())
```

### Events API - Sending Events

```python
from plausible_client import Client

client = Client(api_key="your-api-key")

# Send a pageview
client.send_event(
    domain="example.com",
    name="pageview",
    url="https://example.com/page",
    user_agent="Mozilla/5.0...",  # Forward from visitor
    x_forwarded_for="192.168.1.1",  # Forward visitor IP
)

# Send a custom event with properties
client.send_event(
    domain="example.com",
    name="signup",
    url="https://example.com/signup",
    props={
        "plan": "premium",
        "trial": True,
    },
)

# Send an event with revenue
client.send_event(
    domain="example.com",
    name="purchase",
    url="https://example.com/checkout",
    props={"product": "widget"},
    revenue={
        "amount": 99.99,
        "currency": "USD",
    },
    referrer="https://news.ycombinator.com/",
)

# Behind Cloudflare, also set CF-Connecting-IP to the visitor IP.
# Plausible prefers that header over X-Forwarded-For, and a proxy IP
# can cause the event to be dropped.
client.send_event(
    domain="example.com",
    name="pageview",
    url="https://example.com/docs",
    x_forwarded_for="203.0.113.5",
    cf_connecting_ip="203.0.113.5",
)

# A non-interactive event is excluded from bounce-rate calculations.
# This applies to custom events. pageview and other system events stay
# interactive, and interactive=False is rejected for those names.
# HTTP 202 does not mean the event was recorded: check result.dropped.
result = client.send_event(
    domain="example.com",
    name="scroll",
    url="https://example.com/docs",
    interactive=False,
)
if result.dropped:
    print("Event was dropped (see the x-plausible-dropped response header)")
```

`send_event()` rejects a blank domain, an empty or 120+ character event name, a URL longer than 2000 bytes, and a `data:` URL. Property keys longer than 300 bytes and values longer than 2000 bytes are rejected too. At most 30 properties are stored; further keys are discarded by the API, and blank values are discarded.

### Sites API - Managing Sites Programmatically

```python
from plausible_client import Client

client = Client(api_key="your-sites-api-key")

# List all accessible sites. One response holds at most 100 sites.
# meta["after"] is the next cursor, and null means there is no next page.
sites = client.list_all_sites()
for site in sites:
    print(f"{site.domain} ({site.timezone})")

# Create a new site
new_site = client.create_site(
    domain="newsite.com",
    timezone="America/New_York",
    tracker_script_configuration={
        "file_downloads": True,
        "outbound_links": True,
    },
)

# Get site details
site = client.get_site("example.com")
print(f"Custom properties: {site.custom_properties}")

# Create a goal
goal = client.create_goal(
    site_id="example.com",
    goal_type="event",
    event_name="signup",
    display_name="User Signup",
)

# List goals. list_all_goals, list_all_guests, and list_all_teams
# follow meta["after"] the same way, keeping limit the same on each request.
goals = client.list_all_goals("example.com")

# Invite a guest
guest = client.invite_guest(
    site_id="example.com",
    email="viewer@example.com",
    role="viewer",  # or "editor"
)

# Create a shared dashboard link
link = client.create_shared_link("example.com", "Public Dashboard")
print(f"Share at: {link.url}")
```

## Advanced Usage

### Query Builder Options

The `QueryBuilder` supports all Stats API v2 features:

```python
from datetime import date

from plausible_client import QueryBuilder, Metric, Dimension

query = (
    QueryBuilder("example.com")
    # Multiple metrics
    .metrics(
        Metric.VISITORS,
        Metric.VISITS,
        Metric.PAGEVIEWS,
        Metric.BOUNCE_RATE,
        Metric.VISIT_DURATION,
    )
    # Multiple dimensions for breakdowns
    .dimensions(
        Dimension.EVENT_PAGE,
        Dimension.VISIT_SOURCE,
    )
    # Filters with various operators
    .filter(Dimension.VISIT_SOURCE, "is", "Google")
    # visit:country is and is_not take 2-letter codes. visit:city takes GeoName IDs.
    .filter(Dimension.VISIT_COUNTRY, "is_not", ["US", "GB"])
    .filter(Dimension.VISIT_CITY, "is", 4347778)
    # Saved segments take an integer id: .filter("segment", "is", 123)
    .filter(Dimension.EVENT_PAGE, "contains", "/blog/")
    # Case-insensitive match (Stats API modifier for "is" and "contains")
    .filter(Dimension.VISIT_COUNTRY_NAME, "contains", "united", case_sensitive=False)
    # Custom date range. Presets also work: .date_range("7d")
    .date_range(date(2024, 1, 1), date(2024, 1, 31))
    # Ordering
    .order_by(Metric.VISITORS, "desc")
    # Pagination
    .limit(50)
    .offset(0)
    # Include options. trim_relative_date_range drops empty time after
    # the current moment for "day", "month", and "year" ranges.
    .include(imports=True, time_labels=True, total_rows=True, trim_relative_date_range=True)
)
```

`date_range` is required by the Stats API. Presets are `"day"`, `"24h"`, `"7d"`, `"28d"`, `"30d"`, `"91d"`, `"month"`, `"6mo"`, `"12mo"`, `"year"`, and `"all"`. A relative range is also accepted: `"14d"` means the last 1 to 5000 days, and `"3mo"` means the last 1 to 100 months. A custom range is two dates or two timezone-aware datetimes. Naive datetimes are rejected, because a timestamp without an offset is not a valid Stats API range. The start and end must both be dates or both be datetimes.

Top-level filters are combined with an implicit `and`. `where()` adds `or`, explicit `and`, `not`, and the behavioral filters `has_done` and `has_not_done`. Behavioral filters select sessions by whether another event occurred, and they only accept an `event:` dimension (including `Dimension.event_property("author")`, which is `event:props:author`).

`event:goal` filters only accept `is` and `contains`. `segment` filters only accept `is`. Time dimensions are rejected in filters; set `date_range` for those. `order_by` cannot use `event:goal` or `segment`, and each entry has to be one of the query's metrics or dimensions. `limit` must be from 1 to 10000 and `offset` must be zero or greater. Metrics and dimensions must be unique. `include.time_labels` requires a time dimension.

`scroll_depth` and `time_on_page` need an `event:page` filter or dimension. A nested `event:page` filter is enough for `time_on_page`. `scroll_depth` needs that filter at the top level, or `event:page` as a dimension. `conversion_rate` and `group_conversion_rate` need an `event:goal` filter or dimension. `views_per_visit` cannot be filtered by `event:page` or broken down by a non-time dimension. `bounce_rate`, `visit_duration`, and `views_per_visit` can be broken down by `event:page` (and `event:hostname` together with `event:page`). Other event dimensions cannot be combined with those session metrics. `pageviews`, `events`, `scroll_depth`, and `time_on_page` cannot be broken down by entry or exit page. `event:goal` and `event:hostname` filters have to stay at the top level. A behavioral filter may still use `event:goal`.

```python
from plausible_client import (
    QueryBuilder,
    Dimension,
    Metric,
    any_of,
    filter_clause,
    has_done,
    has_not_done,
)

query = (
    QueryBuilder("example.com")
    .metrics(Metric.VISITORS)
    .date_range("7d")
    .dimensions(Dimension.event_property("author"))
    .where(
        any_of(
            filter_clause(Dimension.VISIT_COUNTRY_NAME, "is", "Germany"),
            filter_clause(Dimension.VISIT_CITY_NAME, "is", "Tallinn"),
        ),
        has_done(filter_clause(Dimension.EVENT_PAGE, "is", "/pricing")),
        has_not_done(filter_clause(Dimension.EVENT_GOAL, "is", "Signup")),
    )
)
```

### Automatic Pagination

For queries with many results, use `query_all()` to automatically fetch all pages:

```python
from plausible_client import Client, QueryBuilder, Metric, Dimension
from datetime import date, timedelta

client = Client(api_key="your-api-key")

# Build query for pages by source
today = date.today()
last_month = today - timedelta(days=30)

query = (
    QueryBuilder("example.com")
    .metrics(Metric.VISITORS, Metric.PAGEVIEWS)
    .dimensions(Dimension.EVENT_PAGE, Dimension.VISIT_SOURCE)
    .date_range(last_month, today)
    .order_by(Metric.VISITORS, "desc")
)

# Fetch all results automatically (handles pagination internally)
result = client.query_all(query, page_size=1000)

print(f"Total rows: {result.meta['total_rows']}")
for row in result.results:
    print(
        f"Page: {row['dimensions'][0]}, Source: {row['dimensions'][1]}, "
        f"Visitors: {row['metrics'][0]}, Pageviews: {row['metrics'][1]}"
    )
```

The `query_all()` method:
- Automatically makes multiple requests to fetch all results
- Combines results from all pages into a single QueryResult
- Defaults to 1000 results per page (configurable up to 10000)
- Works with both `Client` and `AsyncClient`

```python
# Async version
async with AsyncClient(api_key="your-api-key") as client:
    result = await client.query_all(query, page_size=1000)
```

### Available Metrics

```python
from plausible_client import Metric

Metric.VISITORS  # Unique visitors
Metric.VISITS  # Total visits
Metric.PAGEVIEWS  # Total pageviews
Metric.VIEWS_PER_VISIT  # Average pageviews per visit
Metric.BOUNCE_RATE  # Bounce rate percentage
Metric.VISIT_DURATION  # Average visit duration
Metric.EVENTS  # Total custom events
Metric.SCROLL_DEPTH  # Average scroll depth (needs event:page)
Metric.PERCENTAGE  # Share of visitors (needs a dimension)
Metric.CONVERSION_RATE  # Goal conversion rate (needs event:goal)
Metric.GROUP_CONVERSION_RATE  # Conversion rate within each dimension group
Metric.AVERAGE_REVENUE  # Average revenue for a revenue goal
Metric.TOTAL_REVENUE  # Total revenue for a revenue goal
Metric.TIME_ON_PAGE  # Average seconds on a page (needs event:page)
```

### Available Dimensions

```python
from plausible_client import Dimension

# Event dimensions
Dimension.EVENT_NAME
Dimension.EVENT_PAGE
Dimension.EVENT_GOAL
Dimension.EVENT_HOSTNAME

# Visit dimensions
Dimension.VISIT_ENTRY_PAGE
Dimension.VISIT_EXIT_PAGE
Dimension.VISIT_SOURCE
Dimension.VISIT_CHANNEL
Dimension.VISIT_REFERRER
Dimension.VISIT_UTM_MEDIUM
Dimension.VISIT_UTM_SOURCE
Dimension.VISIT_UTM_CAMPAIGN
Dimension.VISIT_UTM_CONTENT
Dimension.VISIT_UTM_TERM

# Technology dimensions
Dimension.VISIT_SCREEN
Dimension.VISIT_DEVICE
Dimension.VISIT_BROWSER
Dimension.VISIT_BROWSER_VERSION
Dimension.VISIT_OS
Dimension.VISIT_OS_VERSION

# Geographic dimensions
Dimension.VISIT_COUNTRY
Dimension.VISIT_REGION
Dimension.VISIT_CITY
Dimension.VISIT_COUNTRY_NAME
Dimension.VISIT_REGION_NAME
Dimension.VISIT_CITY_NAME

# Time dimensions (not usable in filters; set date_range instead)
Dimension.TIME
Dimension.TIME_HOUR
Dimension.TIME_DAY
Dimension.TIME_WEEK
Dimension.TIME_MONTH
```

### Self-Hosted Plausible

```python
from plausible_client import Client

client = Client(
    api_key="your-api-key",
    base_url="https://analytics.yourcompany.com",
    timeout=60.0,  # Custom timeout
)
```

### Error Handling

The client raises typed exceptions for different error scenarios:

```python
from plausible_client import (
    Client,
    AuthenticationError,
    PaymentRequiredError,
    ForbiddenError,
    NotFoundError,
    RateLimitError,
    InvalidQueryError,
    ServerError,
)

client = Client(api_key="your-api-key")

try:
    result = client.query(query)
except AuthenticationError:
    print("Invalid API key")
except PaymentRequiredError as e:
    # The message is the API error, for example a site limit or a missing feature.
    print(e.message)
except ForbiddenError as e:
    print(f"API key cannot do this: {e.message}")
except NotFoundError as e:
    print(f"Missing resource: {e.message}")
except RateLimitError as e:
    print(f"Rate limited. Retry after {e.retry_after} seconds")
except InvalidQueryError as e:
    print(f"Invalid query: {e.message}")
    print(f"Details: {e.errors}")
except ServerError as e:
    print(f"Server error: {e.status_code}")
```

### Retry Behavior

The client automatically retries on:
- **429 (Rate Limit)**: Waits for the `Retry-After` header. Both delay-seconds (`60`, `1.5`) and HTTP-date values are honoured. If the header is missing or cannot be parsed, the client uses exponential backoff instead of failing the retry.
- **5xx (Server Errors)**: Exponential backoff (2^attempt seconds, max 60s)
- **Connection Errors**: Network failures (excluding timeouts)

Timeouts are NOT retried as they indicate the server is too slow rather than temporarily unavailable.

Maximum 3 retries by default. After exhausting retries, raises `RateLimitError` or `ServerError`. `RateLimitError.retry_after` is the parsed delay in seconds when `Retry-After` was understood, and the exception message includes the API `error` string when the response body has one. The Stats API rate limit is 600 requests per hour by default.

## Development

### Setup

```bash
git clone https://github.com/by-ae/plausible-client.git
cd plausible-client
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -e ".[dev]"
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=plausible_client

# Run only fast tests (skip live integration)
pytest -k "not test_live"

# Run live integration tests (requires env vars)
export PLAUSIBLE_API_KEY="your-api-key"
export PLAUSIBLE_SITE_ID="your-site.com"
pytest tests/test_live.py
```

### Linting and Type Checking

```bash
# Format code
ruff format .

# Lint
ruff check .

# Type check
mypy src/plausible_client
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'feat: add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Links

- **PyPI**: https://pypi.org/project/plausible-client/
- **Repository**: https://github.com/by-ae/plausible-client
- **Issues**: https://github.com/by-ae/plausible-client/issues
- **Plausible Analytics**: https://plausible.io/
- **Plausible API Docs**: https://plausible.io/docs/stats-api
