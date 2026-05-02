---
phase: 1
slug: network-data-foundations
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-02
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (audit SDK unit tests); bash/az CLI (infra smoke tests) |
| **Config file** | `packages/barycenter-audit/pyproject.toml` — Wave 0 installs |
| **Quick run command** | `pytest packages/barycenter-audit/tests/ -q` |
| **Full suite command** | `pytest packages/barycenter-audit/tests/ && bash ci/smoke-tests/run-all.sh` |
| **Estimated runtime** | ~90 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest packages/barycenter-audit/tests/ -q`
- **After every plan wave:** Run `pytest packages/barycenter-audit/tests/ && bash ci/smoke-tests/run-all.sh`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 90 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 1-01-01 | 01 | 0 | FOUND-01 | — | Bicep modules exist in infra/ | manual | `ls infra/networking/ infra/data/ infra/identity/ infra/audit/` | ❌ W0 | ⬜ pending |
| 1-01-02 | 01 | 1 | NETW-01 | T-1-01 | FortiGate hub deployed; spoke VNet peered | manual | `az network vnet peering show --name spoke-to-hub --resource-group rg-barycenter-hub --vnet-name vnet-barycenter-spoke` | ❌ W0 | ⬜ pending |
| 1-01-03 | 01 | 1 | NETW-02 | T-1-02 | ETL-subnet deny rule blocks Anthropic-bound traffic | manual | `bash ci/smoke-tests/fortigate_deny_test.sh --subnet etl --target anthropic-egress` | ❌ W0 | ⬜ pending |
| 1-01-04 | 01 | 1 | NETW-03 | T-1-03 | Services-subnet deny rule blocks source-tools traffic | manual | `bash ci/smoke-tests/fortigate_deny_test.sh --subnet services --target source-tools` | ❌ W0 | ⬜ pending |
| 1-01-05 | 01 | 1 | EGRESS-01 | T-1-04 | Deny events appear in Log Analytics after synthetic test | manual | `bash ci/smoke-tests/fortigate_drift.py --check-deny-events` | ❌ W0 | ⬜ pending |
| 1-02-01 | 02 | 1 | FOUND-02 | — | Azure SQL private endpoint live; publicNetworkAccess=Disabled | manual | `az sql server show --name sql-barycenter --resource-group rg-barycenter-data --query publicNetworkAccess` | ❌ W0 | ⬜ pending |
| 1-02-02 | 02 | 1 | FOUND-03 | T-1-05 | raw_* schemas exist with zero grants to platform identity | manual | `bash ci/smoke-tests/sql_schema_check.sh --assert-no-grant platform raw_etl raw_crm raw_ehr` | ❌ W0 | ⬜ pending |
| 1-02-03 | 02 | 2 | VER-02 | — | CI gate fails PR lacking field-class tag on new column | unit | `python ci/gates/field_class_check.py --test-mode` | ❌ W0 | ⬜ pending |
| 1-03-01 | 03 | 2 | AUDIT-01 | T-1-06 | Audit event written with SHA-256 hash chained to prior event | unit | `pytest packages/barycenter-audit/tests/test_chain.py -v` | ❌ W0 | ⬜ pending |
| 1-03-02 | 03 | 2 | AUDIT-02 | T-1-07 | Audit events mirrored to WORM blob; 6-year retention locked | manual | `az storage container immutability-policy show --account-name stbarycenterworm --container-name audit-worm` | ❌ W0 | ⬜ pending |
| 1-03-03 | 03 | 2 | AUDIT-03 | T-1-08 | Audit-of-audit: querying audit log produces a self-audit entry | unit | `pytest packages/barycenter-audit/tests/test_self_audit.py -v` | ❌ W0 | ⬜ pending |
| 1-04-01 | 04 | 1 | IDENT-01 | — | All 4 managed identities exist with no long-lived secrets | manual | `bash ci/smoke-tests/identity_check.sh --assert-no-secrets etl platform audit admin` | ❌ W0 | ⬜ pending |
| 1-04-02 | 04 | 2 | IDENT-02 | T-1-09 | PIM JIT dual-approval is only path to raw_* | manual | `bash ci/smoke-tests/pim_check.sh --assert-jit raw_etl raw_crm raw_ehr` | ❌ W0 | ⬜ pending |
| 1-04-03 | 04 | 2 | IDENT-03 | — | Main branch protected; signed commits + CI required | manual | `gh api repos/:owner/:repo/branches/main/protection` | ❌ W0 | ⬜ pending |
| 1-04-04 | 04 | 2 | IDENT-04 | T-1-10 | GitHub OIDC subject claim branch-scoped per environment | manual | `az identity federated-credential list --name mi-bary-deploy --resource-group rg-barycenter-identity` | ❌ W0 | ⬜ pending |
| 1-04-05 | 04 | 2 | IDENT-05 | — | No wildcard OIDC subject claims on prod credential | manual | `bash ci/smoke-tests/oidc_scope_check.sh --assert-no-wildcard prod` | ❌ W0 | ⬜ pending |
| 1-05-01 | 05 | 2 | ENC-01 | T-1-11 | HMAC salts in KV as oct-HSM keys; sign op logged, key never returned | unit | `pytest packages/barycenter-audit/tests/test_hmac_kv.py -v` | ❌ W0 | ⬜ pending |
| 1-05-02 | 05 | 3 | COMP-06 | — | BAA inventory doc committed to repo | manual | `git log --all --oneline -- docs/compliance/baa-inventory.md` | ❌ W0 | ⬜ pending |
| 1-05-03 | 05 | 3 | FOUND-04 | — | Chain validation CI gate passes | unit | `python ci/gates/chain_validate.py --test-mode` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `packages/barycenter-audit/` — Python package scaffold with pyproject.toml
- [ ] `packages/barycenter-audit/tests/test_chain.py` — stubs for AUDIT-01 chain validation
- [ ] `packages/barycenter-audit/tests/test_self_audit.py` — stubs for AUDIT-03 self-audit
- [ ] `packages/barycenter-audit/tests/test_hmac_kv.py` — stubs for ENC-01 HMAC sign op
- [ ] `packages/barycenter-audit/tests/conftest.py` — shared fixtures (mock KV, mock DCR endpoint)
- [ ] `ci/gates/field_class_check.py` — stub accepting --test-mode flag
- [ ] `ci/gates/chain_validate.py` — stub accepting --test-mode flag
- [ ] `ci/smoke-tests/fortigate_deny_test.sh` — stub for NETW-02/03 deny testing
- [ ] `ci/smoke-tests/fortigate_drift.py` — stub for EGRESS-01 drift check
- [ ] `ci/smoke-tests/run-all.sh` — orchestrator for all smoke tests

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| FortiGate hub + spoke live with deny rules active | NETW-01, NETW-02, NETW-03 | Requires Azure provisioning; no emulator | Run synthetic traffic tests via `ci/smoke-tests/fortigate_deny_test.sh` after Bicep deploy |
| Azure SQL private endpoint; publicNetworkAccess=Disabled | FOUND-02 | Requires live Azure SQL | `az sql server show ... --query publicNetworkAccess` returns "Disabled" |
| WORM container 6-year retention locked | AUDIT-02 | Irreversible lock — must validate on test container first | Create 1-day-retention test container, lock, validate, then proceed with prod 6-year lock |
| PIM JIT dual-approval enforcement | IDENT-02 | Requires Azure AD PIM activation | Attempt direct role assignment to raw_* schema; confirm it is blocked without PIM approval |
| BAA inventory document available | COMP-06 | Administrative process outside automation | Confirm BAA, Anthropic ZDR, and Microsoft HIPAA BAA docs received and committed |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 90s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
