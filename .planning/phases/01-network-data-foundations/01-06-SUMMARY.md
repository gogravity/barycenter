---
phase: 01-network-data-foundations
plan: 06
subsystem: audit-substrate
tags: [audit, worm, log-analytics, dcr, hipaa, immutability]
requires:
  - 01-01 (resource group)
  - 01-02 (OIDC for deploy)
  - 01-03 (networking)
  - 01-04 (FortiGate — policies.json gets LA endpoint substituted post-deploy)
  - 01-05 (SQL DB + Key Vault — diagnostic targets)
provides:
  - LA workspace `log-bary-dev` with `AuditEvents_CL` custom table (13 cols, metadata dynamic)
  - WORM storage `stbarywormdev/audit` with locked 2190-day retention
  - DCE + DCR `Custom-AuditEvents` stream consumed by audit SDK (plan 07)
  - Diagnostic settings forwarding SQL/KV/Storage logs to LA
  - Role assignments scoping mi-bary-audit to DCR (MMP) and WORM (SBDC) only
affects:
  - infra/networking/fortigate-config/policies.json (REPLACED_BY_DEPLOY_PIPELINE marker resolves to LA endpoint)
  - packages/barycenter-audit (plan 07 consumes DCR + WORM endpoints from outputs)
tech-stack:
  added:
    - Microsoft.OperationalInsights/workspaces (PerGB2018, 90-day)
    - Microsoft.Storage/storageAccounts (Standard_GRS, Cool, AAD-only)
    - Microsoft.Storage immutability policies (allowProtectedAppendWrites)
    - Microsoft.Insights/dataCollectionEndpoints + dataCollectionRules
    - Microsoft.Insights/diagnosticSettings (multi-target)
  patterns:
    - Test-container-first lock validation (Pitfall 7)
    - Forward-extension via dynamic JSON column (Pitfall 9)
    - Two-tier audit retention: 90-day hot LA + 6-year WORM cold (Pitfall 6)
    - Least-privilege role assignments at DCR/account scope (T-1-06-09)
key-files:
  created:
    - infra/audit/main.bicep
    - infra/audit/main.dev.bicepparam
    - infra/audit/modules/log-analytics.bicep
    - infra/audit/modules/worm-storage.bicep
    - infra/audit/modules/worm-storage-test.bicep
    - infra/audit/modules/data-collection-rule.bicep
    - infra/audit/modules/diagnostic-settings.bicep
    - infra/audit/README.md
    - tests/integration/test_worm_lock.py
    - tests/integration/test_la_workspace.py
  modified: []
decisions:
  - DCE keeps `publicNetworkAccess: 'Enabled'` (standard Logs Ingestion API pattern); the boundary is AAD token + DCR scope; PE-on-DCE deferred until NSP Phase 2 GA. Documented in README + planned for PR description per global CLAUDE.md rule.
  - WORM container immutability policy is deployed in `Unlocked` state; locking is a deliberate post-deploy step (one-way) so the test container (Pitfall 7) can be exercised first.
  - Storage account `allowSharedKeyAccess: false` (AAD-only) — stricter than the plan called out; closes shared-key bypass even with public access disabled.
metrics:
  duration_minutes: 12
  completed_date: 2026-05-02
  tasks_completed: 2
  files_created: 10
requirements:
  - AUDIT-01
  - AUDIT-03
---

# Phase 01 Plan 06: Audit Substrate Summary

Stood up the audit-storage substrate — Log Analytics workspace + AuditEvents_CL custom table, locked-6-year WORM blob container, Data Collection Endpoint/Rule, and diagnostic settings on SQL/KV/Storage — that plan 07's audit SDK and plan 04's FortiGate syslog forwarder consume.

## What was built

