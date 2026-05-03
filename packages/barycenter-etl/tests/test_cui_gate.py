"""Unit tests for the CUI gate (COMP-03)."""
import pytest

pytest.importorskip("barycenter.etl.framework.cui_gate", reason="Plan 04 implements")


def test_cui_gate_skips_sensitive_table_when_cui_tenant_present(mock_sql):
    from barycenter.etl.framework.cui_gate import CUIGate
    mock_sql.scalar = lambda q: 1  # at least one CUI tenant exists
    assert CUIGate.should_skip(
        "tickets", ["tickets", "configurations", "time_entries"], mock_sql
    )


def test_cui_gate_does_not_skip_when_no_cui_tenants(mock_sql):
    from barycenter.etl.framework.cui_gate import CUIGate
    mock_sql.scalar = lambda q: None
    assert not CUIGate.should_skip("tickets", ["tickets"], mock_sql)
