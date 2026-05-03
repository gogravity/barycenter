# CW Manage Auth Mode Evidence

> INT-01 / Pitfall 2 closure. Documents the authentication mode chosen for Gravity's CW Manage tenant.

## Decision

auth_mode: basic

Date confirmed: 2026-05-02

Rationale: API Member key pair (Basic Auth) available and already provisioned. OAuth client-credentials not required.

## KV secrets provisioned

- `api-cw-server-url`
- `api-cw-company`
- `api-cw-public-key`
- `api-cw-private-key`
- `api-cw-client-id`

Provisioned by operator via `az keyvault secret set` against the project Key Vault. Secrets confirmed present before Phase 2 execution completed.

## CW_AUTH_MODE GH variable

Value: `basic`

Status: **pending** — set this once the branch is merged and pushed to main:
```bash
gh variable set CW_AUTH_MODE --body "basic"
```

## First successful run

Status: **pending** — `etl-cw-nightly.yml` workflow was created in plan 02-05 and will be registered by GitHub once this branch is merged to main.

To trigger after merge:
```bash
gh workflow run etl-cw-nightly.yml
gh run watch
```

Update this file with the run URL once the first successful run completes.
