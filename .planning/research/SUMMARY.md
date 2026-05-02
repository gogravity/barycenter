# Project Research Summary

**Project:** Barycenter — MSP Operations Data Platform
**Domain:** Internal Azure-native data platform with AI-safe two-zone architecture and HIPAA compliance
**Researched:** 2026-05-02 (revised; replaces over-engineered initial research)
**Confidence:** HIGH (stack cost verified against Azure pricing; HIPAA §164.312 mapping verified against HHS; FortiGate sizing verified against Fortinet datasheets); MEDIUM (custom gateway LOC estimate; Container Apps duty-cycle cost)

---

## Executive Summary

Barycenter is a security-first MSP operations data platform whose single load-bearing claim is that AI agents architecturally cannot leak customer PII or CUI — even under malicious prompts, output-filter bypass, or tool bugs. The revised (cost-simplified) architecture achieves this with a five-layer defense (SQL schema permissions, AI-safe views, typed tool functions, gateway scrubbing, per-prompt audit) implemented on a lean Azure stack totaling approximately $166/month — well inside the $200 ceiling — by replacing over-specified components with lighter-weight equivalents that satisfy the same HIPAA floor.

The prior research over-specified by roughly $700/month driven by DC-series Azure SQL ($300+) for Always Encrypted with secure enclaves, APIM Standard v2 ($250+) for LLM gateway policy, and Microsoft Sentinel as the primary SIEM. The revised stack eliminates all three: HIPAA §164.312(a)(2)(iv) is an addressable (not required) control satisfied by TDE + schema-grant isolation without column-level encryption; a ~300-LOC FastAPI gateway in Container Apps consumption replaces APIM at near-zero cost; and Log Analytics + WORM blob satisfies HIPAA §164.312(b) audit controls without the Sentinel surcharge. A FortiGate-VM02 BYOL already under Gravity's MSSP agreement ($62/mo VM compute, $0 license) enforces network-layer egress allowlisting and IDS/IPS, replacing multiple Azure-native perimeter controls and making the Sentinel-for-threat-detection argument moot at v1 scale.

The primary risks are: (1) the five-layer defense degrades silently if any layer is weakened post-deployment — prevention requires VER-01 end-to-end leak tests in CI on every PR that touches schemas, views, ETL, grants, or gateway code; (2) the custom FastAPI gateway introduces HIPAA evidence burden that APIM would have carried via vendor attestation — mitigated by eight concrete evidence artifacts (Presidio version pins, chain-hash audit records, test corpus, rate-limit logs, etc.); and (3) FortiGate misconfiguration can allow ETL-to-Anthropic or agent-to-source-tool egress that breaks subnet isolation — mitigated by explicit deny-and-log policies and FortiGate deny-event ingestion into the audit trail.

---

## Key Findings

### Recommended Stack

The stack converges on Azure-native services sized for a 2-5 person internal tool with ~50 MSP customers and a 25% SQL duty cycle. FortiGate-VM02 BYOL on Standard_F2s_v2 anchors the network perimeter in a hub-and-spoke topology; a single Barycenter spoke with five subnets (etl, services, data, pe, admin) routes all outbound through the FortiGate via UDR. Azure SQL Serverless GP (0.5-2 vCore auto-pause, 32 GB) handles bursty ETL + agent reads at ~$50/month. The AI gateway is an owned FastAPI app (~300 LOC) in Container Apps consumption — free under the monthly grant at v1 traffic. Three managed identities (etl, platform, admin) and one Key Vault with RBAC-scoped access per key/secret replace the original six identities and three vaults.

Critically, TDE replaces Always Encrypted for v1. The HIPAA §164.312(a)(2)(iv) control is addressable, not required; AES-256 TDE plus schema-permission isolation plus AI-safe views satisfies the threat model without the DC-series SQL premium. Always Encrypted is architecture-compatible for a future upgrade (SOC 2 pursuit or specific customer demand) but not justified at HIPAA-only posture.

**Core technologies:**

