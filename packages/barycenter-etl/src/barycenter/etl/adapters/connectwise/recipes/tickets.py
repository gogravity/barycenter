"""ConnectWise Manage tickets recipe (INT-01) -- METADATA ONLY (Pitfall 1).

Body fields (``initialDescription``, ``resolution``, ``initialInternalAnalysis``)
appear ONLY inside ``("drop", ...)`` derivations. The DDL has no body columns;
this file is the recipe-level explicit acknowledgement that those fields are
deliberately discarded. The ``test_tickets_recipe_drops_all_body_fields`` CI
gate walks this dictionary and fails if any non-drop derivation references a
body-like field name.
"""
from __future__ import annotations

from barycenter.etl import ETLRecipe


def tickets_recipe() -> ETLRecipe:
    return ETLRecipe(
        target_table="raw_cw.tickets",
        derivations={
            "ticket_id":     ("as_is", {"field": "id", "field_class": "INTERNAL"}),
            "cw_company_id": ("as_is", {"field": "company.id", "field_class": "INTERNAL"}),
            "summary":       ("as_is", {"field": "summary", "only_classes": ("PUBLIC", "INTERNAL", "SENSITIVE"), "field_class": "SENSITIVE"}),
            "status_name":   ("as_is", {"field": "status.name", "field_class": "PUBLIC"}),
            "priority_name": ("as_is", {"field": "priority.name", "field_class": "PUBLIC"}),
            "type_name":     ("as_is", {"field": "type.name", "field_class": "PUBLIC"}),
            "date_entered":  ("as_is", {"field": "_info.dateEntered", "field_class": "INTERNAL"}),
            "last_updated":  ("as_is", {"field": "_info.lastUpdated", "field_class": "INTERNAL"}),
            "source_etag":   ("as_is", {"field": "_info.lastUpdated", "field_class": "INTERNAL"}),
            # CRITICAL: body fields explicitly dropped. DDL absence is the
            # architectural enforcement; these declarations are the recipe-level
            # explicit acknowledgement that mirror Pitfall 1.
            "_dropped_initial_description": ("drop", {"field": "initialDescription"}),
            "_dropped_resolution":          ("drop", {"field": "resolution"}),
            "_dropped_internal_analysis":   ("drop", {"field": "initialInternalAnalysis"}),
        },
    )
