"""RetentionSweeper: per-class TTL DELETE for raw_*.* tables (RET-01, Pitfall 10).

Reads compliance/retention-policy.yaml; for each row older than the per-class
TTL (with optional per-tenant override), issues a parameterised DELETE and
emits an AuditEvent. Pitfall-10 mitigation (sweep races sync) is handled by
scheduling — sweep runs at 12:00 UTC, sync at 06:00 UTC.
"""
from __future__ import annotations

import datetime as dt
import pathlib

import yaml

from barycenter.etl.framework._audit_helpers import make_event

# Repo-relative resolution: src/barycenter/etl/framework/retention.py -> repo root
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
    return candidate


class RetentionSweeper:
    def __init__(self, policy_yaml: str, sql_conn, audit) -> None:
        self._policy_path = _resolve_yaml_path(policy_yaml)
        self._policy = yaml.safe_load(self._policy_path.read_text()) or {}
        self._sql = sql_conn
        self._audit = audit

    def _ttl_months(self, field_class: str, tenant_id: str | None = None) -> int:
        default = self._policy.get("default", {}) or {}
        ttl = (default.get(field_class) or {}).get("ttl_months", 60)
        if tenant_id:
            for ov in self._policy.get("overrides") or []:
                if ov.get("tenant_id") == tenant_id:
                    cls_ov = (ov.get("classes") or {}).get(field_class) or {}
                    if "ttl_months" in cls_ov:
                        return int(cls_ov["ttl_months"])
        return int(ttl)

    def sweep_table(
        self,
        qualified_table: str,
        field_class: str,
        *,
        tenant_id: str | None = None,
    ) -> int:
        ttl = self._ttl_months(field_class, tenant_id)
        cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=ttl * 30)
        cur = self._sql.cursor()
        # Parameterised DELETE — never f-string interpolate cutoff.
        sql = f"DELETE FROM {qualified_table} WHERE synced_at < ?"
        cur.execute(sql, cutoff)
        deleted = getattr(cur, "rowcount", 0) or 0
        self._sql.commit()
        self._audit.emit(make_event(
            verb="retention.sweep",
            resource_type=qualified_table,
            outcome="success",
            tenant_id=tenant_id,
            metadata={
                "field_class": field_class,
                "ttl_months": ttl,
                "deleted_rows": int(deleted),
                "cutoff": cutoff.isoformat(),
                "tenant_id": tenant_id,
            },
        ))
        return int(deleted)
