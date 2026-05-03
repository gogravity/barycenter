"""Unit tests for the score primitive (TOOL-02)."""
import pytest

pytest.importorskip("barycenter.etl.primitives.score",
                    reason="Plan 02 implements primitives")


def test_score_returns_primitive_result():
    from barycenter.etl.primitives.score import score
    from barycenter.etl.primitives import PrimitiveResult
    result = score({"a": 1, "b": 2}, "a*2+b")
    assert isinstance(result, PrimitiveResult)
    assert result.field_class in {"DROPPED", "INTERNAL", "SENSITIVE", "PUBLIC"}
