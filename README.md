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
        query = QueryBuilder("example.com").metrics(Metric.VISITORS)
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
)
```

### Sites API - Managing Sites Programmatically

```python
from plausible_client import Client

client = Client(api_key="your-sites-api-key")

# List all accessible sites
sites, meta = client.list_sites()
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

# List goals
goals, meta = client.list_goals("example.com")

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
    .filter(Dimension.VISIT_COUNTRY, "is_not", ["US", "UK"])
    .filter(Dimension.EVENT_PAGE, "contains", "/blog/")
    # Date range
    .date_range(date(2024, 1, 1), date(2024, 1, 31))
    # Ordering
    .order_by(Metric.VISITORS, "desc")
    # Pagination
    .limit(50)
    .offset(0)
    # Include options
    .include(imports=True, time_labels=True, total_rows=True)
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
Metric.CONVERSION_RATE  # Goal conversion rate
```

### Available Dimensions

```python
from plausible_client import Dimension

# Event dimensions
Dimension.EVENT_NAME
Dimension.EVENT_PAGE

# Visit dimensions
Dimension.VISIT_SOURCE
Dimension.VISIT_REFERRER
Dimension.VISIT_UTM_MEDIUM
Dimension.VISIT_UTM_SOURCE
Dimension.VISIT_UTM_CAMPAIGN
Dimension.VISIT_UTM_CONTENT
Dimension.VISIT_UTM_TERM

# Technology dimensions
Dimension.VISIT_DEVICE
Dimension.VISIT_BROWSER
Dimension.VISIT_BROWSER_VERSION
Dimension.VISIT_OS
Dimension.VISIT_OS_VERSION

# Geographic dimensions
Dimension.VISIT_COUNTRY
Dimension.VISIT_REGION
Dimension.VISIT_CITY
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
    RateLimitError,
    InvalidQueryError,
    ServerError,
)

client = Client(api_key="your-api-key")

try:
    result = client.query(query)
except AuthenticationError:
    print("Invalid API key")
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
- **429 (Rate Limit)**: Respects `Retry-After` header
- **5xx (Server Errors)**: Exponential backoff (2^attempt seconds, max 60s)

Maximum 3 retries by default. After exhausting retries, raises `RateLimitError` or `ServerError`.

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
