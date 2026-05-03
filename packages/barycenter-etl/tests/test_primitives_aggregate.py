"""Unit tests for the aggregate primitive (TOOL-02)."""
import pytest

pytest.importorskip("barycenter.etl.primitives.aggregate",
                    reason="Plan 02 implements primitives")


def test_aggregate_returns_primitive_result():
    from barycenter.etl.primitives.aggregate import aggregate
    from barycenter.etl.primitives import PrimitiveResult
    result = aggregate("hours", "SUM", [1, 2, 3])
    assert isinstance(result, PrimitiveResult)
    assert result.field_class in {"DROPPED", "INTERNAL", "SENSITIVE", "PUBLIC"}
