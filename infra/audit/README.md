# infra/audit — Audit Substrate

Log Analytics workspace + WORM cold mirror + Data Collection Rule + diagnostic settings
that together satisfy AUDIT-01 (immutable + cryptographically chained audit log) and
AUDIT-03 (6-year retention locked at storage layer).

Plan: `01-06`. Wave 2; depends on plans 01 (RG), 02 (OIDC), 03 (networking),
04 (FortiGate — its `policies.json` is updated post-deploy with the LA ingestion endpoint),
05 (SQL DB + KV diagnostic targets).

## What this deploys

| Resource | Purpose | Module |
|----------|---------|--------|
| Log Analytics workspace `log-bary-dev` (Pay-as-you-go, 90-day retention) | Hot tier audit + diagnostics sink | `modules/log-analytics.bicep` |
| Custom table `AuditEvents_CL` (13 columns, `metadata` is `dynamic`) | DCR target; matches `barycenter.audit.models.AuditEvent` | `modules/log-analytics.bicep` |
| Storage account `stbarywormdev` (Standard_GRS, Cool, public-disabled, AAD-only) | WORM cold mirror, 6-year locked | `modules/worm-storage.bicep` |
| Container `audit` with `immutabilityPeriodSinceCreationInDays: 2190`, `allowProtectedAppendWrites: true` | AUDIT-03 substrate | `modules/worm-storage.bicep` |
| Storage account `stbarywormtest1` + container `audit-test` (1-day retention) | Pitfall 7 lock validation; deleted post-validation | `modules/worm-storage-test.bicep` |
| DCE `dce-bary-audit-dev` + DCR `dcr-bary-audit-dev` (stream `Custom-AuditEvents`) | Audit SDK ingest path | `modules/data-collection-rule.bicep` |
| Diagnostic settings on SQL / KV / WORM Storage → LA | AUDIT-01 source-of-truth coverage; AUDIT-02 audit-of-audit | `modules/diagnostic-settings.bicep` |
| Role assignments: Monitoring Metrics Publisher (DCR) + Storage Blob Data Contributor (WORM) on `mi-bary-audit` | Least-privilege ingest + append | `modules/data-collection-rule.bicep`, `modules/diagnostic-settings.bicep` |

## Test-container-first procedure (Pitfall 7)

The lock on the WORM container is one-way and cannot be shortened by anyone. Once locked,
6 years of append-only retention apply. To validate the lock mechanism without committing
6 years of test data, deploy the test container first:

1. Deploy `wormTest` module only:
   ```bash
   az deployment group create \
     -g rg-barycenter-dev \
     -f infra/audit/modules/worm-storage-test.bicep \
     --parameters location=eastus2 storageAccountName=stbarywormtest1
   ```
2. Manually lock the test container's immutability policy:
   ```bash
   ETAG=$(az storage container immutability-policy show \
     --account-name stbarywormtest1 \
     --container-name audit-test \
     --query etag -o tsv)
   az storage container immutability-policy lock \
     --account-name stbarywormtest1 \
     --container-name audit-test \
     --if-match "$ETAG"
   ```
3. Upload a test blob (append-block) and attempt to delete it — must fail with
   `AuthorizationFailure` / `BlobImmutable`.
4. Attempt to extend retention to a shorter period — must fail.
5. Wait the 1-day retention period; delete the test storage account entirely.
6. Only then deploy `wormProd` (`worm-storage.bicep`) with retention=2190, then run the
   same lock command against `stbarywormdev` / `audit`.

Plan 09 phase exit verifies the test account no longer exists. The integration test
`tests/integration/test_worm_lock.py::test_test_container_account_is_deleted` asserts this
and FAILS the suite if the test account still exists.

## Logs Ingestion API DCE public access tradeoff

The Data Collection Endpoint accepts ingestion over public DNS but requires an AAD token
+ DCR scope (`mi-bary-audit` has `Monitoring Metrics Publisher` ONLY on this DCR). The
auth control + DCR scope is the boundary; the public DNS surface is the standard pattern
for the Logs Ingestion API and accepts no anonymous traffic.

Future enhancement: PE-on-DCE (`networkAcls.publicNetworkAccess: 'SecuredByPerimeter'`)
once Network Security Perimeter Phase 2 reaches GA. For v1.0, the auth control + DCR
scope is the primary boundary. Per the global `~/.claude/CLAUDE.md` rule, this exception
must be called out in the PR description for this plan.

## DCR schema lock (Pitfall 9)

The `metadata` column type is `dynamic` and accepts arbitrary JSON. Adding a top-level
field to `AuditEvent` does NOT require DCR + table schema changes — it lands in `metadata`.
Promotion to a first-class column is a coordinated migration covered in a future plan
(re-tag the field, add column to DCR + table, backfill).

## Diagnostic settings coverage

| Source | Categories Forwarded | Why |
|--------|----------------------|-----|
| SQL DB | `SQLSecurityAuditEvents`, `SQLInsights`, `AutomaticTuning`, `AllMetrics` | HIPAA §164.312(b) source-of-truth for DB access |
| Key Vault | `AuditEvent`, `AzurePolicyEvaluationDetails`, `AllMetrics` | Every `sign()` call (FOUND-03 verification) + secret access |
| Storage (WORM) blob plane | `StorageRead`, `StorageWrite`, `StorageDelete`, `Transaction` metrics | Audit-of-audit (AUDIT-02): queries against WORM logged |

## NETW-03 wiring

The FortiGate syslog target IP in `infra/networking/fortigate-config/policies.json`
contains the marker `REPLACED_BY_DEPLOY_PIPELINE`. The deploy pipeline substitutes the
real LA ingestion endpoint at deploy time:

```bash
LA_INGESTION_ENDPOINT=$(az deployment group show \
  -g rg-barycenter-dev \
  -n audit-deploy \
  --query properties.outputs.dceLogsIngestionEndpoint.value \
  -o tsv)
sed -i "s|REPLACED_BY_DEPLOY_PIPELINE|$LA_INGESTION_ENDPOINT|" \
  infra/networking/fortigate-config/policies.json
# then push policies.json to FortiGate via REST API (handled by plan 08 workflow)
```

## Deployment

```bash
# Wave-2 deploy after plans 01–05 land:
az deployment group create \
  -g rg-barycenter-dev \
  -f infra/audit/main.bicep \
  --parameters infra/audit/main.dev.bicepparam
```

After deploy, run the manual `az storage container immutability-policy lock` step
against `stbarywormdev/audit` to flip the policy from Unlocked to Locked. The deploy
pipeline does NOT do this automatically — locking is one-way and must be a deliberate
human (or PIM-elevated CI job) action.

## CLAUDE.md compliance (network protection callout)

Per `./CLAUDE.md`:

- WORM storage account: `publicNetworkAccess: 'Disabled'`, `networkAcls.defaultAction: 'Deny'`,
  `bypass: 'AzureServices'`, `allowSharedKeyAccess: false` (AAD-only),
  `allowBlobPublicAccess: false`, `minimumTlsVersion: 'TLS1_2'`. ✅
- Log Analytics workspace: `enableLogAccessUsingOnlyResourcePermissions: true` (RBAC enforced
  on read). Public ingestion is needed for diagnostic settings + DCR Logs Ingestion API to
  function; no public query path opens because of the resource-permissions flag. ✅
- DCE: `publicNetworkAccess: 'Enabled'` documented exception above; AAD + DCR scope is the
  boundary. PR description includes this callout.
