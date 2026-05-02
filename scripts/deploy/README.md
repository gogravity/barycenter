# Deploy bootstrap (one-time)

## Pre-flight (admin host)
- `az --version` ≥ 2.67
- `az login` interactively (subscription Owner role required)
- `az account set --subscription <SUB_ID>`
- `gh auth login` (for setting repo variables after bootstrap)

## Run
```bash
./scripts/deploy/bootstrap-oidc.sh gravity barycenter eastus2
```

## Post-bootstrap
1. Copy the four `AZURE_*` lines from the script output.
2. Set them as GitHub **repository variables** (not secrets):
   ```bash
   gh variable set AZURE_TENANT_ID --body '<value>'
   gh variable set AZURE_SUBSCRIPTION_ID --body '<value>'
   gh variable set AZURE_DEPLOY_CLIENT_ID --body '<value>'
   gh variable set AZURE_WHATIF_CLIENT_ID --body '<value>'
   ```
3. Fill in `.planning/phases/01-network-data-foundations/oidc-bootstrap-evidence.md` with the same values plus the date and admin name.

## Why these are variables, not secrets
Tenant ID, subscription ID, and clientId of a managed identity are not credentials — they are identifiers. The actual auth happens via OIDC token exchange (no shared secret to leak). Storing them as variables makes them visible in PR logs (which is fine) and avoids the "is this secret rotated" question.

## Idempotency
Re-running the script is safe. Every operation is gated on `az ... show` and skipped if the resource exists.

## Pitfall 11
Federated credential subjects are env-scoped:
- `mi-bary-deploy` ← `repo:gravity/barycenter:ref:refs/heads/main` (deploy from main only)
- `mi-bary-whatif` ← `repo:gravity/barycenter:pull_request` (read-only what-if for PRs)

No wildcards. No `:*`. Adding a `prod` env later means a new MI + new federated credential, not relaxing the existing subject.
