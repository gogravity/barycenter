# Barycenter — Project Conventions

## Security (inherits and reinforces ~/.claude/CLAUDE.md)
- Every Azure resource MUST set `publicNetworkAccess: 'Disabled'` from first commit.
- Every Azure resource MUST be reachable only via private endpoint or VNet integration.
- Storage accounts and Key Vault: `networkAcls.defaultAction: 'Deny'`, `bypass: 'AzureServices'`.
- SQL: `azureADOnlyAuthentication: true`, `minimalTlsVersion: '1.2'`.
- PR descriptions MUST call out the network protection choice (per global rule).

## IaC (D-01, D-02, D-03)
- Bicep is the only IaC tool. No Terraform, no manual `az` commands after Wave 0.
- Layered modules: infra/networking, infra/data, infra/identity, infra/audit.
- Per-env parameter files (main.dev.bicepparam, main.prod.bicepparam). No secrets in param files — Key Vault references only.
- All deploys go through GitHub Actions OIDC (Pattern 2). No service-principal client secrets.

## Audit SDK (D-04, D-06)
- `from barycenter.audit import AuditClient, AuditEvent` is the ONLY audit path.
- `AuditClient.emit()` is synchronous and fail-closed. No try/except/pass. No fire-and-forget.
- Three failure modes (LA, WORM, chain_state lock) MUST raise AuditEmitError and roll back the parent transaction.

## Mono-repo (D-07)
- Single repository for IaC, Python packages, SQL migrations, CI workflows.
- Branch protection (IDENT-04) is enforced once on `main`.
- Signed commits required.

## CI (D-08)
- GitHub Actions only. All gates run there: VER-02, NETW-02, audit-chain-validate, infra-deploy what-if/create.
- OIDC subject claims are env-scoped per Pitfall 11 (no wildcards).
