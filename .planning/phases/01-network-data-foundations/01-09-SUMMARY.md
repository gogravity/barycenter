---
phase: 01-network-data-foundations
plan: 09
subsystem: compliance
tags: [branch-protection, conditional-access, mfa, fido2, baa, hipaa, phase-exit]

requires:
  - phase: 01-network-data-foundations
    provides: GitHub Actions workflows (plan 08), CODEOWNERS, BAA inventory placeholders, FortiGate policies, WORM audit container
provides:
  - Declarative branch protection ruleset (.github/branch-protection.json)
  - Conditional Access MFA runbook (compliance/runbooks/conditional-access-mfa.md)
  - Phase-exit evidence template with 42 attestation checkboxes
affects: [phase-02-tool-onboarding, phase-03-ai-gateway, phase-04-compliance-posture]

tech-stack:
  added: []
  patterns:
    - "Declarative branch protection via JSON applied with `gh api -X PUT`"
    - "Manual-config runbooks committed to compliance/runbooks/ for primitives that cannot be expressed as Bicep (Conditional Access)"
    - "Phase-exit evidence file as the final attestation gate before next phase begins"

key-files:
  created:
    - .github/branch-protection.json
    - .github/branch-protection.md
    - compliance/runbooks/conditional-access-mfa.md
    - .planning/phases/01-network-data-foundations/phase-exit-evidence.md
  modified: []

key-decisions:
  - "required_status_checks contexts hard-coded to 4 plan-08 job names: what-if, ver-02-static, self-test, unit-tests — drift detection requires updating both the workflow YAML and this JSON in the same PR"
  - "Conditional Access policies documented as a runbook (not Bicep) because Microsoft.Conditional access requires Microsoft Graph API and Bicep coverage is incomplete at Phase 1; runbook explicitly forbids state == enabledForReportingButNotEnforced (Report-only) per T-1-09-02"
  - "Phase 4 idle-session policy (bary-ca-admin-idle-15min) noted but deferred — placeholder kept in runbook so the policy family is discoverable in one location"
  - "Evidence file expanded to 42 checkboxes (plan minimum 25) so each Phase 1 must-have, sweeper, and threat-model mitigation has its own line item"

patterns-established:
  - "Pattern: phase-exit checkpoint plan — one plan at end of each phase that gates on human attestation of items that cannot be tested by CI"
  - "Pattern: branch protection committed as JSON + apply runbook so the protection ruleset is itself version-controlled and reviewable"

requirements-completed: []  # IDENT-01, IDENT-04, COMP-06, EGRESS-01, AUDIT-03 NOT yet complete — gated on human checkpoints (tasks 2, 3, 4)

duration: ~6 min (task 1 only — checkpoints pending)
completed: 2026-05-02 (task 1 only)
---

# Phase 1 Plan 9: Phase Exit Verification Summary

**Authored declarative branch-protection JSON, Conditional Access MFA runbook, and a 42-checkbox phase-exit evidence template — STOPPED at Task 2 checkpoint awaiting human admin to apply branch protection in GitHub and Conditional Access in Entra.**

## Performance

- **Duration:** ~6 min (Task 1 only)
- **Started:** 2026-05-02T21:07:00Z
- **Completed (Task 1):** 2026-05-02T21:13:00Z
- **Tasks completed:** 1 of 4
- **Tasks pending (human checkpoints):** 3 of 4
- **Files created:** 4

## Accomplishments

- `.github/branch-protection.json` — declarative source of truth for `main` protection: `enforce_admins: true` (Pitfall 12), `required_signatures: true`, `require_code_owner_reviews: true`, required CI contexts mapped to plan-08 workflow jobs (`what-if`, `ver-02-static`, `self-test`, `unit-tests`)
- `.github/branch-protection.md` — apply/verify runbook including the Pitfall 12 direct-push rejection test
- `compliance/runbooks/conditional-access-mfa.md` — IDENT-01 manual CA configuration spec covering tenant-wide MFA, FIDO2 authentication strength on privileged operations, break-glass exclusion, and explicit rejection of Report-only state (T-1-09-02)
- `.planning/phases/01-network-data-foundations/phase-exit-evidence.md` — 42-checkbox attestation template covering plan completion (8 plans), IDENT-01, IDENT-04, IDENT-05, COMP-06, EGRESS-01 + NETW-03 deny verification, AUDIT-03 WORM lock + Pitfall 7 cleanup, and 6 additional Phase 1 sweepers

## Task Commits

1. **Task 1: Author branch-protection.json + Conditional Access runbook + phase-exit-evidence template** — `53eeb0a` (feat)

**Tasks 2–4: NOT EXECUTED — blocking human checkpoints (see below).**

## Files Created/Modified

- `.github/branch-protection.json` — declarative GitHub branch protection ruleset
- `.github/branch-protection.md` — admin apply/verify guide
- `compliance/runbooks/conditional-access-mfa.md` — IDENT-01 CA policy manual setup runbook
- `.planning/phases/01-network-data-foundations/phase-exit-evidence.md` — 42-checkbox phase-exit attestation template

## Decisions Made

