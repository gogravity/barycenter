"""Audit sinks: Logs Analytics (DCR Logs Ingestion API) + WORM blob append. Plan 07 implements."""
from barycenter.audit.models import AuditEvent


class LogsAnalyticsSink:
    def __init__(self, ingestion_client, dcr_id: str, stream_name: str):
        self._client = ingestion_client
        self._dcr_id = dcr_id
        self._stream = stream_name

    def upload(self, event: AuditEvent) -> None:
        """Upload one event via DCR. Raises on any error (no swallowing). Plan 07 implements."""
        raise NotImplementedError("Implemented in plan 07")


class WormBlobSink:
    def __init__(self, append_blob_client):
        self._client = append_blob_client

    def append(self, payload_bytes: bytes) -> None:
        """Append-block to WORM container. Raises on any error. Plan 07 implements."""
        raise NotImplementedError("Implemented in plan 07")