- **Azure SQL Database, Serverless GP Gen5 (0.5-2 vCore auto-pause):** Two-zone data store (raw_* + ai_zone.*). Chosen for cost (~$50/mo at 25% duty cycle), Azure BAA coverage, and battle-tested schema-level grant isolation. Cold-start ~30s does not break HIPAA audit continuity because audit writes are asynchronous to Log Analytics + WORM.
- **FortiGate-VM02 BYOL on Standard_F2s_v2:** Hub-and-spoke perimeter enforcing FQDN-based outbound allowlist, IDS/IPS, and subnet separation (ETL spoke cannot reach Anthropic; agent spoke cannot reach source-tool APIs). ~$62/mo VM compute, $0 BYOL license under Gravity MSSP agreement. F2s_v2 (compute-optimized, no CPU credit throttle) is Fortinet's default Azure template SKU for FGT-VM02.
- **FastAPI AI Gateway on Container Apps consumption:** Owned 9-step middleware chain replacing APIM ($250+/mo). Steps: Entra JWT auth, token-bucket rate limit, per-tenant budget check, inbound Presidio PII scan, inbound canary check, Anthropic SDK call, outbound Presidio scan, outbound canary check, async audit emit. ~$0-3/mo under free consumption grant.
- **Log Analytics Workspace + Azure Storage WORM:** Replaces Sentinel as audit tier. Log Analytics (90-day hot, KQL queryable) + WORM blob (6-year retention-locked, Cohasset-validated) satisfies HIPAA §164.312(b). Sentinel deferred until customer HIPAA questionnaire demands a named SIEM or audit volume crosses ~10 GB/month.
- **3 managed identities (etl, platform, admin) + 1 Key Vault:** Down from 6 identities and 3 vaults. Salt-fetch inlined into ETL worker (Key Vault GET per-tenant per-sync, ephemeral, never cached). Platform identity shared by gateway + typed-function service + action dispatcher, with app-layer signed action envelopes between gateway-side and dispatcher to compensate for identity consolidation.
- **One private endpoint (Azure SQL):** All other PaaS services (Key Vault, Storage, Container Registry) use VNet service endpoints (free), justified by FortiGate enforcing the perimeter and publicNetworkAccess = Disabled on each service.

**Total v1 monthly cost: $166 / $200 ceiling. Headroom: $34/month.**

Items explicitly deferred (architecture-compatible, not in v1 budget): Sentinel (~$15/mo), FortiGate HA second VM (~$62/mo), APIM (never — owned gateway suffices), Drata/Vanta ($600+/mo), Always Encrypted on DC-series SQL ($300+/mo).

### Expected Features

The revised feature triage classifies all 27 active PROJECT.md requirements plus 13 newly surfaced requirements (NEW-01 through NEW-13) that simplification would otherwise silently drop.

**Must-have (v1.0 — 37 items including NEW-01 through NEW-13):**

- FOUND-01/02/03/04: Two-zone SQL, field classification, HMAC person_pid, five-layer defense
- TOOL-01/02/03: Onboarding spec, eight ETL primitives, four canonical AI-zone shapes
- INT-01 ConnectWise Manage, INT-02 Pax8, INT-03 Microsoft Graph
- ACCESS-01 through ACCESS-05: AI-safe views, typed functions, communication contract, gateway filtering, per-tenant opt-out
- COMP-01/03/05 (modified): HIPAA baseline, CUI exclusion, AI-specific posture
- AUDIT-01 (modified — WORM blob not Sentinel), IDENT-01/02/03, EGRESS-01 (FortiGate-satisfied), EGRESS-02
- RET-01, ERAS-01, VER-01, VER-02
- NEW-01 through NEW-13: WORM audit blob retention lock, Log Analytics table-level retention, FortiGate deny-event ingestion, per-prompt structured trace, GitHub branch protection, PIM approval policies, salt rotation runbook, gateway kill switch, gateway PII-filter test fixtures, on-call alerting (Teams webhook), BAA inventory document, gateway model allowlist, CUI exclusion canary phrase detection

**Should-have (v1.0, can slip to v1.1 — 4 items):**

