"""SHA-256 chain primitives (D-05).

Pure functions ``canonicalize_json`` and ``compute_digest`` plus the
chain_state SQL helpers ``read_head_locked`` / ``update_head`` and the
offline ``validate_chain`` verifier.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable

from barycenter.audit._canonicalize import canonicalize
from barycenter.audit.exceptions import ChainIntegrityError

GENESIS_HASH: str = "0" * 64


def canonicalize_json(obj: Any) -> str:
    """Stable canonical JSON: sorted keys, no whitespace, UTF-8.

    Raises ValueError on unsupported types (sets, custom objects, etc.).
    Two consecutive calls on the same input return byte-identical output.
    """
    return canonicalize(obj)


def compute_digest(prior_hex: str, canonical: str) -> str:
    """Return ``hex(SHA-256(prior_hex.encode() || canonical.encode()))``.

    ``prior_hex`` must be a 64-character hex string (the chain head). The
    output is exactly 64 lowercase hex characters.
    """
    if not isinstance(prior_hex, str) or len(prior_hex) != 64:
        raise ValueError(f"prior_hex must be a 64-char hex string, got {prior_hex!r}")
    h = hashlib.sha256()
    h.update(prior_hex.encode("utf-8"))
    h.update(canonical.encode("utf-8"))
    return h.hexdigest()


def read_head_locked(cursor) -> str:
    """SELECT head_digest FROM audit.chain_state WITH (UPDLOCK, ROWLOCK) WHERE id=1.

    Returns the singleton chain head as a 64-char hex string. Holds the row
    lock until the surrounding transaction commits or rolls back, serializing
    concurrent emits (T-1-07-07 accept).
    """
    cursor.execute(
        "SELECT head_digest FROM audit.chain_state WITH (UPDLOCK, ROWLOCK) WHERE id = 1"
    )
    row = cursor.fetchone()
    if row is None:
        raise RuntimeError(
            "audit.chain_state row id=1 missing — genesis seed not applied"
        )
    return row[0]


def update_head(cursor, new_digest: str) -> None:
    """UPDATE audit.chain_state SET head_digest = ? WHERE id = 1.

    Asserts ``rowcount == 1`` — chain_state is a singleton; any other count
    means a schema invariant has been violated and we MUST fail closed.
    """
    cursor.execute(
        "UPDATE audit.chain_state SET head_digest = ?, updated_at = SYSUTCDATETIME(), "
        "updated_by = SYSTEM_USER WHERE id = 1",
        new_digest,
    )
    if cursor.rowcount != 1:
        raise RuntimeError(
            f"chain_state UPDATE rowcount={cursor.rowcount}; expected exactly 1"
        )


def validate_chain(canonical_entries: Iterable[str]) -> int:
    """Recompute the chain from GENESIS_HASH and verify each entry.

    ``canonical_entries`` is an ordered iterable of canonical-JSON strings, each
    representing a stored AuditEvent (including its ``this_digest`` field).
    Blank/whitespace-only lines are skipped. Returns the number of validated
    entries on success; raises ``ChainIntegrityError`` on the first mismatch or
    malformed entry.
    """
    prior = GENESIS_HASH
    count = 0
    for raw in canonical_entries:
        if not raw or not raw.strip():
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            raise ChainIntegrityError(f"entry {count}: invalid JSON: {e}") from e
        if not isinstance(data, dict):
            raise ChainIntegrityError(f"entry {count}: not a JSON object")
        claimed_prior = data.get("prior_digest")
        claimed_this = data.get("this_digest")
        if claimed_prior is None or claimed_this is None:
            raise ChainIntegrityError(
                f"entry {count}: missing prior_digest or this_digest"
            )
        if claimed_prior != prior:
            raise ChainIntegrityError(
                f"entry {count} prior_digest mismatch: "
                f"claimed {claimed_prior!r}, expected {prior!r}"
            )
        payload_no_self = {k: v for k, v in data.items() if k != "this_digest"}
        canonical_no_self = canonicalize_json(payload_no_self)
        recomputed = compute_digest(prior, canonical_no_self)
        if recomputed != claimed_this:
            raise ChainIntegrityError(
                f"entry {count} this_digest mismatch: "
                f"claimed {claimed_this!r}, recomputed {recomputed!r}"
            )
        prior = claimed_this
        count += 1
    return count
