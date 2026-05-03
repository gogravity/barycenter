"""CUIGate: framework-level CUI handling check (COMP-03, Pitfall 7).

The check runs in AdapterBase, never in adapter code — adapters cannot bypass.
Default-closed: missing CUI_SENSITIVE_TABLES on an adapter == empty list, so the
gate has no effect; AdapterBase enforces declaration via __init__ inspection.
"""
from __future__ import annotations


class CUIGate:
    @staticmethod
    def should_skip(table: str, sensitive_tables: list[str], sql_conn) -> bool:
        """Return True iff this table is CUI-sensitive AND a CUI tenant exists.

        When True, the entire table sync is skipped (coarse-grain reduction).
        Per-tenant filtering happens in fetch_table.
        """
        if table not in sensitive_tables:
            return False
        cur = sql_conn.cursor()
        cur.execute(
            "SELECT 1 FROM raw_cw.companies WHERE cui_handling_required = 1"
        )
        row = cur.fetchone()
        return row is not None

    @staticmethod
    def is_cui_company(cw_company_id: int, sql_conn) -> bool:
        """Per-company CUI flag check. Used inside fetch_table to filter records."""
        cur = sql_conn.cursor()
        cur.execute(
            "SELECT cui_handling_required FROM raw_cw.companies "
            "WHERE cw_company_id = ?",
            cw_company_id,
        )
        row = cur.fetchone()
        if row is None:
            return False
        # First column whether tuple-row or named-row
        try:
            val = row[0]
        except (TypeError, KeyError, IndexError):
            val = getattr(row, "cui_handling_required", None)
        return bool(val)
