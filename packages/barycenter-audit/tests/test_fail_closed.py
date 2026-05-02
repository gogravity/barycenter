"""Fail-closed tests for the three sink failure modes (Pitfall 10).

Plan 07 turns these from xfail to passing — every sink failure (LA, WORM,
chain_state lock) MUST raise AuditEmitError and roll back the SQL
transaction (chain_state.head_digest unchanged).
"""
from datetime import datetime, timezone
from uuid import uuid4
import pytest
from barycenter.audit import AuditClient, AuditEvent, AuditEmitError, GENESIS_HASH


def _make_event() -> AuditEvent:
    return AuditEvent(
        event_id=uuid4(), occurred_at=datetime.now(timezone.utc),
        actor_id="mi-bary-etl", actor_type="service",
        verb="test.event", resource_type="test", outcome="success",
    )


def _prime_chain_head(mock_sql, head: str = GENESIS_HASH):
    cur = mock_sql.cursor.return_value
    cur.fetchone.return_value = (head,)
    cur.rowcount = 1
    return cur


def test_fail_closed_on_la_outage(mock_sql, mock_la_sink, mock_worm_sink):
    _prime_chain_head(mock_sql)
    mock_la_sink.upload.side_effect = RuntimeError("LA unreachable")
    client = AuditClient(mock_sql, mock_la_sink, mock_worm_sink)
    with pytest.raises(AuditEmitError):
        client.emit(_make_event())
    # No commit — chain_state.head_digest unchanged
    mock_sql.commit.assert_not_called()
    # Rollback was attempted
    mock_sql.rollback.assert_called()


def test_fail_closed_on_worm_outage(mock_sql, mock_la_sink, mock_worm_sink):
    _prime_chain_head(mock_sql)
    mock_worm_sink.append.side_effect = RuntimeError("WORM unreachable")
    client = AuditClient(mock_sql, mock_la_sink, mock_worm_sink)
    with pytest.raises(AuditEmitError):
        client.emit(_make_event())
    mock_sql.commit.assert_not_called()
    mock_sql.rollback.assert_called()


def test_fail_closed_on_chain_state_lock(mock_sql, mock_la_sink, mock_worm_sink):
    # Cursor.execute raises immediately (the SELECT WITH UPDLOCK never returns)
    mock_sql.cursor.return_value.execute.side_effect = RuntimeError("chain_state locked")
    client = AuditClient(mock_sql, mock_la_sink, mock_worm_sink)
    with pytest.raises(AuditEmitError):
        client.emit(_make_event())
    mock_sql.commit.assert_not_called()


def test_chain_state_unchanged_on_la_failure(mock_sql, mock_la_sink, mock_worm_sink):
    """Explicit assertion that the UPDATE never executed when LA fails."""
    cur = _prime_chain_head(mock_sql)
    mock_la_sink.upload.side_effect = RuntimeError("LA unreachable")
    client = AuditClient(mock_sql, mock_la_sink, mock_worm_sink)
    with pytest.raises(AuditEmitError):
        client.emit(_make_event())
    mock_sql.commit.assert_not_called()
    update_calls = [c for c in cur.execute.call_args_list if "UPDATE" in str(c).upper()]
    assert update_calls == [], (
        f"chain_state UPDATE must not run when LA fails; saw {update_calls}"
    )


def test_original_exception_chained(mock_sql, mock_la_sink, mock_worm_sink):
    """The original sink exception must be available via __cause__."""
    _prime_chain_head(mock_sql)
    inner = RuntimeError("LA boom")
    mock_la_sink.upload.side_effect = inner
    client = AuditClient(mock_sql, mock_la_sink, mock_worm_sink)
    with pytest.raises(AuditEmitError) as exc_info:
        client.emit(_make_event())
    assert exc_info.value.__cause__ is inner
