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

- [ ] CA policy `bary-ca-mfa-all-users` exists and is enabled (state == "enabled", NOT "enabledForReportingButNotEnforced")
- [ ] CA policy `bary-ca-fido2-privileged` exists and is enabled
- [ ] Sign-in attempt without MFA was rejected (evidence: Sign-In log entry)
- [ ] PIM activation attempt without FIDO2 was rejected (evidence: PIM activation request log)
- [ ] Break-glass account exists with documented exclusion (UPN noted in `compliance/break-glass.md` — not in this file)

**Status:** PENDING — requires Entra Conditional Access Administrator or Security Administrator role.
See `compliance/runbooks/conditional-access-mfa.md` for full creation instructions.

**Evidence:**

```
[pending — paste az rest table output once policies created]
```

```
[pending — paste sign-in log / PIM activation log filenames or excerpts here]
```

### COMP-06 — BAA inventory

- [ ] Microsoft BAA reference (Service Trust Portal attestation) committed and dated in `compliance/baa/microsoft-baa-reference.md`
- [ ] Anthropic BAA signed PDF committed at `compliance/baa/anthropic-baa.pdf`
- [ ] Anthropic ZDR written confirmation committed at `compliance/baa/anthropic-zdr-confirmation.md` (replaced placeholder; all six required fields populated)
- [ ] `compliance/baa-inventory.md` "Last reviewed" and "Next review due" dates populated
- [ ] All three section "Status" fields updated from `_pending_` to `_confirmed [YYYY-MM-DD]_`

**Evidence:**

```
[paste git log of compliance/ commits here]
```

### EGRESS-01 + NETW-03 — Live deny verification

- [ ] Synthetic traffic test: from etl-subnet, attempt `curl https://api.anthropic.com/`. Result: connection denied/timed out.
- [ ] LA query within 5 minutes shows the deny event with `policyid` matching `etl-to-anthropic-deny`.
- [ ] Synthetic traffic test: from services-subnet, attempt `curl https://api.connectwise.com/`. Result: denied.
- [ ] LA query shows `services-to-source-tools-deny` event.
- [ ] Synthetic traffic test: from services-subnet, `curl https://api.anthropic.com/` → allowed (services may reach Anthropic; etl may not). Verifies positive control.
- [ ] Test VMs deleted after verification (sweeper — see T-1-09-05).

**Evidence:**

```
[paste curl exit codes + LA query JSON results here]
```

### AUDIT-03 — WORM lock + Pitfall 7 cleanup

- [ ] `az storage container immutability-policy show` returns `state: Locked`, `immutabilityPeriodSinceCreationInDays: 2190`
- [ ] Attempted shorten via `az storage container immutability-policy extend --period 30` was rejected
- [ ] Test WORM storage account from plan 06 is no longer present (`az storage account show --name stbarywormtest1` returns NotFound)
- [ ] `pytest tests/integration/test_worm_lock.py -v` passes

**Evidence:**

```
[paste az output + pytest output here]
```

### IDENT-05 — PIM dual approval

- [ ] Role management policy on `mi-bary-admin` raw_* role configured with `isApprovalRequired: true` and 2 primary approvers
- [ ] Test activation by admin with single approver was REJECTED (remained pending)
- [ ] Test activation with 2 approvers SUCCEEDED with audit trail in PIM Sign-In logs

**Evidence:**

```
[paste PIM portal screenshot filenames here]
```

### Other Phase 1 sweepers

- [ ] mi-bary-deploy KV Administrator role assignment removed (post Wave-0 cleanup; tracked in plan 05 README) — paste `az role assignment delete` timestamp
- [ ] FortiGate license actually installed on the VM (not just placeholder); `fgt-cli get system status` shows valid Serial-Number and License Status: Valid
- [ ] FortiGate API token created in KV (`kv-bary-dev/secrets/fortigate-api-token`) for nightly drift detector — `attributes.enabled: true`
- [ ] LA workspace ingestion endpoint substituted into FortiGate `policies.json` (no `REPLACED_BY_DEPLOY_PIPELINE` remaining)
- [ ] All audit SDK integration tests passing in CI run on this commit (`gh run list --workflow=audit-chain-validate.yml --limit=1` shows conclusion=success for both `self-test` and `live-validate`)
- [ ] Secret scanning enabled at GitHub repo level (T-1-09-12 mitigation)

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
