"""Audit SDK exception hierarchy (per D-06 fail-closed discipline)."""


class AuditEmitError(Exception):
    """Raised when audit emission fails. Parent transaction MUST roll back."""


class FailClosedAbort(AuditEmitError):
    """Specific subclass for sink failures (LA, WORM, chain_state lock)."""


class ChainIntegrityError(Exception):
    """Raised when audit chain validation detects tampering or break."""
