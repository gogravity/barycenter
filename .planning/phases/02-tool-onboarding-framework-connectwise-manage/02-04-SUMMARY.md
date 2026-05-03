---
phase: 02
plan: 04
subsystem: etl-framework
tags: [framework, cui, canary, retention, salt-rotation, adapter-base, tool-03, comp-03, comp-07, ret-01, enc-02, tool-04]
requires:
  - barycenter-audit (AuditClient.emit, AuditEvent fail-closed)
  - barycenter.etl.framework.pseudonymizer (Pseudonymizer.derive)
  - barycenter.etl.framework.exceptions (ETLError, CUIBoundaryViolation)
  - compliance/cui-canary-phrases.yaml
  - compliance/retention-policy.yaml
  - compliance/salt-rotation-state.yaml
provides:
  - barycenter.etl.framework.canary.CanaryScanner
  - barycenter.etl.framework.cui_gate.CUIGate
  - barycenter.etl.framework.shape_builder.ShapeBuilder
  - barycenter.etl.framework.retention.RetentionSweeper
  - barycenter.etl.framework.salt_rotation.SaltRotation
  - barycenter.etl.framework.salt_rotation.DualWriteResult
  - barycenter.etl.framework.adapter_base.AdapterBase
  - barycenter.etl.framework.adapter_base.Category
  - barycenter.etl.framework._audit_helpers.make_event (internal)
affects:
  - packages/barycenter-etl/src/barycenter/etl/framework/__init__.py (barrel re-exports)
  - packages/barycenter-etl/src/barycenter/etl/__init__.py (top-level barrel re-exports)
tech-stack:
  added: []
  patterns:
    - "Repo-relative YAML resolver (parents[6] from framework module file)"
    - "AuditEvent helper module to keep verb call sites consistent with audit SDK schema"
    - "StrEnum for fixed taxonomies (Category)"
    - "frozenset for canonical-table allowlist (ShapeBuilder.CANONICAL)"
    - "Static SQL templates per shape with TRUNCATE+INSERT for staging tables"
key-files:
  created:
    - packages/barycenter-etl/src/barycenter/etl/framework/canary.py
    - packages/barycenter-etl/src/barycenter/etl/framework/cui_gate.py
    - packages/barycenter-etl/src/barycenter/etl/framework/shape_builder.py
    - packages/barycenter-etl/src/barycenter/etl/framework/adapter_base.py
    - packages/barycenter-etl/src/barycenter/etl/framework/retention.py
    - packages/barycenter-etl/src/barycenter/etl/framework/salt_rotation.py
    - packages/barycenter-etl/src/barycenter/etl/framework/_audit_helpers.py
  modified:
    - packages/barycenter-etl/src/barycenter/etl/framework/__init__.py
    - packages/barycenter-etl/src/barycenter/etl/__init__.py
    - packages/barycenter-etl/tests/test_canary.py
    - packages/barycenter-etl/tests/test_cui_gate.py
    - packages/barycenter-etl/tests/test_shape_builder.py
    - packages/barycenter-etl/tests/test_category.py
    - packages/barycenter-etl/tests/test_retention.py
    - packages/barycenter-etl/tests/test_salt_rotation.py
decisions:
  - "AuditEvent schema: created `_audit_helpers.make_event` to centralise event construction. The plan's pseudo-code referenced AuditOutcome.SUCCESS and a `resource=` kwarg, but the audit SDK ships a Pydantic model requiring event_id, occurred_at, actor_id, actor_type, verb, resource_type, outcome (string Literal). Helper closes the gap without forcing every framework module to re-derive the boilerplate. (Rule 1 deviation; see below.)"
  - "Per-call YAML path resolution. Tests reference `compliance/cui-canary-phrases.yaml` (repo-relative). Implemented a `_resolve_yaml_path` shim in canary.py and retention.py that resolves to the repo root (parents[6] from framework files) when the relative path is not present in the test cwd. Established pattern in tests/test_no_novel_ai_zone.py."
  - "AdapterBase.run treats CUI skip as success outcome with verb `etl.skip.cui`. Skip is intentional behaviour, not a failure — auditors need to see it but it does not flag the run."
  - "CUIGate.is_cui_company tolerates both tuple-rows and named-rows from pyodbc for forward-compat; prefers row[0] but falls back to attribute access."
