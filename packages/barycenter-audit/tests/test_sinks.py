"""Unit tests for the LA + WORM sinks (plan 07 task 3).

Both sinks must:
  - call the underlying Azure SDK client with the documented args
  - propagate any underlying exception verbatim (no swallowing — D-06)
"""
from datetime import datetime, timezone
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from barycenter.audit import AuditEvent
from barycenter.audit.sinks import LogsAnalyticsSink, WormBlobSink


def _make_event() -> AuditEvent:
    return AuditEvent(
        event_id=uuid4(), occurred_at=datetime.now(timezone.utc),
        actor_id="mi-bary-etl", actor_type="service",
        verb="test.event", resource_type="raw_cw.companies", outcome="success",
    )


def test_la_sink_upload_calls_underlying_client():
    ingestion = MagicMock(name="LogsIngestionClient")
    sink = LogsAnalyticsSink(ingestion, "dcr-immutable-id", "Custom-AuditEvents")
    sink.upload(_make_event())
    ingestion.upload.assert_called_once()
    _args, kwargs = ingestion.upload.call_args
    assert kwargs.get("rule_id") == "dcr-immutable-id"
    assert kwargs.get("stream_name") == "Custom-AuditEvents"
    payload = kwargs.get("logs")
    assert isinstance(payload, list) and len(payload) == 1
    assert payload[0]["verb"] == "test.event"


def test_la_sink_propagates_exceptions():
    ingestion = MagicMock(name="LogsIngestionClient")
    ingestion.upload.side_effect = RuntimeError("network")
    sink = LogsAnalyticsSink(ingestion, "dcr-id", "Custom-AuditEvents")
    with pytest.raises(RuntimeError, match="network"):
        sink.upload(_make_event())


def test_worm_sink_append_calls_append_block_verbatim():
    blob = MagicMock(name="AppendBlobClient")
    sink = WormBlobSink(blob)
    sink.append(b'{"event":1}\n')
    blob.append_block.assert_called_once_with(b'{"event":1}\n')


def test_worm_sink_propagates_exceptions():
    blob = MagicMock(name="AppendBlobClient")
    blob.append_block.side_effect = RuntimeError("storage")
    sink = WormBlobSink(blob)
    with pytest.raises(RuntimeError, match="storage"):
        sink.append(b"x")
