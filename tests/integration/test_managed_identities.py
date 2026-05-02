"""IDENT-03: assert the 4 canonical managed identities exist with no long-lived secrets.
IDENT-02/05: assert mi-bary-admin has zero standing role assignments.
Skipped locally when AZURE_SUBSCRIPTION_ID is not set; runs in CI after plan 03 deploys.
"""
import os
import subprocess
import json
import pytest

AZURE_SUB = os.environ.get("AZURE_SUBSCRIPTION_ID")
RG_IDENTITY = "rg-barycenter-identity"
EXPECTED_MIS = ["mi-bary-etl", "mi-bary-platform", "mi-bary-audit", "mi-bary-admin"]

pytestmark = pytest.mark.skipif(
    not AZURE_SUB,
    reason="AZURE_SUBSCRIPTION_ID not set; integration test requires live Azure",
)


def _az(*args) -> dict | list:
    result = subprocess.run(
        ["az", *args, "--output", "json"],
        capture_output=True, text=True, check=True,
    )
    return json.loads(result.stdout) if result.stdout.strip() else {}


@pytest.mark.parametrize("name", EXPECTED_MIS)
def test_managed_identity_exists(name):
    """IDENT-03: each MI exists with a principalId."""
    mi = _az("identity", "show", "--name", name, "--resource-group", RG_IDENTITY)
    assert mi["name"] == name
    assert mi["principalId"], f"{name} has no principalId"
    assert mi["clientId"], f"{name} has no clientId"
    # Managed identities have no client secret API — confirm the resource type is user-assigned
    assert mi["type"] == "Microsoft.ManagedIdentity/userAssignedIdentities"


def test_admin_mi_has_no_standing_assignments():
    """Pitfall 1 / IDENT-02: mi-bary-admin must be PIM-eligible only — zero standing role assignments."""
    admin = _az("identity", "show", "--name", "mi-bary-admin", "--resource-group", RG_IDENTITY)
    principal_id = admin["principalId"]
    assignments = _az(
        "role", "assignment", "list",
        "--assignee", principal_id,
        "--all",
    )
    assert assignments == [], (
        f"mi-bary-admin must have ZERO standing role assignments (Pitfall 1). Found: {assignments}"
    )


def test_admin_mi_has_pim_eligibility():
    """IDENT-02 + IDENT-05: mi-bary-admin must have at least one PIM eligibility schedule."""
    admin = _az("identity", "show", "--name", "mi-bary-admin", "--resource-group", RG_IDENTITY)
    principal_id = admin["principalId"]
    eligibilities = _az(
        "rest", "--method", "get",
        "--uri", (
            f"https://management.azure.com/subscriptions/{AZURE_SUB}/providers/"
            f"Microsoft.Authorization/roleEligibilitySchedules?api-version=2020-10-01"
            f"&$filter=assignedTo('{principal_id}')"
        ),
    )
    items = eligibilities.get("value", []) if isinstance(eligibilities, dict) else []
    assert len(items) >= 1, "mi-bary-admin must have at least one PIM eligibility schedule"
