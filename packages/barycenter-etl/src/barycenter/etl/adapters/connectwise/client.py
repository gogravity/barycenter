"""CWManageClient: httpx + tenacity + token-bucket throttle + paginate iterator.

Critical correctness invariants:
  - terminal_reason MUST be one of {short_page, empty_page, http_error,
    rate_limit_exhausted} before the iterator returns. Callers that need
    silent-truncation safety MUST check ``last_sync_result().terminal_reason``
    and abort if not in {short_page, empty_page} (Pitfall 4).
  - Token-bucket throttle enforces a sustained 60 rpm cap (configurable).
  - 429 retries via tenacity with exponential backoff respecting Retry-After.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Iterator

import httpx
from tenacity import (
    RetryError,
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from barycenter.etl.adapters.connectwise.auth import CWAuthStrategy
from barycenter.etl.framework.exceptions import (
    PaginationTruncated,
    RateLimitExhausted,
)


def _is_transient(exc: BaseException) -> bool:
    """Return True only for errors worth retrying (transient conditions).

    Permanent 4xx errors (401, 403, 404, 422, …) are not retried — a bad
    credential or misconfigured path should fail immediately rather than
    burning 5 attempts with exponential back-off.
    """
    if isinstance(exc, httpx.TransportError):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in (429, 500, 502, 503, 504)
    return False


@dataclass
class SyncResult:
    """Outcome of a paginate() iteration. ``terminal_reason`` is the gate."""

    pages_fetched: int = 0
    total_records: int = 0
    last_page_size: int = 0
    terminal_reason: str = ""

    def is_clean(self) -> bool:
        return self.terminal_reason in {"short_page", "empty_page"}


class CWManageClient:
    """ConnectWise Manage REST client.

    Defaults: 60 rpm sustained, page_size 1000, version 2024.1, 30s timeout.
    """

    def __init__(
        self,
        server_url: str,
        auth: CWAuthStrategy,
        *,
        rpm: int = 60,
        page_size: int = 1000,
        api_version: str = "2024.1",
        timeout: float = 30.0,
    ) -> None:
        if rpm <= 0:
            raise ValueError(f"rpm must be > 0, got {rpm}")
        if page_size <= 0:
            raise ValueError(f"page_size must be > 0, got {page_size}")
        self._auth = auth
        self._rpm = rpm
        self._page_size = page_size
        self._min_interval = 60.0 / rpm
        self._last_request = 0.0
        # server_url (from api-cw-server-url KV secret) already includes the full
        # API base path (e.g. https://na.myconnectwise.net/v4_6_release/apis/3.0).
        # Use it directly so paths like /finance/agreements resolve correctly.
        self._client = httpx.Client(
            base_url=server_url.rstrip('/'),
            headers={
                "Accept": (
                    f"application/vnd.connectwise.com+json; version={api_version}"
                ),
            },
            timeout=timeout,
        )
        self._last_sync = SyncResult()

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_request = time.monotonic()

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=2, max=60),
        retry=retry_if_exception(_is_transient),
        reraise=True,
    )
    def _get(self, path: str, params: dict) -> httpx.Response:
        self._throttle()
        headers = self._auth.headers()
        r = self._client.get(path, params=params, headers=headers)
        if r.status_code == 429:
            ra = int(r.headers.get("Retry-After", "5"))
            time.sleep(min(ra, 60))
            r.raise_for_status()  # triggers tenacity retry
        r.raise_for_status()
        return r

    def paginate(
        self, path: str, *, conditions: str | None = None
    ) -> Iterator[dict]:
        """Yield records across pages; sets terminal_reason on exit.

        Termination semantics (Pitfall 4):
          - empty_page: first page returned 0 records OR a later page after
            short-page detection returned 0.
          - short_page: a page returned fewer than page_size records (clean).
          - rate_limit_exhausted: tenacity exhausted retries on 429.
          - http_error: any other httpx error (raises after marking).
        """
        self._last_sync = SyncResult()
        page = 1
        while True:
            params: dict = {"page": page, "pageSize": self._page_size}
            if conditions:
                params["conditions"] = conditions
            try:
                r = self._get(path, params)
            except RetryError as exc:
                self._last_sync.terminal_reason = "rate_limit_exhausted"
                raise RateLimitExhausted(
                    f"tenacity retries exhausted on {path} page={page}: {exc}"
                ) from exc
            except httpx.HTTPStatusError as exc:
                # Tenacity reraises the underlying HTTPStatusError after retries
                # are exhausted (e.g., persistent 429 because raise_for_status()
                # fires inside the wrapped function). Treat as rate-limit
                # exhaustion if the final status is 429; else http_error.
                if exc.response is not None and exc.response.status_code == 429:
                    self._last_sync.terminal_reason = "rate_limit_exhausted"
                    raise RateLimitExhausted(
                        f"persistent 429 on {path} page={page}: {exc}"
                    ) from exc
                self._last_sync.terminal_reason = "http_error"
                raise
            except httpx.HTTPError:
                self._last_sync.terminal_reason = "http_error"
                raise

            records = r.json()
            if not isinstance(records, list):
                self._last_sync.terminal_reason = "http_error"
                raise httpx.HTTPError(
                    f"expected list response from {path}, got "
                    f"{type(records).__name__}"
                )
            self._last_sync.pages_fetched = page
            self._last_sync.total_records += len(records)
            self._last_sync.last_page_size = len(records)
            yield from records
            if len(records) == 0:
                self._last_sync.terminal_reason = "empty_page"
                return
            if len(records) < self._page_size:
                self._last_sync.terminal_reason = "short_page"
                return
            page += 1

    def last_sync_result(self) -> SyncResult:
        return self._last_sync

    def assert_clean_termination(self, path: str) -> None:
        """Raise PaginationTruncated unless terminal_reason is clean."""
        if not self._last_sync.is_clean():
            raise PaginationTruncated(
                f"pagination of {path} terminated with reason "
                f"{self._last_sync.terminal_reason!r}; refusing to commit "
                f"truncated data"
            )

    def close(self) -> None:
        self._client.close()
