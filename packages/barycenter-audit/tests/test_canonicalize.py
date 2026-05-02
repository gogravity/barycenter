"""Canonicalization + digest unit tests (plan 07 task 1).

Property tests for canonicalize_json and compute_digest. These are pure
functions — no I/O — so they constitute the foundation of the audit chain.
"""
from datetime import datetime, timezone
from uuid import UUID
import hashlib
import pytest
from barycenter.audit.chain import canonicalize_json, compute_digest, GENESIS_HASH


def test_empty_object():
    assert canonicalize_json({}) == "{}"


def test_keys_sorted_lexicographically():
    assert canonicalize_json({"b": 1, "a": 2}) == '{"a":2,"b":1}'


def test_arrays_not_reordered():
    assert canonicalize_json({"x": [3, 1, 2]}) == '{"x":[3,1,2]}'


def test_nested_objects_sorted_recursively():
    assert canonicalize_json({"o": {"z": 1, "a": 2}, "a": 1}) == '{"a":1,"o":{"a":2,"z":1}}'


def test_uuid_rendered_as_string():
    uid = UUID("11111111-1111-4111-8111-111111111111")
    assert canonicalize_json({"id": uid}) == '{"id":"11111111-1111-4111-8111-111111111111"}'


def test_datetime_isoformat_utc():
    dt = datetime(2026, 5, 2, 19, 32, 42, tzinfo=timezone.utc)
    assert canonicalize_json({"t": dt}) == '{"t":"2026-05-02T19:32:42+00:00"}'


def test_none_bool_rendered_as_json_literals():
    assert canonicalize_json({"a": None, "b": True, "c": False}) == '{"a":null,"b":true,"c":false}'


def test_unsupported_type_raises_value_error():
    with pytest.raises(ValueError):
        canonicalize_json({"s": {1, 2, 3}})


def test_canonicalization_is_stable_across_invocations():
    payload = {"b": 1, "a": [{"y": 2, "x": 1}], "c": "value"}
    assert canonicalize_json(payload) == canonicalize_json(payload)


def test_compute_digest_matches_sha256():
    prior = "0" * 64
    canonical = '{"a":1}'
    expected = hashlib.sha256((prior + canonical).encode("utf-8")).hexdigest()
    assert compute_digest(prior, canonical) == expected
    assert len(compute_digest(prior, canonical)) == 64
    assert compute_digest(prior, canonical) == compute_digest(prior, canonical).lower()
