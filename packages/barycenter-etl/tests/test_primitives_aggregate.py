"""Unit tests for the aggregate primitive (TOOL-02)."""
import pytest


def test_aggregate_sum():
    from barycenter.etl.primitives.aggregate import aggregate
    from barycenter.etl.primitives import PrimitiveResult
    result = aggregate("hours", "SUM", [1.0, 2.0, 3.0])
    assert isinstance(result, PrimitiveResult)
    assert result.params["hours"] == 6.0
    assert result.field_class == "INTERNAL"


def test_aggregate_count_avg_max_min():
    from barycenter.etl.primitives.aggregate import aggregate
    assert aggregate("n", "COUNT", [1, 2, 3]).params["n"] == 3
    assert aggregate("a", "AVG", [2, 4]).params["a"] == 3
    assert aggregate("mx", "MAX", [1, 9, 3]).params["mx"] == 9
    assert aggregate("mn", "MIN", [1, 9, 3]).params["mn"] == 1


def test_aggregate_empty_collapses_to_zero():
    from barycenter.etl.primitives.aggregate import aggregate
    assert aggregate("h", "SUM", []).params["h"] == 0


def test_aggregate_rejects_unknown_fn():
    from barycenter.etl.primitives.aggregate import aggregate
    with pytest.raises(ValueError):
        aggregate("h", "MEDIAN", [1, 2, 3])
