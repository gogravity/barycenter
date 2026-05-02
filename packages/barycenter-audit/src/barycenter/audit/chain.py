"""SHA-256 chain primitives (D-05). Implementation lands in plan 07."""
GENESIS_HASH: str = "0" * 64


def canonicalize_json(obj: dict) -> str:
    """Stable canonical JSON serialization (sorted keys, no whitespace, UTF-8). Plan 07 implements."""
    raise NotImplementedError("Implemented in plan 07")


def compute_digest(prior_hex: str, canonical: str) -> str:
    """Return hex(SHA-256(prior_hex.encode() + canonical.encode())). Plan 07 implements."""
    raise NotImplementedError("Implemented in plan 07")


def read_head_locked(cursor) -> str:
    """SELECT head_digest FROM audit.chain_state WITH (UPDLOCK, ROWLOCK). Plan 07 implements."""
    raise NotImplementedError("Implemented in plan 07")


def update_head(cursor, new_digest: str) -> None:
    """UPDATE audit.chain_state SET head_digest = ?. Plan 07 implements."""
    raise NotImplementedError("Implemented in plan 07")
