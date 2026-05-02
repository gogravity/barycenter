# Barycenter

## What This Is

Barycenter is the operations data repository for Gravity's internal MSP business — a unified, security-architected data layer that ingests from the many tools Gravity uses to run its customers (ConnectWise Manage, Pax8, Microsoft Graph, RMM, security, backup, etc.) and exposes two architecturally separated zones: a raw zone holding full-fidelity sensitive data with restricted access, and an AI zone holding pseudonymized, aggregated data that AI agents can safely reason over. It is consumed by Gravity's internal AI agents and ops tooling — it is not a product sold to other MSPs.

The name reflects the architecture: the gravitational center where data from many tools converges and around which AI agents orbit, never touching the masses themselves.

## Core Value

**Make it architecturally impossible for AI agents to leak customer PII or CUI** — even if a prompt is malicious, an output filter is bypassed, or a tool is buggy. If everything else fails, this must hold.

This is the load-bearing claim of the entire platform. The two-zone model, identifier hierarchy, agent grants, and CUI exclusion controls all serve this single property. Every design tradeoff resolves toward "is the leak boundary still architectural, not procedural?"

## Current Milestone: v1.0 — Barycenter MVP

**Goal:** Build the complete Barycenter platform — two-zone Azure SQL data layer with FortiGate network perimeter, five-layer defense, CW Manage / Pax8 / Graph integrations, owned AI gateway, VER-01 leak test in CI, and HIPAA compliance posture.

**Target features:**
- Block A — Foundations: FortiGate hub-and-spoke, schema topology, identity boundary, audit plane, salt-in-Key-Vault
- Block B — Tool Onboarding Framework + ConnectWise Manage (INT-01)
- Block C — Agent-Safe Access Layer: typed functions, owned FastAPI gateway, VER-01 leak test in CI
- Block D — Pax8 (INT-02) + Microsoft Graph (INT-03)
- Block E — HIPAA compliance posture, CUI controls, erasure workflow, on-call alerting

**Stack (revised 2026-05-02):** Azure SQL Serverless GP · FortiGate NVA BYOL (F2s_v2) · Owned FastAPI gateway (~300 LOC) · Log Analytics + WORM blob · 4 managed identities · 1 Key Vault · ~$166/mo

## Requirements

### Validated

(None yet — ship to validate)

### Active

#### Foundation
- [ ] **FOUND-01**: Two-zone Azure SQL architecture with schema isolation — `raw_*` schemas (full-fidelity, agent has zero grant) and `ai_zone.*` schema (pseudonymized, agent-readable views only)
- [ ] **FOUND-02**: Field classification standard — every column tagged RESTRICTED / SENSITIVE / INTERNAL / PUBLIC, drives storage, encryption, and AI exposure
- [ ] **FOUND-03**: Identifier hierarchy — tenant_id (internal), cw_company_id (system-issued), serial_number (vendor-issued), person_pid (synthetic, derived from HMAC of email per-tenant-salt)
- [ ] **FOUND-04**: Five-layer defense — schema permissions, AI-safe views, typed tool functions, gateway scrubbing, per-prompt audit. All five must fail simultaneously for a leak.

#### Tool Onboarding Framework
- [ ] **TOOL-01**: Standardized Tool Onboarding Spec template — every new tool fills the same intake doc (field map, raw schema, ETL recipe, AI-zone contributions, retention, erasure)
- [ ] **TOOL-02**: Eight standard transformation primitives — drop, hash, pseudonymize, aggregate, bucket, score, keyword_flags, as_is. Tools compose ETL from these.
- [ ] **TOOL-03**: Four canonical AI-zone shapes — `customer_snapshot`, `customer_features_*`, `timeseries_aggregate`, `customer_memory`. Tools contribute into these; tools cannot invent new AI-zone tables.
- [ ] **TOOL-04**: Tool category taxonomy — productivity, RMM, security, backup, docs, distributors, CW. New tools slot into existing category, ETL recipe inherits.

