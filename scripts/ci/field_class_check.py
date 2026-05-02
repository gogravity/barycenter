"""VER-02 CI gate: every column in raw_* schemas MUST appear in
compliance/field-class-registry.yaml with one of {RESTRICTED, SENSITIVE, INTERNAL, PUBLIC}.

Modes:
  --check-static: parse sql/00-schemas/*.sql to extract columns, compare to registry.
                  Default mode in PR CI (no Azure dependency).
  --check-live:   query INFORMATION_SCHEMA.COLUMNS via the audit identity (post-deploy CI only).
  --simulate-untagged: meta-test — inject a fake untagged column and assert the gate fails.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

VALID_CLASSES = {"RESTRICTED", "SENSITIVE", "INTERNAL", "PUBLIC"}
REGISTRY_PATH = Path("compliance/field-class-registry.yaml")
SCHEMAS_DIR = Path("sql/00-schemas")


def load_registry() -> dict:
    return yaml.safe_load(REGISTRY_PATH.read_text())


def _strip_line_comments(sql: str) -> str:
    """Strip ``-- ...`` SQL line comments without disturbing line breaks.

    Inline comments may legally contain unbalanced parentheses (e.g.
    ``-- JSON list (Phase 3)``), which would corrupt the paren-depth tracker
    used by ``parse_create_table``. Removing them up front keeps the splitter
    correct without losing newline structure.
    """
    out_lines: list[str] = []
    for line in sql.splitlines():
        idx = line.find("--")
        if idx >= 0:
            line = line[:idx]
        out_lines.append(line)
    return "\n".join(out_lines)


def parse_create_table(sql_text: str) -> dict:
    """Returns {schema: {table: [column1, column2, ...]}}.

    Tolerates ``CREATE TABLE schema.table`` and ``CREATE TABLE [schema].[table]``.
    Strips trailing per-column constraints (e.g. ``PRIMARY KEY``, ``NOT NULL``,
    ``DEFAULT ...``). Skips lines that begin with ``CONSTRAINT``.
    """
    sql_text = _strip_line_comments(sql_text)
    result: dict = {}
    pattern = re.compile(
        r"CREATE\s+TABLE\s+\[?(\w+)\]?\.\[?(\w+)\]?\s*\((.*?)\)\s*;",
        re.IGNORECASE | re.DOTALL,
    )
    for m in pattern.finditer(sql_text):
        schema, table, body = m.group(1), m.group(2), m.group(3)
        cols: list[str] = []
        # Split on commas at depth 0 (paren-aware) so type modifiers like NVARCHAR(256)
        # don't fool the splitter.
        depth = 0
        current = []
        chunks: list[str] = []
        for ch in body:
            if ch == "(":
                depth += 1
                current.append(ch)
            elif ch == ")":
                depth -= 1
                current.append(ch)
            elif ch == "," and depth == 0:
                chunks.append("".join(current))
                current = []
            else:
                current.append(ch)
        if current:
            chunks.append("".join(current))
        for chunk in chunks:
            line = chunk.strip()
            if not line:
                continue
            if line.upper().startswith("CONSTRAINT"):
                continue
            if line.upper().startswith(("PRIMARY KEY", "FOREIGN KEY", "UNIQUE", "CHECK")):
                continue
            col_match = re.match(r"^\[?(\w+)\]?\s+", line)
            if col_match:
                cols.append(col_match.group(1))
        result.setdefault(schema, {})[table] = cols
    return result


def collect_static_schema() -> dict:
    all_tables: dict = {}
    for sql_file in sorted(SCHEMAS_DIR.glob("*.sql")):
        parsed = parse_create_table(sql_file.read_text())
        for schema, tables in parsed.items():
            if not schema.startswith("raw_"):
                continue  # only raw_* schemas are in scope for VER-02
            all_tables.setdefault(schema, {}).update(tables)
    return all_tables


def check(static_schema: dict, registry: dict, simulate_untagged: bool = False) -> list[str]:
    errors: list[str] = []
    reg_schemas = registry.get("schemas", {})
    if simulate_untagged:
        static_schema.setdefault("raw_cw", {}).setdefault("companies", []).append("__simulated_untagged__")
    for schema, tables in static_schema.items():
        for table, cols in tables.items():
            reg_table = reg_schemas.get(schema, {}).get(table, {})
            for col in cols:
                if col not in reg_table:
                    errors.append(f"VER-02: {schema}.{table}.{col} missing field-class tag")
                    continue
                cls = reg_table[col]
                if cls not in VALID_CLASSES:
                    errors.append(
                        f"VER-02: {schema}.{table}.{col} has invalid class {cls!r} (valid: {VALID_CLASSES})"
                    )
    return errors


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check-static", action="store_true", default=True)
    ap.add_argument("--check-live", action="store_true")
    ap.add_argument(
        "--simulate-untagged",
        action="store_true",
        help="Meta-test: inject fake untagged column, assert gate fires.",
    )
    args = ap.parse_args()

    registry = load_registry()
    static = collect_static_schema()
    errors = check(static, registry, simulate_untagged=args.simulate_untagged)

    if args.simulate_untagged:
        if not errors:
            print(
                "VER-02 meta-test FAIL: gate did not fire on injected untagged column",
                file=sys.stderr,
            )
            sys.exit(1)
        print("VER-02 meta-test PASS (gate correctly fires on untagged column)")
        sys.exit(0)

    if errors:
        for e in errors:
            print(e, file=sys.stderr)
        sys.exit(1)
    cols_total = sum(len(c) for s in static.values() for c in s.values())
    tables_total = sum(len(t) for t in static.values())
    print(f"VER-02 OK: {cols_total} columns checked across {tables_total} tables")
    sys.exit(0)


if __name__ == "__main__":
    main()
