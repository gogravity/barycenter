# OIDC Bootstrap Evidence (plan 01-02)

**Run by:** Craig Vickers (gogravity)
**Date:** 2026-05-02
**Subscription ID:** debe8a68-e9df-4662-92b6-cebd05b776be
**Tenant ID:** fe232127-e947-46be-97fc-92ec7e3e6dc1

## Managed identities

- mi-bary-deploy clientId: 03e530ba-78a8-4bbb-993e-96646d922e13
- mi-bary-deploy principalId: 84e2c373-06a2-4df5-8ebe-9e4e8fd6e802
- mi-bary-whatif clientId: 6478ed2b-42ff-412c-80cf-c48d3f6d2084
- mi-bary-whatif principalId: 934b082d-97ba-4edc-bc79-b62f1db3b636

## Federated credentials (mi-bary-deploy)

- github-main → subject: repo:gogravity/barycenter:ref:refs/heads/main
- (no wildcards — Pitfall 11 verified)

## Federated credentials (mi-bary-whatif)

- github-pr-whatif → subject: repo:gogravity/barycenter:pull_request

## Role assignments

- mi-bary-deploy: Contributor + User Access Administrator on rg-barycenter-dev
- mi-bary-whatif: Reader on rg-barycenter-dev

## GitHub repo variables set

- AZURE_TENANT_ID — pending (repo gogravity/barycenter not yet created)
- AZURE_SUBSCRIPTION_ID — pending
- AZURE_DEPLOY_CLIENT_ID — pending
- AZURE_WHATIF_CLIENT_ID — pending

Values ready to set once repo exists:
```
gh variable set AZURE_TENANT_ID --body 'fe232127-e947-46be-97fc-92ec7e3e6dc1'
gh variable set AZURE_SUBSCRIPTION_ID --body 'debe8a68-e9df-4662-92b6-cebd05b776be'
gh variable set AZURE_DEPLOY_CLIENT_ID --body '03e530ba-78a8-4bbb-993e-96646d922e13'
gh variable set AZURE_WHATIF_CLIENT_ID --body '6478ed2b-42ff-412c-80cf-c48d3f6d2084'
```

## Verification

- `az role assignment list --scope .../rg-barycenter-dev` shows Contributor + UAA (mi-bary-deploy) and Reader (mi-bary-whatif) — per-RG scope, not subscription-wide ✓
- `az identity federated-credential list` shows no wildcard subjects ✓
- Both FIC subjects are env-scoped (main-branch deploy vs PR read-only) ✓
- GitHub repo variables: deferred until gogravity/barycenter repo is created
