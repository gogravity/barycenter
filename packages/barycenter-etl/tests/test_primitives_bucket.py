"""Unit tests for the bucket primitive (TOOL-02)."""
import pytest

pytest.importorskip("barycenter.etl.primitives.bucket",
                    reason="Plan 02 implements primitives")


def test_bucket_returns_primitive_result():
    from barycenter.etl.primitives.bucket import bucket
    from barycenter.etl.primitives import PrimitiveResult
    result = bucket("count", 47, [10, 50, 100])
    assert isinstance(result, PrimitiveResult)
    assert result.field_class in {"DROPPED", "INTERNAL", "SENSITIVE", "PUBLIC"}
