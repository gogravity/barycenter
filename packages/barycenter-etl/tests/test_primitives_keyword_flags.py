"""Unit tests for the keyword_flags primitive (TOOL-02)."""
import pytest


def test_keyword_flags_detects_keywords():
    from barycenter.etl.primitives.keyword_flags import keyword_flags
    from barycenter.etl.primitives import PrimitiveResult
    result = keyword_flags(
        "types",
        "defense industrial base",
        {"defense": "1", "federal": "0"},
    )
    assert isinstance(result, PrimitiveResult)
    flags = result.params["types_flags"]
    assert flags["defense"] is True
    assert flags["federal"] is False
    assert result.field_class == "INTERNAL"


def test_keyword_flags_case_insensitive():
    from barycenter.etl.primitives.keyword_flags import keyword_flags
    result = keyword_flags("t", "DEFENSE", {"defense": "1"})
    assert result.params["t_flags"]["defense"] is True


def test_keyword_flags_handles_none():
    from barycenter.etl.primitives.keyword_flags import keyword_flags
    result = keyword_flags("t", None, {"defense": "1"})
    assert result.params["t_flags"]["defense"] is False
