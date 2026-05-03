"""drop primitive (TOOL-02): explicit non-projection.

Used for body fields, attachments, and any input column the recipe must not
emit downstream. Returns a PrimitiveResult with field_class='DROPPED' so the
recipe compiler can skip it during INSERT projection while still recording
the explicit decision in the registry / audit trail.
"""
from __future__ import annotations

from barycenter.etl.primitives._result import PrimitiveResult


def drop(field: str) -> PrimitiveResult:
    """Mark a source field as explicitly dropped from the projection."""
    if not isinstance(field, str) or not field:
        raise ValueError(f"drop requires a non-empty field name, got {field!r}")
    return PrimitiveResult(expr="", params={}, field_class="DROPPED")
