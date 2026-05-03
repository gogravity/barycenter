"""Unit tests for the RetentionSweeper (RET-01)."""
import pytest

pytest.importorskip("barycenter.etl.framework.retention", reason="Plan 04 implements")


def test_retention_sweeper_deletes_old_rows(mock_sql, mock_audit):
    from barycenter.etl.framework.retention import RetentionSweeper
    sweeper = RetentionSweeper(
        "compliance/retention-policy.yaml", mock_sql, mock_audit
    )
    sweeper.sweep_table("raw_cw.tickets", field_class="RESTRICTED")
    # Should have issued a parameterized DELETE WHERE synced_at < cutoff
    delete_calls = [c for c in mock_sql.cursor().execute.call_args_list
                    if "DELETE" in str(c).upper()]
    assert delete_calls
    mock_audit.emit.assert_called()
