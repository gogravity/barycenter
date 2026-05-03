"""Pseudonymizer: HMAC-SHA256(salt, email_lower) -> person_pid (ENC-02 / Pitfall 5).

Pitfall 5 mitigation invariants:
- Salt is fetched per call from Key Vault, used inline in the HMAC, then
  dereferenced via ``del`` in a finally block.
- Salt material is NEVER assigned to a module attribute or class attribute.
- ``__repr__`` excludes the salt material; only the kv client type name appears.
- Each tenant has its own ``salt-{tenant_id}`` secret name — pids do not
  correlate across tenants without the per-tenant salt (T-02-11).
"""
from __future__ import annotations

import hashlib
import hmac


class Pseudonymizer:
    """Versioned-salt HMAC pseudonymization."""

    def __init__(self, kv_client) -> None:
        self._kv = kv_client

    def derive(
        self,
        email: str,
        tenant_id: str,
        salt_version: str | None = None,
    ) -> tuple[str, str]:
        """Return (person_pid_hex, salt_version) for ``email`` under ``tenant_id``.

        ``email`` is lowercased before HMAC so case variants collapse to the
        same pid. ``salt_version`` is optional; when None the KV client returns
        the current version (its ``properties.version`` is recorded so the
        audit log can replay the derivation under rotation).
        """
        if not isinstance(email, str) or not email:
            raise ValueError(f"email must be a non-empty string, got {email!r}")
        if not isinstance(tenant_id, str) or not tenant_id:
            raise ValueError(
                f"tenant_id must be a non-empty string, got {tenant_id!r}"
            )

        secret_name = f"salt-{tenant_id}"
        if salt_version is not None:
            secret = self._kv.get_secret(secret_name, version=salt_version)
        else:
            secret = self._kv.get_secret(secret_name)

        salt_bytes: bytes | None = None
        try:
            salt_material = secret.value
            if isinstance(salt_material, str):
                salt_bytes = salt_material.encode("utf-8")
            else:
                salt_bytes = bytes(salt_material)
            pid = hmac.new(
                salt_bytes,
                email.lower().encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()
            version = secret.properties.version
            return pid, version
        finally:
            # Pitfall 5: dereference salt material immediately
            if salt_bytes is not None:
                del salt_bytes
            try:
                del salt_material  # may not exist if exception raised before assignment
            except NameError:
                pass
            del secret

    def __repr__(self) -> str:
        # Salt material must NEVER appear here.
        return f"<Pseudonymizer kv={type(self._kv).__name__}>"
