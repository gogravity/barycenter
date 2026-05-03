"""Unit tests for the Category enum (TOOL-04)."""
import pytest

pytest.importorskip("barycenter.etl.framework.adapter_base", reason="Plan 04 implements")


def test_category_enum_has_seven_members():
    from barycenter.etl.framework.adapter_base import Category
    members = {c.value for c in Category}
    assert members == {"productivity", "rmm", "security", "backup",
                       "docs", "distributors", "cw"}
