"""AUDIT-03: WORM container 6-year retention is locked at container creation
and cannot be shortened by any role.

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
STORAGE_ACCT = os.environ.get("WORM_STORAGE_ACCOUNT", "stbarywormdev")
CONTAINER = os.environ.get("WORM_CONTAINER", "audit")
EXPECTED_RETENTION_DAYS = 2190

pytestmark = pytest.mark.skipif(
    not AZURE_SUB,
    reason="AZURE_SUBSCRIPTION_ID not set; integration tests require deployed env",
)


def _az_json(*args: str) -> dict:
    """Run az with --output json and return parsed dict (or {} if empty)."""
    result = subprocess.run(
        ["az", *args, "--output", "json"],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout) if result.stdout.strip() else {}


def test_immutability_policy_locked_at_6_years() -> None:
    """T-1-06-01 / AUDIT-03: production WORM container retention locked at 2190 days."""
    policy = _az_json(
        "storage",
        "container",
        "immutability-policy",
        "show",
        "--account-name",
        STORAGE_ACCT,
        "--container-name",
        CONTAINER,
    )
    assert policy.get("state") == "Locked", (
        f"WORM policy state must be 'Locked', got: {policy.get('state')!r}"
    )
    assert policy.get("immutabilityPeriodSinceCreationInDays") == EXPECTED_RETENTION_DAYS, (
        f"Retention days: {policy.get('immutabilityPeriodSinceCreationInDays')} "
        f"!= {EXPECTED_RETENTION_DAYS}"
    )
    assert policy.get("allowProtectedAppendWrites") is True, (
        "Append writes must be allowed during retention so audit chain can extend"
    )


def test_locked_policy_cannot_be_shortened() -> None:
    """T-1-06-02: attempt to PATCH retention to 30 days. Must fail (Azure refuses)."""
    result = subprocess.run(
        [
            "az",
            "storage",
            "container",
            "immutability-policy",
            "extend",
            "--account-name",
            STORAGE_ACCT,
            "--container-name",
            CONTAINER,
            "--period",
            "30",
        ],
        capture_output=True,
        text=True,
    )
    # Azure must refuse to shorten a locked policy. Any nonzero exit is acceptable;
    # a zero exit means the lock did NOT hold (AUDIT-03 broken).
    assert result.returncode != 0, (
        "Locked WORM policy was shortenable! AUDIT-03 broken. "
        f"stdout: {result.stdout!r} stderr: {result.stderr!r}"
    )


def test_storage_account_is_private() -> None:
    """T-1-06-03: WORM storage account has no public surface, AAD-only access."""
    acct = _az_json(
        "storage",
        "account",
        "show",
        "--name",
        STORAGE_ACCT,
        "--resource-group",
        RG_AUDIT,
    )
    assert acct["publicNetworkAccess"] == "Disabled", acct.get("publicNetworkAccess")
    assert acct["allowBlobPublicAccess"] is False, acct.get("allowBlobPublicAccess")
    assert acct["allowSharedKeyAccess"] is False, "AAD-only access required (no shared key)"
    assert acct["minimumTlsVersion"] == "TLS1_2", acct.get("minimumTlsVersion")
    assert acct["networkRuleSet"]["defaultAction"] == "Deny", acct["networkRuleSet"]


def test_test_container_account_is_deleted() -> None:
    """Pitfall 7: after test-container lock validation, the test storage account
    must no longer exist before plan 01 phase exits.
    """
    test_acct = os.environ.get("WORM_TEST_STORAGE_NAME", "stbarywormtest1")
    result = subprocess.run(
        [
            "az",
            "storage",
            "account",
            "show",
            "--name",
            test_acct,
            "--resource-group",
            RG_AUDIT,
            "--output",
            "json",
        ],
        capture_output=True,
        text=True,
    )
    # Expect failure (account does not exist).
    assert result.returncode != 0, (
        f"Test WORM storage account {test_acct!r} still exists after Pitfall 7 "
        "validation. Delete it manually before phase exit."
    )