#### Initial Tool Integrations (v1)
- [ ] **INT-01**: ConnectWise Manage — companies, agreements, tickets (metadata only, no body content), configurations, time entries (aggregates only)
- [ ] **INT-02**: Pax8 — subscriptions, SKU codes, renewal dates, monthly value
- [ ] **INT-03**: Microsoft Graph — users (hashed → person_pid), license assignments (counts only), tenant metadata
- [ ] **INT-04**: Email-derived signals — domain extraction, vendor matching, structured extracts (PO numbers, sentiment, intent classification). No raw bodies or addresses cross to AI zone.

#### Agent-Safe Access Layer
- [ ] **ACCESS-01**: AI-safe views — every view in `ai_zone.*` schema has documented field-class composition. No RESTRICTED data, no SENSITIVE data without pseudonymization.
- [ ] **ACCESS-02**: Typed tool function contract — agents do not write SQL. They call typed functions (e.g., `get_customer_snapshot(cw_company_id)`) that return validated structures.
- [ ] **ACCESS-03**: Agent-emitted communication contract — agents emit structured actions (`{action, company, recipient_role, template, fields}`); a deterministic dispatcher resolves contacts and sends. Email addresses never appear in any prompt or completion.
- [ ] **ACCESS-04**: Gateway-level output filtering — every LLM completion scanned for PII patterns, identifier leakage, canary tokens. Hits block + alert.
- [ ] **ACCESS-05**: Per-tenant per-class AI opt-out — `companies.ai_opt_out_classes` JSON list filters granularly (e.g., subscriptions yes, security alerts no).

#### Compliance Posture
- [ ] **COMP-01**: HIPAA-defensible baseline — BAA with Microsoft (Azure), BAA with Anthropic (Enterprise + zero retention confirmed in writing), 6-year audit retention for HIPAA-tagged customers, automatic 15-minute idle logoff, breach notification runbook
- [ ] **COMP-02**: SOC 2-ready controls — formal change management, quarterly access reviews, documented IR plan with annual tabletop, vendor risk management, continuous controls evidence (Drata/Vanta or equivalent — wired in but evidence collection optional until SOC 2 pursuit begins)
- [ ] **COMP-03**: CUI exclusion boundary — per-customer `cui_handling_required` flag, reduced sync surface for flagged customers (no tickets, no email, no asset details), default `ai_opt_out=true` for CUI customers, customer attestation on file, regex-based CUI marker detection in synced text fields, quarterly verification sample
- [ ] **COMP-04**: Subprocessor inventory + DPA template — Microsoft, Anthropic, controls platform vendor. Customer notification and opt-out workflow on subprocessor changes.
- [ ] **COMP-05**: AI-specific regulatory posture — model card, DPIA, prompt-injection adversarial test corpus in CI, output filtering, canary tokens in raw zone, decision-reversal paths documented for every agent-initiated action

#### Audit, Identity & Egress
- [ ] **AUDIT-01**: Immutable + cryptographically chained audit log — every audit entry contains SHA-256 of prior entry; mirrored to Azure Storage WORM (write-once, retention-locked) and Azure Sentinel
- [ ] **AUDIT-02**: Audit-of-audit — queries against the audit log are themselves logged
- [ ] **IDENT-01**: MFA mandatory on all access; phishing-resistant MFA (FIDO2 / smart card) on privileged access
- [ ] **IDENT-02**: Just-in-time admin via Entra PIM — no standing admin grants. Dual control on key rotation, schema changes, mass erasure, agent permission changes.
- [ ] **IDENT-03**: Per-service managed identities — agent identity, ETL identity, admin identity. No long-lived secrets; federated workload identity for service-to-service.
- [ ] **EGRESS-01**: Network egress allowlist on agent VNet — agent compute can only reach the LLM gateway, Azure SQL, Azure Storage. No general internet.
- [ ] **EGRESS-02**: Per-customer per-day token budgets and response-size caps at the gateway

#### Encryption, Retention, Erasure
- [ ] **ENC-01**: Always Encrypted on RESTRICTED columns (deterministic where joins required, randomized otherwise); TLS 1.2+ everywhere; Azure-managed keys at rest with architecture allowing customer-managed keys (CMK) as a future tier
- [ ] **RET-01**: Per-class retention policy — RESTRICTED 13 months default (extendable per-customer per-regulation), aggregates 5 years, audit log 6 years for HIPAA-tagged customers
- [ ] **ERAS-01**: Customer erasure workflow — pseudonym map purge invalidates all downstream pseudonyms; documented and tested; meets HIPAA right-to-amendment and GDPR right-to-erasure mechanics

