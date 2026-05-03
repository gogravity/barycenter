"""ConnectWise Manage companies recipe (INT-01).

Every derivation references the PRIMITIVE_REGISTRY exactly; ETLRecipe's
no-bypass validator runs at construction time. Field classes match
``compliance/field-class-registry.yaml`` so the VER-02 gate passes.
"""
from __future__ import annotations

from barycenter.etl import ETLRecipe


def companies_recipe() -> ETLRecipe:
    return ETLRecipe(
        target_table="raw_cw.companies",
        derivations={
            "cw_company_id":          ("as_is",         {"field": "id", "field_class": "INTERNAL"}),
            "company_name":           ("as_is",         {"field": "name", "only_classes": ("PUBLIC", "INTERNAL", "SENSITIVE"), "field_class": "SENSITIVE"}),
            "billing_address_line1":  ("as_is",         {"field": "addressLine1", "only_classes": ("RESTRICTED",), "field_class": "RESTRICTED"}),
            "billing_address_city":   ("as_is",         {"field": "city", "only_classes": ("PUBLIC", "INTERNAL", "SENSITIVE"), "field_class": "SENSITIVE"}),
            "billing_address_region": ("as_is",         {"field": "state", "only_classes": ("PUBLIC", "INTERNAL", "SENSITIVE"), "field_class": "SENSITIVE"}),
            "cui_handling_required":  ("any_keyword",    {"field": "types[]", "keywords": ["defense", "federal"]}),
            "ai_opt_out":             ("as_is",         {"field": "customFields.ai_opt_out", "default": False, "field_class": "INTERNAL"}),
            "source_etag":            ("as_is",         {"field": "_info.lastUpdated", "field_class": "INTERNAL"}),
            # Body-like fields explicitly dropped:
            "_dropped_notes":         ("drop",          {"field": "notes"}),
        },
    )
