"""AdapterBase: D-02 table-isolated ETL orchestrator.

Per CLAUDE.md fail-closed mandate:
  - AuditClient.emit() is the only audit path; failures propagate.

Per D-02 (table-isolated, fail-closed):
  - Each table syncs in its own try/except. ETLError -> emit failure audit
    event, log alert, continue to the next table.
  - AuditEmitError MUST propagate. The whole run aborts.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Iterator

from barycenter.audit import AuditEmitError
from barycenter.etl.framework._audit_helpers import make_event
from barycenter.etl.framework.canary import CanaryScanner
from barycenter.etl.framework.cui_gate import CUIGate
from barycenter.etl.framework.exceptions import ETLError, CUIBoundaryViolation
from barycenter.etl.framework.recipe import ETLRecipe

log = logging.getLogger(__name__)


class Category(StrEnum):
    PRODUCTIVITY = "productivity"
    RMM = "rmm"
    SECURITY = "security"
    BACKUP = "backup"
    DOCS = "docs"
    DISTRIBUTORS = "distributors"
    CW = "cw"


class AdapterBase(ABC):
    # Subclasses MUST set CATEGORY and TABLES; CUI_SENSITIVE_TABLES may be empty.
    CATEGORY: str = ""
    TABLES: list[str] = []
    CUI_SENSITIVE_TABLES: list[str] = []
    CUI_CANARY_FIELDS: dict[str, list[str]] = {}

    def __init__(
        self,
        audit,
        sql_conn,
        kv_client,
        *,
        canary_scanner: CanaryScanner | None = None,
    ) -> None:
        if not self.CATEGORY:
            raise ValueError(
                f"{type(self).__name__} must declare CATEGORY"
            )
        if not self.TABLES:
            raise ValueError(
                f"{type(self).__name__} must declare TABLES"
            )
        if self.CUI_SENSITIVE_TABLES is None:
            raise ValueError(
                f"{type(self).__name__} must declare CUI_SENSITIVE_TABLES "
                f"(empty list is acceptable; missing attribute is not)"
            )
        self._audit = audit
        self._sql = sql_conn
        self._kv = kv_client
        self._canary = canary_scanner or CanaryScanner()

    @abstractmethod
    def fetch_table(self, table: str) -> Iterator[dict]: ...

    @abstractmethod
    def recipe_for(self, table: str) -> ETLRecipe: ...

    def _scan_record(self, record: dict, fields: list[str]) -> None:
        """Raise CUIBoundaryViolation if any canary field hits."""
        for fld in fields:
            value = record.get(fld)
            if isinstance(value, str) and self._canary.scan_text(value):
                raise CUIBoundaryViolation(
                    f"canary phrase detected in field {fld!r}; "
                    f"aborting table sync"
                )

    def run(self) -> dict[str, str]:
        results: dict[str, str] = {}
        for table in self.TABLES:
            qualified = f"raw_{self.CATEGORY}.{table}"
            if CUIGate.should_skip(table, self.CUI_SENSITIVE_TABLES, self._sql):
                log.info("CUI skip: %s", qualified)
                self._audit.emit(make_event(
                    verb="etl.skip.cui",
                    resource_type=qualified,
                    outcome="success",
                    metadata={
                        "reason": "cui_handling_required tenant present",
                    },
                ))
                results[table] = "skipped_cui"
                continue

            try:
                cur = self._sql.cursor()
                cur.execute(f"TRUNCATE TABLE {qualified}")  # D-01
                canary_fields = self.CUI_CANARY_FIELDS.get(table, [])
                recipe = self.recipe_for(table)
                record_count = 0
                for record in self.fetch_table(table):
                    if canary_fields:
                        self._scan_record(record, canary_fields)
                    sql, params = recipe.compile(
                        record,
                        kv_client=self._kv,
                        tenant_id=str(record.get("cw_company_id", "")),
                    )
                    bound = list(params.values())
                    if bound:
                        cur.execute(sql, *bound)
                    else:
                        cur.execute(sql)
                    record_count += 1
                self._sql.commit()
                self._audit.emit(make_event(
                    verb="etl.write",
                    resource_type=qualified,
                    outcome="success",
                    metadata={"record_count": record_count},
                ))
                results[table] = "success"
            except AuditEmitError:
                # CLAUDE.md fail-closed: audit failure propagates.
                raise
            except ETLError as exc:
                log.error("ETL error on %s: %s", qualified, exc)
                try:
                    self._sql.rollback()
                except Exception:
                    pass
                self._audit.emit(make_event(
                    verb="etl.write",
                    resource_type=qualified,
                    outcome="failure",
                    metadata={
                        "error_type": type(exc).__name__,
                        "error_message": str(exc),
                    },
                ))
                results[table] = "failed"
                continue  # D-02: next table
            except Exception as exc:
                log.exception("unexpected error on %s", qualified)
                try:
                    self._sql.rollback()
                except Exception:
                    pass
                self._audit.emit(make_event(
                    verb="etl.write",
                    resource_type=qualified,
                    outcome="failure",
                    metadata={
                        "error_type": type(exc).__name__,
                        "error_message": repr(exc)[:200],
                    },
                ))
                results[table] = "failed"
                continue
        return results
