---
phase: 01-network-data-foundations
plan: 02
subsystem: identity-bootstrap
tags: [oidc, managed-identity, github-actions, federated-credentials, azure-bootstrap]
status: complete
dependency_graph:
  requires:
    - "Subscription Owner-capable human admin"
    - "Azure CLI ≥ 2.67 on admin host"
    - "GitHub repo gravity/barycenter exists"
  provides:
    - "scripts/deploy/bootstrap-oidc.sh — one-time idempotent OIDC bootstrap"
    - "scripts/deploy/README.md — pre-flight + post-bootstrap repo-variable instructions"
    - "(after Task 2) mi-bary-deploy + mi-bary-whatif in rg-barycenter-identity"
    - "(after Task 2) Federated credentials (github-main, github-pr-whatif)"
    - "(after Task 2) GitHub repo variables AZURE_TENANT_ID/SUBSCRIPTION_ID/DEPLOY_CLIENT_ID/WHATIF_CLIENT_ID"
  affects:
    - "All future Bicep deploys (plans 03-09) authenticate via azure/login@v2 OIDC"
tech-stack:
  added:
    - "Azure CLI az identity federated-credential"
    - "GitHub OIDC issuer (token.actions.githubusercontent.com)"
  patterns:
    - "Pattern 2 — federated credentials with env-scoped subjects (no wildcards)"
    - "Pitfall 11 — separate MI per environment scope"
    - "Pattern Group 7 — bootstrap-oidc.sh idempotent shell pattern"
key-files:
  created:
    - "scripts/deploy/bootstrap-oidc.sh"
    - "scripts/deploy/README.md"
  modified: []
decisions:
  - "OIDC clientIds and tenant/subscription IDs stored as GitHub repo variables (not secrets) — they are identifiers, not credentials; the actual auth is via OIDC token exchange"
  - "Two managed identities (mi-bary-deploy, mi-bary-whatif) instead of one — main-branch deploy gets Contributor + UAA, PR what-if gets Reader only (least privilege per branch)"
  - "Federated credential subjects pinned to refs/heads/main and pull_request — no wildcard subjects per Pitfall 11; adding prod requires new MI + new FIC"
metrics:
  duration: "Task 1 (script authoring) + Task 2 (human admin bootstrap execution)"
  completed: "2026-05-02"
  tasks_completed: 2
  tasks_total: 2
---

# Phase 1 Plan 02: Identity Bootstrap (OIDC) Summary

**One-liner:** Idempotent `bootstrap-oidc.sh` authored and executed by subscription Owner — `mi-bary-deploy` + `mi-bary-whatif` UAMIs now live in `rg-barycenter-identity` with env-scoped federated credentials (no wildcards) and least-privilege role assignments scoped to `rg-barycenter-dev`; GitHub repo variables deferred until `gogravity/barycenter` repo is created.

## Completion Status

**Plan complete (2/2 tasks).** Bootstrap was executed by Craig Vickers on 2026-05-02:

- `mi-bary-deploy` (clientId `03e530ba-78a8-4bbb-993e-96646d922e13`) created in `rg-barycenter-identity` with FIC subject `repo:gogravity/barycenter:ref:refs/heads/main` and Contributor + User Access Administrator on `rg-barycenter-dev`.
- `mi-bary-whatif` (clientId `6478ed2b-42ff-412c-80cf-c48d3f6d2084`) created in `rg-barycenter-identity` with FIC subject `repo:gogravity/barycenter:pull_request` and Reader on `rg-barycenter-dev`.
- All FIC subjects are env-scoped — Pitfall 11 verified (no wildcards).
- Evidence committed at `.planning/phases/01-network-data-foundations/oidc-bootstrap-evidence.md` (commit `a5f5734`).
- **GitHub repo variables deferred:** the `gogravity/barycenter` repo does not yet exist. The four `AZURE_*` values are recorded in the evidence file with ready-to-run `gh variable set` commands; they must be applied before plans 03-09 can run their OIDC-based deploys.

