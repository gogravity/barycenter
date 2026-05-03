---
phase: "02"
plan: "03"
subsystem: storage-ddl-grants
tags: [ddl, sql, grants, ver-02, enc-02, tool-03, int-01, ret-01]
requires:
  - "01-create_raw_cw.sql (Phase 1) — raw_cw schema and companies table"
  - "02-create_ai_zone.sql (Phase 1) — ai_zone schema declaration"
  - "04-create_pseudo.sql (Phase 1) — pseudo schema declaration"
  - "10-grants/001_etl_grants.sql (Phase 1) — base ETL grant model"
  - "scripts/ci/field_class_check.py (Phase 1) — VER-02 gate"
  - "scripts/ci/grant_drift_check.py (Phase 1) — Pitfall-1 grant drift gate"
provides:
  - "raw_cw.{agreements, tickets, configurations, time_entries} DDL"
  - "pseudo.person_map DDL with versioned (tenant_id, email_lower, salt_version) PK"
  - "ai_zone.{customer_snapshot, customer_features_cw, timeseries_aggregate, customer_memory} DDL"
  - "Extended ETL grants on pseudo + ai_zone schemas"
  - "Field-class registry entries for every new column"
  - "Architectural enforcement of body-strip and canonical AI-zone constraints"
affects:
  - "02-04 (CW Manage adapter): writes into raw_cw.{agreements,tickets,configurations,time_entries}"
  - "02-05 (ShapeBuilder): populates ai_zone.* via the four canonical shapes"
  - "02-06 (Pseudonymizer + ENC-02 runbook): writes pseudo.person_map; uses salt_version"
tech-stack:
  added: []
  patterns:
    - "Idempotent DDL: IF SCHEMA_ID IS NULL EXEC('CREATE SCHEMA') / IF OBJECT_ID IS NULL CREATE TABLE"
    - "Mandatory raw-zone columns: synced_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(), source_etag NVARCHAR(128) NULL"
    - "Architectural body-strip: raw_cw.tickets has no body/internalAnalysis/resolution/notes column at the DDL level"
    - "TRUNCATE+INSERT for ai_zone (DELETE permitted, UPDATE deliberately denied — race-free shape population, T-02-15 mitigation)"
    - "Versioned pseudonyms: composite PK (tenant_id, email_lower, salt_version) supports ENC-02 dual-write rotation window"
key-files:
  created:
    - "sql/00-schemas/005_create_raw_cw_remaining.sql"
    - "sql/00-schemas/006_create_pseudo_person_map.sql"
    - "sql/00-schemas/007_create_ai_zone_shapes.sql"
  modified:
    - "sql/10-grants/001_etl_grants.sql"
    - "compliance/field-class-registry.yaml"
    - "tests/fixtures/sql_perms_clean.json"
    - "packages/barycenter-etl/tests/test_no_body_column.py"
    - "packages/barycenter-etl/tests/test_no_novel_ai_zone.py"
decisions:
  - "Compose-key pseudo.person_map: PK (tenant_id, email_lower, salt_version) so the dual-write rotation window keeps both versions live without UPSERT collisions."
  - "ai_zone grants: SELECT/INSERT/DELETE only — no UPDATE. Forces TRUNCATE+INSERT shape repopulation (race-free; T-02-15)."
  - "pseudo grants: SELECT/INSERT/UPDATE only — no DELETE. retired_at is set via UPDATE during rotation; physical removal is reserved for the erasure cascade (a separate identity)."
  - "configurations.serial_number tagged RESTRICTED (vendor identifier; correlation risk)."
  - "raw_cw.tickets.summary tagged SENSITIVE (subject only, but still subject to canary scanning)."
  - "Test files now resolve sql/00-schemas via _REPO_ROOT (parents[3] of __file__) so they pass when invoked from packages/barycenter-etl as well as from repo root."
metrics:
  duration_minutes: 13
  completed: "2026-05-03T00:20:47Z"
---

# Phase 2 Plan 03: Storage DDL + ETL Grants Summary

Land the SQL DDL and grant updates for Phase 2: four remaining `raw_cw` tables (with body fields architecturally absent from `raw_cw.tickets`), `pseudo.person_map` for versioned pseudonyms (ENC-02), the four canonical `ai_zone` shape tables (TOOL-03), and extended ETL grants — making `test_no_body_column.py` and `test_no_novel_ai_zone.py` turn green and unblocking adapter implementation in plans 04–05.

