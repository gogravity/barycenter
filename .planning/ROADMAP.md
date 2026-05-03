# Barycenter — v1.0 Roadmap

**Milestone:** v1.0 — Barycenter MVP
**Goal:** Build the complete Barycenter platform — two-zone Azure SQL data layer with FortiGate network perimeter, five-layer defense, CW Manage / Pax8 / Graph integrations, owned AI gateway, VER-01 leak test in CI, and HIPAA compliance posture.
**Granularity:** standard
**Generated:** 2026-05-02
**Coverage:** 42/42 v1.0 MUST requirements mapped

---

## Phases

- [ ] **Phase 1: Network & Data Foundations** — Hub-and-spoke perimeter, two-zone SQL, identity model, audit chain, salt-in-Key-Vault — the load-bearing substrate before any PII row is written.
- [ ] **Phase 2: Tool Onboarding Framework + ConnectWise Manage** — Eight ETL primitives, four AI-zone shapes, CUI enforcement at framework, INT-01 metadata-only ingest, salt rotation runbook fire drill.
- [ ] **Phase 3: Agent-Safe Access Layer + Leak Test** — Typed functions, owned FastAPI gateway with 9-step middleware, action dispatcher, VER-01 in CI gating every agent-affecting PR.
- [ ] **Phase 4: Integrations 2 & 3 + Compliance Posture** — Pax8, Microsoft Graph, HIPAA baseline complete, erasure tested end-to-end, on-call paging wired.

---

## Phase Details

### Phase 1: Network & Data Foundations
**Goal**: A hardened, audit-anchored Azure substrate exists in which any future PII write lands inside a network-perimetered, identity-segregated, immutably-logged data plane — and an attempt to bypass any of those properties is provably blocked or detected.
**Depends on**: Nothing (first phase)
**Requirements**: FOUND-01, FOUND-02, FOUND-03, FOUND-04, NETW-01, NETW-02, NETW-03, AUDIT-01, AUDIT-02, AUDIT-03, IDENT-01, IDENT-02, IDENT-03, IDENT-04, IDENT-05, EGRESS-01, ENC-01, VER-02, COMP-06
**Success Criteria** (what must be TRUE):
  1. A FortiGate hub with a Barycenter spoke is live; the ETL-subnet-to-Anthropic deny rule and the services-subnet-to-source-tools deny rule are both tested with synthetic traffic and the deny events appear in Log Analytics.
  2. Azure SQL is reachable only via private endpoint with `publicNetworkAccess=Disabled`; `raw_*` schemas exist with zero grants to the platform identity, and a CI gate fails any PR adding a column without a field-class tag.
  3. Every audit event written to Log Analytics carries a SHA-256 hash chained to the prior event and is mirrored to a WORM blob container whose 6-year retention policy is locked at container creation; a query against the audit log itself produces an audit-of-audit entry.
  4. All four managed identities (etl, platform, audit, admin) exist with no long-lived secrets; PIM JIT with dual-approval is the only path to `raw_*` access; main branch is protected with required signed commits and CI checks.
  5. Per-tenant HMAC salts live in Key Vault, accessed only by the etl identity via a sign operation (never returned in plaintext), and the BAA inventory document (Microsoft + Anthropic + ZDR confirmation) is committed to the repo.
**Plans**: 9 plans
- [x] 01-01-PLAN.md — Repo bootstrap + audit SDK skeleton + compliance scaffolding (Wave 0)
- [x] 01-02-PLAN.md — OIDC bootstrap (mi-bary-deploy + federated credentials) [checkpoint]
- [x] 01-03-PLAN.md — Identity Bicep (4 MIs + PIM eligibility for admin) (Wave 1)
- [x] 01-04-PLAN.md — Networking Bicep (hub + FortiGate + spoke + recursion-safe UDR + policies.json) (Wave 1)
- [x] 01-05-PLAN.md — Data Bicep (SQL Serverless + KV) + SQL schemas/grants/genesis seed + field-class registry (Wave 2)
- [x] 01-06-PLAN.md — Audit Bicep (LA + WORM-locked-6yr + DCR + diagnostic settings) (Wave 2)
- [x] 01-07-PLAN.md — Audit SDK implementation (TDD: chain + sinks + AuditClient.emit fail-closed) (Wave 3)
- [x] 01-08-PLAN.md — CI scripts + GitHub Actions workflows (VER-02, NETW-02, AUDIT-01, Pitfall-1 grants) (Wave 3)
- [x] 01-09-PLAN.md — Phase exit: branch protection, MFA, BAA inventory, live deny verification [checkpoint] (Wave 4)

