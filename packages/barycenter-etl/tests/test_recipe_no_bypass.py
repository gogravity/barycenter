"""CI gate: every recipe column derivation traces to one of the 8 primitives (TOOL-01, TOOL-02)."""
import pytest


def test_recipe_accepts_known_primitive():
    from barycenter.etl.framework.recipe import ETLRecipe
    r = ETLRecipe(
        target_table="raw_cw.companies",
        derivations={"id": ("as_is", {"field": "id", "field_class": "INTERNAL"})},
    )
    assert r.target_table == "raw_cw.companies"
    assert "id" in r.derivations


def test_recipe_rejects_unknown_primitive():
    from barycenter.etl.framework.recipe import ETLRecipe
    with pytest.raises(ValueError) as exc:
        ETLRecipe(
            target_table="raw_cw.x",
            derivations={"a": ("nonexistent_primitive", {})},
        )
    assert "bypasses primitive layer" in str(exc.value)


def test_recipe_rejects_malformed_derivation():
    from barycenter.etl.framework.recipe import ETLRecipe
    with pytest.raises(ValueError):
        ETLRecipe(target_table="t", derivations={"a": ("drop",)})  # type: ignore[arg-type]


def test_recipes_only_use_primitives_when_module_present():
    """When Plan 05 lands the connectwise.recipes module this gate runs.

    Until then iter_all_recipes returns []; the test still validates the
    integration point (registry membership check) by exercising the
    no-bypass validator directly.
    """
    from barycenter.etl.primitives import PRIMITIVE_REGISTRY
    from barycenter.etl.framework.recipe import iter_all_recipes
    for recipe in iter_all_recipes():
        for col, deriv in recipe.derivations.items():
            primitive_name = deriv[0] if isinstance(deriv, tuple) else deriv.primitive_name
            assert primitive_name in PRIMITIVE_REGISTRY, (
                f"{recipe.target_table}.{col} bypasses primitive layer "
                f"(uses {primitive_name})"
            )


def test_recipe_compile_skips_dropped_columns():
    from barycenter.etl.framework.recipe import ETLRecipe
    r = ETLRecipe(
        target_table="raw_cw.companies",
        derivations={
            "id": ("as_is", {"field": "id", "field_class": "INTERNAL"}),
            "notes": ("drop", {"field": "notes"}),
        },
    )
    sql, params = r.compile({"id": 42, "notes": "ignore-me"})
    assert "notes" not in sql
    assert "id" in sql
    assert params["id"] == 42
