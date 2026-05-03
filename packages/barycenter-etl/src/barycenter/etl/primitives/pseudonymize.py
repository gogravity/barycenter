"""pseudonymize primitive (TOOL-02): HMAC-SHA256(salt, email_lower) -> person_pid.

Delegates to barycenter.etl.framework.pseudonymizer.Pseudonymizer for the
salt fetch + HMAC. Salt is fetched fresh from Key Vault per call and is
never cached at module or class scope (Pitfall 5 mitigation).

field_class='SENSITIVE' because pid plus tenant_id is reversible by anyone
holding the salt material, even though the raw email never appears.
"""
from __future__ import annotations

from barycenter.etl.primitives._result import PrimitiveResult


def pseudonymize(
    field: str,
    email: str,
    tenant_id: str,
    kv_client,
    salt_version: str | None = None,
) -> PrimitiveResult:
    """Derive person_pid for ``email`` under ``tenant_id``.

    Returns a PrimitiveResult whose params contain both the pid and the
    salt version used so the audit log can reproduce the derivation.
    """
    # Local import avoids primitives <-> framework cycle at module load time.
    from barycenter.etl.framework.pseudonymizer import Pseudonymizer

    p = Pseudonymizer(kv_client)
    pid, ver = p.derive(email, tenant_id, salt_version)
    return PrimitiveResult(
        expr="?",
        params={field: pid},
        field_class="SENSITIVE",
        # salt version surfaced out-of-band; binding it as a SQL param
        # would create a placeholder mismatch (one ? but two param entries).
        metadata={"salt_version": ver},
    )
