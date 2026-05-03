"""ConnectWise Manage ETL recipes (INT-01).

``iter_all_recipes()`` is consumed by the no-bypass CI gate (test_recipe_no_bypass)
and by Plan 04's ShapeBuilder when populating ai_zone shapes from raw_cw.*.
"""
from barycenter.etl.adapters.connectwise.recipes.companies import companies_recipe
from barycenter.etl.adapters.connectwise.recipes.agreements import agreements_recipe
from barycenter.etl.adapters.connectwise.recipes.tickets import tickets_recipe
from barycenter.etl.adapters.connectwise.recipes.configurations import configurations_recipe
from barycenter.etl.adapters.connectwise.recipes.time_entries import time_entries_recipe


def iter_all_recipes() -> list:
    return [
        companies_recipe(),
        agreements_recipe(),
        tickets_recipe(),
        configurations_recipe(),
        time_entries_recipe(),
    ]


__all__ = [
    "companies_recipe",
    "agreements_recipe",
    "tickets_recipe",
    "configurations_recipe",
    "time_entries_recipe",
    "iter_all_recipes",
]