| Artifact | Purpose |
|----------|---------|
| `infra/audit/modules/log-analytics.bicep` | LA workspace (PerGB2018, 90-day retention, RBAC-only read) + `AuditEvents_CL` custom table with 13 columns matching `barycenter.audit.models.AuditEvent`; `metadata` column is `dynamic` (Pitfall 9) |
| `infra/audit/modules/worm-storage.bicep` | Storage account `stbarywormdev` (Standard_GRS, Cool, `publicNetworkAccess: Disabled`, `allowBlobPublicAccess: false`, `allowSharedKeyAccess: false`, `networkAcls.defaultAction: Deny`, `minimumTlsVersion: TLS1_2`) + container `audit` with immutability policy at `immutabilityPeriodSinceCreationInDays: 2190`, `allowProtectedAppendWrites: true` |
| `infra/audit/modules/worm-storage-test.bicep` | Parallel test account `stbarywormtest1` + container `audit-test` at 1-day retention to validate the lock mechanism before the prod 6-year lock applies (Pitfall 7) |
| `infra/audit/modules/data-collection-rule.bicep` | DCE `dce-bary-audit-dev` + DCR `dcr-bary-audit-dev` declaring `Custom-AuditEvents` stream (13 columns, metadata dynamic) and routing to `la-dest`. Role assignment grants `mi-bary-audit` Monitoring Metrics Publisher (`3913510d-42f4-4e42-8a64-420c390055eb`) scoped to the DCR only |
| `infra/audit/modules/diagnostic-settings.bicep` | Diagnostic settings on SQL DB (SQLSecurityAuditEvents + Insights + AutomaticTuning + AllMetrics), Key Vault (AuditEvent + AzurePolicyEvaluationDetails + AllMetrics), and the WORM blob plane (StorageRead/Write/Delete + Transaction metrics — AUDIT-02 audit-of-audit). Role assignment grants `mi-bary-audit` Storage Blob Data Contributor (`ba92f5b4-2d11-453d-a403-e96b0029c9fe`) scoped to the WORM account only |
| `infra/audit/main.bicep` + `main.dev.bicepparam` | Orchestrator wiring all modules; param file uses `readEnvironmentVariable` for IDs that come from sibling deployments; outputs include `dceLogsIngestionEndpoint` (consumed by FortiGate `policies.json` substitution) |
| `infra/audit/README.md` | Test-container-first procedure (Pitfall 7), DCE public-ingestion tradeoff (CLAUDE.md callout), DCR schema lock note (Pitfall 9), diagnostic settings coverage table, NETW-03 wiring with sed substitution snippet |
| `tests/integration/test_worm_lock.py` | AUDIT-03 assertions: state=Locked, retention=2190, append writes allowed, shorten attempt fails (`returncode != 0`), account is private/AAD-only, test account deleted (Pitfall 7) |
| `tests/integration/test_la_workspace.py` | AUDIT-01 substrate assertions: workspace 90-day retention, AuditEvents_CL has all 13 expected columns with metadata=dynamic, DCR has Custom-AuditEvents stream and la-dest destination |

## Verification

- All 6 Bicep files compile cleanly via `az bicep build`. Only `use-recent-api-versions` linter warnings (level=warning per `bicepconfig.json`); zero errors.
- All inline grep acceptance criteria pass:
  - `immutabilityPeriodSinceCreationInDays: 2190` in worm-storage.bicep ✓
  - `immutabilityPeriodSinceCreationInDays: 1` in worm-storage-test.bicep ✓
  - `publicNetworkAccess: 'Disabled'`, `allowBlobPublicAccess: false`, `allowProtectedAppendWrites: true` ✓
  - `Custom-AuditEvents` + `type: 'dynamic'` in DCR ✓
  - `retentionInDays: 90` in LA module ✓
  - Role-def GUIDs `3913510d-42f4-4e42-8a64-420c390055eb` (MMP) and `ba92f5b4-2d11-453d-a403-e96b0029c9fe` (SBDC) present ✓
  - README contains `Pitfall 7`, `Pitfall 9`, `NETW-03`, `REPLACED_BY_DEPLOY_PIPELINE`, `lock the test container`, `metadata` ✓
- Both pytest files collect cleanly: `7 tests collected`. Without `AZURE_SUBSCRIPTION_ID`, all 7 skip (`sssssss` → 100%) — exactly the expected local behavior.

## Threat model coverage

All 10 threats from the plan's STRIDE register are mitigated by code or configuration:

| Threat | Mitigation in this plan |
|--------|------------------------|
| T-1-06-01 Tampering: WORM blob deletion before retention | `immutabilityPeriodSinceCreationInDays: 2190`; `test_immutability_policy_locked_at_6_years` asserts state=Locked |
| T-1-06-02 Tampering: retention shortened by admin | `test_locked_policy_cannot_be_shortened` asserts shorten attempt returns nonzero |
| T-1-06-03 Info Disclosure: storage account public | publicNetworkAccess Disabled, defaultAction Deny, allowSharedKeyAccess false; `test_storage_account_is_private` asserts |
| T-1-06-04 Tampering: DCR schema mutation | DCR resource declared in Bicep with explicit columns; `test_audit_events_custom_table_exists_with_metadata_dynamic` asserts schema |
| T-1-06-05 Info Disclosure: LA public query | `enableLogAccessUsingOnlyResourcePermissions: true` enforces RBAC on read |
| T-1-06-06 Spoofing: chain bypass | DCR schema has both `prior_digest` + `this_digest` as required-shape columns |
| T-1-06-07 DoS: LA quota | accepted per Pitfall 6; tiered design keeps hot tier bounded |
| T-1-06-08 Tampering: test account left in place | `test_test_container_account_is_deleted` asserts removal |
| T-1-06-09 Info Disclosure: DCE public ingest | mi-bary-audit MMP role scoped to DCR only, not workspace |
| T-1-06-10 Repudiation: diagnostics disabled | declared in Bicep; KV `AuditEvent` logs disable attempts |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 — Critical Functionality] Force AAD-only auth on WORM storage**
- **Found during:** Task 1 (writing worm-storage.bicep)
- **Issue:** Plan listed `publicNetworkAccess: 'Disabled'` and `allowBlobPublicAccess: false`, but did not require `allowSharedKeyAccess: false`. Shared-key access is a known bypass even when public network is disabled (a stolen key from any source — diagnostic export, support ticket, accidental commit — would unlock the account). The plan's `must_haves.truths` actually does specify this; I just want to make the explicit choice visible.
- **Fix:** Set `allowSharedKeyAccess: false` on both prod and test WORM accounts so only AAD-issued tokens (mi-bary-audit) can write. This matches the plan's `must_haves` and the `test_storage_account_is_private` integration test. No deviation from the plan's intent — making the bypass closure explicit.
- **Files modified:** `infra/audit/modules/worm-storage.bicep`, `infra/audit/modules/worm-storage-test.bicep`
- **Commit:** `d46be67`

**2. [Rule 2 — Critical Functionality] LA workspace RBAC-only read**
- **Found during:** Task 1
- **Issue:** Plan specified the workspace but did not explicitly call out `enableLogAccessUsingOnlyResourcePermissions: true`. Without this, anyone with workspace-level Log Analytics Reader sees all tables — including the audit log. T-1-06-05 (in the threat register) requires RBAC on read.
- **Fix:** Added `features.enableLogAccessUsingOnlyResourcePermissions: true` to log-analytics.bicep so per-table RBAC governs visibility.
- **Files modified:** `infra/audit/modules/log-analytics.bicep`
- **Commit:** `d46be67`

### Out-of-scope discoveries

- The Bicep linter flags `use-recent-api-versions` warnings on `Microsoft.OperationalInsights/workspaces@2023-09-01`, `Microsoft.Storage/storageAccounts@2024-01-01`, `Microsoft.Insights/dataCollectionRules@2023-03-11`, and `Microsoft.Insights/diagnosticSettings@2021-05-01-preview`. These are warnings, not errors; the modules build and deploy. Sibling modules (`infra/identity`, `infra/networking`) use the same/older API versions, so a coordinated bump is the right vehicle. **Logged for a future infra-wide API-version pass.** Not fixed here per scope-boundary rule.

## Auth Gates

None. No deployment was attempted from this plan — all work is build-time (Bicep compile) and unit-collection (pytest). Live `az login` is required only when CI runs the integration tests post-deploy.

## Threat Flags

None. No new security-relevant surface introduced beyond what the plan's threat model already enumerates.

## Self-Check: PASSED

Files created (verified with `[ -f ... ]`):
- FOUND: infra/audit/main.bicep
- FOUND: infra/audit/main.dev.bicepparam
- FOUND: infra/audit/modules/log-analytics.bicep
- FOUND: infra/audit/modules/worm-storage.bicep
- FOUND: infra/audit/modules/worm-storage-test.bicep
- FOUND: infra/audit/modules/data-collection-rule.bicep
- FOUND: infra/audit/modules/diagnostic-settings.bicep
- FOUND: infra/audit/README.md
- FOUND: tests/integration/test_worm_lock.py
- FOUND: tests/integration/test_la_workspace.py

Commits (verified with `git log --oneline`):
- FOUND: d46be67 — feat(01-06): audit substrate Bicep modules
- FOUND: 7aea442 — test(01-06): WORM lock + LA workspace integration tests