#### Verification & Operations
- [ ] **VER-01**: End-to-end leak test — synthetic customer with marker strings loaded into raw zone; agent runs typical workflows; audit logs and completions grep'd for any marker; any hit fails the test. Runs in CI on every PR touching raw schemas, views, ETL, or grants.
- [ ] **VER-02**: Field-class drift detection — every column in raw schemas has a tagged class in source-of-truth; CI fails if a column exists without a tag or class assignment changes without review
- [ ] **OPS-01**: Production sizing baseline — Basic 5-DTU is dev-only; production tier sized for 5-year volume estimates per zone (raw zone heavy, 5–50 GB), monthly partitioning for high-volume tables, cold archive to Parquet on Azure Blob after retention thresholds

### Out of Scope

- **CMMC L2 compliance** — Gravity has no current DoD revenue justifying the ~50% scope expansion (FIPS 140-2 everywhere, GCC High deployment, dual-track architecture, C3PAO assessment, 110 NIST 800-171 controls). Defer until DoD revenue justifies. Replaced by CUI exclusion boundary (COMP-03) so the "we don't process CUI" claim is technically enforced and provable.
- **AI agents themselves** (Renewal Manager Agent, support triage agent, etc.) — Barycenter is the data and access layer those agents consume. Agents are downstream projects in their own repos.
- **Customer-facing surfaces** — dashboards, customer portals, briefings. Downstream consumers, not Barycenter's responsibility.
- **Sale to other MSPs / open source** — internal Gravity-ops tool only. Architectural choices favor Gravity's specific needs over generality.
- **HSM-backed keys (Premium Key Vault / Managed HSM)** — defer until a customer demands FIPS 140-2 Level 3. Architecture allows it; not built.
- **Confidential computing for agent runtime (Azure Confidential Containers)** — deferred. Bleeding-edge defensive depth, not justified yet.
- **Per-customer encryption envelope** — deferred. CMK arrives first if needed.
- **Cross-tool person-identity reconciliation via LLM** — never. Reconciliation runs in raw zone via deterministic code with code review. No fuzzy matching by AI on PII.
- **Synthetic data for development** — out of scope for the spec; v1 dev environment uses real production data behind raw-zone restrictions. Revisit if dev environment ever leaves the production security boundary.
- **GDPR EU-residency / EU AI Act compliance** — Gravity has no current EU customer base. Architecture compatible (region pinning, data flow diagrams) but not certified.

## Context

