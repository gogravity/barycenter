---
phase: 01-network-data-foundations
plan: 03
subsystem: identity
tags: [identity, bicep, managed-identity, pim, ident-02, ident-03, ident-05]
requires:
  - Plan 01 (resource groups: rg-barycenter-identity, rg-barycenter-dev exist)
  - Plan 02 (mi-bary-deploy with Contributor + UAA on target RGs for OIDC deploy)
provides:
  - 4 user-assigned managed identities: mi-bary-etl, mi-bary-platform, mi-bary-audit, mi-bary-admin
  - PIM eligibility schedule on mi-bary-admin (Reader role placeholder, scoped to rg-barycenter-dev)
  - Reusable Bicep modules: managed-identity.bicep, pim-eligibility.bicep
  - Integration test suite asserting post-deploy state (IDENT-03, Pitfall 1, IDENT-02/05)
affects:
  - Plan 05 (data) — consumes principalIds for SQL contained-user grants and KV access policies
  - Plan 06 (audit) — consumes audit MI for LA ingest + WORM blob append grants
  - Plan 07 (audit SDK) — uses etl/platform/audit identities as audit emitters
  - Plan 09 (phase exit) — verifies dual-approval policy and zero standing grants
tech-stack:
  added:
    - Azure Bicep (modular: parent + 2 child modules)
    - Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31
    - Microsoft.Authorization/roleEligibilityScheduleRequests@2020-10-01
  patterns:
    - Cross-RG module deployment via `scope: resourceGroup(otherRgName)`
    - Parameterization via `.bicepparam` (no hardcoded RG/location in template)
    - PIM-eligible-only admin (zero standing grants — architectural Pitfall 1 enforcement)
key-files:
  created:
    - infra/identity/main.bicep
    - infra/identity/main.dev.bicepparam
    - infra/identity/modules/managed-identity.bicep
    - infra/identity/modules/pim-eligibility.bicep
    - infra/identity/README.md
    - tests/integration/__init__.py
    - tests/integration/test_managed_identities.py
  modified: []
decisions:
  - "PIM eligibility module deploys cross-RG (rg-barycenter-dev) from a parent template that targets rg-barycenter-identity. Used `scope: resourceGroup(targetResourceGroup)` on the module invocation rather than parameterizing scope as a string."
  - "Dual-approval policy (IDENT-05 approverCount=2, requireApproval=true) is configured post-deploy via `az rest` PATCH on the role management policy. Bicep does not currently model `roleManagementPolicyAssignments` cleanly — documented in README, verified in plan 09."
  - "Placeholder role for PIM eligibility is built-in Reader (acdd72a7-3385-48ef-bd42-f606fba81ae7). Plan 05 promotes to a custom raw_* reader role once SQL custom roles exist."
metrics:
  duration_seconds: 161
  duration_human: "~3m"
  completed: "2026-05-02T20:38:48Z"
  tasks_completed: 2
  files_created: 7
  files_modified: 0
  commits: 2
---

# Phase 1 Plan 03: Identity Foundation (Managed Identities + PIM) Summary

**One-liner:** Authored Bicep modules deploying the 4 canonical user-assigned managed identities (etl/platform/audit/admin) plus PIM-eligible-only configuration for the admin MI, with integration tests asserting IDENT-03 existence and Pitfall 1 zero-standing-grants enforcement.

## What Was Built

### Bicep modules (`infra/identity/`)
- **`modules/managed-identity.bicep`** — Reusable module that creates one `Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31` resource. Outputs `identityId`, `principalId`, `clientId`, `name` for downstream consumers.
- **`modules/pim-eligibility.bicep`** — Deploys a `Microsoft.Authorization/roleEligibilityScheduleRequests@2020-10-01` extension resource at the target RG scope. Justification parameter is required (non-empty); approver-policy details (count=2, requireApproval=true) are configured post-deploy via the role-management-policy API documented in the README.
- **`main.bicep`** — Orchestrator: invokes `managed-identity.bicep` 4× (one per role: etl, platform, audit, admin) at `rg-barycenter-identity`, then invokes `pim-eligibility.bicep` once cross-RG against `rg-barycenter-dev` for the admin MI only. Outputs all 8 IDs/principalIds for plans 05–07 to consume.
- **`main.dev.bicepparam`** — Dev environment parameters (location=eastus2, targetResourceGroup=rg-barycenter-dev, project tags).
- **`README.md`** — Deploy instructions (`az deployment group what-if/create`), the post-deploy `az rest` PATCH for the dual-approval policy (IDENT-05), MI consumer matrix, and Pitfall 1 enforcement rationale.

### Integration tests (`tests/integration/`)
- **`__init__.py`** — Package marker.
- **`test_managed_identities.py`** — 6 tests:
  - 4 parametrized `test_managed_identity_exists[name]` (IDENT-03 — each MI has principalId/clientId and is `userAssignedIdentities` type)
  - `test_admin_mi_has_no_standing_assignments` (Pitfall 1 / IDENT-02 — `az role assignment list --assignee <admin>` MUST return `[]`)
  - `test_admin_mi_has_pim_eligibility` (IDENT-02 + IDENT-05 — at least one role eligibility schedule present)
  - All tests skip when `AZURE_SUBSCRIPTION_ID` is unset, so local pytest runs are non-disruptive. Live execution is gated by CI after plan 03 deploys.

