"""Unit tests for the CW Manage HTTP client (Plan 05).

Uses respx to mock CW REST endpoints; covers paginate terminal_reason
enforcement (Pitfall 4), 429 retry-after handling, exhaustion behavior,
and BasicAuthStrategy header shape.
"""
from __future__ import annotations

import base64

import httpx
import pytest
import respx

from barycenter.etl.adapters.connectwise.auth import (
    BasicAuthStrategy,
    OAuthClientCredsStrategy,
)
from barycenter.etl.adapters.connectwise.client import (
    CWManageClient,
    SyncResult,
)
from barycenter.etl.framework.exceptions import RateLimitExhausted


# server_url must be the full API base path (matches api-cw-server-url KV secret format).
# The client uses it verbatim as the httpx base_url — no suffix is appended.
SERVER = "https://api-na.myconnectwise.net/v4_6_release/apis/3.0"
BASE = SERVER


def _client(rpm: int = 6000, page_size: int = 2) -> CWManageClient:
    """Build a client with high rpm so tests don't sleep."""
    auth = BasicAuthStrategy("Acme", "pub", "priv", "cid")
    return CWManageClient(SERVER, auth, rpm=rpm, page_size=page_size)


def test_basic_auth_header_shape() -> None:
    auth = BasicAuthStrategy("Acme", "pub", "priv", "cid")
    headers = auth.headers()
    assert headers["clientId"] == "cid"
    assert headers["Authorization"].startswith("Basic ")
    decoded = base64.b64decode(
        headers["Authorization"].split(" ", 1)[1]
    ).decode()
    assert decoded == "Acme+pub:priv"


def test_basic_auth_rejects_empty_inputs() -> None:
    with pytest.raises(ValueError):
        BasicAuthStrategy("", "pub", "priv", "cid")


def test_oauth_strategy_rejects_empty_inputs() -> None:
    with pytest.raises(ValueError):
        OAuthClientCredsStrategy("", "id", "secret")


@respx.mock
def test_paginate_yields_records_and_stops_on_short_page() -> None:
    """Two pages: full first, short second -> terminal_reason='short_page'."""
    cw = _client(page_size=2)
    route = respx.get(f"{BASE}/company/companies").mock(
        side_effect=[
            httpx.Response(200, json=[{"id": 1}, {"id": 2}]),
            httpx.Response(200, json=[{"id": 3}]),
        ]
    )
    records = list(cw.paginate("/company/companies"))
    assert [r["id"] for r in records] == [1, 2, 3]
    res = cw.last_sync_result()
    assert isinstance(res, SyncResult)
    assert res.terminal_reason == "short_page"
    assert res.pages_fetched == 2
    assert res.total_records == 3
    assert res.is_clean()
    assert route.called


@respx.mock
def test_paginate_stops_on_empty_first_page() -> None:
    cw = _client(page_size=10)
    respx.get(f"{BASE}/company/companies").mock(
        return_value=httpx.Response(200, json=[]),
    )
    records = list(cw.paginate("/company/companies"))
    assert records == []
    res = cw.last_sync_result()
    assert res.terminal_reason == "empty_page"
    assert res.is_clean()


@respx.mock
def test_paginate_429_retry_after_then_succeeds() -> None:
    """A single 429 with Retry-After: 0 retries and yields the next page."""
    cw = _client(page_size=10)
    respx.get(f"{BASE}/service/tickets").mock(
        side_effect=[
            httpx.Response(429, headers={"Retry-After": "0"}, json={}),
            httpx.Response(200, json=[{"id": 9}]),
        ]
    )
    records = list(cw.paginate("/service/tickets"))
    assert [r["id"] for r in records] == [9]
    assert cw.last_sync_result().terminal_reason == "short_page"


@respx.mock
def test_paginate_persistent_429_raises_rate_limit_exhausted() -> None:
    """Five consecutive 429s exhaust tenacity -> RateLimitExhausted."""
    cw = _client(page_size=10)
    respx.get(f"{BASE}/service/tickets").mock(
        return_value=httpx.Response(
            429, headers={"Retry-After": "0"}, json={}
        ),
    )
    with pytest.raises(RateLimitExhausted):
        list(cw.paginate("/service/tickets"))
    assert (
        cw.last_sync_result().terminal_reason == "rate_limit_exhausted"
    )


@respx.mock
def test_assert_clean_termination_rejects_truncated_sync() -> None:
    """If terminal_reason is rate_limit_exhausted, assert_clean raises."""
    from barycenter.etl.framework.exceptions import PaginationTruncated

    cw = _client(page_size=10)
    respx.get(f"{BASE}/service/tickets").mock(
        return_value=httpx.Response(
            429, headers={"Retry-After": "0"}, json={}
        ),
    )
    with pytest.raises(RateLimitExhausted):
        list(cw.paginate("/service/tickets"))
    with pytest.raises(PaginationTruncated):
        cw.assert_clean_termination("/service/tickets")


@respx.mock
def test_paginate_non_list_response_raises_http_error() -> None:
    cw = _client(page_size=10)
    respx.get(f"{BASE}/company/companies").mock(
        return_value=httpx.Response(200, json={"oops": "not a list"}),
    )
    with pytest.raises(httpx.HTTPError):
        list(cw.paginate("/company/companies"))
    assert cw.last_sync_result().terminal_reason == "http_error"
