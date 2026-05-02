---
phase: 01-network-data-foundations
plan: 08
subsystem: ci
tags: [github-actions, oidc, ci, drift-detection, audit-chain, sha-256, fortigate, sql-grants, vier-02, audit-01, netw-02]

requires:
  - phase: 01-network-data-foundations/04
    provides: FortiGate policies.json baseline (NETW-02 drift target)
  - phase: 01-network-data-foundations/05
    provides: sql/00-schemas + sql/10-grants files (VER-02 + Pitfall-1 inputs)
  - phase: 01-network-data-foundations/06
    provides: WORM container (AUDIT-01 live-validate target)
  - phase: 01-network-data-foundations/07
    provides: barycenter.audit SDK (AuditEvent model; chain.py extended here with validate_chain)
provides:
  - VER-02 enforcement via field_class_check.py + field-class-check.yml
  - AUDIT-01 enforcement via chain_validate.py + audit-chain-validate.yml + barycenter.audit.chain.validate_chain
  - NETW-02 enforcement via fortigate_drift.py + nightly infra-drift.yml
  - Pitfall-1 enforcement via grant_drift_check.py + nightly infra-drift.yml
  - OIDC-authenticated PR what-if + main-branch deploy pipeline (mi-bary-whatif / mi-bary-deploy)
  - python-tests.yml regression suite covering all 8 self-test variants
affects: [phase-02, phase-03, phase-04, all future PRs touching infra/, sql/, compliance/]

tech-stack:
  added: [github-actions, azure/login@v2, az-bicep, pyyaml, requests, pyodbc, sqlparse, azure-storage-blob, azure-identity, azure-keyvault-secrets]
  patterns:
    - "CI script self-test mode: every gate has --self-test (clean) and --tampered/--drifted/--simulate-untagged variants so the gate can be regression-tested without live Azure"
    - "Lazy import of azure SDKs inside live-mode functions so self-tests run on minimal Python environments"
    - "Workflow OIDC separation (Pitfall 11): PR jobs use vars.AZURE_WHATIF_CLIENT_ID; main-branch deploy uses vars.AZURE_DEPLOY_CLIENT_ID"
    - "Fixture generation uses deterministic UUIDs / timestamps so chain digests are stable in git"

key-files:
  created:
    - scripts/ci/__init__.py
    - scripts/ci/requirements.txt
    - scripts/ci/field_class_check.py
    - scripts/ci/chain_validate.py
    - scripts/ci/fortigate_drift.py
    - scripts/ci/grant_drift_check.py
    - tests/fixtures/chain_good.ndjson
    - tests/fixtures/chain_tampered.ndjson
    - tests/fixtures/fortigate_clean.json
    - tests/fixtures/fortigate_drifted.json
    - tests/fixtures/sql_perms_clean.json
    - tests/fixtures/sql_perms_drifted.json
    - .github/workflows/infra-deploy.yml
    - .github/workflows/infra-drift.yml
    - .github/workflows/field-class-check.yml
    - .github/workflows/audit-chain-validate.yml
    - .github/workflows/python-tests.yml
  modified:
    - packages/barycenter-audit/src/barycenter/audit/chain.py
    - packages/barycenter-audit/src/barycenter/audit/__init__.py
    - .gitignore

key-decisions:
  - "Implement validate_chain (+ canonicalize_json/compute_digest) in plan 08 instead of waiting on plan 07 — the AUDIT-01 self-test fixture cannot exist without these primitives, and they are pure functions that do not need the SQL/LA/WORM emit path."
  - "SQL line-comment stripping inside parse_create_table — required because compliance comments like '-- JSON list (Phase 3)' contain unbalanced parens that corrupt the depth tracker used by the column splitter."
  - "Paren-aware depth tracker for column splitting — handles NVARCHAR(256) and DEFAULT SYSUTCDATETIME() without splitting mid-expression."
  - "Deterministic chain fixture generation (fixed UUIDs + fixed timestamp) so the NDJSON files are byte-stable in git and review diffs are meaningful."
  - "FortiGate fixture mirrors only the diff-relevant fields (name/action/src_addr/dst_addr) rather than copying policies.json verbatim — keeps the fixture's intent obvious and avoids drift between fixture shape and live API shape."

