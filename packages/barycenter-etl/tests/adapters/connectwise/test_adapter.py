"""Unit tests for the CW Manage adapter (INT-01, Plan 05)."""
import pytest

pytest.importorskip("barycenter.etl.adapters.connectwise.adapter",
                    reason="Plan 05 implements")


def test_adapter_declares_five_tables_and_cw_category():
    from barycenter.etl.adapters.connectwise.adapter import CWManageAdapter
    assert CWManageAdapter.CATEGORY == "cw"
    assert set(CWManageAdapter.TABLES) == {
        "companies", "agreements", "tickets", "configurations", "time_entries"}
