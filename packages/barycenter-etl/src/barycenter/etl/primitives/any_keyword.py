"""any_keyword primitive (TOOL-02): substring match -> scalar BIT (0 or 1).

Returns 1 if any keyword in ``keywords`` appears (case-insensitive) in the
string value of ``field``; 0 otherwise. Suitable for SQL BIT columns.

Unlike ``keyword_flags``, which returns a dict of per-keyword booleans,
``any_keyword`` collapses the result to a single integer so it can be bound
to a BIT NOT NULL column without post-processing.
"""
from __future__ import annotations

from barycenter.etl.primitives._result import PrimitiveResult


def any_keyword(field: str, value: str, keywords: list) -> PrimitiveResult:
    """Return 1 if any keyword matches ``value``, else 0.

    ``value`` is lowercased before comparison; ``keywords`` must be a list
    of strings (case-insensitive match).
    """
    if not isinstance(field, str) or not field:
        raise ValueError(
            f"any_keyword requires a non-empty field name, got {field!r}"
        )
    if not isinstance(keywords, list):
        raise ValueError(
            f"any_keyword keywords must be a list, got {type(keywords).__name__}"
        )
    text = (value or "").lower() if isinstance(value, str) else str(value or "").lower()
    matched = int(any(str(kw).lower() in text for kw in keywords))
    return PrimitiveResult(
        expr="?",
        params={field: matched},
        field_class="INTERNAL",
    )
