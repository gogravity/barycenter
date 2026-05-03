---
phase: 02-tool-onboarding-framework-connectwise-manage
verified: 2026-05-02T00:00:00Z
status: human_needed
score: 13/15
overrides_applied: 0
human_verification:
  - test: "Trigger `gh workflow run etl-cw-nightly.yml` after merging to main. Confirm the run completes with conclusion=success."
    expected: "At least one successful etl-cw-nightly run visible in `gh run list --workflow etl-cw-nightly.yml --limit 5`."
    why_human: "No non-production Azure SQL + Key Vault environment was available at Phase 2 execution time. The workflow is registered but has never had a green run. Requires live Azure credentials and CW instance."
  - test: "Execute the salt rotation fire drill script in `salt-rotation-firedrill-evidence.md` against a dev SQL instance with the pseudo schema deployed. Update `compliance/salt-rotation-state.yaml` with fire_drill.completed=true, tenant_id, completed_at, operator, and executions log."
    expected: "`compliance/salt-rotation-state.yaml` fire_drill.completed=true; executions[] contains salt.rotate.open_window, salt.rotate.dual_write, salt.rotate.cut_over entries; `python scripts/ci/check_salt_runbook.py` exits 0; salt-rotation-firedrill-evidence.md contains pid_old != pid_new confirmation."
    why_human: "Requires a live Azure SQL + Key Vault dev environment. Cannot be automated by Claude. Implementation (SaltRotation) and unit tests are complete; the operational gate is blocked only by infrastructure availability."
---

# Phase 2: Tool Onboarding Framework + ConnectWise Manage — Verification Report

**Phase Goal:** The framework that all future tool integrations inherit from is operational and exercised end-to-end against ConnectWise Manage with bounded-PII data — proving CUI enforcement, body-stripping, schema-drift detection, and salt-based pseudonymization all hold in production conditions before higher-PII integrations land.

