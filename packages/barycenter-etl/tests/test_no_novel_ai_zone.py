"""CI gate: only the 4 canonical AI-zone shapes exist (TOOL-03)."""
import pathlib
import re
import pytest

CANONICAL = {"customer_snapshot", "customer_features_cw",
             "timeseries_aggregate", "customer_memory"}


def test_no_novel_ai_zone_table():
    sql_files = list(pathlib.Path("sql/00-schemas").glob("*.sql"))
    if not sql_files:
        pytest.skip("No SQL DDL files found yet (created in later Phase 2 plans)")
    pattern = re.compile(
        r"CREATE\s+TABLE\s+\[?ai_zone\]?\.\[?(\w+)\]?",
        re.IGNORECASE)
    for f in sql_files:
        for m in pattern.finditer(f.read_text()):
            table = m.group(1).lower()
            # customer_features_* glob: per A7 in RESEARCH.md, the family is allowed
            # but for Phase 2 only customer_features_cw is permitted.
            assert table in CANONICAL, \
                f"Novel ai_zone table found: ai_zone.{table} not in {CANONICAL}"
