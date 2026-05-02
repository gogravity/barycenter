"""AUDIT-02 audit-of-audit tests (plan 07 task 3).

Reading from the audit chain must itself emit an audit event with
``verb='audit.read'`` — the SDK exposes a ``recording_query`` context
manager that does this automatically (success or failure).
"""
import pytest
from barycenter.audit import AuditClient, GENESIS_HASH


def _prime_chain(mock_sql, head: str = GENESIS_HASH):
    cur = mock_sql.cursor.return_value
    cur.fetchone.return_value = (head,)
    cur.rowcount = 1
    return cur


def test_recording_query_emits_audit_read_event(mock_sql, mock_la_sink, mock_worm_sink):
    _prime_chain(mock_sql)
    client = AuditClient(mock_sql, mock_la_sink, mock_worm_sink)
    with client.recording_query("mi-bary-audit", "list chain entries"):
        pass  # no actual query in unit test

    uploads = mock_la_sink.upload.call_args_list
    verbs = [call.args[0].verb for call in uploads if call.args]
    assert "audit.read" in verbs, f"Expected audit.read emission; got {verbs}"


def test_recording_query_emits_audit_read_on_failure(
    mock_sql, mock_la_sink, mock_worm_sink
):
    _prime_chain(mock_sql)
    client = AuditClient(mock_sql, mock_la_sink, mock_worm_sink)
    with pytest.raises(RuntimeError, match="boom"):
        with client.recording_query("mi-bary-audit", "list chain entries"):
            raise RuntimeError("boom")

    # The audit-read event was still emitted, with outcome=failure.
    uploads = mock_la_sink.upload.call_args_list
    audit_reads = [c.args[0] for c in uploads if c.args and c.args[0].verb == "audit.read"]
    assert audit_reads, "audit.read event was not emitted on failure path"
    assert audit_reads[0].outcome == "failure"
    assert audit_reads[0].metadata.get("error", "").startswith("RuntimeError")