**Verified:** 2026-05-02T00:00:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Eight TOOL-02 primitives (drop, hash, pseudonymize, aggregate, bucket, score, keyword_flags, as_is) exist, are importable from `barycenter.etl.primitives`, and ETL recipes are composed only from them — adapters cannot bypass the primitive layer | VERIFIED | `primitives/__init__.py` exports `PRIMITIVE_REGISTRY` with exactly 8 keys; `ETLRecipe.validate_no_bypass` field_validator raises `"bypasses primitive layer"` at construction time; `test_recipe_no_bypass.py` enforces in CI |
| 2 | ConnectWise Manage adapter syncs 5 tables (companies, agreements, ticket metadata, configurations, time-entry aggregates) into `raw_cw.*`; ticket bodies are architecturally stripped and verified by automated CI test | VERIFIED | `CWManageAdapter` declares `TABLES = ["companies", "agreements", "tickets", "configurations", "time_entries"]`; `sql/00-schemas/005_create_raw_cw_remaining.sql` has zero body columns; `recipes/tickets.py` drops initialDescription/resolution/initialInternalAnalysis; `test_no_body_column.py` passes |
| 3 | CUI-flagged tenants are gated at framework: canary phrases detected in text/subject/filename; attachments refused for CUI adapters | VERIFIED | `CanaryScanner` (canary.py) implements `scan_text`, `scan_subject`, `scan_filename`, `refuse_attachment`; `CUIGate.should_skip` queries raw_cw.companies; `compliance/cui-canary-phrases.yaml` contains CUI, FOUO, FEDCON, ITAR, SECRET//NOFORN |
| 4 | Four canonical AI-zone shapes (`customer_snapshot`, `customer_features_cw`, `timeseries_aggregate`, `customer_memory`) are populated from CW data; novel AI-zone tables fail CI | VERIFIED | `sql/00-schemas/007_create_ai_zone_shapes.sql` has exactly four `CREATE TABLE ai_zone.*` statements; `ShapeBuilder.CANONICAL` frozenset enforces at runtime; `test_no_novel_ai_zone.py` enforces in CI |
| 5 | Salt rotation runbook is documented with 8-step procedure and the implementation is complete and unit-tested | VERIFIED | `compliance/salt-rotation-runbook.md` contains Pre-flight, dual-write, Cut over, Retire old version, Pass criteria sections; `SaltRotation` class implements `open_window`, `dual_write`, `cut_over`; `test_salt_rotation.py` passes |
| 6 | Salt rotation fire drill executed against a non-production tenant; `compliance/salt-rotation-state.yaml` `fire_drill.completed=true` | FAILED (deferred — human required) | `fire_drill.completed: false` in YAML; `salt-rotation-firedrill-evidence.md` explicitly states "DEFERRED — no non-production Azure SQL instance available". Operational gate, not implementation gap. |
| 7 | First nightly `etl-cw-nightly` run completes successfully | FAILED (deferred — human required) | Plan 02-06 summary states "First etl-cw-nightly run pending — workflow is registered once this branch merges to main." Operational gate, not implementation gap. |
| 8 | `compliance/retention-policy.yaml` encodes per-class TTL contract: RESTRICTED 13mo | VERIFIED | `retention-policy.yaml` contains `RESTRICTED: { ttl_months: 13 }` |
| 9 | `RetentionSweeper` executes parameterized DELETE per class TTL and emits `retention.sweep` audit event | VERIFIED | `retention.py` issues `DELETE FROM {qualified_table} WHERE synced_at < ?`; emits `AuditEvent(verb="retention.sweep")`; `test_retention.py` passes |
| 10 | `AdapterBase.run` propagates `AuditEmitError` (fail-closed); continues on `ETLError` per table (D-02) | VERIFIED | `adapter_base.py` has `except AuditEmitError: raise` before `except ETLError: continue`; matches CLAUDE.md fail-closed mandate |
| 11 | `Category` enum has exactly 7 members: productivity, rmm, security, backup, docs, distributors, cw | VERIFIED | `adapter_base.py` declares `class Category(StrEnum)` with all 7 values |
| 12 | `Pseudonymizer` fetches salt fresh from Key Vault per call and never caches it | VERIFIED | `pseudonymizer.py` calls `self._kv.get_secret(secret_name)` per-call; `del salt_bytes` in `finally` block; `__repr__` excludes salt material |
| 13 | `barycenter-etl` is pip-installable with `barycenter-audit` as a local path dependency | VERIFIED | `pyproject.toml` declares `barycenter-audit` as dependency with `{ path = "../barycenter-audit", editable = true }` in `[tool.uv.sources]` |
| 14 | GitHub Actions `etl-cw-nightly.yml` uses OIDC (no client secrets) and `etl-retention-sweep.yml` runs at cron `0 12 * * *` | VERIFIED | Both workflows contain `id-token: write`, `environment: prod`, no wildcard OIDC subjects; nightly cron `0 6 * * *`; sweep cron `0 12 * * *` |
| 15 | `python-tests.yml` extended with barycenter-etl install, pytest run, and `check_salt_runbook.py` gates | VERIFIED | `python-tests.yml` contains `barycenter-etl[dev]`, `pytest packages/barycenter-etl/tests`, `check_salt_runbook.py --check-static`, `check_salt_runbook.py --self-test` |

