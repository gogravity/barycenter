"""SHA-256 chain primitives (D-05).

Production emit() (client.py) lands in plan 07. The primitives below — canonicalize_json,
compute_digest, and validate_chain — are required by the AUDIT-01 CI gate
(scripts/ci/chain_validate.py) so they are implemented here in plan 08.

read_head_locked / update_head remain stubs because they require a live SQL transaction
and only emit() needs them.
"""
from __future__ import annotations

import hashlib
import json
from typing import Iterable, List

from barycenter.audit.exceptions import ChainIntegrityError

GENESIS_HASH: str = "0" * 64


def canonicalize_json(obj: dict) -> str:
    """Stable canonical JSON serialization.

    - Keys sorted lexicographically (recursive)
    - No whitespace between separators
    - UTF-8 by default; ensure_ascii=False so non-ASCII text round-trips byte-stable
    - NaN/Infinity rejected (allow_nan=False) — chain integrity must not depend on
      lossy float serialization

    The output is the canonical bytes-equivalent form used as input to compute_digest.
    """
    return json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def compute_digest(prior_hex: str, canonical: str) -> str:
    """Return hex(SHA-256(prior_hex.encode() + canonical.encode())).

    prior_hex is expected to be a 64-character lowercase hex string (the prior chain head
    or GENESIS_HASH). canonical is the canonical_json of the event minus the this_digest
    field (so the digest covers everything except the digest itself).
    """
    h = hashlib.sha256()
    h.update(prior_hex.encode("utf-8"))
    h.update(canonical.encode("utf-8"))
    return h.hexdigest()


def read_head_locked(cursor) -> str:
    """SELECT head_digest FROM audit.chain_state WITH (UPDLOCK, ROWLOCK). Plan 07 implements."""
    raise NotImplementedError("Implemented in plan 07")


def update_head(cursor, new_digest: str) -> None:
    """UPDATE audit.chain_state SET head_digest = ?. Plan 07 implements."""
    raise NotImplementedError("Implemented in plan 07")


def validate_chain(entries: Iterable[str]) -> int:
    """Validate an ordered iterable of canonical JSON audit entries against the chain.

    Each entry must be a JSON object with at least: prior_digest, this_digest, and the
    other fields that participate in the digest. The first entry's prior_digest MUST be
    GENESIS_HASH; each subsequent entry's prior_digest MUST equal the previous entry's
    this_digest; and each entry's this_digest MUST equal compute_digest(prior_digest,
    canonicalize_json(entry without this_digest)).

    Returns the number of entries successfully validated.
    Raises ChainIntegrityError on any mismatch.
    """
    expected_prior = GENESIS_HASH
    count = 0
    for raw in entries:
        if not raw or not raw.strip():
            continue
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError as e:
            raise ChainIntegrityError(f"entry {count}: invalid JSON: {e}") from e
        if not isinstance(obj, dict):
            raise ChainIntegrityError(f"entry {count}: not a JSON object")
        prior = obj.get("prior_digest")
        this = obj.get("this_digest")
        if prior is None or this is None:
            raise ChainIntegrityError(
                f"entry {count}: missing prior_digest or this_digest"
            )
        if prior != expected_prior:
            raise ChainIntegrityError(
                f"entry {count}: prior_digest mismatch: expected {expected_prior}, got {prior}"
            )
        # Recompute digest over the entry minus this_digest
        canonical_no_self = canonicalize_json(
            {k: v for k, v in obj.items() if k != "this_digest"}
        )
        recomputed = compute_digest(prior, canonical_no_self)
        if recomputed != this:
            raise ChainIntegrityError(
                f"entry {count}: this_digest mismatch: stored {this}, recomputed {recomputed}"
            )
        expected_prior = this
        count += 1
    return count
