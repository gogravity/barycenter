# infra/data — Azure SQL + Key Vault data plane

Phase 01 / Plan 05. Deploys the data plane behind private endpoints and applies the
two-zone schema model + grant matrix + audit chain genesis seed.

## Order of operations

Deploy after plans 03 (identity) and 04 (networking). The CI workflow (plan 08) sets
all required environment variables before invoking `az deployment group create`:

```
ETL_PRINCIPAL_ID, PLATFORM_PRINCIPAL_ID, AUDIT_PRINCIPAL_ID, ADMIN_PRINCIPAL_ID,
DEPLOY_PRINCIPAL_ID, FGT_VM_PRINCIPAL_ID (optional),
DATA_SUBNET_ID, PE_SUBNET_ID,
SQL_PRIVATE_DNS_ZONE_ID, KV_PRIVATE_DNS_ZONE_ID,
SQL_ADMIN_GROUP_OBJECT_ID,
DEPLOY_IDENTITY_RESOURCE_ID,
SCRIPT_STORAGE_ACCOUNT, SCRIPT_CONTAINER_SAS
```

## Cross-plan inputs

- `dataSubnetId`, `peSubnetId` come from `infra/networking` outputs (plan 04)
- All MI principalIds come from `infra/identity` outputs (plan 03)
- `deployIdentityResourceId` is the OIDC-federated user-assigned MI from plan 02 (see
  `oidc-bootstrap-evidence.md`)
- SQL admin group: an Entra security group `sg-bary-sql-admins` must exist; the SRE
  on-call is the sole eligible member. This group is the **only** "human" path to SQL,
  and access requires PIM JIT activation (Phase 2+ enforces the PIM eligibility on
  this group; for plan 05 the group simply exists with admin as eligible).

## Deploy-script storage

`Microsoft.Resources/deploymentScripts` requires a storage account for script content
and log capture. The deploy MI creates a transient storage account
`stbarydeployscript<unique>` in `rg-barycenter-dev`, uploads the SQL files (under
`00-schemas/`, `10-grants/`, `20-seed/`) as a blob container, generates a container
SAS URI, and passes it as `scriptContainerSasUri @secure()`. After deploy succeeds
(`cleanupPreference: OnSuccess`), the container is auto-deleted by the deployment
scripts service.

## TDE confirmation (ENC-01)

`sql-serverless.bicep` explicitly creates the `transparentDataEncryption` resource
with `state: 'Enabled'`, even though TDE has been on by default since 2017. Explicit
declaration:

1. Makes ENC-01 grep-verifiable in source.
2. Prevents accidental disable via the portal — drift detector flags it.
3. Future-proofs against an unlikely Microsoft default change.

## KV scoping (FOUND-03 + plan 04 dependency)

| Identity | Role | Scope |
|----------|------|-------|
| `mi-bary-etl` | Key Vault Crypto User | `keys/salt-tenant-bootstrap` only |
| FortiGate VM (system-assigned) | Key Vault Secrets User | `secrets/fortigate-license` only |
| `mi-bary-deploy` | Key Vault Administrator | vault-wide (revoke after Wave 0) |

`mi-bary-etl` can sign with the salt key but **cannot** list other keys, retrieve
secrets, or perform vault management. The FortiGate VM identity can read **only** the
license secret. `mi-bary-deploy` has vault-wide admin **temporarily** to provision
keys/secrets; this assignment is **revoked in plan 09 phase exit** once Wave 0
stabilizes — tracked as a TODO in the deploy MI README. Until removal, the OIDC
subject claim on the deploy MI restricts it to `refs/heads/main` only (Pitfall 11),
so there is no human-interactive path.

## Pitfall 7 — test purge protection in dev first

The WORM container retention lock lives in plan 06 (audit). This data plan creates KV
with `enablePurgeProtection: true` (cannot be disabled once on; soft-delete is
permanent for 90 days). Before relying on it: verify in dev by attempting to disable
purge protection — the operation **must** fail. Document the result in
`compliance/runbooks/` (plan 09).

## Validation surface

After deploy completes, plan 08 runs:

- `tests/integration/test_sql_zero_grants.py` — grant matrix assertions
- `tests/integration/test_kv_sign.py` — KV sign-only contract
- `tests/integration/test_tde_enabled.py` — TDE state, publicNetworkAccess, AAD-only
