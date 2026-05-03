"""CWManageAdapter: configures AdapterBase with the five CW tables + recipes (INT-01).

Time-entry aggregation (per Pitfall 4 + research A2): CW returns per-entry rows;
the adapter pre-aggregates client-side to (cw_company_id, entry_date) tuples
and yields the bucketed dicts so the recipe projects already-aggregated values.
"""
from __future__ import annotations

import collections
from datetime import date, datetime
from typing import Iterator

from barycenter.etl import AdapterBase
from barycenter.etl.adapters.connectwise.client import CWManageClient
from barycenter.etl.adapters.connectwise.recipes import (
    agreements_recipe,
    companies_recipe,
    configurations_recipe,
    tickets_recipe,
    time_entries_recipe,
)


class CWManageAdapter(AdapterBase):
    CATEGORY = "cw"
    TABLES = ["companies", "agreements", "tickets", "configurations", "time_entries"]
    CUI_SENSITIVE_TABLES = ["tickets", "configurations", "time_entries"]
    CUI_CANARY_FIELDS = {
        "companies":      ["name"],
        "agreements":     ["agreement_name"],
        "tickets":        ["summary"],
        "configurations": ["configuration_name", "model_number"],
        "time_entries":   [],
    }

    _PATHS = {
        "companies":      "/company/companies",
        "agreements":     "/finance/agreements",
        "tickets":        "/service/tickets",
        "configurations": "/company/configurations",
        "time_entries":   "/time/entries",
    }

    _RECIPES = {
        "companies":      companies_recipe,
        "agreements":     agreements_recipe,
        "tickets":        tickets_recipe,
        "configurations": configurations_recipe,
        "time_entries":   time_entries_recipe,
    }

    def __init__(
        self,
        audit,
        sql_conn,
        kv_client,
        *,
        cw_client: CWManageClient,
        canary_scanner=None,
    ) -> None:
        super().__init__(audit, sql_conn, kv_client, canary_scanner=canary_scanner)
        self._cw = cw_client

    def fetch_table(self, table: str) -> Iterator[dict]:
        path = self._PATHS[table]
        if table == "time_entries":
            yield from self._fetch_time_entries_aggregated(path)
        else:
            yield from self._cw.paginate(path)
            self._cw.assert_clean_termination(path)

    def _fetch_time_entries_aggregated(self, path: str) -> Iterator[dict]:
        """CW returns per-entry rows; aggregate client-side to (company, date)."""
        buckets: dict[tuple[int, date], dict] = collections.defaultdict(
            lambda: {"total_hours": 0.0, "billable_hours": 0.0, "entry_count": 0}
        )
        latest_etag: dict[tuple[int, date], str] = {}
        for raw in self._cw.paginate(path):
            cid = (raw.get("company") or {}).get("id")
            ts = raw.get("timeStart")
            if not cid or not ts:
                continue
            d = self._coerce_date(ts)
            if d is None:
                continue
            key = (cid, d)
            hours = float(raw.get("actualHours") or 0)
            buckets[key]["total_hours"] += hours
            if (raw.get("billableOption") or "").lower() in (
                "billable",
                "yes",
                "true",
            ):
                buckets[key]["billable_hours"] += hours
            buckets[key]["entry_count"] += 1
            etag = (raw.get("_info") or {}).get("lastUpdated")
            if etag:
                latest_etag[key] = etag
        self._cw.assert_clean_termination(path)
        for (cid, d), agg in buckets.items():
            yield {
                "cw_company_id": cid,
                "entry_date": d.isoformat(),
                "total_hours": agg["total_hours"],
                "billable_hours": agg["billable_hours"],
                "entry_count": agg["entry_count"],
                "source_etag": latest_etag.get((cid, d)),
            }

    @staticmethod
    def _coerce_date(ts) -> date | None:
        if isinstance(ts, str):
            try:
                return datetime.fromisoformat(ts.replace("Z", "+00:00")).date()
            except ValueError:
                return None
        if hasattr(ts, "date"):
            return ts.date()
        return None

    def recipe_for(self, table: str):
        return self._RECIPES[table]()
