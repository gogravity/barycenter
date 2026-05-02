"""Pitfall 1 CI gate: reconcile sys.database_principals + sys.database_permissions
against sql/10-grants/*.sql expectations. Fail on any unknown grantee or unexpected grant.

Modes:
  --self-test: parse sql/10-grants/ + tests/fixtures/sql_perms_clean.json fixture; exit 0
  --self-test --drifted: use tests/fixtures/sql_perms_drifted.json; exit nonzero → PASS
  (default): live mode — connect via audit identity, query, diff
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

EXPECTED_PRINCIPALS = {"mi-bary-etl", "mi-bary-platform", "mi-bary-audit", "mi-bary-admin"}

# Match GRANT/DENY <perms> ON [SCHEMA::|OBJECT::]<target> TO|FROM [principal];
GRANT_RE = re.compile(
    r"(GRANT|DENY)\s+([\w,\s]+?)\s+ON\s+(?:SCHEMA::|OBJECT::)?(\S+?)\s+(?:TO|FROM)\s+\[?([^\]\s;]+)\]?\s*;",
    re.IGNORECASE,
)


def parse_expected_grants() -> dict:
    """Returns {principal: {(target, perm): 'GRANT' | 'DENY'}}.

    `target` is normalized to its bare name (schema or object name without the
    ``SCHEMA::`` / ``OBJECT::`` qualifier and without surrounding brackets).
    """
    out: dict = {}
    for sql_file in sorted(Path("sql/10-grants").glob("*.sql")):
        text = sql_file.read_text()
        for m in GRANT_RE.finditer(text):
            action, perms, target, principal = m.groups()
            target_clean = target.strip().strip("[]")
            for p in [x.strip() for x in perms.split(",") if x.strip()]:
                out.setdefault(principal, {})[(target_clean, p.upper())] = action.upper()
    return out


def diff_actual_vs_expected(actual: list[dict], expected: dict) -> list[str]:
    """actual: list of {principal, schema, permission, state} dicts."""
    errors: list[str] = []
    for row in actual:
        principal = row["principal"]
        if principal not in EXPECTED_PRINCIPALS:
            errors.append(
                f"Pitfall-1: unexpected principal {principal!r} has "
                f"{row['state']} {row['permission']} on {row['schema']}"
            )
            continue
        key = (row["schema"], row["permission"].upper())
        exp = expected.get(principal, {}).get(key)
        if exp is None:
            errors.append(
                f"Pitfall-1: {principal} has unexpected {row['state']} "
                f"{row['permission']} on {row['schema']} (not in manifest)"
            )
        elif exp != row["state"].upper():
            errors.append(
                f"Pitfall-1: {principal} {row['permission']} on {row['schema']}: "
                f"expected {exp}, actual {row['state']}"
            )
    return errors


def _fetch_live_perms() -> list[dict]:
    # Lazy imports — live mode only.
    import struct

    import pyodbc  # type: ignore
    from azure.identity import DefaultAzureCredential  # type: ignore

    cred = DefaultAzureCredential()
    token = cred.get_token("https://database.windows.net/.default").token
    conn_str = (
        "Driver={ODBC Driver 18 for SQL Server};"
        f"Server={os.environ['SQL_SERVER_FQDN']};Database=barycenter;Encrypt=yes;"
    )
    token_bytes = token.encode("utf-16-le")
    token_struct = struct.pack(f"=i{len(token_bytes)}s", len(token_bytes), token_bytes)
    conn = pyodbc.connect(conn_str, attrs_before={1256: token_struct})
    cur = conn.cursor()
    cur.execute(
        """
        SELECT pr.name AS principal, sch.name AS schema_name, perm.permission_name, perm.state_desc
        FROM sys.database_permissions perm
        JOIN sys.database_principals pr ON perm.grantee_principal_id = pr.principal_id
        LEFT JOIN sys.schemas sch ON perm.major_id = sch.schema_id
        WHERE pr.name IN ('mi-bary-etl','mi-bary-platform','mi-bary-audit','mi-bary-admin')
        """
    )
    return [
        {"principal": r[0], "schema": r[1] or "", "permission": r[2], "state": r[3]}
        for r in cur.fetchall()
    ]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--drifted", action="store_true")
    args = ap.parse_args()

    expected = parse_expected_grants()
    if args.self_test:
        fixture = Path(
            "tests/fixtures/sql_perms_drifted.json"
            if args.drifted
            else "tests/fixtures/sql_perms_clean.json"
        )
        actual = json.loads(fixture.read_text())
    else:
        actual = _fetch_live_perms()

    errors = diff_actual_vs_expected(actual, expected)
    if args.drifted:
        if not errors:
            print(
                "Pitfall-1 self-test FAIL: drifted fixture produced no errors",
                file=sys.stderr,
            )
            sys.exit(1)
        print(f"Pitfall-1 self-test PASS (gate fired on {len(errors)} drifts)")
        sys.exit(0)

    if errors:
        for e in errors:
            print(e, file=sys.stderr)
        sys.exit(1)
    print(f"Pitfall-1 OK: {len(actual)} permissions reconciled against manifest")
    sys.exit(0)


if __name__ == "__main__":
    main()