## What Shipped

### Task 1 — DDL (commit `5faaebf`)

- **`sql/00-schemas/005_create_raw_cw_remaining.sql`** — `raw_cw.agreements`, `raw_cw.tickets` (no body/initialDescription/resolution/internalAnalysis/initialInternalAnalysis/notes columns), `raw_cw.configurations`, `raw_cw.time_entries` (aggregates only, PK on `(cw_company_id, entry_date)`). Every table carries `synced_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()` and `source_etag NVARCHAR(128) NULL`.
- **`sql/00-schemas/006_create_pseudo_person_map.sql`** — `pseudo.person_map` with composite PK `(tenant_id, email_lower, salt_version)` and a `person_pid` reverse-lookup index for ERAS-01.
- **`sql/00-schemas/007_create_ai_zone_shapes.sql`** — exactly four `CREATE TABLE ai_zone.*` statements: `customer_snapshot`, `customer_features_cw`, `timeseries_aggregate`, `customer_memory`. No others. `test_no_novel_ai_zone.py` enforces this.

### Task 2 — Grants + Registry + Fixture (commit `1b78903`)

- **`sql/10-grants/001_etl_grants.sql`** — replaced the Phase-1 DENY on `pseudo` and `ai_zone` for `mi-bary-etl` with minimal-but-sufficient GRANTs:
  - `pseudo`: GRANT SELECT, INSERT, UPDATE — DELETE deliberately omitted (erasure cascade owns physical removal).
  - `ai_zone`: GRANT SELECT, INSERT, DELETE — UPDATE deliberately omitted (TRUNCATE+INSERT shape population, T-02-15 mitigation).
  - `audit`: DENY preserved verbatim (T-02-14 mitigation: ETL writes audit only via `AuditClient.emit` / audit identity).
- **`compliance/field-class-registry.yaml`** — added entries for every new column across `raw_cw.{agreements,tickets,configurations,time_entries}`, `pseudo.person_map`, and the four `ai_zone` shapes. Notable classifications:
  - `raw_cw.tickets.summary` → SENSITIVE (canary scanned)
  - `raw_cw.configurations.serial_number` → RESTRICTED
  - `pseudo.person_map.email_lower` → RESTRICTED, `person_pid` → SENSITIVE
  - `ai_zone.customer_snapshot.cui_flag` → PUBLIC (it's a flag, not the CUI itself)
  - All `ai_zone.*` columns are PUBLIC or INTERNAL — no RESTRICTED, no un-pseudonymized SENSITIVE, by design.
  - Phase-1 entries for `raw_cw.companies` are unchanged.
- **`tests/fixtures/sql_perms_clean.json`** — refreshed to reflect the new authoritative grant model so `grant_drift_check.py --self-test` continues to pass and `--self-test --drifted` continues to fire on injected drift.

## Verification

| Gate | Command | Result |
| ---- | ------- | ------ |
| body-column architectural rule | `cd packages/barycenter-etl && pytest tests/test_no_body_column.py -v` | PASSED (was previously skipped — see Deviations Rule 3) |
| canonical ai_zone rule | `cd packages/barycenter-etl && pytest tests/test_no_novel_ai_zone.py -v` | PASSED (was previously skipped) |
| VER-02 static check | `python3 scripts/ci/field_class_check.py --check-static` | OK: 48 columns checked across 5 tables |
| VER-02 meta-test | `python3 scripts/ci/field_class_check.py --simulate-untagged` | PASS (gate fires on injected untagged column) |
| Grant drift (clean) | `python3 scripts/ci/grant_drift_check.py --self-test` | OK: 41 permissions reconciled against manifest |
| Grant drift (drifted) | `python3 scripts/ci/grant_drift_check.py --self-test --drifted` | PASS (gate fires on 9 drifts) |
| Grant content (literal) | `grep "GRANT SELECT, INSERT, UPDATE ON SCHEMA::pseudo TO [mi-bary-etl]"` | matched |
| Grant content (literal) | `grep "GRANT SELECT, INSERT, DELETE ON SCHEMA::ai_zone TO [mi-bary-etl]"` | matched |
| No DENY on pseudo/ai_zone for ETL | `! grep "DENY .+ ON SCHEMA::(pseudo|ai_zone) TO [mi-bary-etl]"` | confirmed (no match) |
| audit DENY preserved | `grep "DENY ... ON SCHEMA::audit TO [mi-bary-etl]"` | matched |
| YAML registry assertions | inline pyyaml load + key assertions | "registry OK" |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Blocking] `test_no_body_column.py` and `test_no_novel_ai_zone.py` skipped instead of passed**
- **Found during:** Task 1 verification
- **Issue:** The two tests use `pathlib.Path("sql/00-schemas").glob("*.sql")` — a CWD-relative path. The plan's `<verify>` block runs them via `cd packages/barycenter-etl && pytest …`, which makes the path resolve to `packages/barycenter-etl/sql/00-schemas` (nonexistent). The tests then `pytest.skip(...)`. The plan's acceptance criterion explicitly states "PASSED (not skipped)."
- **Fix:** Replaced the relative path with `_REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]` and `_SCHEMAS_DIR = _REPO_ROOT / "sql" / "00-schemas"`. Tests now pass regardless of pytest CWD.
- **Files modified:** `packages/barycenter-etl/tests/test_no_body_column.py`, `packages/barycenter-etl/tests/test_no_novel_ai_zone.py`
- **Commit:** `5faaebf`

