"""SaltRotation: versioned-pepper dual-write logic for ENC-02.

Implements the runbook (compliance/salt-rotation-runbook.md):
  open_window  -> mode=dual-write
  dual_write   -> writes (pid_old, ver_old) and (pid_new, ver_new) to
                  pseudo.person_map
  cut_over     -> mode=new-only

KV secret create (step 1), backfill (step 6), and version retire (step 7) are
operator-driven via az CLI; this module supports the rotation but does not
provision Key Vault state.
"""
from __future__ import annotations

import datetime as dt
import pathlib
from dataclasses import dataclass

import yaml

from barycenter.etl.framework._audit_helpers import make_event
from barycenter.etl.framework.pseudonymizer import Pseudonymizer

DEFAULT_STATE_PATH = "compliance/salt-rotation-state.yaml"


@dataclass(frozen=True)
class DualWriteResult:
    pid_old: str
    pid_new: str
    salt_version_old: str
    salt_version_new: str


class SaltRotation:
    def __init__(
        self,
        kv_client,
        sql_conn,
        audit,
        *,
        state_path: str = DEFAULT_STATE_PATH,
    ) -> None:
        self._kv = kv_client
        self._sql = sql_conn
        self._audit = audit
        self._state_path = pathlib.Path(state_path)
        self._pseudo = Pseudonymizer(kv_client)

    def _load_state(self) -> dict:
        return yaml.safe_load(self._state_path.read_text()) or {}

    def _save_state(self, doc: dict) -> None:
        self._state_path.write_text(yaml.safe_dump(doc, sort_keys=False))

    def open_window(
        self,
        tenant_id: str,
        *,
        old_version: str,
        new_version: str,
    ) -> None:
        doc = self._load_state()
        doc.setdefault("tenants", {})
        now = dt.datetime.now(dt.timezone.utc)
        doc["tenants"][str(tenant_id)] = {
            "mode": "dual-write",
            "old_version": old_version,
            "new_version": new_version,
            "window_opened_at": now.isoformat(),
            "expected_close_at": (now + dt.timedelta(hours=24)).isoformat(),
        }
        self._save_state(doc)
        self._audit.emit(make_event(
            verb="salt.rotate.open_window",
            resource_type=f"salt-{tenant_id}",
            outcome="success",
            tenant_id=str(tenant_id),
            metadata={"old_version": old_version, "new_version": new_version},
        ))

    def cut_over(self, tenant_id: str) -> None:
        doc = self._load_state()
        entry = (doc.get("tenants") or {}).get(str(tenant_id))
        if entry is None:
            raise ValueError(f"no rotation window for tenant {tenant_id}")
        entry["mode"] = "new-only"
        self._save_state(doc)
        self._audit.emit(make_event(
            verb="salt.rotate.cut_over",
            resource_type=f"salt-{tenant_id}",
            outcome="success",
            tenant_id=str(tenant_id),
            metadata={"new_version": entry.get("new_version")},
        ))

    def dual_write(
        self,
        email: str,
        tenant_id: str,
        *,
        old_version: str,
        new_version: str,
    ) -> DualWriteResult:
        pid_old, ver_old = self._pseudo.derive(
            email, tenant_id, salt_version=old_version
        )
        pid_new, ver_new = self._pseudo.derive(
            email, tenant_id, salt_version=new_version
        )
        cur = self._sql.cursor()
        for pid, ver in ((pid_old, ver_old), (pid_new, ver_new)):
            cur.execute(
                """MERGE pseudo.person_map AS tgt
                   USING (SELECT ? AS tenant_id, ? AS email_lower,
                                 ? AS person_pid, ? AS salt_version) AS src
                   ON tgt.tenant_id = src.tenant_id
                      AND tgt.email_lower = src.email_lower
                      AND tgt.salt_version = src.salt_version
                   WHEN NOT MATCHED THEN INSERT
                        (tenant_id, email_lower, person_pid, salt_version)
                      VALUES (src.tenant_id, src.email_lower,
                              src.person_pid, src.salt_version);""",
                tenant_id, email.lower(), pid, ver,
            )
            self._audit.emit(make_event(
                verb="salt.rotate.dual_write",
                resource_type="pseudo.person_map",
                outcome="success",
                tenant_id=str(tenant_id),
                metadata={"tenant_id": tenant_id, "salt_version": ver},
            ))
        self._sql.commit()
        return DualWriteResult(
            pid_old=pid_old,
            pid_new=pid_new,
            salt_version_old=ver_old,
            salt_version_new=ver_new,
        )
