# Feature Research

**Domain:** MSP operations data platform / AI-safe data layer (two-zone architecture)
**Researched:** 2026-05-01
**Confidence:** MEDIUM-HIGH (verified against current 2026 industry sources; lower confidence on a handful of vertical-specific patterns where direct precedents are thin — MSP-internal AI-safe data platforms are not a mature category, so some recommendations adapt patterns from regulated-data/finance/healthcare domains)

---

## Reading Guide for the Downstream Consumer

PROJECT.md already contains a strong, well-categorized requirements list (FOUND-*, TOOL-*, INT-*, ACCESS-*, COMP-*, AUDIT-*, IDENT-*, EGRESS-*, ENC-*, RET-*, ERAS-*, VER-*, OPS-*). This document does **not** re-list those. Instead it:

1. **Surfaces gaps** — features the industry treats as table stakes that are missing or under-specified in PROJECT.md.
2. **Surfaces mis-categorizations** — items currently in PROJECT.md that read like table stakes but are actually differentiators (or vice versa).
3. **Re-frames anti-features** — items in PROJECT.md's "Out of Scope" that should be promoted to *architectural anti-features* (commitments to never build), distinct from "deferred."
4. **Adds 2026-current patterns** PROJECT.md predates — OWASP Top 10 for Agentic AI 2026, kill-chain canary methodology, governed semantic layer, data contracts.

Each feature row tags `[NEW]` (not in PROJECT.md), `[EXTENDS X]` (refines existing requirement X), or `[GAP-IN X]` (existing requirement X is named but under-specified).

---

## Feature Landscape

### Table Stakes (Must Have or System Fails Its Security Claim)