patterns-established:
  - "Pattern A — Self-test meta-test: every CI gate has a --simulate/--tampered/--drifted mode that proves the gate fires on the failure mode it claims to detect. The self-test exits 0 when the gate correctly fired (which would otherwise be exit nonzero), turning 'gate works' into a CI-checkable property."
  - "Pattern B — OIDC client separation: Pitfall 11 enforced in workflow YAML by gating jobs with `if: github.event_name == 'pull_request'` (whatif client) vs `if: ... github.ref == 'refs/heads/main'` (deploy client)."
  - "Pattern C — Workflow output capture: deploy job writes Bicep outputs into GITHUB_ENV via `jq -r ... >> $GITHUB_ENV` so downstream steps in the same job can consume them without re-running the deployment."

requirements-completed: [VER-02, NETW-02, AUDIT-01]

# Metrics
duration: ~25min
completed: 2026-05-02
---

# Phase 01 Plan 08: CI Gate Wiring Summary

**Four self-tested CI scripts (field_class_check, chain_validate, fortigate_drift, grant_drift_check) plus five OIDC-authenticated GitHub Actions workflows convert plans 01–07's artifacts from "exists" to "enforced on every PR + nightly".**

## Performance

- **Duration:** ~25 min
- **Tasks:** 2
- **Files created:** 17
- **Files modified:** 3
- **Commits:** 2 atomic

## Accomplishments

- VER-02 gate (field_class_check.py) parses every CREATE TABLE in `sql/00-schemas/` and confirms each `raw_*` column appears in `compliance/field-class-registry.yaml` with one of the 4 valid classes. The `--simulate-untagged` meta-test injects a fake column and asserts the gate fires.
- AUDIT-01 gate (chain_validate.py) reads NDJSON entries, recomputes SHA-256 chain from genesis, and fails on any mismatch. Self-test fixtures (clean + tampered) committed; live mode reads the WORM container.
- NETW-02 gate (fortigate_drift.py) diffs FortiGate REST API output against `infra/networking/fortigate-config/policies.json`. Default-deny-all assertion + missing/extra/diverged-policy detection. Self-test fixtures + drifted variant committed.
- Pitfall-1 gate (grant_drift_check.py) parses `sql/10-grants/*.sql` for expected GRANT/DENY and reconciles against `sys.database_permissions` snapshot. Self-test fixture includes an unexpected `intern.alice@gravity.com` principal that the gate must reject.
- Five GitHub Actions workflows wired with OIDC + Pitfall 11 client separation: `infra-deploy.yml` (PR what-if + main-branch deploy in dependency order identity → networking → data → audit), `infra-drift.yml` (nightly cron 06:00 UTC), `field-class-check.yml` (PR), `audit-chain-validate.yml` (PR self-test + scheduled live-validate), `python-tests.yml` (audit SDK pytest + 8 self-test invocations).
- `barycenter.audit.chain.validate_chain` (+ canonicalize_json / compute_digest) implemented so AUDIT-01 self-tests can run without waiting on plan 07's emit path.

## Task Commits

1. **Task 1: CI scripts + fixtures + chain primitives** — `d44e2f3` (feat)
2. **Task 2: GitHub Actions workflows** — `d10873e` (feat)

## Files Created/Modified