- **Plan-required `required_status_checks` contexts left exactly as plan specified** (`what-if`, `ver-02-static`, `self-test`, `unit-tests`). Confirmed each maps to a real plan-08 workflow job before authoring: `infra-deploy.yml::what-if`, `field-class-check.yml::ver-02-static`, `audit-chain-validate.yml::self-test`, `python-tests.yml::unit-tests`. The companion `live-validate` job in audit-chain-validate is intentionally NOT a required check — it depends on live Azure and would block PRs when Azure has transient issues.
- **Created `.github/branch-protection.md`** as a small companion file (not strictly required by task acceptance) so the apply command + Pitfall 12 verification procedure live next to the JSON. Cheap insurance against the JSON being applied incorrectly six months later.
- **Evidence file uses 42 checkboxes (vs. plan minimum 25)** to give a separate line for every threat-model mitigation, sweeper, and acceptance criterion. Makes audit review tractable.

## Deviations from Plan

None — plan executed exactly as written for Task 1. Tasks 2–4 are unexecuted human checkpoints.

## Issues Encountered

None.

## User Setup Required

**Tasks 2, 3, 4 require human administrator action** (this is by design — those tasks are typed `checkpoint:human-action` / `checkpoint:human-verify`). See checkpoint section below.

## Checkpoint State

This plan has `autonomous: false`. After completing Task 1, the executor STOPS at the Task 2 checkpoint. Tasks 2, 3, and 4 each require:

### Task 2 — Apply branch protection + Conditional Access (`checkpoint:human-action`)

- **GitHub repo Admin** must run `gh api -X PUT repos/gravity/barycenter/branches/main/protection --input .github/branch-protection.json`
- Verify with `gh api … | jq` and capture output
- Perform Pitfall 12 admin-bypass test: attempt direct push to `main` as admin; the push MUST be rejected — capture the rejection message + timestamp
- **Entra Conditional Access Administrator** must create `bary-ca-mfa-all-users` and `bary-ca-fido2-privileged` per the runbook, set state to `enabled` (not Report-only)
- Test sign-in without MFA (must prompt) and PIM activation without FIDO2 (must require) — capture Sign-In log evidence
- Update `phase-exit-evidence.md` IDENT-01 + IDENT-04 sections with evidence and commit

### Task 3 — Complete BAA inventory (`checkpoint:human-action`)

- Commit signed Anthropic BAA PDF to `compliance/baa/anthropic-baa.pdf`
- Replace `compliance/baa/anthropic-zdr-confirmation.md` placeholder with real ZDR confirmation populating all six required fields (date, signatory, workspace IDs, pinned model versions, no-retention statement, BAA reference)
- Update Microsoft BAA reference with latest Service Trust Portal attestation date
- Update `compliance/baa-inventory.md` "Last reviewed" / "Next review due" / Status fields
- Update `phase-exit-evidence.md` COMP-06 section and commit
- **Documented exception:** if Anthropic BAA is not yet signed by phase exit, written commitment from Anthropic with target signing date may be committed in lieu of the PDF, AND ZDR confirmation must be in writing. The unsigned-BAA exception is hard-blocked at Phase 3 entry.

### Task 4 — Live verification (`checkpoint:human-verify`)

- EGRESS-01: spin up test VMs in `etl-subnet` and `services-subnet`, run synthetic curls against Anthropic and CW Manage, query Log Analytics for deny events with matching `policyid` (`etl-to-anthropic-deny`, `services-to-source-tools-deny`); positive control: services → Anthropic must succeed; delete test VMs after verification (T-1-09-05 sweeper)
- AUDIT-03: verify `az storage container immutability-policy show` returns `state: Locked`, `immutabilityPeriodSinceCreationInDays: 2190`; attempt to shorten (must fail); run `pytest tests/integration/test_worm_lock.py`
- Pitfall 7 cleanup: confirm `stbarywormtest1` returns NotFound; if not, delete it
- IDENT-05: verify PIM dual approval flow on `mi-bary-admin` raw_* role — single approver test rejects, two-approver test succeeds
- Sweepers: FortiGate license + serial via `fgt-cli get system status`, KV `fortigate-api-token` enabled, `policies.json` substituted (no `REPLACED_BY_DEPLOY_PIPELINE`), audit-chain-validate workflow green, mi-bary-deploy KV Administrator removed, GitHub secret scanning enabled
- Mark all checkboxes `[x]`, paste evidence, sign, and commit `phase-exit-evidence.md`

## Next Phase Readiness

**Phase 2 (Tool Onboarding Framework + ConnectWise Manage) is BLOCKED until tasks 2–4 are completed and `phase-exit-evidence.md` is signed.**

After tasks 2–4 are signed off:

- IDENT-01, IDENT-04, IDENT-05, COMP-06, EGRESS-01, NETW-03, AUDIT-03 are validated and Phase 2 may begin
- The `requirements-completed` array in this SUMMARY frontmatter must be updated to `[IDENT-01, IDENT-04, COMP-06, EGRESS-01, AUDIT-03]` once tasks 2–4 are executed (current value `[]` reflects task-1-only execution)
- `phase-exit-evidence.md` becomes required reading for Phase 2 planning

## Self-Check

After writing this SUMMARY, verifying claims:

- `.github/branch-protection.json` — FOUND
- `.github/branch-protection.md` — FOUND
- `compliance/runbooks/conditional-access-mfa.md` — FOUND
- `.planning/phases/01-network-data-foundations/phase-exit-evidence.md` — FOUND
- Commit `53eeb0a` — FOUND in git log
- All plan-specified `<verify><automated>` checks passed (JSON parse + grep set)

## Self-Check: PASSED

---
*Phase: 01-network-data-foundations*
*Plan 9 — Task 1 complete; tasks 2–4 awaiting human admin checkpoints*
*Updated: 2026-05-02*