metrics:
  duration_minutes: 18
  completed: "2026-05-02"
  tasks: 2
  files_created: 7
  files_modified: 8
  tests_added: 21
  total_tests_passing: 70
  total_tests_skipped: 4
---

# Phase 2 Plan 4: Framework gate layer (CUI + Canonical + Retention + Salt Rotation + AdapterBase) Summary

Implemented the load-bearing framework code that makes adapters incapable of bypassing the safety properties: CanaryScanner detects CUI markers across text/subject/filename; CUIGate enforces per-record skip for sensitive tables when any CUI tenant exists; ShapeBuilder refuses any AI-zone shape outside the four canonical names; RetentionSweeper deletes rows past their per-class TTL with parameterised SQL; SaltRotation does versioned-pepper dual-write to support ENC-02 rotations without breaking historical pseudonyms; AdapterBase orchestrates table-isolated fail-closed sync, propagating AuditEmitError per CLAUDE.md while continuing past ETLError on other tables.

## Tasks

### Task 1 — CanaryScanner + CUIGate + ShapeBuilder + Category enum

**Commit:** `3b8ed6e`

- TDD RED → tests rewritten to assert behaviour (scan_text/subject/filename, refuse_attachment, should_skip cursor mock chain, ShapeBuilder.CANONICAL frozenset, all-7-Category-members).
- TDD GREEN → 4 framework modules created. Public barrels updated.
- Re-ran full ETL suite (62 passed, 6 skipped Task 2 fixtures).

### Task 2 — RetentionSweeper + SaltRotation + AdapterBase

**Commit:** `1bb7c8d`

- TDD RED → tests rewritten for parameterised DELETE, audit verb, per-tenant TTL override, dual_write distinct pids, open_window/cut_over state persistence.
- TDD GREEN → 3 framework modules created/replaced; AdapterBase Category-only stub replaced with full orchestrator while preserving the enum.
- Public barrels updated; verified `from barycenter.etl import AdapterBase, RetentionSweeper, SaltRotation, DualWriteResult, ...` succeeds.
- Verified missing-CATEGORY ValueError fires on subclass instantiation.
- Final suite: 70 passed, 4 skipped (skipped tests are unrelated Wave-0 stubs in test_pseudonymizer/test_no_body_column for Plan 3 work).

## Verification Performed

```bash
cd packages/barycenter-etl
python -m pytest tests/test_canary.py tests/test_cui_gate.py tests/test_shape_builder.py \
                 tests/test_category.py tests/test_retention.py tests/test_salt_rotation.py -v
# 27 passed
python -m pytest
# 70 passed, 4 skipped
python -c "from barycenter.etl import AdapterBase, RetentionSweeper, SaltRotation, \
              CanaryScanner, CUIGate, ShapeBuilder, Category, DualWriteResult; print('OK')"
# OK; Category has 7 members; CANONICAL has 4 shapes
```

Subclass-without-CATEGORY raises ValueError as required (T-02-21 mitigation verified).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Bug] AuditEvent constructor mismatch**

- **Found during:** Task 1 GREEN (first test run on `test_shape_builder_emits_audit_when_provided`).
- **Issue:** Plan code uses `AuditEvent(verb=..., resource=..., outcome=AuditOutcome.SUCCESS, metadata=...)`. Actual SDK schema (`packages/barycenter-audit/src/barycenter/audit/models.py`) requires `event_id`, `occurred_at`, `actor_id`, `actor_type`, `verb`, `resource_type` (not `resource`), and `outcome` is a string Literal (`"success" | "failure" | "denied"`), not an enum.
- **Fix:** Created `framework/_audit_helpers.py` with `make_event(...)` that fills in event_id (uuid4), occurred_at (now UTC), actor_id (`mi-bary-etl`), actor_type (`service`), and accepts the dynamic fields. All framework call sites use the helper.
- **Files modified:** `framework/_audit_helpers.py` (new), `framework/shape_builder.py`, `framework/retention.py`, `framework/salt_rotation.py`, `framework/adapter_base.py`.
- **Commit:** `3b8ed6e` (helper + first uses), extended in `1bb7c8d`.

