"""score primitive (TOOL-02): numeric formula evaluated over named fields.

The formula is char-allowlisted (digits, basic operators, parentheses, dot,
space) AFTER field-name substitution. eval runs with empty builtins and
empty locals — no name resolution, no attribute access, no calls. RESTRICTED
inputs are forbidden by recipe-level field-class declaration, not here.
"""
from __future__ import annotations

from barycenter.etl.primitives._result import PrimitiveResult


_ALLOWED = set("0123456789+-*/(). ")


def score(field: str, fields: dict, formula: str) -> PrimitiveResult:
    """Evaluate ``formula`` using ``fields`` as the symbol table.

    ``field`` is the target column name; it becomes the params key so that
    multiple score columns in one recipe do not collide (previously hardcoded
    to ``"score"``).
    """
    if not isinstance(field, str) or not field:
        raise ValueError(f"score field must be a non-empty string, got {field!r}")
    if not isinstance(fields, dict):
        raise ValueError(f"score fields must be a dict, got {type(fields).__name__}")
    if not isinstance(formula, str) or not formula:
        raise ValueError(f"score formula must be a non-empty string, got {formula!r}")

    # Substitute field names with their numeric values. Order by descending
    # length so longer names match before shorter prefixes.
    safe = formula
    for name in sorted(fields.keys(), key=len, reverse=True):
        safe = safe.replace(name, str(fields[name]))

    if not all(c in _ALLOWED for c in safe):
        raise ValueError(
            f"score formula contains disallowed chars: {formula!r} -> {safe!r}"
        )
    result = eval(safe, {"__builtins__": {}}, {})  # noqa: S307 - sanitized arithmetic
    return PrimitiveResult(
        expr="?",
        params={field: result},
        field_class="INTERNAL",
    )