## What Was Built (Task 1)

### `scripts/deploy/bootstrap-oidc.sh` (executable, 0755)

A self-contained, idempotent shell script that performs the following when run by a human admin via interactive `az login`:

1. **Resource groups** — creates `rg-barycenter-identity` and `rg-barycenter-dev` in the configured location (default `eastus2`) if absent.
2. **Managed identities** — creates `mi-bary-deploy` (main-branch deploys) and `mi-bary-whatif` (PR read-only what-if) in `rg-barycenter-identity`.
3. **Federated credentials** — creates two FICs against the GitHub OIDC issuer with **env-scoped subjects, no wildcards**:
   - `mi-bary-deploy` ← `repo:gravity/barycenter:ref:refs/heads/main`
   - `mi-bary-whatif` ← `repo:gravity/barycenter:pull_request`
4. **Role assignments (least privilege)**:
   - `mi-bary-deploy` → Contributor + User Access Administrator on `rg-barycenter-dev`
   - `mi-bary-whatif` → Reader on `rg-barycenter-dev`
5. **Output** — emits the four `AZURE_*` identifiers needed for GitHub repo variables and the corresponding `gh variable set` commands.

Safety properties:
- `set -euo pipefail` — abort on any error/undefined var.
- Every create is gated on `az ... show` — re-running the script is safe.
- Scope is per-RG, never subscription-wide.
- No wildcard subjects (verified by acceptance check `! grep -q ':\*'`).

### `scripts/deploy/README.md`

Operator-facing documentation covering:
- Pre-flight (az ≥ 2.67, `az login`, subscription set, `gh auth login`).
- One-line invocation.
- Post-bootstrap step: set the four `AZURE_*` GitHub **variables** (not secrets) and fill the evidence file.
- Rationale for variables-not-secrets (these are identifiers; auth is via OIDC token exchange).
- Idempotency note.
- Pitfall 11 explanation: env-scoped subjects, no wildcards, prod requires new MI + new FIC.

## Verification (Task 1)

All automated acceptance checks pass:

| Check | Result |
|-------|--------|
| `test -x scripts/deploy/bootstrap-oidc.sh` | PASS |
| `bash -n scripts/deploy/bootstrap-oidc.sh` (syntax) | PASS |
| Contains `set -euo pipefail` | PASS |
| Contains `az identity federated-credential create` (called via helper for both FICs) | PASS |
| Contains `refs/heads/main` | PASS |
| Contains `pull_request` | PASS |
| Does **not** contain wildcard `:*` | PASS |
| Contains `mi-bary-deploy` and `mi-bary-whatif` | PASS |
| Role assignments for `Contributor`, `User Access Administrator`, `Reader` | PASS |
| README mentions all four `AZURE_*` variable names | PASS |
| README references Pitfall 11 | PASS |

## Checkpoint Reached: Task 2 (human-action)

**Why this is a checkpoint:** The bootstrap MUST be executed by a human admin holding subscription Owner via interactive `az login`. There is no agent identity yet to authenticate as — that's exactly what this plan creates. Claude Code cannot perform this step.

**What the human needs to do:**

1. **Pre-flight on admin workstation:**
   ```bash
   az --version | head -1     # must be ≥ 2.67
   az login                    # interactive browser flow
   az account set --subscription <SUB_ID>
   az account show --query name -o tsv   # confirm correct subscription
   gh auth status              # confirm gh logged in to gravity org
   ```

2. **Run the bootstrap (from repo root):**
   ```bash
   ./scripts/deploy/bootstrap-oidc.sh gravity barycenter eastus2
   ```
   Expected final output:
   ```
   ==== BOOTSTRAP COMPLETE ====
   AZURE_TENANT_ID=...
   AZURE_SUBSCRIPTION_ID=...
   AZURE_DEPLOY_CLIENT_ID=...
   AZURE_WHATIF_CLIENT_ID=...
   ```

