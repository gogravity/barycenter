"""Internal helpers for constructing AuditEvent instances with the schema
defined in barycenter.audit.models. Centralised so framework modules emit
consistent events; not part of the public ETL surface.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from barycenter.audit import AuditEvent

ETL_ACTOR_ID = "mi-bary-etl"
ETL_ACTOR_TYPE = "service"


def make_event(
    *,
    verb: str,
    resource_type: str,
    outcome: str = "success",
    resource_id: str | None = None,
    tenant_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    actor_id: str = ETL_ACTOR_ID,
    actor_type: str = ETL_ACTOR_TYPE,
) -> AuditEvent:
    return AuditEvent(
        event_id=uuid4(),
        occurred_at=datetime.now(timezone.utc),
        actor_id=actor_id,
        actor_type=actor_type,
        verb=verb,
        resource_type=resource_type,
        resource_id=resource_id,
        outcome=outcome,
        tenant_id=tenant_id,
        metadata=metadata or {},
    )
