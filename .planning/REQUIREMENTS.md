# Barycenter — v1.0 Requirements

**Milestone:** v1.0 — Barycenter MVP  
**Goal:** Build the complete Barycenter platform — two-zone Azure SQL data layer with FortiGate network perimeter, five-layer defense, CW Manage / Pax8 / Graph integrations, owned AI gateway, VER-01 leak test in CI, and HIPAA compliance posture.  
**Generated:** 2026-05-02  
**Stack:** Azure SQL Serverless GP · FortiGate NVA BYOL · Owned FastAPI gateway · Log Analytics + WORM blob · 4 managed identities · ~$166/mo

---

## v1.0 Requirements

### Foundation

- [ ] **FOUND-01**: Two-zone Azure SQL architecture with schema isolation — `raw_*` schemas (full-fidelity, agent has zero grant) and `ai_zone.*` schema (pseudonymized, agent-readable views only)
- [ ] **FOUND-02**: Field classification standard — every column tagged RESTRICTED / SENSITIVE / INTERNAL / PUBLIC, drives storage, encryption, and AI exposure
- [ ] **FOUND-03**: Identifier hierarchy — tenant_id (internal), cw_company_id (system-issued), serial_number (vendor-issued), person_pid (synthetic, derived from HMAC of email per-tenant-salt via Key Vault sign operation)
- [ ] **FOUND-04**: Five-layer defense — schema permissions, AI-safe views, typed tool functions, gateway scrubbing, per-prompt audit. All five must fail simultaneously for a leak.

### Network & Perimeter

- [ ] **NETW-01**: FortiGate config-as-code — all firewall rules, FQDN objects, and UDRs defined in version-controlled Bicep/Terraform; zero console-only rules
- [ ] **NETW-02**: FortiGate drift detection — nightly comparison of live FortiGate config against config-as-code; alert on any divergence
- [ ] **NETW-03**: FortiGate log ingestion — IDS/IPS hits, traffic logs, and denied-connection logs forwarded to Log Analytics workspace for HIPAA audit trail

### Tool Onboarding Framework

- [ ] **TOOL-01**: Standardized Tool Onboarding Spec template — every new tool fills the same intake doc (field map, raw schema, ETL recipe, AI-zone contributions, retention, erasure)
- [ ] **TOOL-02**: Eight standard transformation primitives — drop, hash, pseudonymize, aggregate, bucket, score, keyword_flags, as_is. Tools compose ETL from these.
- [ ] **TOOL-03**: Four canonical AI-zone shapes — `customer_snapshot`, `customer_features_*`, `timeseries_aggregate`, `customer_memory`. Tools contribute into these; tools cannot invent new AI-zone tables.
- [ ] **TOOL-04**: Tool category taxonomy — productivity, RMM, security, backup, docs, distributors, CW. New tools slot into existing category, ETL recipe inherits.

### Tool Integrations

- [ ] **INT-01**: ConnectWise Manage — companies, agreements, tickets (metadata only, no body content), configurations, time entries (aggregates only)
- [ ] **INT-02**: Pax8 — subscriptions, SKU codes, renewal dates, monthly value
- [ ] **INT-03**: Microsoft Graph — users (hashed → person_pid), license assignments (counts only), tenant metadata

### Agent-Safe Access Layer

- [ ] **ACCESS-01**: AI-safe views — every view in `ai_zone.*` schema has documented field-class composition. No RESTRICTED data, no SENSITIVE data without pseudonymization.
- [ ] **ACCESS-02**: Typed tool function contract — agents do not write SQL. They call typed functions (e.g., `get_customer_snapshot(cw_company_id)`) that return validated Pydantic structures.
- [ ] **ACCESS-03**: Agent-emitted communication contract — agents emit structured actions (`{action, company, recipient_role, template, fields}`); a deterministic dispatcher resolves contacts and sends. Email addresses never appear in any prompt or completion.
- [ ] **ACCESS-04**: Gateway-level output filtering — every LLM completion scanned for PII patterns (Presidio), identifier leakage, canary tokens. Hits block + alert.
- [ ] **ACCESS-05**: Per-tenant per-class AI opt-out — `companies.ai_opt_out_classes` JSON list filters granularly (e.g., subscriptions yes, security alerts no).
- [ ] **ACCESS-06**: Gateway kill switch — per-tenant disable and global disable without redeployment; configurable via SQL-backed flag table
- [ ] **ACCESS-07**: Gateway PII test fixtures — Presidio recognizer validation suite in CI covering MSP-domain identifiers (cw_company_id, serial numbers, PO numbers, email patterns)
- [ ] **ACCESS-08**: Gateway model allowlist — owned gateway rejects any Anthropic model version not in an explicit allowlist; model version pinned in config, not hardcoded

