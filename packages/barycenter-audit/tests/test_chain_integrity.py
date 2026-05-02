"""Adversarial chain-integrity tests. Implementation in plan 07."""
from datetime import datetime, timezone
from uuid import uuid4
import pytest
from barycenter.audit import AuditClient, AuditEvent, ChainIntegrityError, GENESIS_HASH


def _make_event(verb: str) -> AuditEvent:
    return AuditEvent(
        event_id=uuid4(), occurred_at=datetime.now(timezone.utc),
        actor_id="mi-bary-etl", actor_type="service",
        verb=verb, resource_type="test", outcome="success",
    )


@pytest.mark.xfail(strict=False, reason="impl lands in plan 07")
def test_chain_breaks_on_tamper(mock_sql, mock_la_sink, mock_worm_sink):
    client = AuditClient(mock_sql, mock_la_sink, mock_worm_sink)
    client.emit(_make_event("test.event.1"))
    client.emit(_make_event("test.event.2"))
    # plan 07 will provide validate_chain helper; placeholder shape:
    from barycenter.audit.chain import compute_digest  # noqa: F401
    # Tamper-detect assertion lives here once impl exists
    raise ChainIntegrityError("placeholder")


def test_genesis_hash_is_64_zero_hex():
    assert GENESIS_HASH == "0" * 64
    assert len(GENESIS_HASH) == 64