- TOOL-04: Tool category taxonomy (categories in spec template; full inheritance v1.1)
- AUDIT-02: Audit-of-audit (cheap; skip if costs more than a day)
- COMP-05 (reduced scope): Model card, IR plan, adversarial corpus in CI, output filtering, decision-reversal paths; kill-chain canary and OWASP mapping defer
- ENC-01 (TDE-only variant): TDE + TLS 1.2+ in v1.0; Always Encrypted deferred; OPS-01 sizing baseline only

**Defer to v1.1 (4 items):**

- INT-04 Email-derived signals: Highest-PII surface; in-pipeline LLM extraction adds prompt-injection surface inside the integration. Hard entry criteria: VER-01 clean for 90+ days, gateway has caught live near-miss, kill-chain canaries added, adversarial corpus updated with email injection examples.
- COMP-04: Subprocessor inventory DPA customer notification workflow (BAA inventory lives in NEW-11 for v1.0)
- OPS-01 cold archive to Parquet
- ENC-01 Always Encrypted upgrade

**Drop (1 item):**

- COMP-02 (SOC 2-ready controls via Drata/Vanta): Dropped with explicit re-homing of HIPAA-overlapping sub-items — access reviews and annual tabletop added to COMP-01; dual-control lives in NEW-05 (GitHub branch protection) + NEW-06 (PIM approval policies); vendor risk management lives in NEW-11 (BAA inventory).

**FortiGate satisfies EGRESS-01** at the network layer (FQDN allowlist + UDR forced tunnel). Critical subnet separation: ETL subnet can reach source-tool APIs but not Anthropic. Services subnet can reach Anthropic but not source-tool APIs. Default deny + log on all other destinations.

**INT-04 deferral is a hard security boundary**, not a calendar suggestion. Email bodies contain PHI for healthcare customers; the extraction step is itself an LLM call creating a prompt-injection surface inside the integration pipeline. The breach cost asymmetry (free-text PHI, multi-customer scope) justifies deferral until 90 days of production-proven controls on lower-PII integrations.

### Architecture Approach

The architecture is a hub-and-spoke VNet topology with a single Barycenter spoke (10.20.0.0/22) containing five subnets (etl, services, data, pe, admin), all egress forced through the FortiGate hub via UDR. Six application components run as Container Apps jobs or apps in two environments: Adapter Jobs (ETL per source tool), AI-Zone Builder (scheduled materialization), Typed-Function Service (agent-facing function API), AI Gateway (LLM proxy with full middleware chain), Action Dispatcher (structured action to real recipient to send), and Audit Writer (Service Bus to WORM blob + Log Analytics chain-hash writer). Azure SQL lives behind a private endpoint in the data subnet with publicNetworkAccess = Disabled. All five defense layers are preserved and explicitly mapped to components.

**Major components:**

1. **Adapter Jobs** (Container Apps Job, etl-identity) — per-source-tool scheduled ETL; FQDN-allowlisted via FortiGate; HMAC pseudonymization inline with KV salt fetch; writes to raw_* and pseudo.person_map
2. **AI-Zone Builder** (Container Apps Job, etl-identity) — materializes ai_zone.* views from raw_* on schedule; the physical boundary between zones
3. **Typed-Function Service** (Container App, platform-identity) — the only SQL read path for agents; returns validated DTOs; RLS predicates active; zero RESTRICTED data in any return value
4. **AI Gateway** (Container App, platform-identity) — FastAPI 9-step middleware chain; pinned model version and endpoint; async audit emit that blocks completions if audit queue is unavailable
5. **Action Dispatcher** (Container App, platform-identity, KEDA-scaled) — verifies signed action envelope; resolves recipient email from raw_cw.contacts (narrow grant); sends via Graph/SMTP; email addresses never exposed to agents
6. **Audit Writer** (Azure Function, audit-identity) — Service Bus trigger; SHA-256 chain-hash each event; append to WORM blob and Log Analytics; the exclusive writer to the audit store

### Critical Pitfalls

Nine load-bearing pitfalls identified. Top five for roadmap planning:

1. **Temporary dev access to raw zone becomes permanent** — Nightly grant-manifest drift detector; PIM JIT mandatory for all human raw-zone access (4-hour max, dual-approval, auto-revoke); logon trigger flags human-principal sessions on raw_* outside an active PIM window. Must hold through every phase; test explicitly in Foundation with chaos scenario.

2. **Indirect prompt injection via ticket/email body content** — Strip raw bodies before AI zone (INT-01 metadata-only is architectural, not policy). Adversarial corpus in CI on every PR touching prompts, views, or gateway code. Never weaken the body-stripping enforcement for agent feature convenience.

3. **HMAC person_pid reversible via dictionary attack on low-entropy email** — Per-tenant salt in Key Vault only (never logged, never cached beyond sync function call). Annual salt rotation fire drill. Quasi-identifier review on every new AI-zone view (k-anonymity check for small-tenant edge cases). Treat person_pid as SENSITIVE field class.

4. **Custom gateway HIPAA defensibility gap** — Owned gateway must produce its own evidence package: Presidio version pins in CI, chain-hash audit records, rate-limit enforcement logs, output-filter regression test suite, canary detection end-to-end in CI, code-review records for gateway changes, signed-artifact container registry tags, 90-day clean-run record. ~4 hours/week maintenance + 1 day/quarter review assembly.

5. **FortiGate subnet isolation misconfiguration** — The critical deny rules: ETL subnet to Anthropic DENY + LOG; services subnet to source-tool FQDNs DENY + LOG. These make cross-spoke compromise a network-impossible path. Test both deny rules before any data flows in Phase 1. FortiGate deny-event ingestion into Log Analytics provides the audit signal (NEW-03).

Two pitfalls introduced by the simplification itself:

6. **COMP-02 drop silently removes HIPAA-overlapping controls** — Dropping Drata/Vanta is safe; dropping quarterly access reviews, annual IR tabletop, and dual-control enforcement is not. Explicit re-homing into COMP-01 + NEW-05 + NEW-06 + NEW-11 is required and must be tracked separately in the roadmap.

7. **Audit log truncation or sampling under cost pressure** — Tiered storage prevents this: hot in Log Analytics (~$0 at under 5 GB/month), cold in WORM blob (~$3/month Y1). Budget alarm at 50% of forecast. Truncation is categorically forbidden; tiering earlier is the correct response.

---

## Implications for Roadmap

Based on combined research, the architecture's own build-order recommendation (four phases) maps directly onto the requirement triage and pitfall prevention schedule.

### Phase 1: Network and Data Foundations

**Rationale:** Hub-and-spoke topology, schema isolation, identity topology, and audit chain format are irreversible decisions. All five defense layers depend on foundations established here. No data should flow until FortiGate deny policies are tested and the grant manifest is enforced.

**Delivers:** Hub VNet + FortiGate VM; Barycenter spoke with five subnets; UDRs forcing egress through FortiGate; FortiGate deny rules for ETL-to-Anthropic and agent-to-source-tools tested and logging to Log Analytics; Azure SQL GP Serverless with private endpoint and publicNetworkAccess = Disabled; schema-isolation grants applied; Key Vault with RBAC-scoped access; WORM storage with immutability policy tested; Log Analytics with KV + SQL + FortiGate diagnostic settings; Service Bus (audit topic + action queue); field-class registry in repo with CI gate; Audit Writer Function deployed with chain-integrity verified; GitHub branch protection (NEW-05); PIM approval policies (NEW-06); BAA inventory document (NEW-11); salt rotation runbook (NEW-07).

**Addresses:** FOUND-01, FOUND-02, FOUND-03, FOUND-04, AUDIT-01, IDENT-01, IDENT-02, IDENT-03, EGRESS-01 (baseline), NEW-01, NEW-02, NEW-03, NEW-05, NEW-06, NEW-07, NEW-11

**Avoids:** Pitfall 1 (grant drift), Pitfall 5 (FortiGate misconfiguration), Pitfall 6 (tiered audit storage from day one), Pitfall 13 (dev environment controls)