### Compliance Posture

- [ ] **COMP-01**: HIPAA-defensible baseline — BAA with Microsoft (Azure), BAA with Anthropic (Enterprise + zero retention confirmed in writing), 6-year audit retention for HIPAA-tagged customers, automatic 15-minute idle logoff, breach notification runbook
- [ ] **COMP-03**: CUI exclusion boundary — per-customer `cui_handling_required` flag, reduced sync surface for flagged customers (no tickets, no email, no asset details), default `ai_opt_out=true` for CUI customers, customer attestation on file, regex-based CUI marker detection in synced text fields, quarterly verification sample
- [ ] **COMP-05**: AI-specific regulatory posture — model card, DPIA, prompt-injection adversarial test corpus in CI, output filtering, canary tokens in raw zone, decision-reversal paths documented for every agent-initiated action
- [ ] **COMP-06**: BAA inventory document — Azure BAA reference link, Anthropic BAA copy, ZDR confirmation in writing, all committed to repo and reviewed annually
- [ ] **COMP-07**: CUI canary detection extended to email subjects, filenames, and attachments — attachments refused for CUI-flagged adapters

### Audit, Identity & Egress

- [ ] **AUDIT-01**: Cryptographically chained audit log — every audit entry contains SHA-256 of prior entry; written to Log Analytics (90-day hot) and mirrored to Azure Storage WORM (write-once, retention-locked, 6-year)
- [ ] **AUDIT-02**: Audit-of-audit — queries against the audit log are themselves logged
- [ ] **AUDIT-03**: WORM blob retention policy locked at 6 years for HIPAA-tagged customers; policy lock applied at container creation and cannot be shortened
- [ ] **IDENT-01**: MFA mandatory on all access; phishing-resistant MFA (FIDO2 / hardware key) on privileged access
- [ ] **IDENT-02**: Just-in-time admin via Entra PIM — no standing admin grants. Dual control on key rotation, schema changes, mass erasure, agent permission changes.
- [ ] **IDENT-03**: Per-service managed identities — 4 identities (etl-identity, platform-identity, audit-identity, admin-identity). No long-lived secrets; workload identity for service-to-service.
- [ ] **IDENT-04**: Branch protection and signed commits — no direct push to main branch; CI must pass before merge; commits signed
- [ ] **IDENT-05**: PIM dual-approval for raw-zone access — any human activation for `raw_*` access requires a second approver and a documented justification ticket
- [ ] **EGRESS-01**: Network egress allowlist via FortiGate FQDN policy — agent compute can only reach the Anthropic API endpoint and Azure private endpoints. ETL spoke and agent spoke are network-isolated from each other.
- [ ] **EGRESS-02**: Per-tenant per-day token budgets and response-size caps enforced at the owned gateway

### Encryption, Retention, Erasure

- [ ] **ENC-01**: TDE (transparent data encryption, AES-256) on Azure SQL — enabled by default; satisfies HIPAA §164.312(a)(2)(iv). TLS 1.2+ everywhere. Architecture allows Always Encrypted upgrade on RESTRICTED columns if a future customer demands it.
- [ ] **ENC-02**: Salt rotation runbook — documented and tested procedure for rotating per-tenant HMAC salts (versioned pepper IDs, online rebuild steps, rollback procedure). Runbook in repo; rotation fire drill completed before v1.0 ships.
- [ ] **RET-01**: Per-class retention policy — RESTRICTED 13 months default (extendable per-customer per-regulation), aggregates 5 years, audit log 6 years for HIPAA-tagged customers
- [ ] **ERAS-01**: Customer erasure workflow — pseudonym map purge invalidates all downstream pseudonyms; documented and tested cascade through every data-holding system

### Verification & Operations

- [ ] **VER-01**: End-to-end leak test — synthetic customer with marker strings loaded into raw zone; agent runs typical workflows; audit logs and completions grep'd for any marker; any hit fails the test. Runs in CI on every PR touching raw schemas, views, ETL, or grants.
- [ ] **VER-02**: Field-class drift detection — every column in raw schemas has a tagged class in source-of-truth; CI fails if a column exists without a tag or class assignment changes without review
- [ ] **OPS-02**: On-call alerting — paging integration for: sync job failures, gateway error rate >1%, audit write failures, FortiGate drift detected, VER-01 failure in CI

