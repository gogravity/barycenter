# Project Research Summary

**Project:** Barycenter
**Domain:** MSP-internal AI-safe data platform (Azure-native, two-zone PII architecture, HIPAA floor + SOC 2 aspirational, technical CUI exclusion)
**Researched:** 2026-05-01
**Confidence:** HIGH on the load-bearing decisions; MEDIUM on a small set of product choices (controls platform, LLM gateway build-vs-buy, exact AI-zone shape physicalization) where reasonable alternatives exist.

## Executive Summary

Barycenter is an unusual project: it's an internal MSP data platform whose single load-bearing claim — "architecturally impossible for AI agents to leak customer PII or CUI" — drives every other decision. All four research streams converge on the same conclusion: this is a **security-architecture project that happens to ship data and an LLM**, not the reverse. The roadmap's order of operations is therefore inverted from a typical data-platform build: the *audit plane, identity boundary, and pseudonymization service must exist before a single PII row lands*, and the *typed-function + gateway + leak-test must exist before a single agent prompt is served*. Skipping or reordering these breaks the architectural moat and converts five-layer defense into procedural-defense.

The recommended stack is **Azure-native everywhere it touches data, identity, or audit**, with two carefully scoped non-Azure choices — Anthropic Claude (constraint-given, BAA + ZDR scoped to Messages API + prompt caching + structured outputs only) and Drata (Microsoft Purview Compliance Manager is *not* a viable substitute for auditor-ready evidence). The opinionated calls: Azure SQL DB on **DC-series hardware** (the only SKU with Intel SGX enclaves, required for joinable Always Encrypted on RESTRICTED columns), schema-per-tool in the raw zone, **a thin owned AI gateway** rather than LiteLLM/APIM, **a separate salt-service microservice** rather than a SQL function, **dbt-sqlserver for in-database transformations** (not for ingestion), and **Azure SQL Ledger + WORM blob mirror + Sentinel** as a three-tier audit plane.

