"""Unit tests for the CUI gate (COMP-03)."""
import pytest


def test_cui_gate_skips_sensitive_table_when_cui_tenant_present(mock_sql):
    from barycenter.etl.framework.cui_gate import CUIGate
    mock_sql.cursor.return_value.fetchone.return_value = (1,)
    assert CUIGate.should_skip(
        "tickets", ["tickets", "configurations", "time_entries"], mock_sql
    )


def test_cui_gate_does_not_skip_when_no_cui_tenants(mock_sql):
    from barycenter.etl.framework.cui_gate import CUIGate
    mock_sql.cursor.return_value.fetchone.return_value = None
    assert not CUIGate.should_skip("tickets", ["tickets"], mock_sql)


def test_cui_gate_does_not_skip_non_sensitive_table(mock_sql):
    from barycenter.etl.framework.cui_gate import CUIGate
    mock_sql.cursor.return_value.fetchone.return_value = (1,)
    # 'companies' is not in sensitive list -> should not skip even with CUI tenants
    assert not CUIGate.should_skip("companies", ["tickets"], mock_sql)


def test_is_cui_company_true(mock_sql):
    from barycenter.etl.framework.cui_gate import CUIGate
    mock_sql.cursor.return_value.fetchone.return_value = (1,)
    assert CUIGate.is_cui_company(99999, mock_sql) is True


def test_is_cui_company_false_when_zero(mock_sql):
    from barycenter.etl.framework.cui_gate import CUIGate
    mock_sql.cursor.return_value.fetchone.return_value = (0,)
    assert CUIGate.is_cui_company(12345, mock_sql) is False


def test_is_cui_company_false_when_missing(mock_sql):
    from barycenter.etl.framework.cui_gate import CUIGate
    mock_sql.cursor.return_value.fetchone.return_value = None
    assert CUIGate.is_cui_company(99999, mock_sql) is False
