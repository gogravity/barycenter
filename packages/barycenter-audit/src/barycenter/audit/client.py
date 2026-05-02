"""AuditClient — single fail-closed entry point (D-04, D-06).

``emit()`` opens a SQL transaction (the caller is expected to set
``Transaction Isolation Level SERIALIZABLE`` on the connection;
``read_head_locked`` takes a row lock that serializes concurrent emits
regardless), reads + locks the chain head, computes the new digest, writes
to LA + WORM, updates chain_state, then commits — atomically. Any failure
rolls back and raises ``FailClosedAbort`` with the original exception
chained as ``__cause__``.

Per CLAUDE.md (D-04, D-06): no try/except/pass, no fire-and-forget. The
three sink failure modes (LA, WORM, chain_state lock) all converge on
AuditEmitError so callers can treat the audit path as one boundary.
"""
from __future__ import annotations

import logging
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Iterator, Optional
from uuid import uuid4

from barycenter.audit.chain import (
    canonicalize_json,
    compute_digest,
    read_head_locked,
    update_head,
)
from barycenter.audit.exceptions import AuditEmitError, FailClosedAbort
from barycenter.audit.models import AuditEvent
from barycenter.audit.sinks import LogsAnalyticsSink, WormBlobSink

log = logging.getLogger(__name__)


class AuditClient:
    """Fail-closed audit emitter.

    emit() opens a SQL serializable transaction, locks audit.chain_state,
    computes new digest, writes to LA + WORM, updates chain_state.
    Any failure aborts the parent transaction with AuditEmitError.
    """

    def __init__(
        self,
        sql_conn,
        la_sink: LogsAnalyticsSink,
        worm_sink: WormBlobSink,
    ):
        self._sql = sql_conn
        self._la = la_sink
        self._worm = worm_sink

    def emit(self, event: AuditEvent) -> AuditEvent:
        """Synchronous, fail-closed. Returns event with prior_digest/this_digest filled.

        Order of operations (Property 4):
          1. cursor()
          2. read_head_locked  — UPDLOCK ROWLOCK on audit.chain_state
          3. canonicalize the payload WITHOUT this_digest, compute new digest
          4. canonicalize the FULL payload (with this_digest) for WORM
          5. LA upload    — may raise → rollback
          6. WORM append  — may raise → rollback
          7. chain_state UPDATE  — may raise → rollback
          8. commit
        Caller-supplied prior_digest is OVERWRITTEN (T-1-07-06 spoof
        mitigation).

        Raises AuditEmitError on any sink/SQL failure.
        """
        try:
            cur = self._sql.cursor()
            prior = read_head_locked(cur)
            event.prior_digest = prior

            payload_no_self = event.model_dump(mode="json", exclude={"this_digest"})
            canonical_no_self = canonicalize_json(payload_no_self)
            event.this_digest = compute_digest(prior, canonical_no_self)

            payload_full = event.model_dump(mode="json")
            canonical_full = canonicalize_json(payload_full)

            # LA upload — must succeed before WORM append
            self._la.upload(event)
            # WORM append (ndjson — one event per line)
            self._worm.append((canonical_full + "\n").encode("utf-8"))
            # chain_state UPDATE inside the same transaction as the SELECT
            update_head(cur, event.this_digest)
            # All three sinks succeeded — commit
            self._sql.commit()
            return event
        except Exception as exc:
            # T-1-07-01: never swallow; ALWAYS attempt rollback before raising.
            try:
                self._sql.rollback()
            except Exception as rollback_exc:  # noqa: BLE001 — diagnostic only
                # Pitfall 9: never log raw payloads at INFO; %r at DEBUG.
                log.error(
                    "rollback failed during fail-closed abort: %r",
                    rollback_exc,
                )
            if isinstance(exc, AuditEmitError):
                raise
            raise FailClosedAbort(f"audit emit failed: {exc!r}") from exc

    @contextmanager
    def recording_query(
        self,
        actor_id: str,
        query_description: str,
        tenant_id: Optional[str] = None,
    ) -> Iterator[None]:
        """AUDIT-02: emit an audit-read event around a query against the audit chain.

        Yields control to the caller; emits a ``verb='audit.read'`` event on
        exit (success OR failure). If the caller's block raises, that
        exception propagates after the audit-read event is emitted; the
        audit-read outcome is set to ``failure`` in that case.
        """
        outcome: str = "success"
        error_repr: Optional[str] = None
        try:
            yield
        except Exception as e:
            outcome = "failure"
            error_repr = repr(e)
            raise
        finally:
            try:
                self.emit(
                    AuditEvent(
                        event_id=uuid4(),
                        occurred_at=datetime.now(timezone.utc),
                        actor_id=actor_id,
                        actor_type="service",
                        verb="audit.read",
                        resource_type="audit.chain_state",
                        outcome=outcome,
                        tenant_id=tenant_id,
                        metadata={
                            "query": query_description,
                            "error": error_repr,
                        },
                    )
                )
            except Exception as audit_err:
                # If the user block itself raised, prefer the original; only
                # surface the audit-of-audit failure when the user block was
                # otherwise successful.
                log.error("audit-of-audit emit failed: %r", audit_err)
                if outcome == "success":
                    raise
