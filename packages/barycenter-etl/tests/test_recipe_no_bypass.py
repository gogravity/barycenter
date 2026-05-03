"""CI gate: every recipe column derivation traces to one of the 8 primitives (TOOL-01, TOOL-02)."""
import pytest

pytest.importorskip("barycenter.etl.framework.recipe", reason="Plan 02 implements")
pytest.importorskip("barycenter.etl.adapters.connectwise.recipes",
                    reason="Plan 05 implements recipes")


def test_recipes_only_use_primitives():
    from barycenter.etl.primitives import PRIMITIVE_REGISTRY
    from barycenter.etl.adapters.connectwise.recipes import iter_all_recipes
    for recipe in iter_all_recipes():
        for col, deriv in recipe.derivations.items():
            # deriv is (primitive_name, kwargs) tuple OR an object with primitive_name
            primitive_name = deriv[0] if isinstance(deriv, tuple) else deriv.primitive_name
            assert primitive_name in PRIMITIVE_REGISTRY, \
                f"{recipe.target_table}.{col} bypasses primitive layer (uses {primitive_name})"
