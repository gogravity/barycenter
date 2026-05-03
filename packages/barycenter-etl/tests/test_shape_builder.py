"""Unit tests for the ShapeBuilder (TOOL-03)."""
import pytest

pytest.importorskip("barycenter.etl.framework.shape_builder", reason="Plan 04 implements")


def test_shape_builder_refuses_novel_shape(mock_sql):
    from barycenter.etl.framework.shape_builder import ShapeBuilder
    sb = ShapeBuilder()
    with pytest.raises(ValueError, match="novel"):
        sb.populate("tickets_summary", mock_sql)


def test_shape_builder_accepts_canonical_shape(mock_sql):
    from barycenter.etl.framework.shape_builder import ShapeBuilder
    sb = ShapeBuilder()
    # populates customer_snapshot with a TRUNCATE+INSERT
    sb.populate("customer_snapshot", mock_sql)
    truncate_calls = [c for c in mock_sql.execute.call_args_list
                      if "TRUNCATE TABLE ai_zone.customer_snapshot" in str(c).upper()
                      or "TRUNCATE" in str(c).upper()]
    assert truncate_calls
