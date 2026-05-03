"""Unit tests for the keyword_flags primitive (TOOL-02)."""
import pytest

pytest.importorskip("barycenter.etl.primitives.keyword_flags",
                    reason="Plan 02 implements primitives")


def test_keyword_flags_returns_primitive_result():
    from barycenter.etl.primitives.keyword_flags import keyword_flags
    from barycenter.etl.primitives import PrimitiveResult
    result = keyword_flags("types", "defense", {"defense": "1", "federal": "1"})
    assert isinstance(result, PrimitiveResult)
    assert result.field_class in {"DROPPED", "INTERNAL", "SENSITIVE", "PUBLIC"}
