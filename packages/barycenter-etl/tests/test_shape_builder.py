"""Unit tests for the ShapeBuilder (TOOL-03)."""
import pytest


def test_shape_builder_refuses_novel_shape(mock_sql):
    from barycenter.etl.framework.shape_builder import ShapeBuilder
    sb = ShapeBuilder()
    with pytest.raises(ValueError, match="novel"):
        sb.populate("tickets_summary", mock_sql)


def test_shape_builder_accepts_canonical_shape(mock_sql):
    from barycenter.etl.framework.shape_builder import ShapeBuilder
    sb = ShapeBuilder()
    sb.populate("customer_snapshot", mock_sql)
    cur = mock_sql.cursor.return_value
    truncate_calls = [c for c in cur.execute.call_args_list
                      if "TRUNCATE" in str(c).upper()]
    assert truncate_calls
    insert_calls = [c for c in cur.execute.call_args_list
                    if "INSERT" in str(c).upper() or "SELECT" in str(c).upper()]
    assert insert_calls
    mock_sql.commit.assert_called()


def test_shape_builder_canonical_set():
    from barycenter.etl.framework.shape_builder import ShapeBuilder
    assert ShapeBuilder.CANONICAL == frozenset({
        "customer_snapshot",
        "customer_features_cw",
        "timeseries_aggregate",
        "customer_memory",
    })


def test_shape_builder_emits_audit_when_provided(mock_sql, mock_audit):
    from barycenter.etl.framework.shape_builder import ShapeBuilder
    sb = ShapeBuilder()
    sb.populate("customer_snapshot", mock_sql, audit=mock_audit)
    mock_audit.emit.assert_called()


def test_shape_builder_all_canonical_shapes_populate(mock_sql):
    from barycenter.etl.framework.shape_builder import ShapeBuilder
    sb = ShapeBuilder()
    for shape in ("customer_snapshot", "customer_features_cw",
                  "timeseries_aggregate", "customer_memory"):
        sb.populate(shape, mock_sql)