### Phase 2: Tool Onboarding Framework + ConnectWise Manage
**Goal**: The framework that all future tool integrations inherit from is operational and exercised end-to-end against ConnectWise Manage with bounded-PII data — proving CUI enforcement, body-stripping, schema-drift detection, and salt-based pseudonymization all hold in production conditions before higher-PII integrations land.
**Depends on**: Phase 1
**Requirements**: TOOL-01, TOOL-02, TOOL-03, TOOL-04, INT-01, COMP-03, COMP-07, ENC-02, RET-01
**Success Criteria** (what must be TRUE):
  1. Eight T-SQL transformation primitives (drop, hash, pseudonymize, aggregate, bucket, score, keyword_flags, as_is) are deployed and a new tool's ETL recipe is composed from them — adapters cannot bypass the primitive layer.
  2. The ConnectWise Manage adapter syncs companies, agreements, ticket metadata (no bodies), configurations, and time-entry aggregates into `raw_cw.*`; ticket bodies are architecturally stripped before write, verified by an automated test that fails the build if a body field appears in the raw schema.
  3. A CUI-flagged synthetic customer's data is verifiably reduced at sync time (no tickets, no asset details, `ai_opt_out=true` defaulted), and CUI canary phrases injected into ticket subjects, filenames, and attachments trigger detection and refuse the attachment.
  4. The four canonical AI-zone shapes (`customer_snapshot`, `customer_features_*`, `timeseries_aggregate`, `customer_memory`) are populated from CW data; an attempt to introduce a novel AI-zone table fails review/CI.
  5. The salt rotation runbook has been executed as a fire drill on a non-production tenant — versioned pepper IDs roll forward, downstream pseudonyms remain valid through the rotation window, and the procedure is committed to the repo.
**Plans**: 6 plans
- [x] 02-01-PLAN.md — Wave 0 scaffold: barycenter-etl package, test stubs, compliance YAMLs, salt-runbook CI gate
- [x] 02-02-PLAN.md — Eight TOOL-02 primitives + ETLRecipe + Pseudonymizer + ETL exception hierarchy (Wave 1)
- [x] 02-03-PLAN.md — SQL DDL: raw_cw remaining tables (no body), pseudo.person_map, four ai_zone shapes; grants + field-class registry (Wave 1)
- [x] 02-04-PLAN.md — Framework gates: CanaryScanner, CUIGate, ShapeBuilder, RetentionSweeper, SaltRotation, AdapterBase (Wave 2)
- [ ] 02-05-PLAN.md — ConnectWise adapter: client + auth + recipes + adapter + run.py + GH workflows (Wave 3)
- [ ] 02-06-PLAN.md — Phase exit: CW credential setup + salt rotation fire drill [checkpoint] (Wave 4)

### Phase 3: Agent-Safe Access Layer + Leak Test
**Goal**: The full five-layer defense is active: agents reach data only via typed functions, every LLM call is mediated by the owned gateway with input/output Presidio + canary scanning, communications go through a deterministic dispatcher, and a synthetic-marker leak test in CI fails any PR that breaches the boundary — all before any real agent connects.
**Depends on**: Phase 2
**Requirements**: ACCESS-01, ACCESS-02, ACCESS-03, ACCESS-04, ACCESS-05, ACCESS-06, ACCESS-07, ACCESS-08, EGRESS-02, COMP-05, VER-01
**Success Criteria** (what must be TRUE):
  1. Agents can read AI-zone data only by calling typed functions (e.g. `get_customer_snapshot(cw_company_id)`) returning validated Pydantic DTOs; every `ai_zone.*` view has a documented field-class composition with no RESTRICTED data and no un-pseudonymized SENSITIVE data.
  2. Every LLM call passes through the FastAPI gateway's 9-step middleware chain (auth, rate limit, budget, inbound Presidio, inbound canary, model call, outbound Presidio, outbound canary, async audit); the gateway rejects any model version not in its allowlist and a per-tenant or global kill switch disables traffic without redeployment.
  3. VER-01 runs in CI on every PR touching raw schemas, AI-zone views, ETL, grants, or gateway code: synthetic markers loaded into raw zone are grep-checked across completions and audit logs, and any hit fails the build.
  4. Agent-emitted communications use the structured action contract (`{action, company, recipient_role, template, fields}`) — the dispatcher resolves contacts and sends, and an automated check confirms no email address appears in any prompt, completion, or audit payload.
  5. Per-tenant per-day token budgets, response-size caps, and per-class AI opt-out (`companies.ai_opt_out_classes`) are enforced at the gateway with regression tests; the Presidio recognizer suite covers MSP-domain identifiers (cw_company_id, serial numbers, PO numbers) and the adversarial prompt-injection corpus runs in CI.
