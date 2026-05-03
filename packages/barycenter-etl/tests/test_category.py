"""Unit tests for the Category enum (TOOL-04)."""
import pytest


def test_category_enum_has_seven_members():
    from barycenter.etl.framework.adapter_base import Category
    members = {c.value for c in Category}
    assert members == {"productivity", "rmm", "security", "backup",
                       "docs", "distributors", "cw"}


def test_category_values_are_strings():
    from barycenter.etl.framework.adapter_base import Category
    assert Category.CW.value == "cw"
    assert Category.PRODUCTIVITY.value == "productivity"


def test_category_string_enum_behavior():
    from barycenter.etl.framework.adapter_base import Category
    # StrEnum members compare equal to their str values
    assert Category.RMM == "rmm"
