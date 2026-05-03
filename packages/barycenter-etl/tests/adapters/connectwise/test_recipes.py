"""Unit tests for CW Manage ETL recipes (Plan 05)."""
import pytest

pytest.importorskip("barycenter.etl.adapters.connectwise.recipes",
                    reason="Plan 05 implements")


def test_tickets_recipe_drops_all_body_fields():
    from barycenter.etl.adapters.connectwise.recipes.tickets import tickets_recipe
    r = tickets_recipe()
    for col, deriv in r.derivations.items():
        primitive_name = deriv[0] if isinstance(deriv, tuple) else deriv.primitive_name
        kwargs = deriv[1] if isinstance(deriv, tuple) else deriv.kwargs
        field = kwargs.get("field", "")
        if (
            "body" in field.lower()
            or "resolution" in field.lower()
            or "internalAnalysis" in field.lower()
            or "initialDescription" in field.lower()
        ):
            assert primitive_name == "drop", (
                f"Body-like field '{field}' must use 'drop' primitive, "
                f"got '{primitive_name}'"
            )
