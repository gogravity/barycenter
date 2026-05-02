# Phase 1: Network & Data Foundations - Context

**Gathered:** 2026-05-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 1 delivers the load-bearing Azure substrate that all subsequent phases depend on:
FortiGate hub-and-spoke perimeter, two-zone Azure SQL schema topology, four managed
identities, Key Vault HMAC salt service, cryptographically chained audit log (Log Analytics
+ WORM blob), and BAA inventory committed to repo. No application logic, no ETL, no
integrations — infrastructure and security foundations only.

A FortiGate deny rule blocks ETL-subnet-to-Anthropic and services-subnet-to-source-tools
traffic. Azure SQL is private-endpoint only (`publicNetworkAccess=Disabled`). Raw schemas
have zero grants to the platform identity. CI fails any PR that adds a column without a
field-class tag. All four managed identities exist with no long-lived secrets.

</domain>

<decisions>
## Implementation Decisions

### IaC Tooling

- **D-01:** Use **Bicep** as the IaC tool for all Azure resource definitions (FortiGate, SQL,
  Key Vault, VNets, managed identities, Log Analytics, WORM blob). Azure-native, no state
  file, tight ARM integration, best fit for a single-Azure small-team project.

- **D-02:** Organize Bicep in **layered modules by concern**, not a single monolithic file:
  - `infra/networking/` — FortiGate NVA, hub VNet, spoke VNets, UDRs, NSGs
  - `infra/data/` — Azure SQL Serverless, Key Vault, private endpoints
  - `infra/identity/` — 4 managed identities, PIM role assignments
  - `infra/audit/` — Log Analytics workspace, WORM blob storage, diagnostic settings
  Each module deploys independently; NETW-02 drift detection runs per-module.

- **D-03:** Manage environment parameters via **per-env Bicep parameter files** committed to
  the repo (e.g., `main.dev.bicepparam`, `main.prod.bicepparam`). Secrets are not stored
  in param files — they reference Key Vault. This makes infra changes reviewable in PRs.

### Audit Write Architecture

- **D-04:** All audit events are emitted by a **shared Python audit SDK** (`barycenter.audit`
  package). The SDK hashes the prior event, writes to Log Analytics via the DCR ingestion
  API, and writes synchronously. Every caller (ETL, gateway, admin tooling) imports this
  package — there is no parallel audit path.

- **D-05:** Chain state (the latest event's SHA-256 hash) lives in a **dedicated SQL table
  in the audit schema** (`audit.chain_state`, single row). Written atomically with each
  audit event in the same transaction. Accessible only to the audit identity.

- **D-06:** The audit write is **fail closed**: if the audit event cannot be written (Log
  Analytics unreachable, WORM mirror unavailable, `chain_state` locked), the parent
  operation is rejected. PII writes without audit coverage do not happen. An ops alert
  fires immediately on audit write failure.

### Repo & CI Structure

- **D-07:** Barycenter lives in a **mono-repo**: IaC (Bicep), Python packages (audit SDK,
  ETL framework, gateway), SQL migrations, and CI workflows all in one repository. Branch
  protection (IDENT-04) is enforced once. A change touching SQL schema and the audit SDK
  is a single reviewable PR.

- **D-08:** CI platform is **GitHub Actions**. All gates run there: VER-02 field-class check,
  NETW-01 Bicep lint + `az deployment what-if`, IDENT-04 branch protection, PR-gating.

### Claude's Discretion

- **GitHub Actions Azure auth:** OIDC federated workload identity (no stored secrets, no
  rotation burden, aligns with IDENT-03). Claude to configure the federated credential on
  the deployment managed identity.
- **Audit event schema:** Field names, event types, and metadata structure — Claude designs
  to satisfy AUDIT-01 chaining and HIPAA §164.312(b) minimum fields.
- **VER-02 source-of-truth format:** How column field-class tags are stored (YAML manifest
  alongside migrations vs SQL extended properties) — Claude picks the format that makes
  the CI gate straightforward to implement and maintain.
- **FortiGate subnet layout:** Exact CIDR allocation, spoke count, UDR routing table
  design within the hub-and-spoke topology.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase Requirements
- `.planning/REQUIREMENTS.md` — Full requirement text for FOUND-01, FOUND-02, FOUND-03,
  FOUND-04, NETW-01, NETW-02, NETW-03, AUDIT-01, AUDIT-02, AUDIT-03, IDENT-01, IDENT-02,
  IDENT-03, IDENT-04, IDENT-05, EGRESS-01, ENC-01, VER-02, COMP-06

### Project Context
- `.planning/PROJECT.md` — Architecture decisions table, five-layer defense model,
  identifier hierarchy, constraint rationale (TDE not AE, owned gateway not APIM, FortiGate
  BYOL, $166/mo budget)
- `.planning/ROADMAP.md` §Phase 1 — Phase goal, success criteria 1–5, requirement list

### No external specs committed yet
BAA inventory (COMP-06) is a Phase 1 deliverable — the BAA documents themselves will be
committed to repo during this phase.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
None — greenfield project. No existing src/ directory.

### Established Patterns
None yet — Phase 1 establishes the patterns all subsequent phases inherit:
- Bicep module structure
- Python package layout (audit SDK first)
- SQL migration tooling and field-class tagging convention
- GitHub Actions workflow structure

### Integration Points
- Log Analytics workspace (created this phase) ← used by audit SDK, WORM mirroring,
  FortiGate log ingestion (NETW-03), and all future phases
- Key Vault (created this phase) ← HMAC salt access by ETL identity (Phase 2+)
- Azure SQL private endpoint (created this phase) ← all ETL and app code in Phase 2+
- Managed identities (created this phase) ← referenced by all service code in Phase 2+
- GitHub Actions OIDC federated credential (created this phase) ← used by all future CI gates

</code_context>

<specifics>
## Specific Ideas

No specific implementation references cited during discussion — open to standard approaches
within the decided constraints (Bicep, Python SDK, fail-closed audit, mono-repo, GitHub Actions).

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within Phase 1 scope.

</deferred>

---

*Phase: 01-network-data-foundations*
*Context gathered: 2026-05-02*
