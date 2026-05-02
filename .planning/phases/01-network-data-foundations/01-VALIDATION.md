---
phase: 1
slug: network-data-foundations
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-05-02
revised: 2026-05-02
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Aligned with plan file paths after revision iteration 1.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (audit SDK + integration tests); az CLI / bicep CLI (infra smoke tests) |
| **Config file** | `packages/barycenter-audit/pyproject.toml` — Wave 0 installs |
| **Quick run command** | `pytest packages/barycenter-audit/tests/ -q --ignore=packages/barycenter-audit/tests/integration` |
| **Full suite command** | `pytest packages/barycenter-audit/tests/ --ignore=packages/barycenter-audit/tests/integration && python scripts/ci/field_class_check.py --check-static && python scripts/ci/field_class_check.py --simulate-untagged && python scripts/ci/chain_validate.py --self-test && python scripts/ci/chain_validate.py --self-test --tampered && python scripts/ci/fortigate_drift.py --self-test && python scripts/ci/fortigate_drift.py --self-test --drifted && python scripts/ci/grant_drift_check.py --self-test && python scripts/ci/grant_drift_check.py --self-test --drifted` |
| **Estimated runtime** | ~90 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest packages/barycenter-audit/tests/ -q --ignore=packages/barycenter-audit/tests/integration`
- **After every plan wave:** Run full suite above
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 90 seconds

---

## Per-Task Verification Map

Aligned with file paths actually created by plans 01–08. Paths use `scripts/ci/` (not `ci/gates/`)
and test file names match what plans 05/06/07 produce.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 1-01-01 | 01 | 0 | infra-skeleton | — | Bicep modules exist in infra/ | manual | `ls infra/networking/ infra/data/ infra/identity/ infra/audit/` | ✅ plan 01 | ⬜ pending |
| 1-04-01 | 04 | 1 | NETW-01 | T-1-04 | FortiGate hub deployed; spoke VNet peered | unit | `az bicep build --file infra/networking/main.bicep` | ✅ plan 04 | ⬜ pending |
| 1-04-02 | 04 | 1 | NETW-02 | T-1-04 | ETL-subnet deny rule blocks Anthropic-bound traffic | smoke | `python scripts/ci/fortigate_drift.py --self-test` | ✅ plan 08 | ⬜ pending |
| 1-04-03 | 04 | 1 | NETW-03 | T-1-04 | Services-subnet deny rule blocks source-tools traffic | smoke | `python scripts/ci/fortigate_drift.py --self-test --drifted` | ✅ plan 08 | ⬜ pending |
| 1-04-04 | 04 | 1 | EGRESS-01 | T-1-04 | Deny events appear in Log Analytics after synthetic test | smoke | `python scripts/ci/fortigate_drift.py` (live, post-deploy) | ✅ plan 08 | ⬜ pending |
| 1-05-01 | 05 | 2 | FOUND-01, FOUND-02 | T-1-05 | Azure SQL private endpoint live; publicNetworkAccess=Disabled | unit | `pytest tests/integration/test_tde_enabled.py -q` | ✅ plan 05 | ⬜ pending |
| 1-05-02 | 05 | 2 | FOUND-03 | T-1-05 | KV bootstrap salt key allows sign, never returns key material | unit | `pytest tests/integration/test_kv_sign.py -q` | ✅ plan 05 | ⬜ pending |
| 1-05-03 | 05 | 2 | FOUND-04 | T-1-05 | raw_* schemas exist with zero grants to platform identity | unit | `pytest tests/integration/test_sql_zero_grants.py -q` | ✅ plan 05 | ⬜ pending |
| 1-05-04 | 05 | 2 | ENC-01 | T-1-05 | TDE state Enabled; AAD-only auth; TLS 1.2+ | unit | `pytest tests/integration/test_tde_enabled.py -q` | ✅ plan 05 | ⬜ pending |
| 1-06-01 | 06 | 2 | AUDIT-01 | T-1-06 | LA workspace + AuditEvents_CL custom table with metadata=dynamic | unit | `pytest tests/integration/test_la_workspace.py -q` | ✅ plan 06 | ⬜ pending |
| 1-06-02 | 06 | 2 | AUDIT-03 | T-1-06 | WORM container 6-year retention LOCKED; cannot be shortened | unit | `pytest tests/integration/test_worm_lock.py -q` | ✅ plan 06 | ⬜ pending |
| 1-07-01 | 07 | 3 | AUDIT-01 | T-1-07 | AuditClient.emit fail-closed across all 3 sink failure modes | unit | `pytest packages/barycenter-audit/tests/test_chain_integrity.py packages/barycenter-audit/tests/test_fail_closed.py -q` | ✅ plan 07 | ⬜ pending |
| 1-07-02 | 07 | 3 | AUDIT-02 | T-1-07 | recording_query context manager emits verb='audit.read' | unit | `pytest packages/barycenter-audit/tests/test_audit_of_audit.py -q` | ✅ plan 07 | ⬜ pending |
| 1-07-03 | 07 | 3 | FOUND-04 | T-1-07 | Sinks propagate exceptions; chain advances across emits | unit | `pytest packages/barycenter-audit/tests/test_sinks.py -q` | ✅ plan 07 | ⬜ pending |
| 1-07-04 | 07 | 3 | AUDIT-01 | T-1-07 | End-to-end live emit advances chain_state head_digest | integration | `pytest packages/barycenter-audit/tests/integration/test_emit_end_to_end.py -q` (CI live job, requires DCE_LOGS_INGESTION_ENDPOINT + DCR_IMMUTABLE_ID + WORM_STORAGE_ACCOUNT + SQL_SERVER_FQDN env vars wired by infra-deploy.yml deploy job) | ✅ plan 07 | ⬜ pending |
| 1-08-01 | 08 | 3 | VER-02 | T-1-08 | CI gate fails PR lacking field-class tag on new column | unit | `python scripts/ci/field_class_check.py --simulate-untagged` | ✅ plan 08 | ⬜ pending |
| 1-08-02 | 08 | 3 | AUDIT-01 | T-1-08 | Chain validation CI gate passes on clean fixture and fires on tampered | unit | `python scripts/ci/chain_validate.py --self-test && python scripts/ci/chain_validate.py --self-test --tampered` | ✅ plan 08 | ⬜ pending |
| 1-08-03 | 08 | 3 | NETW-02 | T-1-08 | FortiGate drift gate self-test passes (clean) and fires (drifted) | unit | `python scripts/ci/fortigate_drift.py --self-test && python scripts/ci/fortigate_drift.py --self-test --drifted` | ✅ plan 08 | ⬜ pending |
| 1-08-04 | 08 | 3 | FOUND-04 | T-1-08 | Grant drift gate (Pitfall 1) self-test passes and fires | unit | `python scripts/ci/grant_drift_check.py --self-test && python scripts/ci/grant_drift_check.py --self-test --drifted` | ✅ plan 08 | ⬜ pending |
| 1-09-01 | 09 | 4 | IDENT-01, IDENT-02, IDENT-04, IDENT-05, COMP-06 | T-1-09 | Manual phase-exit checklist (BAA inventory committed; branch protection verified; PIM dual-approval; Pitfall 7 test container deleted) | manual | runbook validation | ✅ plan 09 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

All scaffolding produced by plan 01:

- [x] `packages/barycenter-audit/` — Python package scaffold with pyproject.toml
- [x] `packages/barycenter-audit/tests/test_chain_integrity.py` — stubs for AUDIT-01 chain validation
- [x] `packages/barycenter-audit/tests/test_fail_closed.py` — xfail stubs for fail-closed (turned green by plan 07)
- [x] `packages/barycenter-audit/tests/conftest.py` — shared fixtures (mock SQL, mock LA sink, mock WORM sink)
- [x] `scripts/ci/field_class_check.py` — implemented in plan 08 with --simulate-untagged self-test
- [x] `scripts/ci/chain_validate.py` — implemented in plan 08 with --self-test [--tampered]
- [x] `scripts/ci/fortigate_drift.py` — implemented in plan 08 with --self-test [--drifted]
- [x] `scripts/ci/grant_drift_check.py` — implemented in plan 08 with --self-test [--drifted]
- [x] `tests/fixtures/chain_good.ndjson` + `chain_tampered.ndjson` — produced by plan 08 task 1
- [x] `tests/fixtures/fortigate_clean.json` + `fortigate_drifted.json` — produced by plan 08 task 1
- [x] `tests/fixtures/sql_perms_clean.json` + `sql_perms_drifted.json` — produced by plan 08 task 1

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| FortiGate hub + spoke live with deny rules active | NETW-01, NETW-02, NETW-03 | Requires Azure provisioning; no emulator | After plan 08 infra-deploy.yml runs, observe live `python scripts/ci/fortigate_drift.py` exits 0 (nightly drift job) |
| Azure SQL private endpoint; publicNetworkAccess=Disabled | FOUND-01 | Requires live Azure SQL | `pytest tests/integration/test_tde_enabled.py` against live env asserts `publicNetworkAccess == "Disabled"` |
| WORM container 6-year retention locked | AUDIT-03 | Irreversible lock — must validate on test container first (Pitfall 7) | Plan 06 README documents the test-container-first procedure; plan 09 phase exit asserts test account is deleted |
| PIM JIT dual-approval enforcement | IDENT-02, IDENT-05 | Requires Azure AD PIM activation | Manual checklist in plan 09 phase exit |
| BAA inventory document available | COMP-06 | Administrative process outside automation | Plan 09 phase exit confirms BAA, Anthropic ZDR, Microsoft HIPAA BAA committed |
| Branch protection rules enforced; admin bypass disabled | IDENT-04 | Requires GitHub admin to verify | Plan 09 phase exit: `gh api repos/:owner/:repo/branches/main/protection` |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or are explicit Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (plan 01 produces all stubs; plan 08 produces fixtures)
- [x] No watch-mode flags
- [x] Feedback latency < 90s
- [x] `nyquist_compliant: true` set in frontmatter
- [x] File paths in this map match the actual paths created by plans (revision iteration 1 alignment)

**Approval:** approved (revision iteration 1, 2026-05-02)
