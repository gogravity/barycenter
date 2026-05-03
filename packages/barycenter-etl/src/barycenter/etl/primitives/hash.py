"""hash primitive (TOOL-02): SHA-256 hex digest computed by SQL Server HASHBYTES.

The expression is a static T-SQL fragment with a single '?' parameter; the
caller binds the source value at execute time. field_class='INTERNAL' because
a SHA-256 hash is a one-way derivation that does not, on its own, expose PII.
"""
from __future__ import annotations

from barycenter.etl.primitives._result import PrimitiveResult


def hash_(field: str, value: str) -> PrimitiveResult:
    """Hash ``value`` via SQL Server's HASHBYTES('SHA2_256', ?) expression."""
    if not isinstance(field, str) or not field:
        raise ValueError(f"hash requires a non-empty field name, got {field!r}")
    if not isinstance(value, str):
        value = str(value)
    return PrimitiveResult(
        expr="CONVERT(CHAR(64), HASHBYTES('SHA2_256', ?), 2)",
        params={field: value},
        field_class="INTERNAL",
    )
