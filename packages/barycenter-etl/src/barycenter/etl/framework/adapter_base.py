"""AdapterBase placeholder + Category enum (TOOL-04).

Task 2 of plan 02-04 replaces this file with the full AdapterBase orchestrator
while preserving the Category enum.
"""
from __future__ import annotations

from enum import StrEnum


class Category(StrEnum):
    PRODUCTIVITY = "productivity"
    RMM = "rmm"
    SECURITY = "security"
    BACKUP = "backup"
    DOCS = "docs"
    DISTRIBUTORS = "distributors"
    CW = "cw"
