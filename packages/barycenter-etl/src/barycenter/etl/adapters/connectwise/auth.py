"""ConnectWise Manage authentication strategies (Pitfall 2).

Two strategies because CW tenant capability varies:
  - HTTP Basic Auth (API Member key) -- most universally enabled
  - OAuth 2.0 Client Credentials -- newer CW Cloud

The strategy interface allows the operator to switch via CW_AUTH_MODE env or
config without touching client code. Plan 06 verifies which method is enabled
on Gravity's tenant before first sync.
"""
from __future__ import annotations

import base64
import time
from typing import Protocol

import httpx


class CWAuthStrategy(Protocol):
    """Auth strategy interface; ``headers()`` returns request headers per call."""

    def headers(self) -> dict[str, str]: ...


class BasicAuthStrategy:
    """HTTP Basic Auth using CW Member key (``Company+publicKey:privateKey``)."""

    def __init__(
        self,
        company: str,
        public_key: str,
        private_key: str,
        client_id: str,
    ) -> None:
        if not all((company, public_key, private_key, client_id)):
            raise ValueError("BasicAuthStrategy requires non-empty company/keys/client_id")
        user = f"{company}+{public_key}"
        tok = base64.b64encode(f"{user}:{private_key}".encode()).decode()
        self._headers = {
            "Authorization": f"Basic {tok}",
            "clientId": client_id,
        }

    def headers(self) -> dict[str, str]:
        return dict(self._headers)


class OAuthClientCredsStrategy:
    """OAuth 2.0 client-credentials. Token cached with TTL; refreshes proactively."""

    def __init__(
        self,
        token_endpoint: str,
        client_id: str,
        client_secret: str,
        *,
        scope: str = "default",
    ) -> None:
        if not all((token_endpoint, client_id, client_secret)):
            raise ValueError(
                "OAuthClientCredsStrategy requires endpoint/client_id/client_secret"
            )
        self._endpoint = token_endpoint
        self._client_id = client_id
        self._client_secret = client_secret
        self._scope = scope
        self._token: str | None = None
        self._expires_at: float = 0.0

    def _fetch_token(self) -> None:
        r = httpx.post(
            self._endpoint,
            data={
                "grant_type": "client_credentials",
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "scope": self._scope,
            },
            timeout=30.0,
        )
        r.raise_for_status()
        doc = r.json()
        self._token = doc["access_token"]
        # Refresh ~60s before expiry; default 1h.
        self._expires_at = time.monotonic() + max(
            60, int(doc.get("expires_in", 3600)) - 60
        )

    def headers(self) -> dict[str, str]:
        if not self._token or time.monotonic() >= self._expires_at:
            self._fetch_token()
        return {
            "Authorization": f"Bearer {self._token}",
            "clientId": self._client_id,
        }