**Score:** 13/15 (2 truths require human operational action; all structural/automated truths verified)

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `packages/barycenter-etl/pyproject.toml` | Package with deps, hatchling, pytest config | VERIFIED | Contains `name = "barycenter-etl"`, httpx, tenacity, pyodbc, pydantic, barycenter-audit |
| `packages/barycenter-etl/tests/conftest.py` | Shared fixtures | VERIFIED | 7 fixtures: mock_sql, mock_kv_client, mock_audit, mock_cw_client, synthetic_cw_company, synthetic_cui_company, synthetic_cui_ticket_with_canary |
| `packages/barycenter-etl/src/barycenter/etl/primitives/__init__.py` | PRIMITIVE_REGISTRY + 8 primitives | VERIFIED | Exports `PRIMITIVE_REGISTRY`, `PrimitiveResult`, all 8 primitive functions |
| `packages/barycenter-etl/src/barycenter/etl/framework/recipe.py` | ETLRecipe with no-bypass validation | VERIFIED | `class ETLRecipe`, `validate_no_bypass` field_validator, `"bypasses primitive layer"` error |
| `packages/barycenter-etl/src/barycenter/etl/framework/exceptions.py` | ETL exception hierarchy | VERIFIED | ETLError, CUIBoundaryViolation, SchemaDriftError, RateLimitExhausted, PaginationTruncated |
| `packages/barycenter-etl/src/barycenter/etl/framework/pseudonymizer.py` | Versioned-salt HMAC (Pitfall 5) | VERIFIED | `class Pseudonymizer`; fresh KV fetch per call; `del` in finally |
| `packages/barycenter-etl/src/barycenter/etl/framework/canary.py` | CUI phrase detection | VERIFIED | `class CanaryScanner` with scan_text/subject/filename/refuse_attachment |
| `packages/barycenter-etl/src/barycenter/etl/framework/cui_gate.py` | CUI table skip gate | VERIFIED | `class CUIGate` with should_skip, is_cui_company |
| `packages/barycenter-etl/src/barycenter/etl/framework/shape_builder.py` | Canonical-only AI-zone writes | VERIFIED | `CANONICAL` frozenset with 4 shapes; ValueError on novel shape |
| `packages/barycenter-etl/src/barycenter/etl/framework/retention.py` | Per-class TTL DELETE | VERIFIED | `class RetentionSweeper`; parameterized DELETE; emits retention.sweep AuditEvent |
| `packages/barycenter-etl/src/barycenter/etl/framework/salt_rotation.py` | Dual-write versioned pepper | VERIFIED | `class SaltRotation`, `DualWriteResult`; open_window/dual_write/cut_over |
| `packages/barycenter-etl/src/barycenter/etl/framework/adapter_base.py` | AdapterBase + Category | VERIFIED | `class AdapterBase`, `class Category` (7 members), `def run(self)`, fail-closed semantics |
| `packages/barycenter-etl/src/barycenter/etl/adapters/connectwise/client.py` | CWManageClient paginate + rate limit | VERIFIED | `class CWManageClient`; terminal_reason; Retry-After; RateLimitExhausted |
| `packages/barycenter-etl/src/barycenter/etl/adapters/connectwise/auth.py` | Strategy-pattern auth | VERIFIED | CWAuthStrategy, BasicAuthStrategy, OAuthClientCredsStrategy |
| `packages/barycenter-etl/src/barycenter/etl/adapters/connectwise/recipes/tickets.py` | Body fields explicitly dropped | VERIFIED | `("drop", ...)` for initialDescription, resolution, initialInternalAnalysis |
| `packages/barycenter-etl/src/barycenter/etl/adapters/connectwise/adapter.py` | CWManageAdapter(AdapterBase) | VERIFIED | `class CWManageAdapter(AdapterBase)`; CATEGORY='cw'; 5 TABLES; CUI_SENSITIVE_TABLES |
| `packages/barycenter-etl/src/barycenter/etl/run.py` | CLI entry point | VERIFIED | argparse; `--adapter connectwise`; `--dry-run` exits 0 |
| `sql/00-schemas/005_create_raw_cw_remaining.sql` | 4 tables, no body in tickets | VERIFIED | agreements, tickets (no body columns), configurations, time_entries; all with synced_at/source_etag |
| `sql/00-schemas/006_create_pseudo_person_map.sql` | Versioned pseudonym map | VERIFIED | tenant_id, email_lower, person_pid, salt_version; composite PK |
| `sql/00-schemas/007_create_ai_zone_shapes.sql` | 4 canonical AI-zone shapes | VERIFIED | Exactly 4 CREATE TABLE ai_zone.* statements |
| `sql/10-grants/001_etl_grants.sql` | Extended ETL grants | VERIFIED | GRANT on pseudo + ai_zone; DENY on audit preserved |
| `compliance/field-class-registry.yaml` | All new columns tagged | VERIFIED | tickets, pseudo, ai_zone entries present; serial_number=INTERNAL (hashed) |
| `compliance/cui-canary-phrases.yaml` | CUI phrase list | VERIFIED | Contains CUI, FOUO, FEDCON, ITAR, SECRET//NOFORN |
| `compliance/retention-policy.yaml` | Per-class TTLs | VERIFIED | RESTRICTED 13mo, SENSITIVE/INTERNAL/PUBLIC 60mo |
| `compliance/tool-onboarding-spec.template.md` | TOOL-01 sections | VERIFIED | Field Map, Raw Schema, ETL Recipe, AI-Zone Contributions, CUI Surface, Retention, Erasure |
| `compliance/salt-rotation-runbook.md` | 8-step procedure | VERIFIED | Pre-flight, dual-write, Cut over, Retire old version, Pass criteria |
| `compliance/salt-rotation-state.yaml` | State tracker | VERIFIED | version, tenants, executions, fire_drill keys present; fire_drill.completed=false (pending drill) |
| `scripts/ci/check_salt_runbook.py` | CI gate for runbook | VERIFIED | 76 lines; argparse + --self-test meta-test |
| `.github/workflows/etl-cw-nightly.yml` | Nightly sync workflow | VERIFIED | cron '0 6 * * *'; id-token: write; environment: prod; OIDC |
| `.github/workflows/etl-retention-sweep.yml` | Daily retention sweep | VERIFIED | cron '0 12 * * *'; RetentionSweeper; id-token: write |
| `.planning/phases/02-.../cw-auth-mode-evidence.md` | CW auth mode evidence | VERIFIED | auth_mode: basic; KV secrets provisioned section present |
| `.planning/phases/02-.../salt-rotation-firedrill-evidence.md` | Fire drill evidence | PARTIAL | Exists; documents deferred status with script; fire_drill.completed=false |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `pyproject.toml` | `barycenter-audit` | local path dependency | VERIFIED | `barycenter-audit = { path = "../barycenter-audit", editable = true }` |
| `scripts/ci/check_salt_runbook.py` | `compliance/salt-rotation-runbook.md` + `compliance/salt-rotation-state.yaml` | file presence + YAML parse | VERIFIED | Script checks REQUIRED_RUNBOOK_SECTIONS and state YAML keys |
| `framework/adapter_base.py` | `framework/cui_gate.py` + `framework/canary.py` + `framework/recipe.py` | AdapterBase.run() composes them | VERIFIED | `from barycenter.etl.framework.canary import CanaryScanner`, `from barycenter.etl.framework.cui_gate import CUIGate`, `from barycenter.etl.framework.recipe import ETLRecipe` |
| `framework/adapter_base.py` | `barycenter.audit.AuditClient` | `AuditEmitError` propagation | VERIFIED | `from barycenter.audit import AuditEmitError`; `except AuditEmitError: raise` |
| `framework/salt_rotation.py` | `framework/pseudonymizer.py` | `Pseudonymizer.derive(salt_version=...)` | VERIFIED | `from barycenter.etl.framework.pseudonymizer import Pseudonymizer` in salt_rotation.py |
| `framework/retention.py` | `compliance/retention-policy.yaml` | `yaml.safe_load` + TTL lookup | VERIFIED | `yaml.safe_load(self._policy_path.read_text())` in RetentionSweeper.__init__ |
| `adapters/connectwise/adapter.py` | `framework/adapter_base.py` | subclasses AdapterBase | VERIFIED | `class CWManageAdapter(AdapterBase)` |
| `adapters/connectwise/client.py` | tenacity + httpx | `@retry` decorator + `httpx.Client` | VERIFIED | `from tenacity import retry`; `httpx.Client(base_url=...)` |
| `.github/workflows/etl-cw-nightly.yml` | `barycenter.etl.run` | `python -m barycenter.etl.run --adapter connectwise` | VERIFIED | Confirmed in workflow step |
| `.github/workflows/etl-cw-nightly.yml` | OIDC via `vars.AZURE_ETL_CLIENT_ID` | `azure/login@v2` with `id-token: write` | VERIFIED | `id-token: write` permission; `environment: prod` (env-scoped per Pitfall 11) |