**Lock-early decisions:** Hub-and-spoke topology, 4-identity model, single Key Vault, audit chain format, WORM retention period, schema-per-tool design.

**Research flag:** None needed. FortiGate Azure hub-and-spoke is a Fortinet reference architecture; ARCHITECTURE.md provides concrete subnet/UDR/policy tables. Gravity ops team familiar with FortiGate.

### Phase 2: Tool Onboarding Framework and First Integration (ConnectWise)

**Rationale:** The eight ETL primitives, four canonical AI-zone shapes, adapter base contract, and cursor convention are load-bearing once any tool is onboarded — retrofitting after multiple adapters is expensive. INT-01 (ConnectWise) must be first because cw_company_id is the system-wide customer anchor. This phase exercises the full ETL framework against bounded-PII data before person-level PII is introduced.

**Delivers:** Eight T-SQL transformation primitives; adapter base image with fetch_page, delta_cursor, and inline HMAC pseudonymization; Tool Onboarding Spec template with mandatory CUI section; ConnectWise adapter (companies, agreements, ticket metadata only — no bodies); AI-Zone Builder with customer_snapshot and timeseries_aggregate shapes; end-to-end smoke test with synthetic CW data; sync-health monitoring (structured sync result, partial-sync alerting, circuit breaker); schema drift detection (strict field validation, unknown-field logging, daily structural checksum); CUI exclusion flag enforcement at framework level (default deny if flag missing).

**Addresses:** TOOL-01, TOOL-02, TOOL-03, INT-01, COMP-03, RET-01, NEW-10 (sync-health alerting), NEW-13 (CUI canary phrase detection)

**Avoids:** Pitfall 2 (body-stripping enforced here — metadata-only is the architectural rule), Pitfall 7 (CUI flag at framework, not adapter), Pitfall 8 (schema drift detection), Pitfall 9 (partial sync monitoring), Pitfall 12 (deterministic reconciliation groundwork)

**Lock-early decisions:** Eight primitives, four AI-zone shapes, adapter base contract, cursor convention, CUI enforcement at framework layer.

**Research flag:** ConnectWise Manage API rate limits and incremental sync cursor mechanics. Standard patterns exist but Gravity's specific CW instance may have custom fields. Verify at implementation, not pre-planning.

### Phase 3: Agent-Safe Access Layer and Verification

**Rationale:** All five defense layers activate simultaneously. The typed-function service, gateway, and dispatcher form a trust chain and must be built together. VER-01 must wire into CI before any real agent connects — not after.

**Delivers:** Typed-Function Service (get_customer_snapshot, list_renewals_due, emit_action; RLS predicates; platform-identity grants validated); Action Dispatcher with signed-action-envelope contract; AI Gateway with full 9-step middleware chain; gateway kill switch (NEW-08); gateway model allowlist enforcing Anthropic Enterprise endpoint only (NEW-12); per-tenant per-class opt-out (ACCESS-05); VER-01 end-to-end leak test in CI with synthetic markers; VER-02 field-class drift detection in CI; adversarial prompt-injection corpus in CI; per-prompt structured trace (NEW-04); on-call alerting for VER-01 failure, gateway PII hits, token-budget exhaustion (NEW-10).

**Addresses:** ACCESS-01 through ACCESS-05, EGRESS-02, VER-01, VER-02, COMP-05 (reduced), NEW-04, NEW-08, NEW-09, NEW-10, NEW-12

**Avoids:** Pitfall 2 (gateway + adversarial corpus), Pitfall 3 (canary chain verifying pseudonymization), Pitfall 4 (view composition review on every new function), Pitfall 14 (aggregate token budgets)

**Lock-early decisions:** Typed-function naming convention, action envelope schema, canary token format, audit payload schema, signed-action-envelope contract between services.

**Research flag:** Presidio custom recognizer configuration for MSP-specific PII patterns (company names, CW ticket IDs, serial numbers). Allocate implementation time but no formal phase research needed. Confirm Anthropic BAA scope (pinned model versions, workspace isolation) before Phase 3 begins — this is a gap identified in the confidence assessment.

