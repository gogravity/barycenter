"""Unit tests for the score primitive (TOOL-02)."""
import pytest


def test_score_basic_arithmetic():
    from barycenter.etl.primitives.score import score
    from barycenter.etl.primitives import PrimitiveResult
    result = score("health_score", {"a": 1, "b": 2}, "a*2+b")
    assert isinstance(result, PrimitiveResult)
    assert result.params["health_score"] == 4
    assert result.field_class == "INTERNAL"


def test_score_with_parens():
    from barycenter.etl.primitives.score import score
    assert score("total", {"a": 2, "b": 3}, "(a+b)*2").params["total"] == 10


def test_score_rejects_disallowed_chars():
    from barycenter.etl.primitives.score import score
    with pytest.raises(ValueError):
        score("x", {"a": 1}, "__import__('os')")


def test_score_rejects_function_calls():
    from barycenter.etl.primitives.score import score
    with pytest.raises(ValueError):
        # The 'pow' identifier is unknown; substitution leaves letters in expr.
        score("x", {"a": 1}, "pow(a, 2)")
