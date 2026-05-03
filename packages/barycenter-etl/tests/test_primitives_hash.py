"""Unit tests for the hash primitive (TOOL-02)."""
import pytest


def test_hash_returns_hashbytes_expr():
    from barycenter.etl.primitives.hash import hash_
    from barycenter.etl.primitives import PrimitiveResult
    result = hash_("email", "alice@example.com")
    assert isinstance(result, PrimitiveResult)
    assert result.field_class == "INTERNAL"
    assert "HASHBYTES('SHA2_256'" in result.expr


def test_hash_binds_value_in_params():
    from barycenter.etl.primitives.hash import hash_
    result = hash_("email", "alice@example.com")
    assert result.params == {"email": "alice@example.com"}


def test_hash_coerces_non_str():
    from barycenter.etl.primitives.hash import hash_
    result = hash_("id", 42)
    assert result.params == {"id": "42"}
