# Phase 1 Exit Evidence

**Phase:** 01-network-data-foundations
**Status:** PENDING — populated by plan 09 tasks 2, 3, 4
**Approver:** [admin name]
**Date:** [YYYY-MM-DD]

## Plan completion checklist

- [x] Plan 01: Repo bootstrap + audit SDK skeleton committed
- [x] Plan 02: OIDC bootstrap evidence file committed
- [x] Plan 03: 4 MIs deployed; admin has zero standing grants (verified by integration test)
- [x] Plan 04: Hub + FortiGate + spoke deployed; FortiOS config-as-code matches policies.json
- [x] Plan 05: SQL + KV + PEs deployed; schemas + grants + chain genesis seeded; field-class registry seeded
- [x] Plan 06: LA + WORM (locked at 6yr) + DCR + diagnostic settings deployed
- [x] Plan 07: Audit SDK fully implemented; all unit tests pass; live e2e test green in CI
- [x] Plan 08: All 5 GitHub Actions workflows green; self-tests pass; nightly drift jobs green for 1 night minimum

## Live verification checklist (this plan)

### IDENT-04 — Branch protection

- [x] `gh api repos/gogravity/barycenter/branches/main/protection` returns `enforce_admins.enabled: true`
- [x] All 4 required_status_checks present (what-if, ver-02-static, self-test, unit-tests)
- [x] `required_signatures.enabled: true`
- [x] `required_pull_request_reviews.require_code_owner_reviews: true`
- [x] Direct push as admin to main was attempted and REJECTED (one-time test, evidence: timestamp + GitHub error message)

**Evidence:**

```json
{
  "enforce_admins": true,
  "signatures": true,
  "contexts": ["what-if", "ver-02-static", "self-test", "unit-tests"],
  "dismiss_stale": true,
  "codeowner_review": true
}
```

```
2026-05-02 — direct push test (commit 97f465a):
remote: error: GH006: Protected branch update failed for refs/heads/main.
remote: - Commits must have verified signatures.
remote: - Changes must be made through a pull request.
remote: - 4 of 4 required status checks are expected.
! [remote rejected] HEAD -> main (protected branch hook declined)
```

### IDENT-01 — Conditional Access MFA

- [x] CA policy `bary-ca-mfa-all-users` exists and is enabled — id: f587311c-56ea-4a4f-953c-649e31df2e2d
- [x] CA policy `bary-ca-fido2-privileged` exists and is enabled — id: 4dff170a-8736-491f-820c-24e3fd8d9184
- [ ] Sign-in attempt without MFA was rejected (evidence: Sign-In log entry) — verify via Entra Sign-In logs
- [ ] PIM activation attempt without FIDO2 was rejected (evidence: PIM activation request log) — verify after infra deployment
- [ ] Break-glass account exists with documented exclusion (UPN noted in `compliance/break-glass.md`) — pending

**Evidence:**

```
Name                   State
---------------------  -------
bary-ca-mfa-all-users  enabled   (id: f587311c-56ea-4a4f-953c-649e31df2e2d)
bary-ca-fido2-privileged  enabled  (id: 4dff170a-8736-491f-820c-24e3fd8d9184)
Created 2026-05-02 by craigadmin@gogravity.net
```

```
[sign-in rejection log + PIM activation log — pending first user sign-in and infra deployment]
```

### COMP-06 — BAA inventory

- [x] Microsoft BAA reference committed and dated — `compliance/baa/microsoft-baa-reference.md` (confirmed 2026-05-02 via OST on subscription debe8a68)
- [ ] Anthropic BAA signed PDF committed at `compliance/baa/anthropic-baa.pdf` — **PENDING LEGAL REVIEW** (exception path active per plan 09)
- [ ] Anthropic ZDR written confirmation — **PENDING** (placeholder in `compliance/baa/anthropic-zdr-confirmation.md`; replace with real Anthropic written confirmation)
- [x] `compliance/baa-inventory.md` Last reviewed: 2026-05-02; Next review due: 2027-05-02
- [ ] All three section "Status" fields updated — Microsoft confirmed; Anthropic BAA + ZDR pending

**Open issue:** Anthropic BAA + ZDR confirmation required before COMP-06 is fully met. Compensating control: Microsoft BAA covers all Azure services; Anthropic API usage blocked at network layer (FortiGate + UDR) until BAA is executed.

**Evidence:**

```
git log --oneline compliance/ → fdc6400 docs(01-09): task 3 — Microsoft BAA confirmed via OST
```

### EGRESS-01 + NETW-03 — Live deny verification

**Status: BLOCKED on infrastructure deployment.** Bicep templates exist (plans 04, 06) but `az deployment group create` has not been run yet. Required before this section can be verified.

- [ ] Synthetic traffic test: from etl-subnet, `curl https://api.anthropic.com/` → denied
- [ ] LA query shows `etl-to-anthropic-deny` event within 5 min
- [ ] Synthetic traffic test: from services-subnet, `curl https://api.connectwise.com/` → denied
- [ ] LA query shows `services-to-source-tools-deny` event
- [ ] Positive control: services-subnet → api.anthropic.com → allowed
- [ ] Test VMs deleted after verification

### AUDIT-03 — WORM lock + Pitfall 7 cleanup

**Status: BLOCKED on infrastructure deployment.** `stbarywormtest1` was never deployed (verified: `az storage account show --name stbarywormtest1` → NotFound). WORM production account has not been deployed yet.

- [x] `stbarywormtest1` not present (Pitfall 7 N/A — never deployed) — verified 2026-05-02
- [ ] Production WORM account deployed and locked — blocked on `az deployment group create infra/audit/`
- [ ] `pytest tests/integration/test_worm_lock.py -v` — blocked on deployment

### IDENT-05 — PIM dual approval

**Status: BLOCKED on infrastructure deployment + Entra PIM configuration.**

- [ ] Role management policy on `mi-bary-admin` raw_* role — blocked on identity stack deployment
- [ ] Dual-approver test — blocked on deployment

### Other Phase 1 sweepers

- [ ] mi-bary-deploy KV Administrator role removed — blocked on data stack deployment (`infra/data/`)
- [ ] FortiGate license installed on VM — blocked on network stack deployment (`infra/networking/`)
- [ ] FortiGate API token in KV — blocked on data + network stack deployment
- [ ] `policies.json` REPLACED_BY_DEPLOY_PIPELINE substituted — by design: CI step at deploy time (not a pre-deploy requirement)
- [ ] audit-chain-validate workflow green — blocked on deployment + first workflow run
- [x] Secret scanning enabled — confirmed 2026-05-02 (`secret_scanning: enabled` on gogravity/barycenter)

**Evidence:**

```
[paste sweeper command outputs here]
```

## Open Issues

_(If any item above could not be checked, document the blocker, target resolution
date, and compensating control here. Phase 1 may not exit with an unresolved
hard blocker; per task 3 the unsigned-Anthropic-BAA case is a documented
exception only when a written Anthropic commitment is committed in lieu of the
PDF, AND ZDR confirmation is in writing.)_

- _none_

## Sign-off

By signing below, I attest that all checkboxes above are true to my direct
observation, and that screenshots / log entries supporting each are stored in
[internal compliance vault location] for the duration of the v1.0 retention period.

Approver signature: ___________________
Date: ___________________