### Phase 4: Integrations 2 and 3, Compliance Posture, and Operations

**Rationale:** Pax8 (INT-02, lowest PII) before Graph (INT-03, person-level PII) exercises the controls progressively. Compliance documentation is assembled after the system is functional and VER-01 has at least one release of CI coverage — doing it earlier produces stale artifacts.

**Delivers:** Pax8 adapter (subscriptions, renewal dates, monthly value); Microsoft Graph adapter (users hashed to person_pid, license counts, tenant metadata); CUI exclusion end-to-end verification; customer erasure workflow with marker-string test customer; erasure verification across raw, AI zone, audit log (retained with documented justification), dev, and WORM; COMP-01 HIPAA baseline documentation (BAA scope, ZDR confirmation, 15-min idle logoff, breach notification runbook, quarterly access review schedule, annual tabletop calendar entry); AUDIT-02 (audit-of-audit, stored-procedure-gated); production sizing review; Defender for SQL and Defender for Storage enabled.

**Addresses:** INT-02, INT-03, ERAS-01, COMP-01 (complete), AUDIT-02, ENC-01 (TDE-only variant), TOOL-04, OPS-01 (sizing)

**Avoids:** Pitfall 3 (Graph is the full pseudonymization stress test; re-identification adversarial test runs here), Pitfall 6 (production sizing review), Pitfall 15 (erasure tested end-to-end, not just happy path)

**Research flag:** Microsoft Graph MSSP permissions at scale with GDAP/CSP delegation. Verify whether Gravity's CSP relationship allows required application permissions (Users.Read.All, LicenseDetails.Read.All) without per-customer admin consent. This could affect INT-03 design and onboarding flow — may benefit from a targeted research spike before INT-03 design begins.

### Phase Ordering Rationale

- **Network before data:** FortiGate deny policies must be tested before any data flows. A misconfigured firewall during ETL onboarding would allow ETL identity to reach Anthropic or agent identity to reach source-tool APIs — both are the exact threat the architecture prevents.
- **Framework before tools:** Each adapter must inherit CUI enforcement, schema drift detection, and sync-health monitoring from the framework. Retrofitting these after three adapters are in production is multi-week rework.
- **Lowest-PII tool first within each integration phase:** CW (bounded PII) before Pax8 (minimal PII) before Graph (person-level PII) exercises controls progressively and ensures bugs are caught on bounded-blast-radius data first.
- **VER-01 before any real agent:** The leak test in CI is the external contract downstream agent projects depend on. It must exist and pass before any agent receives typed-function access.
- **INT-04 after 90+ days of VER-01 clean runs:** Hard entry criterion, not a scheduling suggestion. Email-layer breach cost is categorically higher than CW/Pax8/Graph breach cost.

### Research Flags

**Phases needing deeper research during planning:**

- **Phase 3 (Gateway HIPAA evidence):** The custom FastAPI gateway replaces APIM's vendor-attested HIPAA evidence. Validate the ~4 hours/week evidence maintenance estimate against Gravity's actual compliance workload before committing the roadmap to this approach. Confirm Anthropic Enterprise BAA scope (pinned model versions, workspace isolation, ZDR confirmation) before Phase 3 begins.
- **Phase 4 (Graph MSSP permissions):** Microsoft Graph at MSP scale with GDAP/CSP delegation is a known complexity point. Verify whether Gravity's current CSP relationship allows required application permissions without per-customer admin consent. This affects INT-03 design — targeted research spike recommended before Phase 4 planning.

**Phases with standard patterns (skip research):**