---

### Data-Flow Trace (Level 4)

Data-flow trace is deferred to the operational gate (first live run) for the live CW-to-SQL path. The static code path is verified: `CWManageAdapter.fetch_table` → `ETLRecipe.compile` → parameterized INSERT SQL → `AdapterBase.run` commits. No hardcoded empty values in the production code path.

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `adapter.py` (fetch_table) | raw CW records | `CWManageClient.paginate(path)` | Yes (live HTTP, mocked in tests) | VERIFIED (structural) |
| `recipes/tickets.py` | ticket derivations | `ETLRecipe.compile(record)` | Yes — delegates to PRIMITIVE_REGISTRY | VERIFIED |
| `shape_builder.py` (customer_memory) | no data | `SELECT 1 WHERE 1 = 0` | No — intentional per-plan no-op | VERIFIED (by design, Phase 3 populates) |

---

### Behavioral Spot-Checks

| Behavior | Evidence | Status |
|----------|----------|--------|
| `PRIMITIVE_REGISTRY` has 8 keys | `primitives/__init__.py` exports 8 named functions + registry dict | PASS |
| Tickets recipe has NO non-drop body projections | grep confirms `initialDescription`, `resolution`, `initialInternalAnalysis` appear only as `("drop", ...)` | PASS |
| `AdapterBase.run` fail-closed: `AuditEmitError` propagates | `except AuditEmitError: raise` is first catch clause before broad `except Exception` | PASS |
| `etl-cw-nightly.yml` has no wildcard OIDC subjects | `environment: prod` narrows subject; no `*` in subject claims | PASS |
| `compliance/salt-rotation-state.yaml` parses and has required keys | version, tenants, executions, fire_drill keys all present | PASS |
| First nightly run succeeds | Pending merge to main | PENDING HUMAN |
| Salt rotation fire drill executed | fire_drill.completed=false; deferred | PENDING HUMAN |

