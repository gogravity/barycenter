"""as_is primitive (TOOL-02): passthrough projection with class guardrail.

Refuses to project a field whose declared ``field_class`` is not in
``only_classes``. Default ``only_classes=('PUBLIC','INTERNAL')`` ensures
RESTRICTED and SENSITIVE values cannot reach a target column without an
explicit, auditable opt-in by the recipe author (Threat T-02-08).
"""
from __future__ import annotations

from typing import Any

from barycenter.etl.primitives._result import PrimitiveResult


def as_is(
    field: str,
    value: Any,
    *,
    only_classes: tuple = ("PUBLIC", "INTERNAL"),
    field_class: str = "PUBLIC",
) -> PrimitiveResult:
    """Pass ``value`` through unchanged after verifying its class is allowed."""
    if not isinstance(field, str) or not field:
        raise ValueError(f"as_is requires a non-empty field name, got {field!r}")
    if field_class not in only_classes:
        raise ValueError(
            f"as_is refuses to project field {field!r} of class {field_class!r}; "
            f"only_classes={only_classes}"
        )
    return PrimitiveResult(
        expr="?",
        params={field: value},
        field_class=field_class,
    )
