"""Unit tests for the drop primitive (TOOL-02)."""
import pytest

pytest.importorskip("barycenter.etl.primitives.drop",
                    reason="Plan 02 implements primitives")


def test_drop_returns_primitive_result():
    from barycenter.etl.primitives.drop import drop
    from barycenter.etl.primitives import PrimitiveResult
    result = drop("body")
    assert isinstance(result, PrimitiveResult)
    assert result.field_class == "DROPPED"
    assert result.expr == ""
