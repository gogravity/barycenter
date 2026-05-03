"""Pydantic models for CW Manage responses. Drift-tolerant (extra='ignore') with logging.

Per Pitfall 6: every unknown field that arrives is recorded once per
(model, field) tuple via ``log_drift``. The model still ignores it (so a
benign CW additive change does not break the sync), but the drift report
makes silent schema changes visible.

NOTE: ``CWTicket`` deliberately does NOT declare ``body``,
``initialDescription``, ``resolution``, or ``initialInternalAnalysis``.
``extra='ignore'`` discards them; the body-strip rule is enforced at the DDL
level (Pitfall 1) and at the recipe level (drop primitive).
"""
from __future__ import annotations

import logging
from datetime import datetime

from pydantic import BaseModel, ConfigDict

log = logging.getLogger("barycenter.etl.cw.drift")
_seen_drift: set[tuple[str, str]] = set()


def log_drift(model_name: str, unknown_fields: set[str]) -> None:
    """Record each (model, field) drift exactly once per process."""
    for f in unknown_fields:
        key = (model_name, f)
        if key not in _seen_drift:
            _seen_drift.add(key)
            log.warning(
                "CW response drift: %s.%s observed (model uses extra='ignore')",
                model_name,
                f,
            )


class _CWBase(BaseModel):
    """Drift-tolerant base for inbound CW JSON shapes (Pitfall 6)."""

    model_config = ConfigDict(extra="ignore")


class CWInfo(_CWBase):
    lastUpdated: datetime | None = None
    dateEntered: datetime | None = None


class CWCompany(_CWBase):
    id: int
    name: str
    addressLine1: str | None = None
    city: str | None = None
    state: str | None = None
    types: list[dict] | None = None
    customFields: dict | None = None
    info: CWInfo | None = None


class CWAgreement(_CWBase):
    id: int
    company: dict
    name: str
    type: dict | None = None
    startDate: datetime | None = None
    endDate: datetime | None = None
    billingCycle: dict | None = None
    info: CWInfo | None = None


class CWTicket(_CWBase):
    """Ticket metadata only.

    body / initialDescription / resolution / initialInternalAnalysis are
    deliberately NOT declared. extra='ignore' drops them; drift logger
    records their occurrence so a CW schema change is visible.
    """

    id: int
    company: dict
    summary: str | None = None
    status: dict | None = None
    priority: dict | None = None
    type: dict | None = None
    info: CWInfo | None = None


class CWConfiguration(_CWBase):
    id: int
    company: dict
    name: str | None = None
    type: dict | None = None
    manufacturer: dict | None = None
    modelNumber: str | None = None
    serialNumber: str | None = None
    status: dict | None = None
    installationDate: datetime | None = None
    info: CWInfo | None = None


class CWTimeEntry(_CWBase):
    id: int
    company: dict
    timeStart: datetime | None = None
    actualHours: float | None = None
    billableOption: str | None = None
    info: CWInfo | None = None