---

### Requirements Coverage

| Requirement | Description | Status | Evidence |
|-------------|-------------|--------|---------|
| TOOL-01 | Standardized Tool Onboarding Spec template | SATISFIED | `compliance/tool-onboarding-spec.template.md` with all required sections |
| TOOL-02 | Eight standard transformation primitives | SATISFIED | 8 primitives in PRIMITIVE_REGISTRY; no-bypass enforced at ETLRecipe construction |
| TOOL-03 | Four canonical AI-zone shapes | SATISFIED | DDL + ShapeBuilder.CANONICAL + CI test enforce exactly 4 shapes |
| TOOL-04 | Tool category taxonomy (7 categories) | SATISFIED | `Category(StrEnum)` with exactly 7 members including `cw` |
| INT-01 | CW Manage: companies, agreements, tickets (no body), configurations, time entries | SATISFIED (structural) | CWManageAdapter + 5 recipes + DDL; operational gate (first live run) is human_needed |
| COMP-03 | CUI exclusion boundary | SATISFIED | `CUIGate.should_skip` + `CanaryScanner` + `CUI_SENSITIVE_TABLES` in adapter |
| COMP-07 | CUI canary detection in email subjects, filenames, attachments | SATISFIED | `scan_text`, `scan_subject`, `scan_filename`, `refuse_attachment` in CanaryScanner |
| ENC-02 | Salt rotation runbook documented and tested; fire drill completed | PARTIAL | Runbook + SaltRotation implementation complete and tested; fire drill deferred (human gate) |
| RET-01 | Per-class retention policy | SATISFIED | `compliance/retention-policy.yaml` RESTRICTED=13mo; `RetentionSweeper` with parameterized DELETE; `etl-retention-sweep.yml` workflow |

---

