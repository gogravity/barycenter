"""Unit tests for the drop primitive (TOOL-02)."""
import pytest


def test_drop_returns_dropped_primitive_result():
    from barycenter.etl.primitives.drop import drop
    from barycenter.etl.primitives import PrimitiveResult
    result = drop("body")
    assert isinstance(result, PrimitiveResult)
    assert result.field_class == "DROPPED"
    assert result.expr == ""
    assert result.params == {}


def test_drop_rejects_empty_field_name():
    from barycenter.etl.primitives.drop import drop
    with pytest.raises(ValueError):
        drop("")


def test_drop_in_registry():
    from barycenter.etl.primitives import PRIMITIVE_REGISTRY
    assert "drop" in PRIMITIVE_REGISTRY
    assert PRIMITIVE_REGISTRY["drop"]("attachments").field_class == "DROPPED"