Risk concentration is unusually high in three areas the roadmap must front-load: (1) **prompt-injection via tool-sourced free text** is now a published CVE-class threat (CVE-2026-21520, Anthropic's own Claude Code Security Review post-mortem) — Barycenter's mitigation is architectural (no ticket bodies, structured extracts only, gateway canary scrubbing); (2) **HMAC-on-email pseudonymization is reversible against a low-entropy input space** if the salt ever leaks or quasi-identifiers re-identify across views — mitigation requires per-tenant salt in Key Vault accessed only by the salt-service identity, plus k-anonymity discipline on view composition, not just per-column tagging; (3) **Anthropic BAA scope is product- and feature-specific** — Batch API, Files API, Computer Use, Web Fetch, and Code Execution are *not* covered, and ZDR is opt-in per workspace. These three pitfalls each require both a foundation-phase control and a verification-phase test that runs on every PR.

## Key Findings

### Recommended Stack

The stack converges on Azure platform services for everything that touches data, identity, or audit. The two non-Azure choices (Anthropic, Drata) are scope-bounded and BAA-covered. The build-vs-buy lines are deliberate: APIM AI Gateway is the *generic* HIPAA-defensible LLM gateway, but Barycenter's gateway needs HIPAA audit-chain integration, domain-specific canary detection, and per-tenant per-class opt-out — all custom enough that a small (~1-2k LOC) owned gateway is the right call.

**Core technologies:**
- **Azure SQL Database, General Purpose vCore Gen5, DC-series hardware, single instance** — two-zone schema-isolated store; DC-series is the only SKU with Intel SGX enclaves required for joinable Always Encrypted on RESTRICTED columns. Hyperscale is rejected (no enclave support as of 2026-05).
- **Azure SQL Ledger + WORM Blob (Cool, immutable, retention-locked) + Microsoft Sentinel** — three-tier audit plane. Ledger gives engine-level append-only protection; WORM is the cold legal-hold; Sentinel is the off-system observability mirror.
- **Azure Container Apps (services) + Container Apps Jobs (sync workers)** — VNet-integrated, managed-identity-native, scale-to-zero where possible. Adapters as Jobs, salt-service / tool-functions / gateway / dispatcher as services.
- **Anthropic Claude API direct** (claude-sonnet-4-5, claude-opus-4-7, dated versions only) — BAA covers Messages API + prompt caching + structured outputs *only*. Batch / Files / Computer Use / Web Fetch / Code Execution are excluded and must be blocked at the gateway. Bedrock and Vertex have different cache-isolation scope and a different BAA party — the project pins to first-party.
- **Entra ID P2 + PIM + FIDO2 + Conditional Access + per-service managed identities** — six service identities (etl, salt, tool, gateway, dispatcher, audit-writer) plus admin via PIM JIT. Three Key Vaults: salt-vault, cmk-vault, api-vault.
- **dbt-core + dbt-sqlserver** — for in-database raw → ai_zone transformations (the eight primitives encoded as dbt macros). Not for ingestion; ingestion is custom Python + httpx + tenacity per adapter.
- **Microsoft Presidio** — PII detection inside the gateway scrubber and the VER-01 leak-test runner.
- **Drata** — controls platform for SOC 2 + HIPAA evidence. Wired in early (Block E), evidence collection optional until SOC 2 pursuit. Vanta is a defensible alternative; **Microsoft Purview Compliance Manager is explicitly not a substitute** (posture-only, not auditor-ready).

**Anti-recommendations:** Hyperscale (no SGX), GCC High (out of scope), public OpenAI / OpenAI SDK direct, generic LiteLLM-as-primary-gateway (operational ownership burden in HIPAA boundary), Microsoft Fabric (overkill, less mature workspace identity model), Azure AD B2C (wrong product), Premium Key Vault / Managed HSM (deferred), Anthropic via Bedrock/Vertex (cache-isolation and BAA scope diverge).

See: `.planning/research/STACK.md`

### Expected Features

PROJECT.md already encodes most table-stakes features. Feature research focused on **gaps and mis-categorizations**.

**Must have (table stakes) — gaps surfaced beyond PROJECT.md:**
- Per-tool incremental sync with cursor persistence + distinct backfill workflow
- Retry + DLQ for failed records + per-tool rate-limit awareness
- Source schema drift detection (distinct from VER-02 Barycenter-internal drift)
- Sync health dashboard + AI-zone freshness SLA per view
- On-call alerting (paging) integration
- Per-prompt + per-completion trace shape standardized (gap in AUDIT-01)
- Salt rotation mechanics (versioned pepper) — gap in FOUND-03
- Erasure cascade specification (gap in ERAS-01) enumerating every data-holding system
- Schema-change impact analysis tooling

**Should have (differentiators):**
- Schema registry as control plane (not just YAML catalog)
- AI-zone view contract per view (dual-reviewed artifact)
- Kill-chain canary methodology (arXiv 2603.28013) — stage-level tracking
- OWASP Top 10 for Agentic AI 2026 explicit control mapping
- Source-of-truth reconciliation rules (deterministic only, never LLM)

**Anti-features (architectural commitments to never build):**
- LLM-driven entity resolution / fuzzy matching of PII
- Agent-writable raw zone, ever
- Email or RESTRICTED PII in AI zone
- Raw email/ticket bodies in AI zone (only structured extracts)
- Novel AI-zone tables per-tool (must compose into the four canonical shapes)
- Free-form agent SQL access
- AI-zone reads through BAA-less LLMs
- Agent identity with salt access
- **Cross-tenant joins in AI zone** (newly surfaced)
- **Bulk LLM-driven field classification** (newly surfaced)

**Defer (v1.x / v2+):** INT-02 Pax8 (after CW + Graph), INT-04 email signals (last; highest-PII), Drata evidence collection turned on, kill-chain canary methodology, OWASP control mapping, additional integrations, CMK, HSM, confidential computing, CMMC L2, EU residency.

See: `.planning/research/FEATURES.md`

### Architecture Approach

**Azure SQL with two schema zones (raw_* and ai_zone), bracketed by a salt-service microservice on the input side and a typed-function + AI-gateway pair on the agent side, with a single audit plane fanning out to WORM + Sentinel.** Six service identities, three Key Vaults, one VNet with private endpoints. The five layers of defense are not five components — they are five places where a leak must independently fail.

**Major components:**
1. **Sync Plane (Container Apps Jobs)** — adapter + staging loader + DLQ. ETL identity has zero on `ai_zone`.
2. **Azure SQL DB** — `raw_<tool>.*` (per-tool, AE on RESTRICTED), `ai_zone.*` (indexed views hot / refreshed tables heavy: `customer_snapshot`, `customer_features_*`, `timeseries_aggregate`, `customer_memory`), `pseudo.*` (etl-only).
3. **Salt Service** — own identity, own Key Vault, exclusive salt access. Stateless. Crown-jewel microservice.
4. **AI-Zone Builder** — eight T-SQL primitives + dbt-sqlserver orchestration.
5. **Typed Tool Function Layer** — DAB (read 80%) + custom FastAPI/.NET (action-emission, orchestration 20%).
6. **Action Dispatcher** — only component besides ETL with raw-zone read. Resolves agent actions → outbound.
7. **AI Gateway (~1-2k LOC owned)** — input scrub + canary + budget enforce + Anthropic call (pinned endpoint + model) + output filter + audit emit.
8. **Audit Plane** — Service Bus → single Audit Writer → WORM (locked retention) + Sentinel mirror.
9. **Identity & Key Plane** — Entra PIM + six managed identities + three Key Vaults.

**Patterns to preserve:** schema-per-tool (not shared raw); ELT inside Azure SQL; salt service as separate microservice; indexed views hot + refreshed tables heavy; build the AI gateway, don't buy; audit on Service Bus → single writer → WORM + Sentinel.

See: `.planning/research/ARCHITECTURE.md`

### Critical Pitfalls

15 distinct failure modes; **7 are LOAD-BEARING**. Top of the list:

1. **Indirect prompt injection via tool-sourced free text** [LOAD-BEARING] — CVE-2026-21520; Anthropic Claude Code "not hardened against prompt injection." Mitigation: strip raw bodies, structured extractors with restrictive system prompts + validated DTO outputs, gateway canary regex, instruction-data XML wrapping, adversarial corpus in CI. **Tool Onboarding + Access Layer.**
2. **HMAC pid reversible against low-entropy email** [LOAD-BEARING] — EDPS/ENISA flag this. Mitigation: per-tenant salt never reused/logged, salt access only via Key Vault managed identity, scheduled rotation fire drill, treat pid as SENSITIVE, k-anonymity on small-tenant views. **Foundation + Encryption/Retention.**
3. **Multi-hop reasoning reconstructs identity** [LOAD-BEARING] — view cross-product enables linkage attacks. Mitigation: view-composition review, cell-suppression k<5, bucketing, per-tenant pid never global. **Foundation + Access Layer.**
4. **Anthropic BAA / ZDR scope misunderstood** [LOAD-BEARING] — Batch / Files / Computer Use / Web Fetch / Code Execution NOT covered; ZDR opt-in per workspace; Bedrock/Vertex differ. Mitigation: BAA-scope doc in repo, ZDR confirmation tested, model version pinned, egress allowlist enforces first-party host, every Anthropic-feature addition gated by compliance review. **Compliance + Access Layer.**
5. **CUI exclusion flag set late or unenforced per-adapter** [LOAD-BEARING] — adapter-level enforcement forgets new tools; regex misses non-text fields. Mitigation: framework-level enforcement, default-deny on missing flag, attestation gate, marker detection on subjects/filenames/attachments (refuse attachments for CUI tools), quarterly verification. **Compliance + Tool Onboarding.**
6. **Audit log volume crushes storage; sampled or truncated** [LOAD-BEARING] — defense-collapse. Mitigation: tiered (90d hot Sentinel / 1y warm Storage / 6y cold WORM), gzip-but-never-truncate, retention from customer-class tag, 50%-of-forecast budget alarm. **Audit/Identity + Encryption/Retention.**
7. **Temporary developer raw-zone access becomes permanent** [LOAD-BEARING] — phished developer = breach path. Mitigation: standing grants impossible (managed identities only), human access via PIM JIT with dual approval + 4-hour bound, nightly grant manifest drift detector + auto-revoke, LOGON trigger on raw_* outside PIM window. **Foundation + Audit/Identity.**

Plus pitfalls 8-15 (schema drift, partial sync silence, canary not tested in CI, audit-of-audit gap, reconciliation drift, dev as leak vector, parallel-call budget bypass, erasure happy-path-only).

See: `.planning/research/PITFALLS.md`

## Implications for Roadmap

**5-block phase structure with a strict spine:** Foundations → Onboarding Framework + Tool #1 → Agent-Safe Access Layer + Leak Test → Tools #2/#3 → Compliance Posture. Reversing any inter-block ordering breaks the architectural claim.

### Phase 1: Foundations (Block A)

**Rationale:** Audit plane, identity boundary, schema topology, and salt service must exist before a single PII row is written. Audit format must be locked before data flows — retroactive audit is impossible. Salt service must exist before pseudonymization.
**Delivers:** field-class registry + CI gate; VNet + private endpoints + three Key Vaults + six managed identities + PIM rules; Azure SQL provisioned with `raw_*` placeholder + `ai_zone` + `pseudo` schemas, schema-level grants from manifest, Always Encrypted CMK; audit plane (Service Bus, audit-writer Function, WORM with retention *locked*, Sentinel forwarding); salt service deployed.
**Addresses:** FOUND-01..04, IDENT-01..03, EGRESS-01, ENC-01, AUDIT-01, AUDIT-02, VER-02 (registry only).
**Avoids:** Pitfalls 1, 3, 6, 11, 13.
**Lock-early:** schema-per-tool, single SQL DB schema isolation, salt-service-as-microservice, audit chain format, identity topology, WORM retention locked at write, field-class registry as source of truth.

### Phase 2: Tool Onboarding Framework + Tool #1 (Block B)

**Rationale:** Framework must be built and validated by exactly one tool first. ConnectWise is right "tool #1" — it issues `cw_company_id` (root identifier), exercises every primitive, both physicalizations.
**Delivers:** eight transformation primitives as T-SQL with tests; Tool Onboarding Spec template + adapter base class (cursor, RFC 5988 pagination, retry + DLQ + rate-limit, structured sync result, source schema validation); pseudonymizer wired to salt service; ConnectWise adapter (INT-01, metadata only); first two AI-zone shapes (`customer_snapshot` indexed + `timeseries_aggregate` refreshed); CUI exclusion enforcement at framework level.
**Addresses:** TOOL-01..04, INT-01, FOUND-03 (pseudonymizer), TOOL-02, TOOL-03 (first two of four), sync-framework gap features.
**Avoids:** Pitfalls 7 (CUI framework enforcement), 8 (source drift), 9 (partial sync), 12 (deterministic reconciliation).
**Lock-early:** the eight primitives, the four shapes, onboarding spec format, cursor convention, structured sync result shape, framework-level CUI enforcement.

### Phase 3: Agent-Safe Access Layer + Leak Test (Block C)

**Rationale:** Tool function layer first so gateway has a real backend; gateway last so output filtering applies to real completions. **VER-01 is the integration test that gates the architectural claim** — it cannot pass until all five defense layers exist; passing it is the ship gate before any agent consumes Barycenter.
**Delivers:** Tool Function Layer (DAB + custom service) with first three typed functions (`get_customer_snapshot`, `list_renewals_due`, `emit_action`); Action Dispatcher; AI Gateway (owned, ~1-2k LOC, input scrub + Presidio + canary + aggregate token budget + first-party endpoint + model version pinning + output filter + audit emit); per-tenant per-class opt-out; per-prompt + per-completion structured trace shape; **VER-01 wired into CI on every PR touching raw schemas, views, ETL, grants, OR agent code**; canary tokens registered, deployed, rotated, asserted blocked.
**Addresses:** ACCESS-01..05, EGRESS-02, COMP-05, VER-01.
**Avoids:** Pitfalls 2 (indirect injection — gateway + corpus + body-stripping verified end-to-end), 4 (multi-hop — view-composition review), 5 (BAA scope — endpoint + model pinning), 10 (canaries tested in CI), 14 (aggregate not per-call budgets).
**Lock-early:** typed function naming, action-emission contract, canary token format + rotation cadence, leak-test marker format, structured trace shape, gateway audit-event format (must match Block A chain format).

### Phase 4: Tools #2 and #3 (Block D)

**Rationale:** Each tool exercises a different framework dimension. Pax8 = different domain (subscriptions). Graph = pseudonymization at scale. Email signals = highest-PII surface, requires hardened framework + leak test running on every PR.
**Delivers:** INT-02 Pax8; INT-03 Graph (delta queries, hashed user → person_pid at ingest); INT-04 email-derived signals (structured extracts only with restrictive extractor system prompt, validated DTO, length-capped fields); third + fourth AI-zone shapes (`customer_features_*`, `customer_memory`); cross-tool deterministic reconciliation rules.
**Addresses:** INT-02, INT-03, INT-04, TOOL-03 (remaining two shapes), source-of-truth reconciliation differentiator.
**Avoids:** Pitfalls 1 (extractor with restrictive prompt), 12 (deterministic reconciliation, never LLM).

### Phase 5: Compliance Posture (Block E)

**Rationale:** Drata wiring overlaps backwards (it can collect from Block A onward). Policy artifacts and operational fire drills (salt rotation, erasure end-to-end, breach tabletop, quarterly access reviews, quarterly CUI verification) need real production data + functioning audit plane to be meaningful. Production sizing tunable based on observed Block D volume.
**Delivers:** Drata or Vanta wired (read-only managed identity); CUI controls fully verified (regex extended to subjects/filenames/attachments, attachment refusal for CUI tools, quarterly verification sample); subprocessor inventory + DPA + change-notification; AI-specific posture (model card, DPIA, adversarial corpus formalized in CI, decision-reversal runbooks); erasure end-to-end with cascade through every data-holding system, tested against marker customer; production sizing baseline + monthly partitioning + cold archive to Parquet; first salt rotation fire drill; first breach-notification tabletop.
**Addresses:** COMP-01..05, ERAS-01 (with cascade), RET-01, OPS-01.
**Avoids:** Pitfalls 5 (BAA re-verification at milestone), 7 (CUI multi-layer verification), 15 (erasure end-to-end with leak-test re-run).

### Phase Ordering Rationale

- **Audit plane before any PII row** (Pitfall 6).
- **Salt service before pseudonymization** (Pitfall 3).
- **Framework before tool #2** (architecture rationale).
- **AI gateway + leak test before any agent** (Pitfalls 1, 4, 5, 10, 14).
- **Highest-PII tools last** — INT-04 after framework + leak test hardened (Pitfall 2).
- **Compliance posture overlaps backwards** — Drata wiring additive; fire drills cluster in Block E.

### Lock-Early-or-Pay-Later Decisions

| Decision | Phase to lock | Reversal cost |
|----------|---------------|---------------|
| Schema-per-tool vs shared raw | Block A | Touches every adapter, grant, audit row |
| Single SQL DB, schema isolation | Block A | Doubles operational + grant surface |
| Salt service as separate component | Block A | Every salt-touching component re-architected |
| HMAC with per-tenant salt | Block A | Random pids prevent reconciliation |
| Audit chain format | Block A | Cannot retroactively re-chain history |
| Field-class registry as source of truth | Block A | Re-tagging requires re-validating CI history |
| WORM retention period | Block A | Cannot shorten once locked (the point) |
| Six service identities + three Key Vaults | Block A | Identity changes ripple through grants/RLS/audit/Drata |
| Eight transformation primitives | Block B | Redefining forces every tool's ETL re-validated |
| Four AI-zone shapes | Block B | Adding a 5th changes every agent's tool list |
| Identifier hierarchy | Block A (PROJECT.md) | Every shape, function, audit row gets a new field |
| Typed function naming + action-emission contract | Block C | Every consuming agent affected |
| Canary token + leak-test marker format | Block C | Existing data needs re-stamping |
| Gateway endpoint + model version pinning | Block C | Drift = HIPAA scope break |

### Decisions That Can Iterate

AI-zone refresh cadence per shape; indexed-view vs refreshed-table per shape; adapter language per tool; gateway scrubbing regex (additive); `customer_memory` storage (start in SQL); Drata vs Vanta; RLS predicate logic.

### Research Flags

**Needs `/gsd-research-phase` at planning time:**
- **Block C:** owned-AI-gateway design — aggregate token-budget bucket implementation, canary registry runtime pull pattern, kill-chain canary stage tracking, instruction-data XML wrapping, Presidio recognizer customization for MSP-domain identifiers (cw_company_id, serial numbers, PO numbers).
- **Block D — INT-04:** structured-extract correctness — extractor system-prompt design, validated DTO schemas for sentiment/intent/PO-number, length-cap and pattern-scrub policies, adversarial corpus growth.
- **Block E — erasure cascade:** data-flow-graph manifest of every data-holding system, per-tenant backup encryption, agent memory store erasure semantics, Drata/Vanta side-effect accounting.

**Standard patterns (skip research-phase):**
- **Block A:** Azure provisioning, Key Vault, PIM, WORM, Sentinel — well-documented Microsoft Learn patterns.
- **Block B:** ConnectWise patterns documented (pyconnectwise); adapter base class standard; eight primitives + four shapes architecturally simple T-SQL.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Azure + Anthropic + identity stack HIGH (Microsoft Learn, Anthropic Privacy Center, verified BAA matrix). MEDIUM only on LLM-gateway product choice and Drata-vs-Vanta. |
| Features | MEDIUM-HIGH | Verified against current 2026 sources; lower confidence on vertical-specific patterns (MSP-internal AI-safe data platforms not a mature category; some patterns adapted from regulated-data/finance/healthcare). |
| Architecture | HIGH | Load-bearing structural decisions HIGH. MEDIUM only on AI gateway product selection (build-vs-buy genuinely open; build is opinionated). |
| Pitfalls | HIGH | Anthropic verified against Privacy + Trust Centers; HIPAA against HHS audit protocol; prompt-injection against CVE-2026-21520 + Anthropic Claude Code post-mortem; pseudonymization against EDPS/ENISA. |

**Overall confidence:** HIGH on the spine. Four research streams convergent — no surfaced disagreements. Where each identifies tradeoffs, the others reference and align with the same recommendation.

### Gaps to Address

- Drata vs Vanta final selection — defer to procurement; reconfirm pricing at Block E entry.
- `customer_memory` physical store — start in Azure SQL JSON; revisit if agents demand vector recall.
- Specific Presidio recognizer set for MSP-domain identifiers — Block C research.
- Salt rotation specific migration mechanics — versioned pepper IDs; online rebuild needs schema-change-impact-analysis tooling (Block E).
- HIPAA-ready API surface from Anthropic — per-feature gating, not one-time check.
- Cross-tenant analytics — anti-feature for v1; flag for Out-of-Scope discipline.
- CUI marker on attachments — recommendation: refuse attachments for CUI-flagged adapters; confirm in Block E.
- APIM-vs-owned-gateway revisit point — owned-gateway is right for v1; not necessarily forever.

## Sources

### Primary (HIGH confidence)
- Microsoft Learn — Azure SQL DB, Always Encrypted with secure enclaves, Ledger, Immutable storage, Container Apps, Sentinel, APIM AI Gateway, Entra PIM + FIDO2, Key Vault HMAC, Data API Builder + RLS.
- Anthropic Privacy Center + Trust Center + API Docs — BAA scope matrix, ZDR opt-in, prompt cache scope, model versioning.
- EDPS / AEPD + ENISA — pseudonymization guidance.
- HHS HIPAA Audit Protocol + HIPAA Journal retention guidance.
- OWASP Gen AI Security Project — prompt injection taxonomy.
- arXiv 2603.28013 — Kill-Chain Canaries.
- CVE-2026-21520 + Anthropic Claude Code Security Review post-mortem.
- Microsoft Graph SDK + pyconnectwise + Pax8 PSA integration docs.

### Secondary (MEDIUM confidence)
- Atlan, Monte Carlo, Datalakehouse Hub — schema registry, data contracts, freshness SLA.
- Drata vs Vanta comparisons (Comp AI, vendor blogs).
- Microsoft Presidio docs.
- Aptible, Konfirmity, RectifyCloud — HIPAA-grade audit logging + SOC 2 cadence.
- EDPB 2025 Coordinated Enforcement Action on Right to Erasure.

### Tertiary (LOW confidence — revalidate at phase entry)
- Drata vs Vanta detailed pricing.
- LiteLLM-vs-APIM specific feature parity.
- pyconnectwise vs connectpyse maintainer activity.
- Hyperscale + SGX availability.

### Project source documents
- `/Users/craig/projects/repository/.planning/PROJECT.md`
- `/Users/craig/projects/repository/.planning/research/STACK.md`
- `/Users/craig/projects/repository/.planning/research/FEATURES.md`
- `/Users/craig/projects/repository/.planning/research/ARCHITECTURE.md`
- `/Users/craig/projects/repository/.planning/research/PITFALLS.md`

---
*Research completed: 2026-05-01*
*Ready for roadmap: yes*
