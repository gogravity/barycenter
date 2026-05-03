"""bucket primitive (TOOL-02): map a numeric value to a labeled bucket range.

Given ``ranges = [10, 50, 100]`` the bucket labels are:
    "<10", "10-50", "50-100", ">=100", and "null" for None inputs.
"""
from __future__ import annotations

from barycenter.etl.primitives._result import PrimitiveResult


def bucket(field: str, value, ranges: list) -> PrimitiveResult:
    """Bucket ``value`` against sorted ``ranges`` boundaries."""
    if not isinstance(field, str) or not field:
        raise ValueError(f"bucket requires a non-empty field name, got {field!r}")
    if not ranges:
        raise ValueError("bucket requires at least one range boundary")
    if value is None:
        label: str = "null"
    else:
        sorted_r = sorted(ranges)
        label = ""
        if value < sorted_r[0]:
            label = f"<{sorted_r[0]}"
        elif value >= sorted_r[-1]:
            label = f">={sorted_r[-1]}"
        else:
            for lo, hi in zip(sorted_r, sorted_r[1:]):
                if lo <= value < hi:
                    label = f"{lo}-{hi}"
                    break
    return PrimitiveResult(
        expr="?",
        params={f"{field}_bucket": label},
        field_class="INTERNAL",
    )
