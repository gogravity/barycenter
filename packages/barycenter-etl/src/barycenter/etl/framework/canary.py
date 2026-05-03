"""CanaryScanner: multi-field CUI phrase detection (COMP-07).

Scans text, subject, filename, and attachment metadata for CUI canary phrases.
For CUI-flagged tenants, attachments are refused outright (not fetched).
"""
from __future__ import annotations

import pathlib
import re

import yaml

DEFAULT_PHRASES_YAML = "compliance/cui-canary-phrases.yaml"

# Repo-relative resolution: src/barycenter/etl/framework/canary.py -> repo root
_REPO_ROOT = pathlib.Path(__file__).resolve().parents[6]


def _resolve_yaml_path(p: str) -> pathlib.Path:
    candidate = pathlib.Path(p)
    if candidate.is_absolute() and candidate.exists():
        return candidate
    if candidate.exists():
        return candidate
    repo_relative = _REPO_ROOT / p
    if repo_relative.exists():
        return repo_relative
    return candidate  # let open() raise


class CanaryScanner:
    def __init__(self, phrases_yaml: str = DEFAULT_PHRASES_YAML) -> None:
        self._yaml_path = phrases_yaml
        doc = yaml.safe_load(_resolve_yaml_path(phrases_yaml).read_text())
        phrases: list[str] = list(doc.get("phrases", []) or [])
        phrases.extend(doc.get("test_canaries", []) or [])
        if not phrases:
            raise ValueError(f"{phrases_yaml} contains no canary phrases")
        self._phrases = phrases
        self._regex = re.compile(
            "|".join(re.escape(p) for p in phrases),
            re.IGNORECASE,
        )

    def _scan(self, value: str | None) -> bool:
        if value is None or not isinstance(value, str):
            return False
        return self._regex.search(value) is not None

    def scan_text(self, value: str | None) -> bool:
        return self._scan(value)

    def scan_subject(self, value: str | None) -> bool:
        return self._scan(value)

    def scan_filename(self, value: str | None) -> bool:
        return self._scan(value)

    def refuse_attachment(self, tenant_cui_flag: bool) -> bool:
        # COMP-07: attachments refused outright for CUI-flagged adapters/tenants.
        return bool(tenant_cui_flag)
