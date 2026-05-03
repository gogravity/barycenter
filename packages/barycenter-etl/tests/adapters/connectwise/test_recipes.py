"""Unit tests for CW Manage ETL recipes (Plan 05)."""
from __future__ import annotations

from barycenter.etl.adapters.connectwise.recipes import (
    iter_all_recipes,
)
from barycenter.etl.adapters.connectwise.recipes.tickets import tickets_recipe
from barycenter.etl.primitives import PRIMITIVE_REGISTRY


BODY_FIELD_FRAGMENTS = (
    "body",
    "resolution",
    "internalAnalysis",
    "initialDescription",
)


def test_iter_all_recipes_returns_five_recipes() -> None:
    recipes = iter_all_recipes()
    assert len(recipes) == 5
    targets = {r.target_table for r in recipes}
    assert targets == {
        "raw_cw.companies",
        "raw_cw.agreements",
        "raw_cw.tickets",
        "raw_cw.configurations",
        "raw_cw.time_entries",
    }


def test_every_recipe_only_uses_primitives() -> None:
    for r in iter_all_recipes():
        for col, deriv in r.derivations.items():
            primitive_name = deriv[0]
            assert primitive_name in PRIMITIVE_REGISTRY, (
                f"{r.target_table}.{col} bypasses primitive layer "
                f"(uses {primitive_name})"
            )


def test_tickets_recipe_drops_all_body_fields() -> None:
    r = tickets_recipe()
    for col, deriv in r.derivations.items():
        primitive_name = deriv[0]
        kwargs = deriv[1]
        field = (kwargs.get("field") or "").lower()
        if any(frag.lower() in field for frag in BODY_FIELD_FRAGMENTS):
            assert primitive_name == "drop", (
                f"Body-like field '{field}' must use 'drop' primitive, "
                f"got '{primitive_name}'"
            )


def test_tickets_recipe_has_no_body_projection() -> None:
    """Counterpart to the DDL absence: assert recipe never projects body."""
    r = tickets_recipe()
    body_in_proj = [
        col
        for col, (prim, kw) in r.derivations.items()
        if prim != "drop"
        and any(frag.lower() in (kw.get("field") or "").lower() for frag in BODY_FIELD_FRAGMENTS)
    ]
    assert not body_in_proj, f"BODY LEAK: {body_in_proj}"


def test_configurations_recipe_hashes_serial_number() -> None:
    from barycenter.etl.adapters.connectwise.recipes.configurations import (
        configurations_recipe,
    )

    r = configurations_recipe()
    prim, _ = r.derivations["serial_number"]
    assert prim == "hash"
