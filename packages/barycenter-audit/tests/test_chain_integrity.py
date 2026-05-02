"""Adversarial chain-integrity tests. Implementation in plan 07."""
from datetime import datetime, timezone
from uuid import uuid4
import pytest
from barycenter.audit import AuditClient, AuditEvent, ChainIntegrityError, GENESIS_HASH


def _make_event(verb: str = "test.event") -> AuditEvent:
    return AuditEvent(
        event_id=uuid4(), occurred_at=datetime.now(timezone.utc),
        actor_id="mi-bary-etl", actor_type="service",
        verb=verb, resource_type="test", outcome="success",
    )


def _setup_mock_chain(mock_sql, head: str = GENESIS_HASH):
    """Configure mock_sql.cursor() so SELECT returns ``head`` and UPDATE
    reports rowcount=1. Returns the cursor for further customization."""
    cur = mock_sql.cursor.return_value
    cur.fetchone.return_value = (head,)
    cur.rowcount = 1
    return cur


def test_genesis_hash_is_64_zero_hex():
    assert GENESIS_HASH == "0" * 64
    assert len(GENESIS_HASH) == 64


def test_emit_updates_chain_state_on_success(mock_sql, mock_la_sink, mock_worm_sink):
    cur = _setup_mock_chain(mock_sql)
    client = AuditClient(mock_sql, mock_la_sink, mock_worm_sink)
    ev = client.emit(_make_event())
    assert ev.prior_digest == GENESIS_HASH
    assert ev.this_digest is not None and len(ev.this_digest) == 64
    # UPDATE on chain_state was called
    update_calls = [
        c for c in cur.execute.call_args_list if "UPDATE" in str(c).upper()
    ]
    assert update_calls, "UPDATE on chain_state was never called"
    # commit was called exactly once on success
    mock_sql.commit.assert_called_once()


def test_chain_advances_across_consecutive_emits(mock_sql, mock_la_sink, mock_worm_sink):
    """Second emit's prior_digest equals first's this_digest."""
    cur = _setup_mock_chain(mock_sql, GENESIS_HASH)
    client = AuditClient(mock_sql, mock_la_sink, mock_worm_sink)
    ev1 = client.emit(_make_event("test.event.1"))
    # Simulate chain_state advance by reconfiguring fetchone
    cur.fetchone.return_value = (ev1.this_digest,)
    ev2 = client.emit(_make_event("test.event.2"))
    assert ev2.prior_digest == ev1.this_digest
    assert ev2.this_digest != ev1.this_digest


def test_chain_breaks_on_tamper():
    """validate_chain detects a tampered ``this_digest`` field."""
    from barycenter.audit.chain import validate_chain, canonicalize_json, compute_digest

    # Build a valid two-entry chain.
    payload1 = {
        "event_id": "11111111-1111-4111-8111-111111111111",
        "verb": "a", "actor_id": "mi", "outcome": "success",
        "prior_digest": GENESIS_HASH,
    }
    canon1 = canonicalize_json(payload1)
    digest1 = compute_digest(GENESIS_HASH, canon1)
    entry1 = dict(payload1)
    entry1["this_digest"] = digest1
    raw1 = canonicalize_json(entry1)

    payload2 = {
        "event_id": "22222222-2222-4222-8222-222222222222",
        "verb": "b", "actor_id": "mi", "outcome": "success",
        "prior_digest": digest1,
    }
    canon2 = canonicalize_json(payload2)
    digest2 = compute_digest(digest1, canon2)
    entry2 = dict(payload2)
    entry2["this_digest"] = digest2
    raw2 = canonicalize_json(entry2)

    # Sanity: untampered chain validates.
    assert validate_chain([raw1, raw2]) == 2

    # Tamper: flip a character in entry2's this_digest.
    bad_entry = dict(entry2)
    bad_entry["this_digest"] = ("f" if digest2[0] != "f" else "0") + digest2[1:]
    bad_raw2 = canonicalize_json(bad_entry)
    with pytest.raises(ChainIntegrityError):
        validate_chain([raw1, bad_raw2])
