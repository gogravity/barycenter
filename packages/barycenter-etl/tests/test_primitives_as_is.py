"""Unit tests for the as_is primitive (TOOL-02)."""
import pytest

pytest.importorskip("barycenter.etl.primitives.as_is",
                    reason="Plan 02 implements primitives")


def test_as_is_returns_primitive_result():
    from barycenter.etl.primitives.as_is import as_is
    from barycenter.etl.primitives import PrimitiveResult
    result = as_is("name", "Acme")
    assert isinstance(result, PrimitiveResult)
    assert result.field_class in {"PUBLIC", "INTERNAL"}


def test_as_is_refuses_restricted_when_only_classes_public():
    from barycenter.etl.primitives.as_is import as_is
    with pytest.raises(ValueError):
        # Implementation must refuse RESTRICTED-class fields when caller
        # restricts allowed classes to PUBLIC.
        as_is("ssn", "123-45-6789", only_classes=("PUBLIC",))