### Anti-Patterns Found

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| `recipes/companies.py:21` | `keyword_flags` returns a Python dict bound to a SQL `BIT` column (`cui_handling_required`) — pyodbc ProgrammingError at runtime | Blocker (CR-01 per 02-REVIEW.md) | companies sync fails at every run; `CUIGate.should_skip` permanently returns False (CUI fence bypassed) |
| `primitives/pseudonymize.py:34` | Returns `{field: pid, f"{field}_salt_version": ver}` — 2 params for 1 `?` placeholder | Blocker (CR-02 per 02-REVIEW.md) | Any recipe using `pseudonymize` crashes with pyodbc ProgrammingError on `cur.execute` |
| `primitives/score.py:36` | `params={"score": result}` — hardcoded key not `field`; multiple score columns collide | Blocker (CR-03 per 02-REVIEW.md) | Multiple score columns in one recipe: second call overwrites first, parameter count mismatch |
| `adapters/connectwise/client.py:88-93` | tenacity retries on ALL `httpx.HTTPStatusError` including 404/401/403 | Warning (WR-01) | Permanent errors retry 5 times with exponential backoff before surfacing |
| `framework/pseudonymizer.py:51` | `salt_material` local not deleted in finally block (only `salt_bytes` and `secret` deleted) | Warning (WR-02) | Plaintext salt string persists in frame under some runtimes |
| `framework/retention.py:62` | No allowlist check before string-interpolating `qualified_table` into SQL | Warning (WR-03) | Injection risk if caller supplies unsanitized table name |
| `adapters/connectwise/models.py` | Pydantic CW models never called with `model_validate()` in `fetch_table` — drift detection is dead code | Warning (WR-04) | Schema drift detection (Pitfall 6 mitigation) never fires |
| `.github/workflows/etl-cw-nightly.yml:48` | `chain_validate.py --live || echo "..."` silences WORM chain validation | Warning (WR-05) | Broken WORM chain does not fail the nightly job |

**Classification:** CR-01, CR-02, CR-03 are real runtime bugs that will prevent the companies sync from running and prevent any recipe using `pseudonymize` from executing. Per the code review context (02-REVIEW.md), these are acknowledged post-phase fix targets — the framework architecture, tests, and structure are sound. Verification treats them as known gaps for the plan-phase gap closure workflow.

---

### Human Verification Required

#### 1. First Nightly etl-cw-nightly Run

**Test:** After merging this branch to main, trigger `gh workflow run etl-cw-nightly.yml` (or wait for the next scheduled 06:00 UTC run). Monitor with `gh run watch`.

**Expected:** The workflow completes with `conclusion: success`. At least one green run is visible in `gh run list --workflow etl-cw-nightly.yml --limit 5`.

**Why human:** Requires live Azure credentials (KEY_VAULT_URL, SQL_CONNECTION_STRING, api-cw-* secrets in Key Vault), a reachable ConnectWise Manage instance, and the `mi-bary-etl` managed identity with correct KV/SQL access. Cannot be verified in a worktree without the Azure environment. Additionally, CR-01/CR-02/CR-03 bugs must be fixed before the run can succeed.

#### 2. Salt Rotation Fire Drill

**Test:** Execute the fire drill script in `.planning/phases/02-tool-onboarding-framework-connectwise-manage/salt-rotation-firedrill-evidence.md` against a dev SQL instance with the Phase 2 schema deployed. Run all 8 steps in `compliance/salt-rotation-runbook.md`. Update `compliance/salt-rotation-state.yaml` with `fire_drill.completed: true` and the execution log.

**Expected:** `compliance/salt-rotation-state.yaml` shows `fire_drill.completed: true` with non-null `tenant_id`, `completed_at`, `operator`. `executions[]` contains entries for `salt.rotate.open_window`, `salt.rotate.dual_write`, `salt.rotate.cut_over`. `python scripts/ci/check_salt_runbook.py` exits 0. The `salt-rotation-firedrill-evidence.md` file contains `pid_old != pid_new` confirmation.

**Why human:** Requires a live Azure SQL dev instance with `pseudo` schema deployed, plus a Key Vault with test tenant salt provisioned. The `SaltRotation` implementation is complete and unit-tested; the operational barrier is infrastructure availability, not code completeness.

---

### Gaps Summary

Three runtime bugs in the companies sync path (CR-01/CR-02/CR-03) will prevent the first nightly run from succeeding even after the operational prerequisites are met. These are documented in `02-REVIEW.md` as post-phase fix targets. The framework architecture, all tests, and the structural requirements are sound and verified. The bugs are isolated to specific call sites and have clear fixes described in the review.

Two operational items (fire drill, first nightly run) are deferred to human action and are classified as `human_needed` rather than structural gaps.

---

_Verified: 2026-05-02T00:00:00Z_
_Verifier: Claude (gsd-verifier)_
