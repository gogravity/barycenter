"""AuditClient — single fail-closed entry point (D-04, D-06). Plan 07 implements emit()."""
from barycenter.audit.models import AuditEvent
from barycenter.audit.sinks import LogsAnalyticsSink, WormBlobSink


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

        Raises AuditEmitError on any sink failure.
        """
        raise NotImplementedError("Implemented in plan 07")
