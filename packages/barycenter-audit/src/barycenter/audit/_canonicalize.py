"""Stable JSON canonicalization helper (RFC 8785-style subset).

Used by ``barycenter.audit.chain.canonicalize_json``. Renders dict-like
payloads with:
  - keys sorted lexicographically (recursively)
  - no whitespace between separators
  - UTF-8 encoding (non-ASCII passed through, no \\uXXXX escapes)
  - UUID via str(), datetime/date via isoformat()
  - None as null, bool as true/false
  - any other non-JSON-serializable type raises ValueError
"""
from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any
from uuid import UUID


def _default(obj: Any) -> Any:
    if isinstance(obj, UUID):
        return str(obj)
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise ValueError(f"Cannot canonicalize value of type {type(obj).__name__}")


def canonicalize(obj: Any) -> str:
    """Return a stable canonical JSON string for ``obj``.

    Raises ValueError on any non-JSON-serializable value (json.dumps wraps
    the default-callable's ValueError as TypeError, so we unwrap it).
    """
    try:
        return json.dumps(
            obj,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            default=_default,
            allow_nan=False,
        )
    except TypeError as exc:
        # json.dumps re-raises our default()'s ValueError as TypeError when
        # encountering an unsupported type at the top level. Normalize to
        # ValueError per the contract documented in chain.canonicalize_json.
        raise ValueError(str(exc)) from exc
