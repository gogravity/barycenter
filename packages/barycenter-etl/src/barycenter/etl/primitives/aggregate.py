"""aggregate primitive (TOOL-02): numeric reduction over a list of values.

Supports SUM / COUNT / AVG / MAX / MIN. Empty input collapses to 0 instead
of raising so recipe authors can rely on a stable numeric output even when
a CW response yields zero rows for the aggregation window.
"""
from __future__ import annotations

import statistics
from typing import Callable

from barycenter.etl.primitives._result import PrimitiveResult


_FNS: dict[str, Callable] = {
    "SUM": sum,
    "COUNT": len,
    "AVG": lambda xs: statistics.mean(xs) if xs else 0,
    "MAX": max,
    "MIN": min,
}


def aggregate(field: str, fn: str, values: list) -> PrimitiveResult:
    """Reduce ``values`` with ``fn`` and emit a parameter-bound projection."""
    if not isinstance(field, str) or not field:
        raise ValueError(f"aggregate requires a non-empty field name, got {field!r}")
    if fn not in _FNS:
        raise ValueError(
            f"aggregate fn must be one of {sorted(_FNS)}, got {fn!r}"
        )
    if values:
        result = _FNS[fn](values)
    else:
        result = 0
    return PrimitiveResult(
        expr="?",
        params={field: result},
        field_class="INTERNAL",
    )
