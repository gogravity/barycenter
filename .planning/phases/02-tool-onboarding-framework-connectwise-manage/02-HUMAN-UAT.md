---
status: partial
phase: 02-tool-onboarding-framework-connectwise-manage
source: [02-VERIFICATION.md]
started: 2026-05-02T00:00:00Z
updated: 2026-05-02T00:00:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. First successful etl-cw-nightly run (INT-01)
expected: After merging to main and setting `gh variable set CW_AUTH_MODE --body "basic"`, trigger `gh workflow run etl-cw-nightly.yml` and confirm at least one run completes with `conclusion: success`. Note: fix CR-01/CR-02/CR-03 (see `/gsd-code-review-fix 2`) before running.
result: [pending]

### 2. Salt rotation fire drill (ENC-02 / Phase 2 success criterion 5)
expected: Execute the fire drill script in `salt-rotation-firedrill-evidence.md` against a dev SQL + Key Vault instance. `compliance/salt-rotation-state.yaml` must have `fire_drill.completed: true` with non-null `tenant_id`, `completed_at`, `operator`. `executions[]` must contain `salt.rotate.open_window`, `salt.rotate.dual_write`, `salt.rotate.cut_over` entries.
result: [pending — no dev SQL instance available at phase execution time]

## Summary

total: 2
passed: 0
issues: 0
pending: 2
skipped: 0
blocked: 0

## Gaps
