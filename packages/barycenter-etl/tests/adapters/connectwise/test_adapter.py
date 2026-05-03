"""Unit tests for the CW Manage adapter (INT-01, Plan 05)."""
from __future__ import annotations

from unittest.mock import MagicMock

from barycenter.etl.adapters.connectwise.adapter import CWManageAdapter


def test_adapter_declares_five_tables_and_cw_category() -> None:
    assert CWManageAdapter.CATEGORY == "cw"
    assert CWManageAdapter.TABLES == [
        "companies",
        "agreements",
        "tickets",
        "configurations",
        "time_entries",
    ]


def test_cui_sensitive_tables_include_tickets_configs_and_time() -> None:
    sensitive = set(CWManageAdapter.CUI_SENSITIVE_TABLES)
    assert {"tickets", "configurations", "time_entries"} <= sensitive


def test_cui_canary_fields_populated() -> None:
    fields = CWManageAdapter.CUI_CANARY_FIELDS
    assert "summary" in fields["tickets"]
    assert "configuration_name" in fields["configurations"]


def test_recipe_for_returns_distinct_recipes() -> None:
    audit = MagicMock()
    sql = MagicMock()
    kv = MagicMock()
    cw = MagicMock()
    adapter = CWManageAdapter(audit, sql, kv, cw_client=cw)
    targets = {
        adapter.recipe_for(t).target_table
        for t in CWManageAdapter.TABLES
    }
    assert targets == {
        "raw_cw.companies",
        "raw_cw.agreements",
        "raw_cw.tickets",
        "raw_cw.configurations",
        "raw_cw.time_entries",
    }


def test_fetch_table_aggregates_time_entries_per_company_per_day() -> None:
    audit = MagicMock()
    sql = MagicMock()
    kv = MagicMock()
    cw = MagicMock(unsafe=True)
    cw.paginate.return_value = iter(
        [
            {
                "company": {"id": 1},
                "timeStart": "2026-05-01T08:00:00Z",
                "actualHours": 1.5,
                "billableOption": "Billable",
                "_info": {"lastUpdated": "2026-05-01T09:00:00Z"},
            },
            {
                "company": {"id": 1},
                "timeStart": "2026-05-01T13:00:00Z",
                "actualHours": 2.0,
                "billableOption": "NoCharge",
                "_info": {"lastUpdated": "2026-05-01T14:00:00Z"},
            },
            {
                "company": {"id": 2},
                "timeStart": "2026-05-01T10:00:00Z",
                "actualHours": 4.0,
                "billableOption": "Billable",
                "_info": {"lastUpdated": "2026-05-01T11:00:00Z"},
            },
        ]
    )
    cw.assert_clean_termination.return_value = None
    adapter = CWManageAdapter(audit, sql, kv, cw_client=cw)
    rows = list(adapter.fetch_table("time_entries"))
    by_key = {(r["cw_company_id"], r["entry_date"]): r for r in rows}
    a = by_key[(1, "2026-05-01")]
    assert a["entry_count"] == 2
    assert a["total_hours"] == 3.5
    assert a["billable_hours"] == 1.5
    b = by_key[(2, "2026-05-01")]
    assert b["entry_count"] == 1
    assert b["billable_hours"] == 4.0