### Created
- `scripts/ci/__init__.py` — package marker
- `scripts/ci/requirements.txt` — pyyaml, requests, azure-identity, azure-storage-blob, pyodbc, sqlparse
- `scripts/ci/field_class_check.py` — VER-02 implementation; static parser + paren-aware splitter + comment stripping; `--check-static` / `--check-live` / `--simulate-untagged` modes
- `scripts/ci/chain_validate.py` — AUDIT-01 implementation; self-test (clean + tampered) and live-mode WORM read
- `scripts/ci/fortigate_drift.py` — NETW-02 implementation; FortiGate REST API + Key Vault token; default-deny-all assertion; self-test (clean + drifted)
- `scripts/ci/grant_drift_check.py` — Pitfall-1 implementation; sql/10-grants parser + sys.database_permissions reconciliation; self-test (clean + drifted with unexpected intern principal)
- `tests/fixtures/chain_good.ndjson` — 3-event valid chain (deterministic UUIDs/timestamps)
- `tests/fixtures/chain_tampered.ndjson` — same chain with entry 1 verb mutated post-digest
- `tests/fixtures/fortigate_clean.json` — mirror of policies.json fields the diff compares
- `tests/fixtures/fortigate_drifted.json` — clean minus etl-to-anthropic-deny + flipped action on services-to-anthropic-allow
- `tests/fixtures/sql_perms_clean.json` — 43 rows reflecting current GRANT/DENY state
- `tests/fixtures/sql_perms_drifted.json` — clean + 1 unexpected `intern.alice@gravity.com` principal
- `.github/workflows/infra-deploy.yml` — what-if (PR) + deploy (main); module dependency order
- `.github/workflows/infra-drift.yml` — nightly cron + workflow_dispatch; per-module RG routing
- `.github/workflows/field-class-check.yml` — PR + main; static + meta-test
- `.github/workflows/audit-chain-validate.yml` — PR self-test + scheduled live-validate
- `.github/workflows/python-tests.yml` — audit SDK pytest + 8 self-test invocations

### Modified
- `packages/barycenter-audit/src/barycenter/audit/chain.py` — implemented `canonicalize_json`, `compute_digest`, `validate_chain` (was NotImplementedError stubs)
- `packages/barycenter-audit/src/barycenter/audit/__init__.py` — re-export `canonicalize_json`, `compute_digest`, `validate_chain`
- `.gitignore` — add `.venv-test/` and `*.egg-info/`

## Decisions Made