- **Phase 1 (Network/FortiGate):** Fortinet's Azure hub-and-spoke reference architecture is well-documented. ARCHITECTURE.md has concrete subnet, UDR, and policy tables. Gravity ops team likely already familiar.
- **Phase 2 (CW/Pax8 adapters):** Both have well-documented REST APIs. ETL primitive framework follows standard cursor-based sync patterns.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Azure pricing verified against official pricing pages (May 2026). FortiGate throughput and SKU sizing verified against Fortinet datasheet. HIPAA §164.312 mapping verified against HHS eCFR and Tenable audit kit. TDE-only defensibility grounded in "addressable vs required" distinction in Security Rule text. |
| Features | HIGH | Requirement triage grounded in HIPAA Security Rule text. FortiGate mapping concrete and verifiable. INT-04 deferral grounded in OWASP LLM01 risk and breach cost asymmetry. NEW-01 through NEW-13 are gap-fills that prevent silent loss of HIPAA controls under simplification. |
| Architecture | HIGH (structural); MEDIUM (LOC estimates, Container Apps cost) | Hub-and-spoke with FortiGate is a Fortinet reference architecture. Four-identity consolidation is a judgment call with explicit blast-radius analysis. Gateway LOC estimate (200-400) is design estimate, not measured. Container Apps cost assumes 25% duty cycle — verify at first deployment. |
| Pitfalls | HIGH | Prompt injection grounded in CVE-2026-21520 and Anthropic Claude Code Security Review post-mortem. HMAC reversibility grounded in EDPS/ENISA guidance. Custom gateway evidence estimate (~4 hrs/week) is a judgment call — validate against Gravity's actual compliance workload. |

**Overall confidence: HIGH** for architectural and compliance decisions; MEDIUM for cost projections beyond first 3 months.

### Gaps to Address

- **SQL duty-cycle calibration:** The $50/month estimate assumes ~25% active compute fraction. Measure actual duty cycle after Phase 2 (first real ETL syncs). If duty cycle exceeds 50%, evaluate GP Provisioned 1 vCore (~$185/mo — still inside budget).
- **Anthropic BAA and ZDR confirmation:** Load-bearing for HIPAA compliance (Pitfall 5). Before Phase 3, confirm: signed BAA covers the specific workspace and API key in use; ZDR is enabled and verified in admin console; HIPAA-ready API surface covers the pinned model version. Document in NEW-11 BAA inventory.
- **FortiGate FQDN DNS resolution for Anthropic endpoint:** Verify api.anthropic.com resolves correctly via Fortinet's DNS proxy and that CDN IP changes don't require manual policy updates. TLS inspection of Anthropic traffic is explicitly not recommended (would break BAA zero-retention guarantee) — pass-through only.
- **Platform-identity blast radius for dispatcher:** Dispatcher shares platform-identity but holds a narrow SELECT grant on raw_cw.contacts. Compensating control (signed action envelopes) is app-layer. Before Phase 3 GA, confirm envelope signing key is in Key Vault (not hardcoded) and that gateway compromise cannot forge a signed envelope without the signing key.
- **Graph MSSP permission model:** Verify before INT-03 design whether Gravity's GDAP relationship allows required Graph application permissions without per-customer admin-consent prompts. If per-customer consent is required, the INT-03 onboarding flow needs a consent step.
- **PROJECT.md updates required before roadmap planning:** ENC-01 should be revised from "Always Encrypted on RESTRICTED columns" to "TDE-only with AE deferred, architecture-compatible." AUDIT-01 should be revised from "mirrored to Azure Sentinel" to "mirrored to Azure Storage WORM and Log Analytics; Sentinel deferred." These changes should be made before the roadmapper creates phases, to avoid stale requirement text driving phase design.

---

## Sources

### Primary (HIGH confidence)

