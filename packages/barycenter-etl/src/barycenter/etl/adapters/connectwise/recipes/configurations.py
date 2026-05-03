"""ConnectWise Manage configurations recipe (INT-01).

``serial_number`` is hashed at recipe time (SHA-256 via the ``hash`` primitive),
so the column stored is INTERNAL-class (one-way derivation), NOT the raw vendor
serial. The field-class registry tags ``serial_number: INTERNAL`` accordingly.
"""
from __future__ import annotations

from barycenter.etl import ETLRecipe


def configurations_recipe() -> ETLRecipe:
    return ETLRecipe(
        target_table="raw_cw.configurations",
        derivations={
            "configuration_id":        ("as_is", {"field": "id", "field_class": "INTERNAL"}),
            "cw_company_id":           ("as_is", {"field": "company.id", "field_class": "INTERNAL"}),
            "configuration_name":      ("as_is", {"field": "name", "field_class": "PUBLIC"}),
            "configuration_type_name": ("as_is", {"field": "type.name", "field_class": "PUBLIC"}),
            "manufacturer_name":       ("as_is", {"field": "manufacturer.name", "field_class": "PUBLIC"}),
            "model_number":            ("as_is", {"field": "modelNumber", "field_class": "PUBLIC"}),
            "serial_number":           ("hash",  {"field": "serialNumber"}),
            "status_name":             ("as_is", {"field": "status.name", "field_class": "PUBLIC"}),
            "installation_date":       ("as_is", {"field": "installationDate", "field_class": "INTERNAL"}),
            "source_etag":             ("as_is", {"field": "_info.lastUpdated", "field_class": "INTERNAL"}),
        },
    )
