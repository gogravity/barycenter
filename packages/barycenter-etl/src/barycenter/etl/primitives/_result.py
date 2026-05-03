"""PrimitiveResult dataclass — return type of every primitive."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

VALID_FIELD_CLASSES = frozenset(
    {"RESTRICTED", "SENSITIVE", "INTERNAL", "PUBLIC", "DROPPED"}
)


@dataclass(frozen=True)
class PrimitiveResult:
    """Return type of every TOOL-02 primitive.

    expr:        SQL expression fragment ('?' placeholder, static expr, or '' for drop).
    params:      Parameters dict to bind into the parameterized SQL.
    field_class: One of VALID_FIELD_CLASSES (RESTRICTED, SENSITIVE, INTERNAL, PUBLIC, DROPPED).
    """

    expr: str
    params: dict[str, Any] = field(default_factory=dict)
    field_class: str = "INTERNAL"

    def __post_init__(self) -> None:
        if self.field_class not in VALID_FIELD_CLASSES:
            raise ValueError(
                f"field_class must be one of {sorted(VALID_FIELD_CLASSES)}, "
                f"got {self.field_class!r}"
            )
