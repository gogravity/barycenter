"""CLI entry: ``python -m barycenter.etl.run --adapter <name> [--dry-run]``.

Wires Azure managed identity -> SQL + KV + audit -> CW client -> CWManageAdapter.run.
Per D-08 this runs in GitHub Actions; per D-03 the OIDC federated credential on
``mi-bary-etl`` is the auth path. Local dev uses DefaultAzureCredential as well.

Dry-run mode prints the planned actions without importing Azure SDKs or pyodbc,
so the workflow can exercise the entry point in CI without provisioning secrets.
"""
from __future__ import annotations

import argparse
import logging
import os
import sys


def _build_cw_adapter(audit, sql_conn, kv_client):
    from barycenter.etl.adapters.connectwise.adapter import CWManageAdapter
    from barycenter.etl.adapters.connectwise.auth import (
        BasicAuthStrategy,
        OAuthClientCredsStrategy,
    )
    from barycenter.etl.adapters.connectwise.client import CWManageClient

    server_url = kv_client.get_secret("api-cw-server-url").value
    auth_mode = (os.environ.get("CW_AUTH_MODE", "basic") or "basic").lower()
    if auth_mode == "oauth":
        client_id = kv_client.get_secret("api-cw-client-id").value
        client_secret = kv_client.get_secret("api-cw-client-secret").value
        token_endpoint = kv_client.get_secret("api-cw-token-endpoint").value
        auth = OAuthClientCredsStrategy(token_endpoint, client_id, client_secret)
    else:
        company = kv_client.get_secret("api-cw-company").value
        public_key = kv_client.get_secret("api-cw-public-key").value
        private_key = kv_client.get_secret("api-cw-private-key").value
        client_id = kv_client.get_secret("api-cw-client-id").value
        auth = BasicAuthStrategy(company, public_key, private_key, client_id)
    cw = CWManageClient(server_url, auth)
    return CWManageAdapter(audit, sql_conn, kv_client, cw_client=cw)


ADAPTERS = {"connectwise": _build_cw_adapter}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Barycenter ETL runner")
    ap.add_argument("--adapter", required=True, choices=list(ADAPTERS))
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned actions without connecting to CW or SQL",
    )
    args = ap.parse_args(argv)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    if args.dry_run:
        print(f"DRY RUN: would invoke {args.adapter} adapter")
        print(
            "  TABLES: companies, agreements, tickets, configurations, time_entries"
        )
        print(f"  Auth mode: {os.environ.get('CW_AUTH_MODE', 'basic')}")
        print(
            "  Audit path: barycenter.audit.AuditClient.emit() (fail-closed)"
        )
        return 0

    # Real path: import lazily so dry-run doesn't require Azure SDKs.
    import struct

    import pyodbc  # type: ignore[import-not-found]
    from azure.identity import DefaultAzureCredential
    from azure.keyvault.secrets import SecretClient

    from barycenter.audit import AuditClient
    from barycenter.audit.sinks import LogsAnalyticsSink, WormBlobSink

    kv_url = os.environ["KEY_VAULT_URL"]
    sql_conn_str = os.environ["SQL_CONNECTION_STRING"]
    # AZURE_CLIENT_ID selects mi-bary-etl (raw_cw/pseudo/ai_zone access).
    cred = DefaultAzureCredential()
    kv = SecretClient(vault_url=kv_url, credential=cred)

    # Use azure-identity to acquire the SQL token — ODBC Driver 18's built-in
    # Authentication=ActiveDirectoryMsi does not reliably detect the
    # IDENTITY_ENDPOINT used by Container Apps (it looks for the Azure VM IMDS
    # instead). Passing the token via SQL_COPT_SS_ACCESS_TOKEN bypasses the
    # driver's MSI path and uses the already-working DefaultAzureCredential.
    SQL_COPT_SS_ACCESS_TOKEN = 1256

    def _make_sql_conn(token_cred) -> "pyodbc.Connection":
        """Open a SQL connection using a managed-identity token."""
        _tok = token_cred.get_token("https://database.windows.net/.default").token
        _tok_bytes = _tok.encode("utf-16-le")
        _tok_struct = struct.pack("<I", len(_tok_bytes)) + _tok_bytes
        _base = ";".join(
            p for p in sql_conn_str.split(";")
            if not p.strip().lower().startswith("authentication")
        )
        return pyodbc.connect(_base, attrs_before={SQL_COPT_SS_ACCESS_TOKEN: _tok_struct})

    sql = _make_sql_conn(cred)

    # mi-bary-etl has DENY on the audit schema; audit.chain_state must be
    # accessed via the mi-bary-audit identity (SELECT/UPDATE only).
    # AUDIT_CLIENT_ID is injected by the CAJ alongside AZURE_CLIENT_ID.
    from azure.identity import ManagedIdentityCredential
    audit_client_id = os.environ.get("AUDIT_CLIENT_ID", "")
    audit_cred = (
        ManagedIdentityCredential(client_id=audit_client_id)
        if audit_client_id
        else cred  # fallback for local dev (single identity)
    )
    audit_sql = _make_sql_conn(audit_cred)

    # Sink construction follows Phase 1 conventions: env-driven SDK clients
    # injected into the thin sink wrappers. If a future ops change relocates
    # these helpers, update here in coordination with barycenter-audit.
    from azure.monitor.ingestion import LogsIngestionClient
    from azure.storage.blob import BlobClient

    dce_endpoint = os.environ["DCE_LOGS_INGESTION_ENDPOINT"]
    dcr_id = os.environ["DCR_IMMUTABLE_ID"]
    stream = os.environ.get("DCR_STREAM_NAME", "Custom-AuditEvents_CL")
    worm_url = os.environ["WORM_APPEND_BLOB_URL"]
    # All three audit sinks use audit_cred (mi-bary-audit):
    # - LA: Monitoring Metrics Publisher on DCR granted to mi-bary-audit (Bicep)
    # - WORM: Storage Blob Data Contributor on stbarywormdev granted to mi-bary-audit
    # - SQL chain_state: SELECT/UPDATE granted to mi-bary-audit (002_audit_grants.sql)
    la = LogsAnalyticsSink(
        LogsIngestionClient(endpoint=dce_endpoint, credential=audit_cred),
        dcr_immutable_id=dcr_id,
        stream_name=stream,
    )
    # Ensure the append blob exists before the first write. create_append_blob()
    # is idempotent when the blob already exists — ResourceExistsError is expected
    # on every run after the first and is not a fault condition.
    from azure.core.exceptions import ResourceExistsError
    # azure-storage-blob>=12.24 removed AppendBlobClient from the public API;
    # append blob operations (create_append_blob, append_block) are now on BlobClient.
    _worm_blob_client = BlobClient.from_blob_url(worm_url, credential=audit_cred)
    try:
        _worm_blob_client.create_append_blob()
    except ResourceExistsError:
        pass  # already exists — normal on every run after the first
    worm = WormBlobSink(_worm_blob_client)
    audit = AuditClient(audit_sql, la, worm)
    adapter = ADAPTERS[args.adapter](audit, sql, kv)
    results = adapter.run()
    print(f"Results: {results}")
    any_failed = any(v == "failed" for v in results.values())
    return 1 if any_failed else 0


if __name__ == "__main__":
    sys.exit(main())