**Origin.** Barycenter began as Phase 35 of a parent project, Gravitron — an MSP-internal AI platform. As Gravitron grew (multiple agents, multiple consumers, customer-facing surfaces), the data layer became too entangled with too many concerns. Extracting it as its own project gives Barycenter:
- A clean ownership boundary (it's a data + security platform, not an agent platform)
- Its own release cadence and versioning independent of agent work
- A defensible compliance scope (HIPAA + SOC 2 + CUI exclusion is enough to claim; agent-side risks are not Barycenter's surface)
- Forced API discipline — agents become real consumers calling typed functions, not co-tenants of the data

**Domain.** Gravity is a Managed Service Provider (MSP). MSPs operate inside customer Microsoft 365 / Azure tenants, manage their endpoints, security, backup, and licensing, and bill monthly via subscriptions and ticket time. A typical Gravity customer touches 20–50 tools across categories: PSA (ConnectWise), distributor (Pax8), productivity (Microsoft Graph), RMM (Ninja, Datto), security (SentinelOne, Duo), backup, docs, MFA, quoting (FortiQuote), and more. Every tool has its own data model, its own PII surface, and its own renewal/billing dynamics. Without Barycenter, AI agents would have to reach into each tool's API individually, with no consistent security or pseudonymization story.

**The five layers of defense.** This is the architectural commitment that drives every decision:
1. SQL schema permissions — agent identity has zero grants on `raw_*` schemas
2. AI-safe views — only `ai_zone.*` views are exposed; field-class composition reviewed and tagged
3. Typed tool function layer — agents call functions, not raw queries; functions return validated DTOs
4. Gateway scrubbing — input and output filtering, pattern matching, canary detection
5. Per-prompt audit — every prompt and completion logged with structured metadata, immutable storage

A leak requires all five to fail at once. Each is independently sufficient against most threat classes; together they're the architectural moat.

**Identifier hierarchy.**

| Level | Pseudonym | Source | AI zone visible? |
|-------|-----------|--------|------------------|
| Tenant | tenant_id | Internal UUID | yes |
| Company | cw_company_id | ConnectWise (system-issued) | yes |
| Asset | serial_number | Vendor (system-issued) | yes |
| Person | person_pid | Synthetic from HMAC(email, per-tenant-salt) | yes |

Email never reaches AI zone. Hostnames, MACs, IPs are sensitive and are either dropped or hashed.

**Compliance posture.**
- **HIPAA = mandatory floor.** Gravity has healthcare customers handling PHI; HIPAA breach notification, BAAs, audit retention, and access controls are required, not optional.
- **SOC 2 Type II = deferred.** Dropped from v1.0 scope. Controls that overlap with HIPAA are re-homed to HIPAA requirements. Revisit when SOC 2 pursuit begins.
- **CMMC L2 = explicitly out.** No current DoD revenue. CUI exclusion controls (COMP-03) make the boundary technically enforceable instead of procedural.

**Existing tools, no existing code.** The source tools (CW Manage, Pax8, Graph, etc.) are already in production at Gravity — Barycenter syncs from them. There is no prior Barycenter code to inherit; the parent Gravitron repo had a security-spec draft that informs design but is not load-bearing.

**Prior architectural exploration.** A 645-line security spec draft (`35-SECURITY-SPEC.md`) exists in the parent Gravitron repo. It contains: starter field maps for CW Manage / Pax8 / Graph; the four-class field taxonomy; the eight transformation primitives; the four canonical AI-zone shapes; nine open decisions (D-01 through D-09) plus two added during the regulatory discussion (D-10 person identity strategy, D-11 agent-emitted communication contract). That spec is informational input here, not a binding artifact — Barycenter rewrites it under its own ownership.

## Constraints

- **Tech stack — Azure SQL Serverless (General Purpose)**: schema isolation between raw and AI zones, standard Gen5 hardware, auto-pause enabled. Why: schema-level grants are battle-tested; Serverless auto-pause fits infrequent agent query patterns and keeps cost under $50/mo; DC-series (Always Encrypted enclaves) dropped — CMMC is out of scope and TDE satisfies HIPAA §164.312.
- **Tech stack — FortiGate NVA (BYOL, hub-and-spoke)**: Gravity's Fortinet MSSP licensing; FortiGate-VM02 on Standard_F2s_v2 in Azure hub VNet. Why: provides outbound FQDN allowlisting, IDS/IPS, and subnet isolation at the network layer — stronger than per-application controls because it enforces before any code runs.
- **Tech stack — Microsoft Azure as cloud**: Gravity is M365-centric and the source tools are Azure-adjacent. Why: minimizes egress, simplifies BAA coverage, single identity plane (Entra ID).
- **Tech stack — Anthropic Claude as LLM**: BAA + ZDR confirmed in writing; Messages API + prompt caching + structured outputs only. Why: required for HIPAA-defensible AI. Batch API, Files API, Computer Use, Web Fetch, Code Execution are NOT BAA-covered and must be blocked at the gateway.
- **Tech stack — Owned FastAPI gateway (~300 LOC)**: replaces Azure API Management. Why: APIM Standard v2 is ~$250/mo alone — over budget. Owned gateway with Presidio PII scanning, canary checks, fail-closed audit emit, and model allowlist satisfies HIPAA Technical Safeguards with lower operational cost.
- **Budget — under $200/mo total Azure infrastructure**: FortiGate VM (~$62) + SQL Serverless (~$50) + Container Apps (~$20) + Key Vault + Storage + Log Analytics + Defender ≈ $166/mo. Why: internal MSP tool; cost must scale with Gravity's operational budget, not enterprise product assumptions.
- **Security — architectural over procedural**: every control must be enforced by code or configuration, not by someone remembering. Why: regulated environments and incident response require provable, auditable boundaries.
- **Compliance — HIPAA is the floor**: every design decision is HIPAA-compatible by default. Why: Gravity has PHI-handling customers; non-HIPAA modes add operational divergence we don't want.
- **Performance — sync-time filtering on CUI customers**: enforced in every adapter. Why: technical enforcement of "we don't process CUI" claim — attestation alone is not defensible.
- **Dependencies — agents are downstream consumers**: Barycenter ships its API contract; agents adapt. Why: prevents agent-side requirements from leaking into the security architecture.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Single Azure SQL DB with schema isolation (not split databases) | Schema permissions are battle-tested, less operational overhead, sufficient for the threat model. Re-evaluate if a customer demands physically separate storage. | — Pending |
| Two-zone model: `raw_*` + `ai_zone.*` | Architectural enforcement of the leak boundary. Agent identity has zero grants on raw schemas. | — Pending |
| Four field classes: RESTRICTED / SENSITIVE / INTERNAL / PUBLIC | Every column tagged; class drives storage, encryption, and AI exposure. Without classification, controls become ad hoc. | — Pending |
| HMAC-based person_pid (per-tenant salt, salt in Key Vault) | Email is both the cross-tool user key and PII. HMAC + synthetic pid preserves cross-tool correlation while keeping email out of AI zone. Agent identity has no salt access — one-way. | — Pending |
| Agent-emitted communication contract: structured actions, dispatcher resolves recipients | Email addresses never enter prompts or completions. Agent expresses intent; deterministic dispatcher acts. | — Pending |
| CUI handling explicitly out of scope, technically enforced | No current DoD revenue. `cui_handling_required` flag + reduced sync surface + canary detection makes the exclusion provable, not procedural. Avoids ~50% scope expansion of CMMC L2 compliance. | — Pending |
| HIPAA as compliance floor, SOC 2 as aspirational target | Gravity has PHI-handling customers (HIPAA mandatory). SOC 2 controls baked into architecture; evidence collection deferred until pursuit decision. | — Pending |
| Agents are downstream consumers, not co-tenants | Barycenter owns the API contract. Forces discipline at the boundary; prevents agent-specific concerns from polluting the data layer. | — Pending |
| Eight standard transformation primitives + four canonical AI-zone shapes | New tools compose ETL from primitives and contribute to existing shapes — they cannot invent novel AI-zone tables. Keeps the agent's mental model stable as tool count grows. | — Pending |
| Five-layer defense (schema permissions → views → typed functions → gateway → audit) | Each layer independently sufficient against most threat classes. All five must fail simultaneously for a leak. | — Pending |
| TDE (not Always Encrypted) on RESTRICTED columns; architecture allows AE upgrade later | AE with DC-series enclaves was CMMC-driven defensive depth, not a HIPAA requirement. TDE (AES-256) satisfies §164.312(a)(2)(iv). DBA-level threat mitigated by PIM JIT dual-approval + no standing `db_owner` + audit-of-audit. Upgrade path preserved. | — Pending |
| Cryptographically chained audit log to Log Analytics (90-day) + WORM blob (6-year); Sentinel deferred | HIPAA §164.312(b) audit controls satisfied by Log Analytics + WORM. Sentinel adds threat detection and SOC 2 evidence but costs scale with log volume. Deferred until SOC 2 pursuit begins. | — Pending |
| FortiGate NVA (BYOL hub-and-spoke) as network perimeter | FortiGate enforces outbound FQDN allowlist + IDS/IPS + subnet isolation at the network layer before any application code runs. Gravity's MSSP licensing makes VM compute the only cost (~$62/mo). Stronger than per-application VNet rules. | — Pending |
| Owned FastAPI gateway (~300 LOC) instead of Azure API Management | APIM Standard v2 is ~$250/mo — exceeds budget. Custom gateway with Presidio, canary checks, fail-closed audit emit, and model allowlist satisfies HIPAA Technical Safeguards. Evidence artifacts: git history, signed container SHAs, CI test suite, STRIDE threat model, annual pen test. | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-05-02 — v1.0 milestone started; architecture revised (cost-simplified, FortiGate hub-and-spoke, TDE not AE, owned gateway not APIM, HIPAA-only)*