**2. [Rule 1 — Bug] Repo-root path resolution off by one**

- **Found during:** Task 1 GREEN (first canary test run).
- **Issue:** Initial `_REPO_ROOT = parents[5]` resolved to `packages/` instead of the worktree root. The framework module path is `packages/barycenter-etl/src/barycenter/etl/framework/canary.py` → `parents[6]` is the repo root.
- **Fix:** Updated to `parents[6]` in `canary.py` and applied the same pattern in `retention.py`.
- **Files modified:** `framework/canary.py`, `framework/retention.py`.
- **Commit:** `3b8ed6e`.

**3. [Rule 2 — Missing functionality] Use timezone-aware datetimes**

- **Found during:** Task 2 implementation review.
- **Issue:** Plan code used `datetime.utcnow()` (deprecated in Python 3.12). Naive datetimes lose UTC information when round-tripped to JSON.
- **Fix:** Used `datetime.now(timezone.utc)` in retention.py and salt_rotation.py for cutoff math, window timestamps, and `_audit_helpers.make_event`.
- **Files modified:** `framework/retention.py`, `framework/salt_rotation.py`, `framework/_audit_helpers.py`.
- **Commit:** `1bb7c8d`.

### Deferred Items

None — all plan tasks completed.

## Threat Model Compliance

| Threat ID | Mitigation Verified |
|-----------|---------------------|
| T-02-18 (audit emit silent failure) | `AdapterBase.run` has `except AuditEmitError: raise` BEFORE the broad `except ETLError` and `except Exception` clauses. AuditEmitError propagates and aborts the run as required. |
| T-02-19 (CUI marker bypass) | CanaryScanner.scan_text/subject/filename delegate to a single regex; AdapterBase._scan_record runs over CUI_CANARY_FIELDS for every record; CUIBoundaryViolation aborts table sync via the ETLError branch. |
| T-02-20 (sweep races sync) | RetentionSweeper sweep_table is callable per-table; cron offset (12:00 UTC vs 06:00 UTC) is enforced by the workflow file (Plan 06 territory) and documented in retention-policy.yaml. |
| T-02-21 (wrong CATEGORY) | AdapterBase.__init__ raises ValueError if `not self.CATEGORY` or `not self.TABLES`. Verified manually. |
| T-02-22 (cross-tenant correlation) | dual_write derives pid_old and pid_new with distinct salt_versions; the MERGE in pseudo.person_map keys on `(tenant_id, email_lower, salt_version)` so versions are distinct rows. |
| T-02-23 (TRUNCATE bypass) | AdapterBase.run executes `TRUNCATE TABLE {qualified}` BEFORE iterating fetch_table. Subclasses cannot override `run()` without re-implementing all the safety properties. |
| T-02-24 (salt rotation skipped audit) | SaltRotation emits a distinct verb per phase: `salt.rotate.open_window`, `salt.rotate.dual_write` (twice per call — once per version), `salt.rotate.cut_over`. |

## Self-Check: PASSED

**Files exist:**

- FOUND: packages/barycenter-etl/src/barycenter/etl/framework/canary.py
- FOUND: packages/barycenter-etl/src/barycenter/etl/framework/cui_gate.py
- FOUND: packages/barycenter-etl/src/barycenter/etl/framework/shape_builder.py
- FOUND: packages/barycenter-etl/src/barycenter/etl/framework/retention.py
- FOUND: packages/barycenter-etl/src/barycenter/etl/framework/salt_rotation.py
- FOUND: packages/barycenter-etl/src/barycenter/etl/framework/adapter_base.py
- FOUND: packages/barycenter-etl/src/barycenter/etl/framework/_audit_helpers.py

**Commits exist:**

- FOUND: 3b8ed6e (Task 1)
- FOUND: 1bb7c8d (Task 2)

**Tests:** 70 passed, 4 skipped (Wave-0 stubs unrelated to this plan).

## Known Stubs

None — every public class is fully implemented. `customer_memory` shape's SQL template is intentionally a no-op (`SELECT 1 WHERE 1 = 0`) per plan §Pattern 3 ("sparse for CW Phase 2; populated in Phase 3+ when agent-derived summaries land"). This is the documented Phase 2 contract, not an unfinished stub.
