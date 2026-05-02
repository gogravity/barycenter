"""Audit sinks: Logs Analytics (DCR Logs Ingestion API) + WORM blob append.

Both sinks are thin adapters over the official Azure SDK clients
(``azure.monitor.ingestion.LogsIngestionClient`` and
``azure.storage.blob.AppendBlobClient``). Per CLAUDE.md (D-06): no
exception swallowing — every underlying SDK error propagates verbatim and
is converted to ``FailClosedAbort`` by ``AuditClient.emit``.
"""
from __future__ import annotations

from barycenter.audit.models import AuditEvent


class LogsAnalyticsSink:
    """Wraps a LogsIngestionClient for the Custom-AuditEvents stream."""

    def __init__(self, ingestion_client, dcr_immutable_id: str, stream_name: str):
        self._client = ingestion_client
        self._dcr_id = dcr_immutable_id
        self._stream = stream_name

    def upload(self, event: AuditEvent) -> None:
        """Upload one event via the DCR Logs Ingestion API.

        Raises whatever the underlying client raises (no swallowing).
        ``mode='json'`` ensures UUID/datetime are rendered as their string
        forms — matching the Custom-AuditEvents column types.
        """
        payload = event.model_dump(mode="json")
        self._client.upload(
            rule_id=self._dcr_id,
            stream_name=self._stream,
            logs=[payload],
        )


class WormBlobSink:
    """Wraps an AppendBlobClient for the immutable audit container.

    The caller is responsible for newline framing (the SDK ndjson contract
    is "one event per line"). ``append`` writes the bytes verbatim to keep
    the canonical-JSON byte sequence intact for chain validation.
    """

    def __init__(self, append_blob_client):
        self._client = append_blob_client

    def append(self, payload_bytes: bytes) -> None:
        """Append the given bytes to the WORM container.

        Raises whatever the underlying client raises (no swallowing).
        """
        self._client.append_block(payload_bytes)
