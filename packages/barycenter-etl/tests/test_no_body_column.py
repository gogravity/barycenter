"""CI gate: raw_cw.tickets has no body-like columns (Pitfall 1, INT-01 success criterion 2)."""
import pathlib
import re

BODY_FIELDS = {"body", "internalAnalysis", "resolution", "notes",
               "initialDescription", "initialInternalAnalysis"}

# Resolve sql/00-schemas relative to repo root, regardless of pytest CWD.
_REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
_SCHEMAS_DIR = _REPO_ROOT / "sql" / "00-schemas"


def test_raw_cw_tickets_has_no_body_column():
    sql_files = list(_SCHEMAS_DIR.glob("*.sql"))
    if not sql_files:
        pytest.skip("No SQL DDL files found yet (created in later Phase 2 plans)")
    ticket_cols: set[str] = set()
    pattern = re.compile(
        r"CREATE\s+TABLE\s+\[?(\w+)\]?\.\[?(\w+)\]?\s*\((.*?)\)\s*;",
        re.IGNORECASE | re.DOTALL)
    for f in sql_files:
        for m in pattern.finditer(f.read_text()):
            if m.group(1).lower() == "raw_cw" and m.group(2).lower() == "tickets":
                body = m.group(3)
                for line in body.splitlines():
                    line = line.strip().lstrip(",").strip()
                    if line and not line.startswith("--"):
                        col = line.split()[0].strip("[]")
                        ticket_cols.add(col)
    forbidden = (
        ({c.lower() for c in ticket_cols} & {f.lower() for f in BODY_FIELDS})
    )
    assert not forbidden, \
        f"raw_cw.tickets must not have body columns; found: {forbidden}"


# Top-level pytest import for skip()
import pytest  # noqa: E402