**2. [Rule 3 — Blocking] `tests/fixtures/sql_perms_clean.json` encoded the old DENY-on-pseudo/ai_zone grant model**
- **Found during:** Task 2 verification
- **Issue:** The plan's verify command `python scripts/ci/grant_drift_check.py` runs in *live* mode (no flag), which requires `DefaultAzureCredential` + ODBC Driver 18 + an actual SQL connection — none available in this worktree. The supported local/CI mode is `--self-test`, which loads `tests/fixtures/sql_perms_clean.json` and diffs against the manifest parsed from `sql/10-grants/*.sql`. After the grant migration, the existing fixture still encoded `mi-bary-etl` as `DENY` on pseudo/ai_zone; self-test would have produced 8 drift errors.
- **Fix:** Refreshed the fixture to mirror the new authoritative grant model (GRANT on pseudo {SELECT,INSERT,UPDATE}; GRANT on ai_zone {SELECT,INSERT,DELETE}; DENY on audit preserved). Drifted fixture untouched (its drifted-grantee `intern.alice@gravity.com` remains the meta-test signal).
- **Files modified:** `tests/fixtures/sql_perms_clean.json`
- **Commit:** `1b78903`

### Plan-Verify Substitution

The plan's verify uses `python scripts/ci/grant_drift_check.py` (live mode). Because this requires Azure connectivity, I ran the supported equivalent `python3 scripts/ci/grant_drift_check.py --self-test` (clean) and `--self-test --drifted` (meta-test) — both pass. Live mode will be exercised in the post-deploy CI workflow (Phase 1 plumbing).

## Threat Flags

None. All new surface is anticipated by the threat model; no new endpoints, auth paths, or trust boundaries introduced.

## Known Stubs

None. All new tables have complete column definitions, PKs, and the registry/grants needed for the next plans (04 CW adapter, 05 ShapeBuilder, 06 Pseudonymizer) to write into them.

## Self-Check: PASSED

Files exist:
- `sql/00-schemas/005_create_raw_cw_remaining.sql` — FOUND
- `sql/00-schemas/006_create_pseudo_person_map.sql` — FOUND
- `sql/00-schemas/007_create_ai_zone_shapes.sql` — FOUND
- `sql/10-grants/001_etl_grants.sql` — FOUND (modified)
- `compliance/field-class-registry.yaml` — FOUND (modified)
- `tests/fixtures/sql_perms_clean.json` — FOUND (modified)
- `packages/barycenter-etl/tests/test_no_body_column.py` — FOUND (modified)
- `packages/barycenter-etl/tests/test_no_novel_ai_zone.py` — FOUND (modified)

Commits exist (`git log --oneline`):
- `5faaebf` feat(02-03): add Phase 2 storage DDL — FOUND
- `1b78903` feat(02-03): extend ETL grants to pseudo + ai_zone — FOUND
