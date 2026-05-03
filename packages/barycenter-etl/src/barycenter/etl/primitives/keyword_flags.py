"""keyword_flags primitive (TOOL-02): substring match -> boolean flag dict.

Lowercase substring scan of ``value`` against the keys of ``kw_dict``.
The resulting flag dict is bound as a single JSON-shaped parameter under
``{field}_flags``; downstream the recipe binds it as nvarchar(max) JSON.
"""
from __future__ import annotations

from barycenter.etl.primitives._result import PrimitiveResult


def keyword_flags(field: str, value: str, kw_dict: dict) -> PrimitiveResult:
    """Set a boolean flag per kw_dict key based on case-insensitive substring match."""
    if not isinstance(field, str) or not field:
        raise ValueError(
            f"keyword_flags requires a non-empty field name, got {field!r}"
        )
    if not isinstance(kw_dict, dict):
        raise ValueError(
            f"keyword_flags kw_dict must be a dict, got {type(kw_dict).__name__}"
        )
    text = (value or "").lower() if isinstance(value, str) else str(value or "").lower()
    flags = {kw: (str(kw).lower() in text) for kw in kw_dict.keys()}
    return PrimitiveResult(
        expr="?",
        params={f"{field}_flags": flags},
        field_class="INTERNAL",
    )