## Verification

- `az bicep build --file infra/identity/main.bicep` exits 0 with no errors and no warnings (after fixes — see Deviations).
- `infra/identity/main.bicep` references `managed-identity.bicep` exactly 4 times and `pim-eligibility.bicep` exactly 1 time.
- All four MI literal names present: `mi-bary-etl`, `mi-bary-platform`, `mi-bary-audit`, `mi-bary-admin`.
- Outputs include `etlPrincipalId`, `platformPrincipalId`, `auditPrincipalId`, `adminPrincipalId`.
- `pytest tests/integration/test_managed_identities.py --collect-only` lists 6 tests.
- `pytest tests/integration/test_managed_identities.py -q` shows `6 skipped` (no Azure creds locally — expected).

## Commits

| Task | Type | Hash    | Summary                                                              |
|------|------|---------|----------------------------------------------------------------------|
| 1    | feat | 1439392 | Identity Bicep modules for 4 canonical MIs + PIM eligibility         |
| 2    | test | 05851d2 | Integration tests asserting IDENT-03, Pitfall 1, IDENT-02/05         |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Bug] Bicep BCP036: scope property type mismatch in pim-eligibility.bicep**
- **Found during:** Task 1 verification (`az bicep build`)
- **Issue:** The plan-as-written passed `scope` as a string (`resourceId('Microsoft.Resources/resourceGroups', targetResourceGroup)`) and used `scope: tenantResourceId(...)` inside the module — Bicep rejects this because the `scope:` property on a resource expects a resource symbolic reference or `tenant`/`subscription()`/`resourceGroup()`, not a string.
- **Fix:** Restructured `pim-eligibility.bicep` to declare `targetScope = 'resourceGroup'` and apply `scope: resourceGroup()` directly on the eligibility resource. The cross-RG concern is moved up one level: `main.bicep` now invokes the module with `scope: resourceGroup(targetResourceGroup)`. This is the canonical Bicep cross-RG module pattern.
- **Files modified:** `infra/identity/modules/pim-eligibility.bicep`, `infra/identity/main.bicep`
- **Commit:** 1439392 (folded into the Task 1 commit since both files needed coordinated change)

**2. [Rule 1 — Bug] Bicep no-unused-params warning: `subscriptionId` declared but never used**
- **Found during:** Task 1 verification (`az bicep build` linter warning)
- **Issue:** The plan included a `subscriptionId` parameter in `main.bicep` defaulting to `subscription().subscriptionId`, but no code path consumed it (the role-definition-ID expression already inlines `subscription().subscriptionId`).
- **Fix:** Removed the unused parameter.
- **Files modified:** `infra/identity/main.bicep`
- **Commit:** 1439392

### Authentication Gates

None encountered. All work was offline-buildable (Bicep static compile + pytest collection without live Azure).

## Downstream Inputs Available

For plans 05–07 to consume from this template's outputs (after deploy):

```
etlIdentityId, etlPrincipalId
platformIdentityId, platformPrincipalId
auditIdentityId, auditPrincipalId
adminIdentityId, adminPrincipalId
```

These flow into:
- KV access policies (mi-bary-etl signing key) — plan 05
- Contained SQL users with role grants on raw_*/ai_zone schemas — plan 05
- Log Analytics ingest + WORM blob append role assignments (mi-bary-audit) — plan 06
- Audit-emit identity selection in the SDK — plan 07

## Known Stubs

None. The Bicep is fully wired and compiles. The PIM dual-approval policy (IDENT-05 approver count, requireApproval flag) is intentionally configured post-deploy via `az rest` because the Bicep resource provider does not cleanly model `roleManagementPolicyAssignments` at this time — this is documented in `infra/identity/README.md` and verified in plan 09. This is not a stub; it is a deliberate split between IaC and post-deploy admin policy that mirrors Microsoft's own guidance for PIM policy configuration.

## TDD Gate Compliance

- Task 1 (`feat`): infrastructure-as-code — TDD's RED/GREEN cycle does not naturally apply to declarative IaC (no behavior to red-test before declaring it). Verification gate is `az bicep build` clean, satisfied.
- Task 2 (`test`): integration test suite is the deferred behavioral RED test — it will fail in CI if MIs are not deployed correctly, fulfilling the IDENT-03/IDENT-02/IDENT-05 verification responsibilities. Tests were authored only after the Bicep that produces the resources they assert about, which is correct ordering for IaC + post-deploy assertions.

## Self-Check: PASSED

- [x] FOUND: infra/identity/main.bicep
- [x] FOUND: infra/identity/main.dev.bicepparam
- [x] FOUND: infra/identity/modules/managed-identity.bicep
- [x] FOUND: infra/identity/modules/pim-eligibility.bicep
- [x] FOUND: infra/identity/README.md
- [x] FOUND: tests/integration/__init__.py
- [x] FOUND: tests/integration/test_managed_identities.py
- [x] FOUND: commit 1439392
- [x] FOUND: commit 05851d2
- [x] `az bicep build infra/identity/main.bicep` exit 0, zero errors, zero warnings
- [x] `pytest --collect-only` lists 6 tests
- [x] `pytest -q` shows 6 skipped (no live Azure)