These are non-negotiable for an AI-safe MSP data platform. Missing any of these means either (a) the leak boundary is procedural rather than architectural, or (b) the platform can't sustain operations past the first sync incident.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Tool Onboarding Spec template + intake form** | New tools must follow a uniform classification + ETL + retention process, or controls become ad hoc | LOW | PROJECT.md TOOL-01 covers this. Gap: needs a *blocking CI check* that rejects PRs adding raw tables without a corresponding spec entry. |
| **Per-column field classification (4-class taxonomy) with CI enforcement** | Untagged columns = unknown blast radius. Every column must be RESTRICTED/SENSITIVE/INTERNAL/PUBLIC. | MEDIUM | PROJECT.md FOUND-02 + VER-02 cover this. Gap: classification source-of-truth (YAML in repo? table in DB? Atlan-style metadata?) is undefined. Recommend YAML-in-repo for diff-ability. |
| **HMAC-based deterministic pseudonymization with per-tenant salt** | Cross-tool joins on person/asset without exposing raw PII to AI | MEDIUM | PROJECT.md FOUND-03. Gap: salt rotation mechanics (re-keying without breaking historical joins) is unspecified. ENISA's pseudonymisation guidance recommends versioned pepper IDs stored alongside pseudonyms so old and new salts can coexist during rotation. |
| **AI-safe view contract with documented field-class composition** | Every `ai_zone.*` view must enumerate which raw columns feed it and how (drop / hash / aggregate). Otherwise no one can audit "is this view safe?" | MEDIUM | PROJECT.md ACCESS-01. Gap: needs a *contract document per view* (input columns + transformation primitive + output classification) that's reviewed before merge — analogous to data contracts. |
| **Typed function library (no agent SQL)** | Agents calling raw SQL = unbounded query surface. Functions = bounded, validated, auditable. | MEDIUM | PROJECT.md ACCESS-02. Industry pattern: JSON-Schema-validated function calling, model emits structured args, dispatcher executes. |
| **Structured-action communication contract (no email in prompts)** | Email addresses in prompts/completions = leak channel. Agent emits intent, dispatcher resolves recipients. | MEDIUM | PROJECT.md ACCESS-03. Strong design. |
| **Gateway-level input + output PII filtering** | Last line of defense before LLM and before user sees output | MEDIUM | PROJECT.md ACCESS-04. Industry standard (Kong, Skyflow, Arthur). |
| **Per-tenant per-data-class AI opt-out** | Customers (especially HIPAA-tagged) need granular control beyond "AI on/off" | MEDIUM | PROJECT.md ACCESS-05. Strong design. |
| **Incremental sync with high-water-mark / cursor tracking** | Polling everything every cycle blows API quotas; incremental is the only viable mode at 20-50 tools × N customers | MEDIUM | **[GAP-IN INT-01..04]** — PROJECT.md names integrations but doesn't specify the sync model. Industry standard: per-table cursor (timestamp or sequence ID), persisted across runs, with explicit "last successful sync" telemetry. |
| **Backfill workflow (replay history without disrupting incremental)** | New tools, recovered outages, schema additions all require re-ingesting historical data without breaking the cursor | MEDIUM | **[NEW]** — Not in PROJECT.md. Industry standard: separate backfill job from incremental, with idempotent upsert semantics (so re-runs don't double-count). Critical for onboarding tools mid-flight. |
| **Retry + dead-letter queue (DLQ) for failed records** | Source APIs fail in 100 ways (rate limits, transient 5xx, malformed payloads). Without a DLQ, failures either silently drop or crash the whole sync. | MEDIUM | **[NEW]** — Not in PROJECT.md. Standard pattern: retry with exponential backoff for transient errors, DLQ for permanent; manual re-process workflow. |
| **Source-API rate-limit handling (per-tool quota awareness)** | ConnectWise, Pax8, Graph each have different rate limits (per-second, per-day, per-tenant). Hitting them = silent data loss or account lockout. | MEDIUM | **[NEW]** — Not in PROJECT.md. Standard: token bucket or leaky bucket per tool, observability on remaining budget. |
| **Source schema drift detection** | Vendors add/rename/retype columns without notice. Drift on a tool that feeds RESTRICTED data = compliance break. | MEDIUM | **[NEW, related to VER-02]** — VER-02 detects drift in *Barycenter's* raw schemas after they're written; this is needed *upstream* — detecting that the source API's response schema changed before the change reaches our tables. Recommend automated diffing of source schema between sync runs, alert + halt on unfamiliar columns until classified. |
| **Immutable + cryptographically chained audit log mirrored to external SIEM** | A compromised primary system must not be able to tamper its own audit log. Off-system mirror = independent observability. HIPAA mandates 6 years. | MEDIUM | PROJECT.md AUDIT-01. Strong design. Industry-standard now is hash-chained entries + WORM mirror; PROJECT.md captures both. |
| **Audit-of-audit (queries against audit log are themselves logged)** | Insider threat: someone who can read the audit log can use it to learn what's NOT being logged | LOW (additive) | PROJECT.md AUDIT-02. |
| **Per-prompt + per-completion tracing tied to customer / agent / function** | Required for HIPAA forensics, SOC 2 evidence, and regression testing of AI behavior | MEDIUM | **[GAP-IN AUDIT-01]** — AUDIT-01 says "every audit entry" but doesn't specify the LLM-trace shape. Industry standard 2026: prompt, completion, model, token counts, tool calls, latency, customer_id, agent_id, request_id; structured (JSON), queryable, retained for the audit retention window. |
| **Customer erasure workflow (pseudonym map purge + cascading)** | HIPAA right-to-amendment + GDPR Art.17. Pseudonymized data is still personal data while the salt exists. | HIGH | PROJECT.md ERAS-01. Gap: need *cascade* spec — purging the salt for tenant T must invalidate all `person_pid` rows derived from it across raw tables, AI zone views, audit log (where retention permits), and any downstream agent memory. EDPB 2025 enforcement actions explicitly cite cascade failures. |
| **Per-class retention policy with automated enforcement** | Manual retention = certain failure. Automated job that purges per-class TTL or moves to cold storage. | MEDIUM | PROJECT.md RET-01 + OPS-01. |
| **MFA mandatory + JIT admin (PIM)** | Standing admin = 24/7 ransomware target. JIT = blast radius window of minutes not months. | LOW (config) | PROJECT.md IDENT-01, IDENT-02. |
| **Dual control (four-eyes) on key rotation, schema changes, mass erasure, agent permission changes** | Any single privileged action that can defeat the architecture must require two humans | MEDIUM | PROJECT.md IDENT-02 names it; gap: needs explicit *enforcement mechanism* (Entra PIM approval workflow? GitHub branch protection rule with required reviewers? both?). Multi-admin approval (MAA) is the 2026 industry pattern. |
| **Per-service managed identities, no long-lived secrets** | Long-lived secrets in env files = the #1 MSP breach vector | LOW (config) | PROJECT.md IDENT-03. |
| **Network egress allowlist on agent VNet** | Agent compute reaching the open internet = exfil channel | LOW (config) | PROJECT.md EGRESS-01. |
| **Per-customer per-day token budgets + response-size caps** | Runaway prompts = both cost incident and exfil signal | LOW (config) | PROJECT.md EGRESS-02. |
| **Always Encrypted on RESTRICTED columns (deterministic / randomized as needed)** | Protects against DBA-level threats; required for HIPAA defensible posture in shared infra | MEDIUM | PROJECT.md ENC-01. |
| **End-to-end synthetic-leak test in CI (canary markers)** | The only test that proves the architectural claim. Without this, "five layers of defense" is aspirational. | HIGH | PROJECT.md VER-01. **Critically important.** Should run on every PR touching raw schemas, views, ETL, grants, OR agent code. |
| **Field-class drift detection in CI** | New columns that show up unclassified = drift in the trust boundary | MEDIUM | PROJECT.md VER-02. |
| **Sync health dashboard (per-tool status, last-success, freshness, error rate)** | Without operational visibility, sync failures become "we noticed three weeks later" | MEDIUM | **[NEW]** — Not in PROJECT.md. Standard data-platform pattern; also feeds the AI-zone freshness SLA below. |
| **AI-zone freshness SLA per view** | Agents reasoning over stale data = bad decisions. Each `ai_zone.*` view should declare its expected freshness (e.g., `customer_snapshot` ≤ 4h; `timeseries_aggregate` ≤ 24h) and alert when violated. | MEDIUM | **[NEW]** — Not in PROJECT.md. Industry standard 2026 (dbt SLAs, Monte Carlo, Atlan). Critical because *agents will silently use stale data* if no enforcement exists. |
| **On-call alerting (paging) on sync failures, drift, leak-test failures, audit-log tamper signals** | Without paging, severe failures are detected during business hours only | MEDIUM | **[NEW]** — Not in PROJECT.md. Should integrate with whatever Gravity uses for ops paging (PagerDuty / Teams / etc.). |
| **HIPAA 6-year audit retention + tiered storage (hot / warm / cold)** | HIPAA requirement; tiered storage keeps cost sane | MEDIUM | PROJECT.md COMP-01 + RET-01. Industry standard 2026: 30-90d hot, 3-12m warm, remainder in cold archive (Azure Blob Cool/Archive). |
| **Subprocessor inventory + customer notification workflow** | HIPAA + GDPR + most B2B contracts require it | LOW | PROJECT.md COMP-04. |
| **CUI exclusion technical enforcement (per-customer flag + sync-time filtering + canary detection)** | Without technical enforcement, "we don't process CUI" is unprovable; with it, the boundary is auditable | MEDIUM | PROJECT.md COMP-03. Strong design. |

### Differentiators (Depth That Matters for HIPAA Defensibility / Agent Reasoning Quality)

These distinguish a *defensible* platform from one that merely claims to be safe. Each maps to either compliance defensibility, agent reasoning quality, or operational maturity.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Schema registry as a *control plane*, not a *catalog*** | Atlan/2026 pattern: registry sits between producers and consumers, *enforces compatibility before merge*, propagates classifications automatically. Shifts governance from runtime to pre-deployment. | HIGH | **[NEW / EXTENDS FOUND-02 + VER-02]** — PROJECT.md treats classification as a tag; treating it as a contract enforced by the registry is the 2026 maturity step. Concretely: every column has a `(class, source_tool, transformation_chain, view_consumers)` record; merging a schema change without updating consumers fails CI. |
| **Per-view AI-zone composition review (data contract per view)** | For every `ai_zone.*` view, a checked-in contract: "this view exposes columns A (PUBLIC), B (SENSITIVE→hashed), C (RESTRICTED→aggregated to bucket)." Reviewed by a different person than the author. | MEDIUM | **[NEW / EXTENDS ACCESS-01]** — PROJECT.md says views have "documented composition" but doesn't make it a *reviewable artifact*. Making it a contract that requires explicit approval = HIPAA defensibility upgrade. |
| **Kill-chain canary methodology in adversarial test corpus** | 2026 research (Kill-Chain Canaries, arXiv 2603.28013): inject a canary token through PDF / pre-seeded memory / tool response and track whether it reaches EXPOSED → PERSISTED → RELAYED → EXECUTED. Catches indirect prompt injection that single-stage tests miss. | HIGH | **[NEW / EXTENDS COMP-05 + VER-01]** — PROJECT.md mentions canary tokens and prompt-injection adversarial corpus; the kill-chain framing makes the test *stage-aware* — a leak that PERSISTS into agent memory but doesn't EXECUTE is still a finding. |
| **OWASP Top 10 for Agentic AI 2026 conformance** | Published Dec 2025 by OWASP. First formal taxonomy for autonomous-agent risks: goal hijacking, tool misuse, identity abuse, memory poisoning, cascading failures, rogue agents. Maps to specific controls. | MEDIUM | **[NEW]** — Not in PROJECT.md. Adopting this as an explicit control mapping (which OWASP item maps to which Barycenter control) is a defensibility win for SOC 2 questionnaires. |
| **Source-of-truth reconciliation across overlapping tools** | ConnectWise and Pax8 both name customers. Microsoft Graph and ConnectWise both name people. Without explicit reconciliation rules, agents see duplicates and make wrong decisions. | HIGH | **[NEW]** — Not in PROJECT.md. Industry pattern: explicit precedence rules per entity (e.g., "company name = ConnectWise wins; SKU = Pax8 wins; license count = Graph wins") with conflict-detection alerts. **Note: must be deterministic code, not LLM-driven** (PROJECT.md correctly excludes LLM-driven reconciliation). |
| **Per-tool taxonomy with inheritance** | New tool slots into category (RMM, security, backup...); ETL recipe inherits category defaults | MEDIUM | PROJECT.md TOOL-04 has this. Differentiator-grade only if categories actually carry *enforced defaults* (default classification per field-name pattern, default retention, default opt-out behavior). |
| **Standardized 8-primitive ETL composition** | drop/hash/pseudonymize/aggregate/bucket/score/keyword_flags/as_is. Tools cannot invent novel transformations. Stable agent mental model as tool count grows. | MEDIUM | PROJECT.md TOOL-02. Strong design. |
| **Four canonical AI-zone shapes with no extensions** | `customer_snapshot`, `customer_features_*`, `timeseries_aggregate`, `customer_memory`. Tools contribute, never invent shapes. | MEDIUM | PROJECT.md TOOL-03. Strong design — this is the highest-leverage architectural commitment in the project; treat it as load-bearing. |
| **Schema-change approval workflow with required dual review** | Schema changes are the most dangerous ops action — they can silently re-class data. Dual-control + automated impact analysis. | MEDIUM | **[NEW / EXTENDS IDENT-02]** — IDENT-02 names dual control on schema changes; the differentiator is *automated impact analysis* — when col X is renamed, the system shows every view, function, and agent prompt template that references X. |
| **Adversarial prompt-injection regression test corpus in CI** | A growing test set of "prompts that almost worked" — every near-miss becomes a permanent regression test. Compounds defensive value over time. | MEDIUM | PROJECT.md COMP-05 names it; differentiator value comes from *operational discipline* of growing the corpus. |
| **Decision-reversal paths for every agent-initiated action** | If an agent sends a wrong email or files a wrong ticket, there is a documented, tested undo path. Required for HIPAA decision-amendment defensibility. | MEDIUM | PROJECT.md COMP-05 names it. |
| **Customer attestation workflow for CUI / HIPAA tagging** | Customer self-attests CUI/PHI handling status; Barycenter syncs accordingly. Auditable record. | LOW | PROJECT.md COMP-03 mentions attestation. Differentiator: tie attestation expiry to a recurring re-confirmation. |
| **Automatic 15-minute idle logoff** | HIPAA shared-workstation requirement; defensible | LOW | PROJECT.md COMP-01. |
| **Continuous-controls evidence collection (Drata/Vanta wired in, optional collection)** | Wired in early = SOC 2 pursuit later costs weeks not quarters | LOW (config) | PROJECT.md COMP-02. Smart design — wiring without collecting is cheap insurance. |
| **DPIA + model card + IR plan documented** | Required artifacts for HIPAA / SOC 2 / EU AI Act readiness | LOW (paperwork) | PROJECT.md COMP-05. |
| **Per-customer breach notification runbook** | Tested, documented, owned. The 5am test of HIPAA defensibility. | MEDIUM | PROJECT.md COMP-01 mentions the runbook; differentiator is *annual tabletop test*. |
| **Cold archive to Parquet on Azure Blob after retention thresholds** | Cost discipline at scale; preserves audit value while shrinking hot DB | MEDIUM | PROJECT.md OPS-01. |

### Anti-Features (Architectural Commitments — Deliberately NOT Built, Ever)

PROJECT.md's "Out of Scope" section mixes two distinct categories: things that are *deferred* (CMMC L2, HSM, confidential containers, CMK, EU residency) and things that are *architecturally forbidden* (LLM-driven reconciliation, agent grants on raw zone, email in AI zone). This section promotes the second category to *anti-features* — commitments to never build because building them would defeat the architecture.

| Anti-Feature | Why Tempting | Why Architecturally Forbidden | Documented Alternative |
|--------------|--------------|-------------------------------|------------------------|
| **LLM-driven entity resolution / fuzzy matching of PII** | "Just have Claude reconcile Acme Corp vs. Acme Corporation" — easy and cheap | LLM sees raw PII to do the match → defeats two-zone model. Non-determinism makes audits impossible. Hallucinated matches are wrong silently. | Deterministic code in raw zone, code-reviewed, unit-tested. Confirmed in PROJECT.md "Out of Scope." Promote to first-class anti-feature. |
| **Agent-writable raw zone (any write grant on `raw_*`)** | "Let the agent update the customer note" — saves a function | Single grant defeats schema-permissions layer (layer 1 of 5). Even one write breaks the architectural claim. | Agents emit structured actions; deterministic dispatcher writes. Functions return DTOs only. Implicit in PROJECT.md FOUND-01; should be explicit. |
| **Email addresses (or any RESTRICTED PII) in AI zone, ever** | "Let the agent see the email so it can pick the right person" | Defeats the leak boundary. Once email is in a view, it's in prompts, it's in completions, it's in audit logs — breach surface explodes. | `person_pid` + structured-action dispatcher resolves recipient. PROJECT.md ACCESS-03 captures this; promote to anti-feature. |
| **Raw email/ticket bodies in AI zone** | "Let the agent read the ticket to summarize" | Bodies contain PII, PHI, customer secrets, vendor secrets. Once in AI zone they leak into prompts. | Structured extracts only: PO numbers, sentiment buckets, intent classification, keyword flags. PROJECT.md INT-04 implies this; make it explicit. |
| **Novel AI-zone tables invented per-tool** | "This tool's data doesn't fit the four shapes" | Defeats the agent's mental model; every new shape is a new threat surface to review. | Compose into existing shapes via the 8 primitives. If genuinely doesn't fit, that's a *platform design decision* requiring full review, not a tool-onboarding decision. PROJECT.md TOOL-03 implies this; make explicit. |
| **Free-form agent SQL access** | "It would be so much more flexible" | Unbounded query surface defeats the function-layer (layer 3 of 5). Agents can construct arbitrary joins on hashed columns and re-derive PII via inference. | Typed function library only. PROJECT.md ACCESS-02. |
| **AI-zone reads in BAA-less LLMs (e.g., free-tier APIs, consumer-grade tools)** | "Just for prototyping" | One BAA-less call leaks customer data; HIPAA breach. | Gateway-enforced model allowlist; only BAA'd Anthropic Enterprise. PROJECT.md COMP-01 implies this; make explicit at the gateway. |
| **Agent identity with access to the pseudonym salt** | "Let the agent re-identify when it has a good reason" | One-way pseudonymization is the property. Two-way breaks the architectural claim. | Agent has zero salt access; salt in Key Vault, accessed only by ETL identity. PROJECT.md FOUND-03 implies this; make explicit. |
| **Cross-tenant joins in AI zone** | "Insights across the customer base" | Cross-tenant correlation in pseudonymized space is still re-identifiable; one customer's anomalies fingerprint them. | Per-tenant aggregations only; cross-tenant analytics, if ever needed, run in a separate process with explicit consent and different controls. **[NEW]** — Not in PROJECT.md; recommend adding. |
| **Agent memory that persists raw-zone data** | "Let the agent remember the customer's full context" | Agent memory is durable state outside the audit window of a prompt. RESTRICTED data in memory = leak surface. | `customer_memory` shape (one of the four canonical shapes) holds AI-zone-class data only. PROJECT.md TOOL-03 implies this. |
| **Synthetic data from production via LLM** | "Let Claude generate fake customers that look real" | LLM trained on real data leaks real data via "synthetic" outputs. Has happened in published incidents. | If synthetic data ever needed: deterministic generator, no LLM. PROJECT.md correctly defers synthetic data; reframe the *LLM-generated* variant as anti-feature. |
| **Bulk AI-driven data classification (let the LLM tag columns)** | "We have 500 columns — have Claude classify them" | LLM sees the column data to tag it; sees PII; tagging is non-deterministic. | Human-reviewed classification per column, stored in YAML, CI-enforced. **[NEW]** — Not explicit in PROJECT.md; recommend adding. |

### Mis-Categorizations Worth Surfacing

A small number of items in PROJECT.md may benefit from re-categorization:

- **AUDIT-02 (audit-of-audit)** is currently flat with AUDIT-01. It should arguably be a **differentiator**, not table stakes — it goes beyond what HIPAA/SOC 2 strictly require, and it specifically defends against insider audit-log abuse. Most platforms don't have it; calling it a differentiator advertises the rigor.
- **VER-01 (synthetic leak test in CI)** is the load-bearing feature for the entire architectural claim. PROJECT.md lists it alongside other ops work; it deserves elevated emphasis — without it, the "five layers of defense" is unverified. Treat as **table stakes critical-path**.
- **FOUND-04 (five-layer defense)** is described as a requirement but is actually an *architectural property emergent from the other requirements*. Not a feature to "build" but a property to verify (which VER-01 does). Worth restating as a property rather than a checkbox.
- **EGRESS-02 (token budgets)** is currently table stakes; it's also a **detection signal** — sudden budget exhaustion is an exfil indicator. Worth noting in the alerting section that token-budget anomalies should page.
- **OPS-01 (production sizing)** is currently in operations; the "Basic 5-DTU is dev-only" guard rail is actually a **safety control** against a known failure mode (dev config leaking into prod). Worth flagging as such.

---

## Feature Dependencies

```
[Field classification standard]
    └──required-by──> [AI-safe view contract]
                          └──required-by──> [Typed function library]
                                                └──required-by──> [Agent runtime]

[HMAC pseudonymization + per-tenant salt]
    └──required-by──> [Cross-tool person reconciliation]
    └──required-by──> [Customer erasure (cascade depends on salt purge)]

[Schema registry as control plane]
    └──enables──> [Field-class drift detection]
    └──enables──> [Schema-change impact analysis]
    └──enables──> [Source schema drift detection]

[Per-tool incremental sync with cursor]
    └──required-by──> [Backfill workflow]  (must coexist without disrupting cursor)
    └──required-by──> [Sync health dashboard]
    └──required-by──> [AI-zone freshness SLA]

[Immutable + chained audit log]
    └──required-by──> [Audit-of-audit]
    └──required-by──> [Per-prompt + per-completion tracing]
    └──required-by──> [Breach notification runbook] (forensics)
    └──required-by──> [Customer erasure audit trail]

[End-to-end synthetic leak test (VER-01)]
    └──depends-on──> [All five layers being implemented]
    └──blocks-merge-on──> [PRs touching: raw schemas, views, ETL, grants, agent code]

[Dual control / four-eyes]
    └──required-by──> [Schema changes]
    └──required-by──> [Mass erasure]
    └──required-by──> [Salt rotation]
    └──required-by──> [Agent permission changes]

[Tool Onboarding Spec template]
    └──required-by──> [Adding any new tool]
    └──CI-blocks──> [PRs adding raw_* tables without spec entry]

[Structured-action dispatcher]
    └──required-by──> [Agent-emitted communications]
    └──prevents──> [Email addresses entering prompts]
```

### Dependency Notes

- **Field classification → AI-safe views → Typed functions:** This is the dependency spine. Skipping classification means views can't certify their composition; skipping view contracts means functions return un-vetted DTOs. Build in this order, no shortcuts.
- **HMAC + salt → erasure cascade:** The salt is the master key. Purging the salt invalidates all pseudonyms derived from it — but only if every consumer (raw tables, AI views, audit log, agent memory) is enumerable. This requires a salt-to-consumer registry to make erasure provable.
- **Schema registry → drift detection → impact analysis:** The registry is the control plane that makes both downstream features possible. Without a single source of truth for "which columns exist and what class are they," drift detection is best-effort and impact analysis is impossible.
- **Synthetic leak test depends on everything:** VER-01 cannot pass until all five defense layers exist. Therefore VER-01 is the *integration test* that gates the architectural claim. Run it in CI on every PR touching the boundary.
- **Backfill conflicts with naive cursor design:** A backfill job that resets the cursor breaks incremental sync. Backfill must use a separate watermark or idempotent upsert with the existing cursor preserved. This is the most common implementation bug in this space.
- **Source schema drift detection vs. Barycenter schema drift detection:** These are *two different features*. PROJECT.md VER-02 is the second (Barycenter's own raw schema). The first (source API schema) is needed and missing.

---

## MVP Definition (For Roadmap Phase Sequencing)

### Launch With (v1) — Cannot Ship Without

The architectural claim must hold from day one. v1 ships with a small tool surface but full controls.

- [ ] FOUND-01..04 — Two-zone, classification, identifiers, five-layer defense
- [ ] TOOL-01..04 — Onboarding spec, primitives, canonical shapes, taxonomy
- [ ] INT-01 — ConnectWise Manage (anchor tool)
- [ ] INT-03 — Microsoft Graph (anchor identity tool)
- [ ] ACCESS-01..05 — Views, functions, communication contract, output filter, opt-out
- [ ] AUDIT-01, AUDIT-02 — Immutable chained log + audit-of-audit
- [ ] IDENT-01..03 — MFA, JIT admin, managed identities
- [ ] EGRESS-01, EGRESS-02 — Egress allowlist + token budgets
- [ ] ENC-01 — Always Encrypted on RESTRICTED
- [ ] RET-01 — Retention policy
- [ ] ERAS-01 — Erasure workflow (with cascade spec)
- [ ] VER-01, VER-02 — Synthetic leak test + classification drift CI checks
- [ ] OPS-01 — Production sizing baseline

**Plus the gaps surfaced above:**
- [ ] Per-tool incremental sync model with cursor persistence
- [ ] Backfill workflow distinct from incremental
- [ ] Retry + DLQ for failed records
- [ ] Source-API rate-limit handling
- [ ] Source schema drift detection
- [ ] Sync health dashboard
- [ ] AI-zone freshness SLA per view (at least the four canonical shapes)
- [ ] On-call alerting integration
- [ ] Per-prompt/completion trace shape standardized
- [ ] Salt rotation mechanics (versioned pepper)
- [ ] Schema-change impact analysis tooling

### Add After Validation (v1.x)

- [ ] INT-02 — Pax8 (high value, but ConnectWise + Graph proves the model first)
- [ ] INT-04 — Email-derived signals (highest-PII surface; do last so the controls are battle-tested)
- [ ] Schema registry promoted from "tags in YAML" to control plane (Atlan or equivalent)
- [ ] Kill-chain canary methodology in adversarial corpus
- [ ] OWASP Top 10 for Agentic AI 2026 explicit control mapping
- [ ] Continuous-controls evidence collection turned on (Drata/Vanta)
- [ ] Cold archive to Parquet
- [ ] Subprocessor change notification workflow
- [ ] Source-of-truth reconciliation rules per overlapping entity (CW vs. Pax8 vs. Graph)

### Future Consideration (v2+)

- [ ] Additional tool integrations: RMM (Ninja/Datto), security (SentinelOne, Duo), backup, docs, MFA, quoting (FortiQuote)
- [ ] CMK (customer-managed keys) — when first customer demands
- [ ] HSM-backed keys — when first FIPS 140-2 L3 customer demands
- [ ] Confidential computing for agent runtime — defensive depth, not justified yet
- [ ] Per-customer encryption envelope — after CMK
- [ ] CMMC L2 — when DoD revenue justifies (~50% scope expansion)
- [ ] EU residency / EU AI Act certification — when EU customers
- [ ] Cross-tenant analytics (with explicit consent + separate process) — if ever genuinely needed; default never

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Two-zone schema architecture (FOUND-01) | HIGH | MEDIUM | P1 |
| Field classification + CI enforcement (FOUND-02 + VER-02) | HIGH | MEDIUM | P1 |
| HMAC pseudonymization (FOUND-03) | HIGH | MEDIUM | P1 |
| Synthetic leak test in CI (VER-01) | HIGH (critical) | HIGH | P1 |
| Tool Onboarding Spec template (TOOL-01) | HIGH | LOW | P1 |
| 8 ETL primitives + 4 canonical shapes (TOOL-02, TOOL-03) | HIGH | MEDIUM | P1 |
| Typed function library (ACCESS-02) | HIGH | MEDIUM | P1 |
| Structured-action dispatcher (ACCESS-03) | HIGH | MEDIUM | P1 |
| Gateway PII filtering (ACCESS-04) | HIGH | MEDIUM | P1 |
| Per-tenant per-class opt-out (ACCESS-05) | HIGH | MEDIUM | P1 |
| Immutable chained audit log + audit-of-audit (AUDIT-01, 02) | HIGH | MEDIUM | P1 |
| MFA + JIT admin + managed identities (IDENT-01..03) | HIGH | LOW | P1 |
| Egress allowlist + token budgets (EGRESS-01, 02) | HIGH | LOW | P1 |
| Always Encrypted (ENC-01) | HIGH | MEDIUM | P1 |
| Retention policy automation (RET-01) | HIGH | MEDIUM | P1 |
| Erasure workflow with cascade (ERAS-01) | HIGH | HIGH | P1 |
| Per-tool incremental sync + cursor | HIGH | MEDIUM | P1 |
| Backfill workflow | HIGH | MEDIUM | P1 |
| Retry + DLQ | HIGH | MEDIUM | P1 |
| Source schema drift detection | HIGH | MEDIUM | P1 |
| Sync health dashboard | HIGH | MEDIUM | P1 |
| AI-zone freshness SLA | MEDIUM | MEDIUM | P1 |
| On-call alerting | HIGH | LOW | P1 |
| Per-prompt/completion trace shape | HIGH | MEDIUM | P1 |
| Salt rotation mechanics | MEDIUM | MEDIUM | P1 |
| Dual control on critical ops (IDENT-02 detail) | HIGH | MEDIUM | P1 |
| HIPAA 6-year retention + tiered storage (COMP-01 + RET-01) | HIGH | MEDIUM | P1 |
| Subprocessor inventory + DPA (COMP-04) | HIGH | LOW | P1 |
| CUI exclusion technical enforcement (COMP-03) | HIGH | MEDIUM | P1 |
| Schema registry as control plane | MEDIUM | HIGH | P2 |
| AI-zone view contract per view | HIGH | MEDIUM | P2 |
| Kill-chain canary methodology | MEDIUM | HIGH | P2 |
| OWASP Top 10 for Agentic AI mapping | MEDIUM | LOW | P2 |
| Continuous-controls evidence wired in (COMP-02) | MEDIUM | LOW | P2 |
| Source-of-truth reconciliation rules | HIGH | HIGH | P2 |
| Schema-change impact analysis tooling | MEDIUM | MEDIUM | P2 |
| Cold archive to Parquet | LOW | MEDIUM | P2 |
| Annual breach-notification tabletop test | HIGH | LOW | P2 |
| Additional tool integrations beyond v1 | HIGH | MEDIUM | P2 |
| CMK | LOW (no demand yet) | HIGH | P3 |
| HSM-backed keys | LOW | HIGH | P3 |
| Confidential computing | LOW | HIGH | P3 |
| Cross-tenant analytics | LOW (anti-feature absent consent) | HIGH | P3 |

**Priority key:**
- **P1**: Must have for v1 launch — the architectural claim depends on these
- **P2**: Should have for v1.x — extends defensibility and operational maturity
- **P3**: Future / on-demand only — defer until customer or regulation demands

---

## Competitor Feature Analysis

There is no direct competitor — Barycenter is an MSP-internal data layer, not a product. But three adjacent product categories inform feature expectations:

| Feature | MSP PSAs (ConnectWise, Autotask) | Modern Data Platforms (Snowflake, Databricks) | Privacy/Security Tooling (Skyflow, Privacera) | Barycenter's Approach |
|---------|----------------------------------|-----------------------------------------------|-----------------------------------------------|----------------------|
| Tool integration framework | Native connectors per tool, often paid | Generic ETL via Fivetran/Airbyte | Pre-built privacy-aware connectors | Per-tool spec + 8 primitives + 4 shapes |
| Field classification | None (data is raw) | Tags + lineage (Atlan, Unity Catalog) | First-class (Skyflow vault, tokenization) | Mandatory 4-class taxonomy with CI |
| Pseudonymization | None | Manual / via add-on | Built-in vault tokenization | HMAC per-tenant salt, deterministic |
| AI safe access | N/A — no AI integration | Semantic layer (Atlan, AtScale) — recent | Privacy vaults expose tokenized views | Two-zone + typed functions + view contracts |
| Audit log | Standard app logging | Query history + lineage | Cryptographically chained, WORM | Hash-chained + WORM mirror to Sentinel |
| Erasure workflow | Manual / ticket-based | Manual via SQL | Automated subject-rights workflow | Salt purge + cascade (HIPAA + GDPR) |
| Sync orchestration | Per-vendor scheduler | Airflow / Dagster / Prefect | Vendor-specific | Custom, per-tool with cursor + DLQ |
| AI agent integration | Bolted-on (Voyager, etc.) | Semantic layer + MCP | Tokenized exposure to LLMs | Typed functions + structured actions only |

**Key takeaway:** Barycenter cherry-picks the strongest patterns from each category — classification + lineage from data platforms, pseudonymization from privacy tools, MSP-tool literacy from PSAs, agent-specific safety from emerging governance tooling — and combines them in a way no off-the-shelf product offers. The differentiator is the *combination plus the architectural commitment to the leak boundary*, not any single feature.

---

## Sources

**Verified (HIGH confidence — used for architectural commitments):**
- [HIPAA Audit Logs: Complete Requirements for Healthcare Compliance in 2025 — Kiteworks](https://www.kiteworks.com/hipaa-compliance/hipaa-audit-log-requirements/)
- [HIPAA Logging Pipelines: Best Practices and Key Steps for 2026 — Konfirmity](https://www.konfirmity.com/blog/hipaa-logging-pipelines-for-hipaa)
- [Pseudonymisation techniques and best practices — ENISA](https://www.enisa.europa.eu/sites/default/files/publications/Guidelines%20on%20shaping%20technology%20according%20to%20GDPR%20provisions.pdf)
- [The False Allure of Hashing for Anonymization — Hacker News discussion](https://news.ycombinator.com/item?id=16960866) (informs why HMAC + salt is the right choice over plain hashing)
- [Pseudonymization | Sensitive Data Protection — Google Cloud](https://docs.cloud.google.com/sensitive-data-protection/docs/pseudonymization)
- [Protecting GDPR Personal Data with Pseudonymization — Elastic](https://www.elastic.co/blog/gdpr-personal-data-pseudonymization-part-1)
- [GDPR Right to Erasure: What "The Right to Be Forgotten" Actually Requires — DEV](https://dev.to/custodiaadmin/gdpr-right-to-erasure-what-the-right-to-be-forgotten-actually-requires-493n)
- [EDPB report on the right to erasure: Key takeaways from the 2025 Coordinated Enforcement Action — Reed Smith](https://www.reedsmith.com/our-insights/blogs/viewpoints/102mm9l/edpb-report-on-the-right-to-erasure-key-takeaways-from-the-2025-coordinated-enfo/)
- [LLM01:2025 Prompt Injection — OWASP Gen AI Security Project](https://genai.owasp.org/llmrisk/llm01-prompt-injection/)
- [Kill-Chain Canaries: Stage-Level Tracking of Prompt Injection — arXiv 2603.28013](https://arxiv.org/abs/2603.28013)
- [Log-To-Leak: Prompt Injection Attacks on Tool-Using LLM Agents via MCP — OpenReview](https://openreview.net/forum?id=UVgbFuXPaO)
- [The Biggest AI Security Vulnerabilities Discovered in 2026 — Redfox Cybersecurity](https://www.redfoxsec.com/blog/the-biggest-ai-security-vulnerabilities-discovered-in-2026-redfox-cybersecurity)

**Verified (MEDIUM-HIGH confidence — used for design patterns):**
- [Context Drift Detection: Guide for 2026 — Atlan](https://atlan.com/know/context-drift-detection/)
- [Data Lineage Tracking: Complete Guide for 2026 — Atlan](https://atlan.com/know/data-lineage-tracking/)
- [Schema Drift Detection — apxml](https://apxml.com/courses/data-governance-quality-observability-production/chapter-3-data-observability-systems/schema-drift-detection)
- [Governed Semantic Layer for AI — OvalEdge](https://www.ovaledge.com/blog/governed-semantic-layer-for-ai)
- [Context Layer Harness Engineering: The 2026 Complete Guide — Atlan](https://atlan.com/know/context-layer-harness-engineering/)
- [Introducing the Agent Governance Toolkit — Microsoft Open Source Blog (Apr 2026)](https://opensource.microsoft.com/blog/2026/04/02/introducing-the-agent-governance-toolkit-open-source-runtime-security-for-ai-agents/)
- [AI Agent Guardrails: Pre-LLM & Post-LLM Best Practices — Arthur AI](https://www.arthur.ai/blog/best-practices-for-building-agents-guardrails)
- [The complete guide to LLM observability for 2026 — Portkey](https://portkey.ai/blog/the-complete-guide-to-llm-observability/)
- [LLM Observability & Application Tracing — Langfuse](https://langfuse.com/docs/observability/overview)
- [PII Sanitization for LLMs and Agentic AI — Kong](https://konghq.com/blog/enterprise/building-pii-sanitization-for-llms-and-agentic-ai)
- [Understanding AI & LLM Agents: Architecture, Security, & Deployment — Skyflow](https://www.skyflow.com/post/understanding-llm-agents)
- [Schema Change Governance: Approvals & Audit Trails — SchemaSmith](https://schemasmith.com/guides/database-change-approval-workflows.html)
- [Data Contracts Explained: Key Aspects, Tools, Setup in 2026 — Atlan](https://atlan.com/data-contracts/)
- [Data Contracts in Cloud-Native Analytics — IJCESEN journal](https://ijcesen.com/index.php/ijcesen/article/view/5152)
- [How to Build SLAs for Real-Time Dashboards with AI-ETL — Integrate.io](https://www.integrate.io/blog/build-slas-for-real-time-dashboards-with-ai-etl/)
- [Pipeline Observability: Know When Things Break — Datalakehouse Hub](https://datalakehousehub.com/blog/2026-02-de-best-practices-09-observability-monitoring/)
- [How to Monitor ETL Pipeline Health | Complete Guide 2026 — Airbyte](https://airbyte.com/data-engineering-resources/how-do-i-monitor-etl-pipeline-health)
- [Data Reconciliation Guide | Ensuring Accuracy & Consistency — Acceldata](https://www.acceldata.io/blog/data-reconciliation)
- [What is Data Reconciliation: Tools, Examples, Techniques — Airbyte](https://airbyte.com/data-engineering-resources/data-reconciliation)
- [Multi-Admin Approvals (MAA) — Windows News on Intune Feb 2026](https://windowsnews.ai/article/intune-february-update-multi-admin-approvals-mdq-enhancements-ddm-filters-explained.403754)
- [What Are Immutable Logs? A Complete Guide — Hubifi](https://www.hubifi.com/blog/immutable-audit-log-guide)
- [Building a HIPAA-Grade Audit Logging System — Medium / Keshav Agrawal](https://medium.com/@keshavagrawal/building-a-hipaa-grade-audit-logging-system-lessons-from-the-healthcare-trenches-d5a8bb691e3b)

**Context (MEDIUM confidence — used for MSP domain feel, not load-bearing claims):**
- [The Pax8 PSA Integrations Guide — Pax8 Blog](https://www.pax8.com/blog/psa-integrations-guide/)
- [How a Pax8 PSA integration can boost your business — Pax8 Blog](https://www.pax8.com/blog/psa-integrations/)
- [Top 10 AI Tools for MSP Growth, Automation & Security in 2026 — Guardz](https://guardz.com/blog/ai-tools-for-msp/)
- [The anatomy of a deep Salesforce sync integration — Ampersand](https://www.withampersand.com/blog/the-anatomy-of-a-deep-salesforce-sync-integration) (analogous SaaS sync patterns)
- [Top 10 SaaS Data Integration Platforms to Consider in 2026 — Hevo](https://hevodata.com/learn/saas-integration-platforms/)
- [How to Perform Historical Backfills and Incremental Loads — Rivery](https://rivery.io/blog/rivery-tips-how-to-perform-historical-backfills-and-incremental-loads/)

---
*Feature research for: MSP operations data platform / AI-safe two-zone data architecture (Barycenter)*
*Researched: 2026-05-01*