- **Implemented chain primitives in plan 08 rather than blocking on plan 07.** `validate_chain`, `canonicalize_json`, and `compute_digest` are pure functions with no SQL / LA / WORM dependencies; they belong on the chain object regardless of whether `emit()` is wired yet. AUDIT-01 self-tests cannot run without them. Plan 07's remaining work (`AuditClient.emit`, `read_head_locked`, `update_head`, sinks) is unaffected.
- **Default `--check-static` is the PR-time gate**, not `--check-live`. Live INFORMATION_SCHEMA query requires Azure auth and only runs after deploy; static parsing catches the same drift class without an Azure dependency.
- **Self-test fixtures encode failure modes the gate is supposed to detect.** A regression in the gate that no longer fires on tampered data will fail the self-test job — turning "gate works" into a CI-checkable property rather than human review.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Blocking] Implemented chain validate_chain helper plus canonicalize_json / compute_digest**
- **Found during:** Task 1 (chain_validate.py self-test cannot import what doesn't exist)
- **Issue:** Plan 08 references `from barycenter.audit.chain import validate_chain`, but plan 07 left those primitives as `NotImplementedError` stubs. Without `validate_chain`, the AUDIT-01 self-test could not run, violating the plan's success criteria.
- **Fix:** Implemented `canonicalize_json` (sorted-keys, no-whitespace, allow_nan=False), `compute_digest` (SHA-256 of `prior_hex || canonical`), and `validate_chain` (iterates entries, recomputes digests, raises ChainIntegrityError on mismatch) directly in `packages/barycenter-audit/src/barycenter/audit/chain.py`. Re-exported from `__init__.py`. The remaining stubs (`read_head_locked`, `update_head`, `AuditClient.emit`, sinks) still raise NotImplementedError and remain plan 07's territory.
- **Files modified:** `packages/barycenter-audit/src/barycenter/audit/chain.py`, `packages/barycenter-audit/src/barycenter/audit/__init__.py`
- **Verification:** `python scripts/ci/chain_validate.py --self-test` exits 0 over 3 entries; `--self-test --tampered` exits 0 with the gate firing on entry 1's recomputed-vs-stored digest mismatch.
- **Committed in:** d44e2f3 (Task 1)

**2. [Rule 1 — Bug] SQL line-comment stripping in parse_create_table**
- **Found during:** Task 1 (initial run reported 9/10 columns; `synced_at` missing)
- **Issue:** The CREATE TABLE for `raw_cw.companies` contains an inline SQL comment `-- JSON list (Phase 3)` whose `(` and `)` confused the paren-depth tracker used to split columns. The chunk that should have been the `synced_at` line got fused to the `ai_opt_out_classes` chunk and the column-name regex didn't match `--`.
- **Fix:** Added `_strip_line_comments` helper that removes everything from `--` to end-of-line before the depth tracker runs. Newlines preserved so structure is intact.
- **Files modified:** `scripts/ci/field_class_check.py`
- **Verification:** Re-running `--check-static` reports 10 columns (was 9). All 8 self-tests still pass.
- **Committed in:** d44e2f3 (Task 1, same commit since the fix landed before the first commit)

**3. [Rule 2 — Missing Critical] `.venv-test/` and `*.egg-info/` added to .gitignore**
- **Found during:** Task 1 (post-task `git status` audit)
- **Issue:** Local pip installs (`pip install -e packages/barycenter-audit` and `pip install pyyaml ...`) created `.venv-test/` and `barycenter_audit.egg-info/` artifacts that risk being committed accidentally on a future `git add -A`.
- **Fix:** Added `.venv-test/` and `*.egg-info/` to `.gitignore`.
- **Files modified:** `.gitignore`
- **Verification:** `git status` confirms artifacts no longer surface as untracked.
- **Committed in:** d44e2f3 (Task 1)

---

**Total deviations:** 3 auto-fixed (1 blocking, 1 bug, 1 missing critical)
**Impact on plan:** All three were necessary to satisfy the plan's own acceptance criteria. The chain-primitives implementation is the largest of the three but stays inside the plan's frontmatter `files_modified` list scope (it's a chain.py change, which the plan implicitly requires when it asserts AUDIT-01 self-test must work).

## Issues Encountered

- None beyond the deviations above. All 8 self-test invocations produced the expected exit codes on the first complete run.

## TDD Gate Compliance

This plan is `type: execute` (not `type: tdd`), but both tasks are tagged `tdd="true"`. The test artifacts here are the deterministic NDJSON / JSON fixtures whose mutated variants are themselves the failing-tests; they were committed alongside the implementations because the failure mode (gate doesn't fire) only becomes detectable once both the gate and the tampered fixture exist. There is no separate `test(...)` commit because the fixture-as-test design means the test is data, not code, and lives next to the script that consumes it.

## Threat Flags

None. The artifacts created here are CI gates that detect threats at trust boundaries already enumerated in the plan's `<threat_model>`. No new network endpoints, auth paths, or schema changes were introduced.

## Self-Check: PASSED

Verified all claims:
- `scripts/ci/__init__.py`, `scripts/ci/field_class_check.py`, `scripts/ci/chain_validate.py`, `scripts/ci/fortigate_drift.py`, `scripts/ci/grant_drift_check.py`, `scripts/ci/requirements.txt` — present.
- `tests/fixtures/chain_good.ndjson`, `chain_tampered.ndjson`, `fortigate_clean.json`, `fortigate_drifted.json`, `sql_perms_clean.json`, `sql_perms_drifted.json` — present.
- `.github/workflows/infra-deploy.yml`, `infra-drift.yml`, `field-class-check.yml`, `audit-chain-validate.yml`, `python-tests.yml` — present, all parse as YAML, all declare `permissions.contents: read`, all Azure-touching workflows declare `id-token: write`.
- Commits `d44e2f3` and `d10873e` exist on the worktree branch and contain the expected file sets.
- All 8 CI self-test invocations produced their expected exit codes on the final consolidated run.

## Next Plan Readiness

- Phase 01's CI plane is complete. Plan 09 (branch protection / CODEOWNERS) can now reference these workflow names as required status checks.
- Phase 02's tool-onboarding work can land new sql/00-schemas/*.sql files knowing field-class-check.yml will fail-fast on missing tags.
- Phase 03's gateway can rely on AUDIT-01 nightly drift detection covering its own emitted events.

---
*Phase: 01-network-data-foundations*
*Completed: 2026-05-02*
