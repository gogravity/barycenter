"""ConnectWise Manage agreements recipe (INT-01)."""
from __future__ import annotations

from barycenter.etl import ETLRecipe


def agreements_recipe() -> ETLRecipe:
    return ETLRecipe(
        target_table="raw_cw.agreements",
        derivations={
            "agreement_id":        ("as_is", {"field": "id", "field_class": "INTERNAL"}),
            "cw_company_id":       ("as_is", {"field": "company.id", "field_class": "INTERNAL"}),
            "agreement_name":      ("as_is", {"field": "name", "field_class": "PUBLIC"}),
            "agreement_type_name": ("as_is", {"field": "type.name", "field_class": "PUBLIC"}),
            "start_date":          ("as_is", {"field": "startDate", "field_class": "PUBLIC"}),
            "end_date":            ("as_is", {"field": "endDate", "field_class": "PUBLIC"}),
            "billing_cycle":       ("as_is", {"field": "billingCycle.name", "field_class": "PUBLIC"}),
            "monthly_value_cents": ("as_is", {"field": "billAmount", "default": 0, "field_class": "PUBLIC"}),
            "source_etag":         ("as_is", {"field": "_info.lastUpdated", "field_class": "INTERNAL"}),
        },
    )