**Plans**: TBD

### Phase 4: Integrations 2 & 3 + Compliance Posture
**Goal**: Pax8 and Microsoft Graph are integrated through the proven framework in escalating-PII order, customer erasure works end-to-end across every data-holding system, and the HIPAA evidence package + on-call alerting are complete — v1.0 is shippable.
**Depends on**: Phase 3
**Requirements**: INT-02, INT-03, COMP-01, ERAS-01, OPS-02
**Success Criteria** (what must be TRUE):
  1. The Pax8 adapter (subscriptions, SKU codes, renewal dates, monthly value) and the Microsoft Graph adapter (users hashed to person_pid, license counts, tenant metadata) sync through the existing framework — no new adapter base, no novel AI-zone shapes, no body content.
  2. A test customer's erasure request purges the pseudonym map and cascades through raw zone, AI-zone projections, dev environment, and downstream caches; the audit log is preserved with documented justification, and the procedure is documented and timed.
  3. The HIPAA baseline is complete and provable: signed BAAs (Microsoft + Anthropic with ZDR) are referenced in the repo, 15-minute idle logoff is enforced, the breach notification runbook is written, the quarterly access review schedule and annual IR tabletop are on the calendar, and 6-year audit retention is confirmed for HIPAA-tagged customers.
  4. On-call alerting pages the right human within minutes of: a sync job failure, gateway error rate above 1%, an audit write failure, FortiGate config drift, or a VER-01 failure in CI — verified by an injected-failure drill for each alert class.
  5. VER-01 has run clean across at least one full release cycle covering all three integrations; this is the gate that unlocks v1.1 (INT-04 email signals).
**Plans**: TBD

---

## Phase Order Constraints

The phase ordering is not negotiable — reversing any of these breaks the architectural claim:

1. **Network + foundations before any PII row** (Phase 1 first). FortiGate deny rules, schema isolation, audit chain, salt service, managed identities all exist before data flows.
2. **Audit chain format locked before data flows** (Phase 1). Retroactive re-chaining is impossible.
3. **Salt service before pseudonymization** (Phase 1 before Phase 2). HMAC pid generation depends on Key Vault salt access path being live.
4. **Tool onboarding framework validated with INT-01 before INT-02/INT-03** (Phase 2 before Phase 4). CW is bounded-PII; framework correctness must be proven on it before person-level PII enters.
5. **Agent-safe access layer complete before any real agent connects** (Phase 3 gates downstream agent projects).
6. **VER-01 wired into CI and passing before INT-02/INT-03** (Phase 3 before Phase 4). Leak test must guard the higher-PII integrations.
7. **INT-02 (Pax8, lower PII) before INT-03 (Graph, person-level PII)** (within Phase 4). Escalating-PII exposure order.

---

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Network & Data Foundations | 0/9 | Planned | — |
| 2. Tool Onboarding + ConnectWise | 0/0 | Not started | — |
| 3. Agent-Safe Access + Leak Test | 0/0 | Not started | — |
| 4. Integrations 2/3 + Compliance | 0/0 | Not started | — |

---

## Coverage Validation

All 42 v1.0 MUST requirements mapped to exactly one phase. No orphans. No duplicates.

| Category | Count | Phases |
|----------|-------|--------|
| Foundation (FOUND) | 4 | P1 |
| Network (NETW) | 3 | P1 |
| Tool Onboarding (TOOL) | 4 | P2 |
| Integrations (INT) | 3 | P2 (INT-01), P4 (INT-02, INT-03) |
| Agent Access (ACCESS) | 8 | P3 |
| Compliance (COMP) | 5 | P1 (COMP-06), P2 (COMP-03, COMP-07), P3 (COMP-05), P4 (COMP-01) |
| Audit (AUDIT) | 3 | P1 |
| Identity (IDENT) | 5 | P1 |
| Egress (EGRESS) | 2 | P1 (EGRESS-01), P3 (EGRESS-02) |
| Encryption (ENC) | 2 | P1 (ENC-01), P2 (ENC-02) |
| Retention/Erasure (RET/ERAS) | 2 | P2 (RET-01), P4 (ERAS-01) |
| Verification/Ops (VER/OPS) | 3 | P1 (VER-02), P3 (VER-01), P4 (OPS-02) |
| **Total** | **42** | — |

INT-04 explicitly deferred to v1.1 (hard entry criterion: 90 days of clean VER-01 in CI).

---

*Last updated: 2026-05-02 — roadmap created from revised cost-simplified architecture research*
