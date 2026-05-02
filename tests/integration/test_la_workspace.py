"""LA workspace exists, retains 90 days, AuditEvents_CL custom table present
with the expected schema (Pitfall 9 — metadata column is dynamic).

Runs against a deployed environment. Requires AZURE_SUBSCRIPTION_ID + az login.
Locally without AZURE_SUBSCRIPTION_ID, all tests skip cleanly.
"""
from __future__ import annotations

import json
import os
import subprocess

import pytest

AZURE_SUB = os.environ.get("AZURE_SUBSCRIPTION_ID")
RG_AUDIT = os.environ.get("RG_AUDIT", "rg-barycenter-dev")
WORKSPACE = os.environ.get("LA_WORKSPACE", "log-bary-dev")
DCR_NAME = os.environ.get("DCR_NAME", "dcr-bary-audit-dev")

EXPECTED_COLUMNS = {
    "TimeGenerated",
    "event_id",
    "occurred_at",
    "actor_id",
    "actor_type",
    "verb",
    "resource_type",
    "resource_id",
    "outcome",
    "tenant_id",
    "prior_digest",
    "this_digest",
    "metadata",
}

pytestmark = pytest.mark.skipif(
    not AZURE_SUB,
    reason="AZURE_SUBSCRIPTION_ID not set; integration tests require deployed env",
)


def _az_json(*args: str) -> dict:
    result = subprocess.run(
        ["az", *args, "--output", "json"],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout) if result.stdout.strip() else {}


def test_workspace_exists_with_90_day_retention() -> None:
    ws = _az_json(
        "monitor",
        "log-analytics",
        "workspace",
        "show",
        "--resource-group",
        RG_AUDIT,
        "--workspace-name",
        WORKSPACE,
    )
    assert ws["retentionInDays"] == 90, (
        f"LA retentionInDays must be 90, got: {ws.get('retentionInDays')}"
    )


def test_audit_events_custom_table_exists_with_metadata_dynamic() -> None:
    """T-1-06-04 + Pitfall 9: schema columns match the AuditEvent model and
    metadata is `dynamic` so forward-extension of AuditEvent does not require
    a coordinated DCR + table migration.
    """
    table = _az_json(
        "monitor",
        "log-analytics",
        "workspace",
        "table",
        "show",
        "--resource-group",
        RG_AUDIT,
        "--workspace-name",
        WORKSPACE,
        "--name",
        "AuditEvents_CL",
    )
    cols = {c["name"]: c["type"] for c in table["schema"]["columns"]}
    missing = EXPECTED_COLUMNS - set(cols.keys())
    assert not missing, f"Missing columns in AuditEvents_CL: {sorted(missing)}"
    # Pitfall 9: metadata MUST be dynamic.
    assert cols["metadata"] == "dynamic", (
        f"metadata column type must be 'dynamic' (Pitfall 9), got: {cols['metadata']!r}"
    )


def test_dcr_exists_and_targets_workspace() -> None:
    dcr = _az_json(
        "monitor",
        "data-collection",
        "rule",
        "show",
        "--resource-group",
        RG_AUDIT,
        "--name",
        DCR_NAME,
    )
    streams = dcr["properties"]["streamDeclarations"]
    assert "Custom-AuditEvents" in streams, (
        f"DCR must declare Custom-AuditEvents stream; got: {list(streams.keys())}"
    )
    destinations = dcr["properties"]["destinations"]["logAnalytics"]
    assert any(d["name"] == "la-dest" for d in destinations), (
        f"DCR must have la-dest LA destination; got: {[d.get('name') for d in destinations]}"
    )
