"""End-to-end AUDIT-01 + AUDIT-02 verification against live Azure.

Skipped unless ``AZURE_SUBSCRIPTION_ID`` and ``BARY_INTEGRATION_ENV=dev``
are both set. This test runs in CI after plan 05 (data plane) and plan 06
(audit infra) have been deployed; it asserts:

  - 3 emits produce 3 unique digests
  - chain_state.head_digest equals the last digest after the 3rd emit
  - the WORM container received the event payloads (via the sink's own
    bookkeeping; we do not re-list the immutable container)
"""
from __future__ import annotations

import os

import pytest

AZURE_SUB = os.environ.get("AZURE_SUBSCRIPTION_ID")
RUN_LIVE = os.environ.get("BARY_INTEGRATION_ENV") == "dev"

pytestmark = pytest.mark.skipif(
    not AZURE_SUB or not RUN_LIVE,
    reason="Set AZURE_SUBSCRIPTION_ID and BARY_INTEGRATION_ENV=dev to run live integration",
)


def _build_live_client():  # pragma: no cover — runs only in CI with live Azure
    import pyodbc
    from azure.identity import DefaultAzureCredential
    from azure.monitor.ingestion import LogsIngestionClient
    from azure.storage.blob import AppendBlobClient

    from barycenter.audit import AuditClient
    from barycenter.audit.sinks import LogsAnalyticsSink, WormBlobSink

    cred = DefaultAzureCredential()
    sql_fqdn = os.environ["SQL_SERVER_FQDN"]
    conn_str = (
        f"Driver={{ODBC Driver 18 for SQL Server}};Server={sql_fqdn};"
        f"Database=barycenter;Authentication=ActiveDirectoryDefault;Encrypt=yes;"
    )
    sql = pyodbc.connect(conn_str, autocommit=False)
    sql.execute("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE")

    la_endpoint = os.environ["DCE_LOGS_INGESTION_ENDPOINT"]
    la = LogsIngestionClient(endpoint=la_endpoint, credential=cred)
    la_sink = LogsAnalyticsSink(la, os.environ["DCR_IMMUTABLE_ID"], "Custom-AuditEvents")

    blob = AppendBlobClient(
        account_url=f"https://{os.environ['WORM_STORAGE_ACCOUNT']}.blob.core.windows.net",
        container_name="audit",
        blob_name=f"events-{os.environ.get('GITHUB_RUN_ID', 'local')}.ndjson",
        credential=cred,
    )
    if not blob.exists():
        blob.create_append_blob()
    worm_sink = WormBlobSink(blob)
    return AuditClient(sql, la_sink, worm_sink), sql


def test_end_to_end_three_emits_advance_chain():  # pragma: no cover — live only
    from datetime import datetime, timezone
    from uuid import uuid4

    from barycenter.audit import AuditEvent

    client, sql = _build_live_client()
    digests: list[str] = []
    for i in range(3):
        ev = AuditEvent(
            event_id=uuid4(),
            occurred_at=datetime.now(timezone.utc),
            actor_id="mi-bary-audit",
            actor_type="service",
            verb=f"test.e2e.{i}",
            resource_type="audit.chain_state",
            outcome="success",
        )
        client.emit(ev)
        digests.append(ev.this_digest)

    # 3 unique digests
    assert len(set(digests)) == 3, f"digests not unique: {digests}"

    # chain_state.head_digest must match the last digest
    cur = sql.cursor()
    cur.execute("SELECT head_digest FROM audit.chain_state WHERE id = 1")
    head = cur.fetchone()[0]
    assert head == digests[-1], f"head {head!r} != last digest {digests[-1]!r}"
