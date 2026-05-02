# Phase 1: Network & Data Foundations - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-02
**Phase:** 01-network-data-foundations
**Areas discussed:** IaC tooling, Audit write architecture, Repo & CI structure

---

## IaC Tooling

### Q1: Which IaC tool?

| Option | Description | Selected |
|--------|-------------|----------|
| Bicep | Azure-native, no state file, tight ARM integration | ✓ |
| Terraform (AzureRM) | Cross-cloud portability, mature ecosystem, state file overhead | |
| Pulumi (TypeScript/Python) | IaC-as-real-code, more moving parts | |
| You decide | Claude picks most pragmatic fit | |

**User's choice:** Bicep
**Notes:** Recommended option accepted without modification.

---

### Q2: Bicep module organization?

| Option | Description | Selected |
|--------|-------------|----------|
| Layered modules | Separate modules per concern (networking, data, identity, audit) | ✓ |
| Single deployment file | One main.bicep orchestrates everything | |
| You decide | Claude structures modules | |

**User's choice:** Layered modules
**Notes:** User initially asked for pros/cons trade-off. After analysis explaining independent
deployability, contained blast radius, and per-module drift detection vs. single-file simplicity,
user selected layered modules.

---

### Q3: Parameter management?

| Option | Description | Selected |
|--------|-------------|----------|
| Per-env parameter files | .bicepparam files committed to repo, KV refs for secrets | ✓ |
| Environment variables in CI only | No committed param files, injected by pipeline | |
| You decide | Claude picks approach making drift reviewable in PRs | |

**User's choice:** Per-env parameter files
**Notes:** Recommended option accepted.

---

## Audit Write Architecture

### Q1: Who emits audit events?

| Option | Description | Selected |
|--------|-------------|----------|
| Shared Python audit SDK | barycenter.audit package, all app code imports it | ✓ |
| SQL triggers on sensitive tables | DML triggers auto-emit, but can't cover gateway/KV events | |
| Azure Monitor Diagnostic Settings only | Platform logging — can't satisfy AUDIT-01 SHA-256 chain | |
| You decide | Claude picks approach satisfying AUDIT-01/02 | |

**User's choice:** Shared Python audit SDK
**Notes:** Recommended option accepted.

---

### Q2: Chain state storage?

| Option | Description | Selected |
|--------|-------------|----------|
| Dedicated SQL table in audit schema | audit.chain_state, atomic with each event, survives restarts | ✓ |
| In-memory within process | Fast but lost on restart, chain breaks on pod restart | |
| Key Vault secret | Adds latency, KV rate limits, unnecessarily complex | |
| You decide | Claude picks durable, transactional, auditable option | |

**User's choice:** Dedicated SQL table in audit schema
**Notes:** Recommended option accepted.

---

### Q3: Audit write failure behavior?

| Option | Description | Selected |
|--------|-------------|----------|
| Fail closed — block the operation | No audit = no operation; ops paged immediately | ✓ |
| Fail open with local buffer | Queue and retry, but creates unaudited operation window | |
| You decide | Claude picks failure mode consistent with architectural-over-procedural constraint | |

**User's choice:** Fail closed
**Notes:** Recommended option accepted. Consistent with PROJECT.md "architectural over procedural" constraint.

---

## Repo & CI Structure

### Q1: Mono-repo vs split repos?

| Option | Description | Selected |
|--------|-------------|----------|
| Mono-repo | IaC + Python + SQL migrations + CI in one repo | ✓ |
| Split: IaC repo + app repo | Infrastructure and application code separated | |
| You decide | Claude picks structure minimizing coordination overhead | |

**User's choice:** Mono-repo
**Notes:** Recommended option accepted.

---

### Q2: CI platform?

| Option | Description | Selected |
|--------|-------------|----------|
| GitHub Actions | Azure-adjacent, native Bicep/Python support, no extra platform | ✓ |
| Azure DevOps Pipelines | Tighter Azure deployment integration, adds second platform | |
| You decide | Claude picks CI with minimal overhead and first-class Azure support | |

**User's choice:** GitHub Actions
**Notes:** Recommended option accepted.

---

### Q3: GitHub Actions Azure authentication?

| Option | Description | Selected |
|--------|-------------|----------|
| OIDC federated workload identity | No stored secrets, short-lived tokens, no rotation | |
| Service principal + client secret | Simpler setup, but long-lived secret contradicts IDENT-03 | |
| You decide | Claude picks auth satisfying IDENT-03 no-long-lived-secrets | ✓ |

**User's choice:** You decide (deferred to Claude)
**Notes:** Obvious choice is OIDC given IDENT-03; captured as Claude's Discretion in CONTEXT.md.

---

## Claude's Discretion

- GitHub Actions Azure auth → OIDC federated workload identity
- Audit event schema → Claude designs to satisfy AUDIT-01 chaining + HIPAA §164.312(b)
- VER-02 field-class source-of-truth format → Claude picks CI-friendly format
- FortiGate subnet CIDR allocation and UDR design → Claude designs hub-and-spoke topology

## Deferred Ideas

None — discussion stayed within Phase 1 scope.
