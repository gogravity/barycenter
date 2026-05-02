"""ENC-01: TDE state must be Enabled on the database.

Also asserts CLAUDE.md global rule (publicNetworkAccess Disabled) and AAD-only auth.
"""
import os
import subprocess
import json
import pytest

AZURE_SUB = os.environ.get("AZURE_SUBSCRIPTION_ID")
RG_DATA = os.environ.get("RG_DATA", "rg-barycenter-dev")
SQL_SERVER = os.environ.get("SQL_SERVER_NAME", "sql-bary-dev")
SQL_DB = "barycenter"

pytestmark = pytest.mark.skipif(
    not AZURE_SUB,
    reason="AZURE_SUBSCRIPTION_ID not set",
)


def test_tde_state_enabled():
    result = subprocess.run(
        ["az", "sql", "db", "tde", "show",
         "--resource-group", RG_DATA,
         "--server", SQL_SERVER,
         "--database", SQL_DB,
         "--output", "json"],
        capture_output=True, text=True, check=True,
    )
    tde = json.loads(result.stdout)
    assert tde.get("state") == "Enabled", f"TDE not enabled: {tde}"


def test_sql_public_network_access_disabled():
    """CLAUDE.md global rule: SQL must be private-endpoint only."""
    result = subprocess.run(
        ["az", "sql", "server", "show",
         "--resource-group", RG_DATA,
         "--name", SQL_SERVER,
         "--query", "publicNetworkAccess",
         "--output", "tsv"],
        capture_output=True, text=True, check=True,
    )
    assert result.stdout.strip() == "Disabled", f"SQL publicNetworkAccess: {result.stdout!r}"


def test_sql_aad_only_authentication():
    result = subprocess.run(
        ["az", "sql", "server", "ad-only-auth", "get",
         "--resource-group", RG_DATA,
         "--server", SQL_SERVER,
         "--query", "azureAdOnlyAuthentication",
         "--output", "tsv"],
        capture_output=True, text=True, check=True,
    )
    assert result.stdout.strip().lower() == "true", f"AAD-only-auth: {result.stdout!r}"
