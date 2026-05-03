"""Unit tests for the RetentionSweeper (RET-01)."""
import datetime as dt
import pytest


def test_retention_sweeper_deletes_old_rows(mock_sql, mock_audit):
    from barycenter.etl.framework.retention import RetentionSweeper
    cur = mock_sql.cursor.return_value
    cur.rowcount = 7
    sweeper = RetentionSweeper(
        "compliance/retention-policy.yaml", mock_sql, mock_audit
    )
    deleted = sweeper.sweep_table("raw_cw.tickets", field_class="RESTRICTED")
    assert deleted == 7
    # parameterised DELETE issued
    delete_calls = [c for c in cur.execute.call_args_list
                    if "DELETE FROM raw_cw.tickets" in str(c)
                    and "synced_at < ?" in str(c)]
    assert delete_calls, f"expected parameterised DELETE; got {cur.execute.call_args_list}"
    # audit event emitted
    mock_audit.emit.assert_called()
    args, _ = mock_audit.emit.call_args
    event = args[0]
    assert event.verb == "retention.sweep"


def test_retention_sweeper_uses_per_class_ttl(mock_sql, mock_audit, tmp_path):
    """RESTRICTED defaults to 13 months per the policy YAML."""
    from barycenter.etl.framework.retention import RetentionSweeper
    sweeper = RetentionSweeper(
        "compliance/retention-policy.yaml", mock_sql, mock_audit
    )
    sweeper.sweep_table("raw_cw.tickets", field_class="RESTRICTED")
    args, _ = mock_audit.emit.call_args
    event = args[0]
    assert event.metadata["ttl_months"] == 13
    assert event.metadata["field_class"] == "RESTRICTED"


def test_retention_sweeper_tenant_override(tmp_path, mock_sql, mock_audit):
    """Per-tenant override extends TTL."""
    from barycenter.etl.framework.retention import RetentionSweeper
    policy = tmp_path / "retention.yaml"
    policy.write_text(
        "version: 1\n"
        "default:\n"
        "  RESTRICTED: { ttl_months: 13 }\n"
        "overrides:\n"
        "  - tenant_id: \"hipaa-1\"\n"
        "    classes: { RESTRICTED: { ttl_months: 84 } }\n"
    )
    sweeper = RetentionSweeper(str(policy), mock_sql, mock_audit)
    sweeper.sweep_table("raw_cw.tickets", field_class="RESTRICTED",
                        tenant_id="hipaa-1")
    args, _ = mock_audit.emit.call_args
    assert args[0].metadata["ttl_months"] == 84