---

## Future Requirements (v1.1+)

- **INT-04**: Email-derived signals — structured extracts only (PO numbers, sentiment, intent). Deferred: highest-PII surface; requires VER-01 with 90 days clean in CI before introducing LLM-in-pipeline extraction.
- **COMP-04**: Subprocessor inventory + DPA template — Microsoft, Anthropic, controls platform vendor. Document task; not blocking v1.0.
- **OPS-01**: Production sizing baseline — cold archive to Parquet on Azure Blob after retention thresholds, monthly partitioning for high-volume tables. Tune after v1.0 deployment data.

---

## Out of Scope

- **COMP-02 (SOC 2-ready controls)** — Dropped for this milestone. Controls re-homed: quarterly access reviews → COMP-01; dual-control mechanisms → IDENT-04/IDENT-05; BAA inventory → COMP-06. Revisit when SOC 2 pursuit begins.
- **CMMC L2** — No current DoD revenue. CUI exclusion boundary (COMP-03) makes the "we don't process CUI" claim technically enforced.
- **AI agents themselves** — Barycenter is the data and access layer. Agents are downstream.
- **Customer-facing surfaces** — dashboards, portals. Downstream consumers.
- **Always Encrypted with secure enclaves (DC-series)** — Deferred; architecture is compatible. Upgrade when a customer demands it or CMMC scope expands.
- **Microsoft Sentinel as primary SIEM** — Deferred; Log Analytics + WORM blob satisfies HIPAA §164.312(b) for v1.0. Add Sentinel when SOC 2 evidence collection begins.
- **Drata/Vanta** — Deferred until SOC 2 pursuit or HHS audit risk warrants it.
- **HSM-backed keys (Premium Key Vault / Managed HSM)** — Deferred; architecture allows upgrade.
- **Azure Confidential Containers** — Deferred; no current threat model justification.
- **INT-04 email signals in v1.0** — Deferred to v1.1 (see Future Requirements).

---

## Traceability

| REQ-ID | Phase | Status |
|--------|-------|--------|
| FOUND-01 | Phase 1 | Pending |
| FOUND-02 | Phase 1 | Pending |
| FOUND-03 | Phase 1 | Pending |
| FOUND-04 | Phase 1 | Pending |
| NETW-01 | Phase 1 | Pending |
| NETW-02 | Phase 1 | Pending |
| NETW-03 | Phase 1 | Pending |
| TOOL-01 | Phase 2 | Pending |
| TOOL-02 | Phase 2 | Pending |
| TOOL-03 | Phase 2 | Pending |
| TOOL-04 | Phase 2 | Pending |
| INT-01 | Phase 2 | Pending |
| INT-02 | Phase 4 | Pending |
| INT-03 | Phase 4 | Pending |
| ACCESS-01 | Phase 3 | Pending |
| ACCESS-02 | Phase 3 | Pending |
| ACCESS-03 | Phase 3 | Pending |
| ACCESS-04 | Phase 3 | Pending |
| ACCESS-05 | Phase 3 | Pending |
| ACCESS-06 | Phase 3 | Pending |
| ACCESS-07 | Phase 3 | Pending |
| ACCESS-08 | Phase 3 | Pending |
| COMP-01 | Phase 4 | Pending |
| COMP-03 | Phase 2 | Pending |
| COMP-05 | Phase 3 | Pending |
| COMP-06 | Phase 1 | Pending |
| COMP-07 | Phase 2 | Pending |
| AUDIT-01 | Phase 1 | Pending |
| AUDIT-02 | Phase 1 | Pending |
| AUDIT-03 | Phase 1 | Pending |
| IDENT-01 | Phase 1 | Pending |
| IDENT-02 | Phase 1 | Pending |
| IDENT-03 | Phase 1 | Pending |
| IDENT-04 | Phase 1 | Pending |
| IDENT-05 | Phase 1 | Pending |
| EGRESS-01 | Phase 1 | Pending |
| EGRESS-02 | Phase 3 | Pending |
| ENC-01 | Phase 1 | Pending |
| ENC-02 | Phase 2 | Pending |
| RET-01 | Phase 2 | Pending |
| ERAS-01 | Phase 4 | Pending |
| VER-01 | Phase 3 | Pending |
| VER-02 | Phase 1 | Pending |
| OPS-02 | Phase 4 | Pending |

**Coverage:** 42/42 v1.0 MUST requirements mapped (no orphans, no duplicates).
