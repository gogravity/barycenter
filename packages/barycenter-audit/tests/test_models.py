"""AuditEvent schema validation tests (passes today; no impl required)."""
from datetime import datetime, timezone
from uuid import uuid4
import pytest
from pydantic import ValidationError
from barycenter.audit import AuditEvent


def _valid_kwargs():
    return dict(
        event_id=uuid4(),
        occurred_at=datetime.now(timezone.utc),
        actor_id="mi-bary-etl",
        actor_type="service",
        verb="raw_cw.companies.write",
        resource_type="raw_cw.companies",
        outcome="success",
    )


def test_valid_event_constructs():
    ev = AuditEvent(**_valid_kwargs())
    assert ev.metadata == {}
    assert ev.prior_digest is None and ev.this_digest is None


@pytest.mark.parametrize("missing", ["event_id", "occurred_at", "actor_id", "actor_type", "verb", "resource_type", "outcome"])
def test_missing_required_field_rejected(missing):
    kw = _valid_kwargs()
    kw.pop(missing)
    with pytest.raises(ValidationError):
        AuditEvent(**kw)


def test_metadata_accepts_arbitrary_extension():
    kw = _valid_kwargs()
    kw["metadata"] = {"future_field_a": 1, "future_field_b": ["x", "y"]}
    ev = AuditEvent(**kw)
    assert ev.metadata["future_field_a"] == 1


def test_invalid_outcome_rejected():
    kw = _valid_kwargs()
    kw["outcome"] = "ok"
    with pytest.raises(ValidationError):
        AuditEvent(**kw)


def test_extra_fields_rejected():
    kw = _valid_kwargs()
    kw["bogus"] = "x"
    with pytest.raises(ValidationError):
        AuditEvent(**kw)
