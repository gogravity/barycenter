"""Unit tests for the as_is primitive (TOOL-02)."""
import pytest


def test_as_is_passthrough_public():
    from barycenter.etl.primitives.as_is import as_is
    from barycenter.etl.primitives import PrimitiveResult
    result = as_is("name", "Acme")
    assert isinstance(result, PrimitiveResult)
    assert result.field_class == "PUBLIC"
    assert result.params == {"name": "Acme"}
    assert result.expr == "?"


def test_as_is_internal_when_declared():
    from barycenter.etl.primitives.as_is import as_is
    result = as_is("city", "Springfield", field_class="INTERNAL")
    assert result.field_class == "INTERNAL"


def test_as_is_refuses_restricted_when_only_classes_public():
    from barycenter.etl.primitives.as_is import as_is
    with pytest.raises(ValueError):
        as_is("ssn", "123-45-6789", only_classes=("PUBLIC",),
              field_class="RESTRICTED")


def test_as_is_refuses_default_class_outside_only_classes():
    from barycenter.etl.primitives.as_is import as_is
    # Default field_class='PUBLIC' must NOT pass when only_classes excludes PUBLIC.
    with pytest.raises(ValueError):
        as_is("ssn", "123-45-6789", only_classes=("INTERNAL",))
