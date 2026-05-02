"""Audit event Pydantic v2 model. Required fields satisfy HIPAA §164.312(b)."""
from datetime import datetime
from typing import Any, Dict, Literal, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

AuditOutcome = Literal["success", "failure", "denied"]
ActorType = Literal["user", "service"]


class AuditEvent(BaseModel):
    """A single audit event. Constructed by callers; chain digests filled by AuditClient.emit."""
    model_config = ConfigDict(extra="forbid", frozen=False)

    event_id: UUID
    occurred_at: datetime
    actor_id: str
    actor_type: ActorType
    verb: str
    resource_type: str
    resource_id: Optional[str] = None
    outcome: AuditOutcome
    tenant_id: Optional[str] = None
    prior_digest: Optional[str] = None     # 64-hex SHA-256, set by emit()
    this_digest: Optional[str] = None      # 64-hex SHA-256, set by emit()
    metadata: Dict[str, Any] = Field(default_factory=dict)  # Pitfall 9 forward-extension
