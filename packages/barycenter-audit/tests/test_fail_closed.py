"""Fail-closed tests for the three sink failure modes (Pitfall 10). Impl lands in plan 07."""
from datetime import datetime, timezone
from uuid import uuid4
import pytest
from barycenter.audit import AuditClient, AuditEvent, AuditEmitError


def _make_event() -> AuditEvent:
    return AuditEvent(
        event_id=uuid4(), occurred_at=datetime.now(timezone.utc),
        actor_id="mi-bary-etl", actor_type="service",
        verb="test.event", resource_type="test", outcome="success",
    )


@pytest.mark.xfail(strict=False, reason="emit() impl lands in plan 07")
def test_fail_closed_on_la_outage(mock_sql, mock_la_sink, mock_worm_sink):
    mock_la_sink.upload.side_effect = RuntimeError("LA unreachable")
    client = AuditClient(mock_sql, mock_la_sink, mock_worm_sink)
    with pytest.raises(AuditEmitError):
        client.emit(_make_event())


@pytest.mark.xfail(strict=False, reason="emit() impl lands in plan 07")
def test_fail_closed_on_worm_outage(mock_sql, mock_la_sink, mock_worm_sink):
    mock_worm_sink.append.side_effect = RuntimeError("WORM unreachable")
    client = AuditClient(mock_sql, mock_la_sink, mock_worm_sink)
    with pytest.raises(AuditEmitError):
        client.emit(_make_event())


@pytest.mark.xfail(strict=False, reason="emit() impl lands in plan 07")
def test_fail_closed_on_chain_state_lock(mock_sql, mock_la_sink, mock_worm_sink):
    mock_sql.cursor.return_value.execute.side_effect = RuntimeError("chain_state locked")
    client = AuditClient(mock_sql, mock_la_sink, mock_worm_sink)
    with pytest.raises(AuditEmitError):
        client.emit(_make_event())
