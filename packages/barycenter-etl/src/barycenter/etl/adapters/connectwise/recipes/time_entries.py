"""Time entries recipe -- aggregated per (company, date) per INT-01.

CW returns one row per time entry. ``CWManageAdapter.fetch_table('time_entries')``
pre-aggregates client-side and emits one record per (cw_company_id, entry_date).
The recipe here projects the already-aggregated dict.
"""
from __future__ import annotations

from barycenter.etl import ETLRecipe


def time_entries_recipe() -> ETLRecipe:
    return ETLRecipe(
        target_table="raw_cw.time_entries",
        derivations={
            "cw_company_id":  ("as_is", {"field": "cw_company_id", "field_class": "INTERNAL"}),
            "entry_date":     ("as_is", {"field": "entry_date", "field_class": "INTERNAL"}),
            "total_hours":    ("as_is", {"field": "total_hours", "field_class": "PUBLIC"}),
            "billable_hours": ("as_is", {"field": "billable_hours", "field_class": "PUBLIC"}),
            "entry_count":    ("as_is", {"field": "entry_count", "field_class": "PUBLIC"}),
            "source_etag":    ("as_is", {"field": "source_etag", "field_class": "INTERNAL"}),
        },
    )
