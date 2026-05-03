"""ETL exception hierarchy (Phase 2). Mirrors barycenter.audit.exceptions style.

Per CLAUDE.md fail-closed mandate: AuditEmitError from the audit SDK MUST
propagate. The ETL-specific errors below signal table-isolated rollback (D-02) —
adapter.run() catches them per-table, emits a failure audit event, alerts, and
continues to the next table. AuditEmitError itself is NEVER caught here.
"""
from __future__ import annotations


class ETLError(Exception):
    """Base for all ETL framework errors. Caught by adapter.run() per-table (D-02)."""


class CUIBoundaryViolation(ETLError):
    """Raised when a CUI canary phrase is detected in a record. Table sync rolls back."""


class SchemaDriftError(ETLError):
    """Raised when the upstream API response shape diverges from the pinned model."""


class RateLimitExhausted(ETLError):
    """Raised when tenacity exhausts all retries against a 429-returning endpoint."""


class PaginationTruncated(ETLError):
    """Raised when paginate() exits with terminal_reason not in {short_page, empty_page}."""
