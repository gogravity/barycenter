"""Unit tests for the bucket primitive (TOOL-02)."""
import pytest


def test_bucket_middle_range():
    from barycenter.etl.primitives.bucket import bucket
    from barycenter.etl.primitives import PrimitiveResult
    result = bucket("count", 47, [10, 50, 100])
    assert isinstance(result, PrimitiveResult)
    assert result.params["count_bucket"] == "10-50"
    assert result.field_class == "INTERNAL"


def test_bucket_below_lowest():
    from barycenter.etl.primitives.bucket import bucket
    assert bucket("c", 5, [10, 50, 100]).params["c_bucket"] == "<10"


def test_bucket_at_or_above_highest():
    from barycenter.etl.primitives.bucket import bucket
    assert bucket("c", 200, [10, 50, 100]).params["c_bucket"] == ">=100"


def test_bucket_null_value():
    from barycenter.etl.primitives.bucket import bucket
    assert bucket("c", None, [10, 50, 100]).params["c_bucket"] == "null"