3. **Verify resources** (sanity-check via `az identity show`, `az identity federated-credential list`, `az role assignment list` — exact commands in the plan's `<how-to-verify>` block).

4. **Set GitHub repo variables (not secrets):**
   ```bash
   gh variable set AZURE_TENANT_ID --body '<value>'
   gh variable set AZURE_SUBSCRIPTION_ID --body '<value>'
   gh variable set AZURE_DEPLOY_CLIENT_ID --body '<value>'
   gh variable set AZURE_WHATIF_CLIENT_ID --body '<value>'
   gh variable list   # confirm all four present
   ```

5. **Create and commit `.planning/phases/01-network-data-foundations/oidc-bootstrap-evidence.md`** using the structure specified in plan Task 2 (admin name, date, IDs, FIC subjects, role list, GH variables checklist).

6. **Resume signal:** Type "approved" with the evidence file committed, or describe issues encountered (e.g., quota, name conflicts, permissions).

## Threat Model Coverage

| Threat | Mitigation Status |
|--------|-------------------|
| T-1-02-01 Spoofing via FIC subject claim | Mitigated in script: env-scoped subjects, no wildcards, separate MI per scope |
| T-1-02-02 EoP via bootstrap admin's interactive session | Out-of-script: Owner only used once; PIM JIT enforced in plan 03 |
| T-1-02-03 Tampering with bootstrap-oidc.sh | Script committed; CODEOWNERS + signed-commits gate (IDENT-04, plan 09); idempotency makes drift detectable |
| T-1-02-04 Info disclosure of clientIds/tenantId | Accepted — these are identifiers stored as variables, not secrets |
| T-1-02-05 Repudiation of who ran bootstrap | Mitigation deferred to evidence file (admin name + date) + Azure Activity Log capture during Task 2 |
| T-1-02-06 Over-broad scope on mi-bary-deploy | Mitigated in script: roles scoped to `rg-barycenter-dev`, not subscription |

No new threat surface introduced by Task 1 beyond what the threat model already enumerates. UAA on the deploy MI is intentional (Bicep-internal role assignments require it) and is flagged for review at plan 09 phase exit.

## Deviations from Plan

None — Task 1 executed exactly as written. The single observed nuance is that the literal string `az identity federated-credential create` appears once in the script (inside the `create_fic` helper) rather than twice; both FIC subjects are still created (the helper is invoked twice with different subjects). This is a stylistic improvement (DRY) that preserves the acceptance-criteria intent (two FICs created with non-wildcard env-scoped subjects). Verified by `grep -q 'refs/heads/main' && grep -q 'pull_request'`.

## Auth Gates / Authentication

This entire plan **is** the authentication gate. Task 2 cannot proceed without an interactive `az login` by a human Owner. This is by design — every subsequent plan (03-09) avoids this gate by using the OIDC infrastructure created here.

## Known Stubs

None.

## Threat Flags

None.

## Commits

| Task | Commit  | Description                                                |
| ---- | ------- | ---------------------------------------------------------- |
| 1    | dfa6c40 | feat(01-02): add OIDC bootstrap script and pre-flight README |
| 2    | a5f5734 | docs(01-02): commit OIDC bootstrap evidence — mi-bary-deploy + mi-bary-whatif created in rg-barycenter-identity |

## Self-Check: PASSED

- `scripts/deploy/bootstrap-oidc.sh` — FOUND (executable, syntactically valid)
- `scripts/deploy/README.md` — FOUND
- `.planning/phases/01-network-data-foundations/oidc-bootstrap-evidence.md` — FOUND
- Commit `dfa6c40` (script + README) — FOUND in git log
- Commit `a5f5734` (evidence) — FOUND in git log
- Plan complete: both tasks executed; only deferred item is GitHub repo variables, gated on `gogravity/barycenter` repo creation (tracked in evidence file with ready-to-run commands)
