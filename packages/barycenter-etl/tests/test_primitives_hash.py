"""Unit tests for the hash primitive (TOOL-02)."""
import pytest

pytest.importorskip("barycenter.etl.primitives.hash",
                    reason="Plan 02 implements primitives")


def test_hash_returns_primitive_result():
    from barycenter.etl.primitives.hash import hash_
    from barycenter.etl.primitives import PrimitiveResult
    result = hash_("email", "alice@example.com")
    assert isinstance(result, PrimitiveResult)
    assert result.field_class == "INTERNAL"
    assert "HASHBYTES" in result.expr
