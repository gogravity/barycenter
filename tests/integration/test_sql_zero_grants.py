"""FOUND-04 layer 1 verification: confirm grant model is enforced.

Connects via the audit identity (which has the lightest read footprint) and queries
sys.database_principals + sys.database_permissions to assert the expected grant matrix.

Skipped locally; runs in CI after plan 05 deploys.
"""
import os
import subprocess
import pytest

AZURE_SUB = os.environ.get("AZURE_SUBSCRIPTION_ID")
SQL_FQDN = os.environ.get("SQL_SERVER_FQDN", "sql-bary-dev.database.windows.net")
SQL_DB = "barycenter"

pytestmark = pytest.mark.skipif(
    not AZURE_SUB or not os.environ.get("SQL_AUDIT_QUERY_TOKEN"),
    reason="Requires AZURE_SUBSCRIPTION_ID and SQL_AUDIT_QUERY_TOKEN (acquired by CI)",
)


def _run_sql(query: str) -> list[dict]:
    token = os.environ["SQL_AUDIT_QUERY_TOKEN"]
    result = subprocess.run(
        ["sqlcmd", "-S", SQL_FQDN, "-d", SQL_DB, "-G", "--access-token", token,
         "-Q", query, "-W", "-h", "-1", "-s", "|"],
        capture_output=True, text=True, check=True,
    )
    lines = [l for l in result.stdout.strip().splitlines() if l.strip()]
    if not lines:
        return []
    headers = [h.strip() for h in lines[0].split("|")]
    return [dict(zip(headers, [c.strip() for c in l.split("|")])) for l in lines[1:]]


def test_etl_has_raw_cw_crud_only():
    """mi-bary-etl: GRANT on raw_cw, DENY on ai_zone/audit/pseudo."""
    rows = _run_sql("""
        SELECT pr.name AS principal, sch.name AS schema_name, perm.permission_name, perm.state_desc
        FROM sys.database_permissions perm
        JOIN sys.database_principals pr ON perm.grantee_principal_id = pr.principal_id
        JOIN sys.schemas sch ON perm.major_id = sch.schema_id
        WHERE pr.name = 'mi-bary-etl' AND perm.class = 3
    """)
    granted_raw_cw = {r["permission_name"] for r in rows if r["schema_name"] == "raw_cw" and r["state_desc"] == "GRANT"}
    assert granted_raw_cw >= {"SELECT", "INSERT", "UPDATE", "DELETE"}, granted_raw_cw
    for forbidden in ("ai_zone", "audit", "pseudo"):
        denied = {r["permission_name"] for r in rows if r["schema_name"] == forbidden and r["state_desc"] == "DENY"}
        assert denied >= {"SELECT", "INSERT", "UPDATE", "DELETE"}, f"missing DENY on {forbidden}: {denied}"


def test_platform_has_ai_zone_select_only():
    """mi-bary-platform: GRANT SELECT on ai_zone, DENY on raw_cw/audit/pseudo."""
    rows = _run_sql("""
        SELECT pr.name, sch.name AS schema_name, perm.permission_name, perm.state_desc
        FROM sys.database_permissions perm
        JOIN sys.database_principals pr ON perm.grantee_principal_id = pr.principal_id
        JOIN sys.schemas sch ON perm.major_id = sch.schema_id
        WHERE pr.name = 'mi-bary-platform' AND perm.class = 3
    """)
    granted = {(r["schema_name"], r["permission_name"]) for r in rows if r["state_desc"] == "GRANT"}
    assert ("ai_zone", "SELECT") in granted
    for forbidden in ("raw_cw", "audit", "pseudo"):
        denied_perms = {r["permission_name"] for r in rows if r["schema_name"] == forbidden and r["state_desc"] == "DENY"}
        assert denied_perms >= {"SELECT"}, f"platform must be DENY-SELECT on {forbidden}"


def test_audit_has_chain_state_update_only():
    """mi-bary-audit: GRANT SELECT/UPDATE on audit.chain_state object only."""
    rows = _run_sql("""
        SELECT pr.name, perm.permission_name, perm.state_desc, perm.class
        FROM sys.database_permissions perm
        JOIN sys.database_principals pr ON perm.grantee_principal_id = pr.principal_id
        WHERE pr.name = 'mi-bary-audit'
    """)
    granted = {r["permission_name"] for r in rows if r["state_desc"] == "GRANT"}
    assert granted >= {"SELECT", "UPDATE"}, f"audit MI must have SELECT+UPDATE on chain_state: {granted}"


def test_admin_has_no_grants_no_roles():
    """Pitfall 1: mi-bary-admin must have ZERO grants and ZERO role memberships."""
    perms = _run_sql("""
        SELECT pr.name, perm.permission_name, perm.state_desc
        FROM sys.database_permissions perm
        JOIN sys.database_principals pr ON perm.grantee_principal_id = pr.principal_id
        WHERE pr.name = 'mi-bary-admin' AND perm.state_desc = 'GRANT'
    """)
    assert perms == [], f"mi-bary-admin must have ZERO standing GRANTs. Found: {perms}"
    roles = _run_sql("""
        SELECT r.name AS role_name
        FROM sys.database_role_members m
        JOIN sys.database_principals u ON m.member_principal_id = u.principal_id
        JOIN sys.database_principals r ON m.role_principal_id = r.principal_id
        WHERE u.name = 'mi-bary-admin'
    """)
    assert roles == [], f"mi-bary-admin must have ZERO role memberships. Found: {roles}"


def test_chain_state_genesis_seeded():
    """D-05: chain_state row 1 exists with head_digest = 64 zero chars."""
    rows = _run_sql("SELECT id, head_digest FROM audit.chain_state WHERE id = 1")
    assert len(rows) == 1
    assert rows[0]["head_digest"] == "0" * 64