- [Azure SQL Database Serverless pricing](https://azure.microsoft.com/en-us/pricing/details/azure-sql-database/single/) — $0.5218/vCore-hr, GP storage $0.115/GB
- [Azure SQL Serverless tier overview](https://learn.microsoft.com/en-us/azure/azure-sql/database/serverless-tier-overview) — auto-pause semantics, ~1 min resume
- [Azure Monitor pricing](https://azure.microsoft.com/en-us/pricing/details/monitor/) — LA Analytics, first 5 GB free
- [Azure Blob Storage pricing](https://azure.microsoft.com/en-us/pricing/details/storage/blobs/) — Cool tier $0.01/GB-month
- [Azure Container Apps pricing](https://azure.microsoft.com/en-us/pricing/details/container-apps/) — free grant 180K vCPU-s, 360K GiB-s, 2M req/month
- [Immutable storage for blob data](https://learn.microsoft.com/en-us/azure/storage/blobs/immutable-storage-overview) — WORM, time-based retention, Cohasset SEC 17a-4(f)
- [Transparent Data Encryption for Azure SQL](https://learn.microsoft.com/en-us/azure/azure-sql/database/transparent-data-encryption-tde-overview) — TDE default on, AES-256
- [Key Vault VNet service endpoints](https://learn.microsoft.com/en-us/azure/key-vault/general/overview-vnet-service-endpoints)
- [Microsoft HIPAA/HITECH Implementation Guidance](https://learn.microsoft.com/en-us/compliance/regulatory/offering-hipaa-hitech) — BAA covers all listed Azure services
- [FortiGate VM on Azure Data Sheet](https://www.fortinet.com/content/dam/fortinet/assets/data-sheets/FortiGate_VM_Azure.pdf) — FGT-VM02: 15 Gbps firewall, 2.5 Gbps IPS, default Azure SKU F2s_v2
- [FortiGate Public Cloud 7.6.0 Azure Administration Guide](https://docs.fortinet.com/document/fortigate-public-cloud/7.6.0/azure-administration-guide/562841/instance-type-support) — Azure SKU compatibility
- [eCFR 45 CFR §164.312 — Technical Safeguards](https://www.ecfr.gov/current/title-45/subtitle-A/subchapter-C/part-164/subpart-C/section-164.312) — Security Rule text; §164.312(a)(2)(iv) is addressable
- [HIPAA 164.312(a)(2)(iv) — Tenable audit kit](https://www.tenable.com/audits/items/HIPAA_MS_OS.audit:0693dc6eafdb883eaca69db8f9bbce17) — TDE-class AES-256 satisfies addressable control
- [HIPAA 164.312(b) Audit Controls — AlertLogic](https://docs.alertlogic.com/analyze/reports/compliance/HIPAA-164.312-audit-controls.htm) — required audit field set
- [Anthropic BAA for Commercial Customers](https://privacy.claude.com/en/articles/8114513-business-associate-agreements-baa-for-commercial-customers) — BAA scope; ZDR no longer prerequisite for HIPAA in 2026
- [Anthropic ZDR scope](https://privacy.claude.com/en/articles/8956058-i-have-a-zero-data-retention-agreement-with-anthropic-what-products-does-it-apply-to) — opt-in, per-customer, eligible APIs only

### Secondary (MEDIUM confidence)

- [Anthropic API docs — Prompt caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching) — workspace-level isolation since Feb 5, 2026 on first-party API; org-level on Bedrock/Vertex
- [Microsoft Sentinel billing](https://learn.microsoft.com/en-us/azure/sentinel/billing) — $5.20/GB surcharge on top of LA ingestion (justifies deferral)
- [EDPS/AEPD — Hash Function as Personal Data Pseudonymisation](https://www.edps.europa.eu/sites/default/files/publication/19-10-30_aepd-edps_paper_hash_final_en.pdf) — HMAC reversibility on low-entropy inputs
- [VentureBeat — CVE-2026-21520 Copilot Studio prompt injection](https://venturebeat.com/security/microsoft-salesforce-copilot-agentforce-prompt-injection-cve-agent-remediation-playbook) — exfiltration with no upper bound
- [Microsoft Presidio](https://microsoft.github.io/presidio/) — PII detection library, Python-native

### Tertiary (LOW confidence — verify at implementation)

- Container Apps actual cost above free grant — measure at first deployment
- Azure Bastion Developer SKU pricing — newer SKU, pricing model evolving
- Defender for SQL ($15/mo) and Defender for Storage ($10/mo) — verify in Azure pricing calculator at deployment

---

*Research completed: 2026-05-02 (revised for cost-simplified Barycenter architecture)*
*Ready for roadmap: yes*
*Supersedes: initial SUMMARY.md (over-engineered; DC-series SQL, APIM, 6 identities, Sentinel)*
