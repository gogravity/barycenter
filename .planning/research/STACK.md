# Stack Research (Revised — Cost-Simplified)

**Domain:** MSP-internal AI data platform (Azure-native, HIPAA-floor only, Anthropic Claude as LLM, FortiGate NVA perimeter, BYOL)
**Researched:** 2026-05-02 (revision of 2026-05-01 over-specified stack)
**Budget ceiling:** **$200/month total** including FortiGate VM compute
**Confidence:** HIGH (Azure pricing, FortiGate sizing, HIPAA §164.312 mapping); MEDIUM (FastAPI gateway middleware composition — design choice, not a discovered standard)

---

## Executive Summary

The previous stack research over-specified by ~$700/mo. The cost driver was DC-series Azure SQL ($300+), APIM Standard v2 ($250+), Sentinel-as-primary-SIEM, Drata, and a dense matrix of private endpoints. With CMMC out, Always Encrypted dropped, and a FortiGate NVA already paid for under Gravity's Fortinet MSSP BYOL agreement, the architecture collapses cleanly into:

1. **Azure SQL Serverless GP, 0.5–2 vCore auto-pause** — sized for sync-heavy + bursty agent reads, not 24/7 OLTP. Realistic billing: **~$30–55/mo** at projected duty cycle. TDE (always-on) + schema permissions + AI-safe views satisfy HIPAA §164.312(a)(2)(iv) for RESTRICTED columns; Always Encrypted was defensive depth, not a HIPAA requirement.
2. **FortiGate-VM02 BYOL on Standard_F2s_v2 (single VM, no HA in v1)** — ~$62/mo VM compute, BYOL license cost = $0 (Gravity MSSP). FGT-VM02 is licensed for 2 vCPU and rated to 15 Gbps L3 throughput per Fortinet's Azure datasheet — vastly more than Barycenter needs.
3. **Hub-and-spoke with one Barycenter spoke** — three subnets inside the spoke (data, compute, admin), UDR points to FortiGate. No per-service private endpoints except SQL. Key Vault and Storage use VNet service endpoints (free) since FortiGate is already enforcing the perimeter.
4. **Owned FastAPI gateway in Container Apps (~300 LOC)** — replaces APIM AI Gateway. Middleware: auth (Entra JWT), rate limit (token bucket per identity), Presidio inbound scrub, Anthropic SDK call with streaming, Presidio outbound scrub + canary scan, structured audit emit. Free under Container Apps consumption-tier monthly grant.
5. **Three-managed-identity model**: ETL identity, agent/gateway identity, admin (PIM-eligible) identity. **One Key Vault** with RBAC scope-per-key.
6. **Audit:** Log Analytics workspace (90-day hot, ~$5–10/mo at 50–100 MB/day) + WORM blob (cool tier, 6-year retention-locked, ~$3/mo growing to ~$10/mo by year 6). Sentinel deferred — Log Analytics + WORM satisfies HIPAA §164.312(b). Sentinel adds *threat detection* value, not *audit retention* value.

**Total itemized:** **$166/month** at v1 (see §7). Headroom of $34 for cost growth.

---

## 1. Azure SQL Tier Selection — Serverless wins

### Workload profile
- Sync jobs: 4×/day (every 6h), 15–30 min active per cycle, ETL writes to `raw_*`
- Agent queries: 2–4 hours/day during business hours, read-only against `ai_zone.*` views
- 5-year volume estimate: 5–50 GB raw, much smaller AI zone

**Active compute fraction:** roughly 4×0.5h + 4h = **6 hours/day = 25%** duty cycle, often less.

### Tier comparison

| Tier | Min config | Compute price | Always-on cost (730h) | Realistic Barycenter cost |
|------|-----------|---------------|----------------------|--------------------------|
| **Serverless GP** | 0.5–2 vCore auto-pause | $0.5218/vCore-hr | $190/mo at 0.5 vCore continuous | **~$30–55/mo** at 25% duty + auto-pause |
| GP Provisioned 1 vCore | 1 vCore continuous | $0.2528/vCore-hr | ~$185/mo | ~$185/mo |
| GP Provisioned 2 vCore | 2 vCore continuous | $0.2528/vCore-hr | ~$370/mo | ~$370/mo |
| Business Critical | 2 vCore min | ~3x GP rate | ~$1100+/mo | over budget |
| Hyperscale | 2 vCore min + per-replica | $0.30+/vCore-hr + storage | ~$220+/mo | over budget |

**Math for Serverless at projected usage:**
- Active: 6 hr/day × 1 vCore avg × $0.5218 × 30 days = **$93.92/mo at 1 vCore avg**
- Active: 6 hr/day × 0.75 vCore avg × $0.5218 × 30 days = **$70/mo**
- More realistic: bursts to 2 vCore for 1h/day, 0.5 vCore for 5h/day, paused 18h/day:
  - (2×1 + 0.5×5) × $0.5218 × 30 = **$70/mo** compute
  - Storage: 32 GB × $0.115 = $3.68/mo
  - **Total SQL: ~$74/mo** at upper envelope

For v1 with smaller volumes, **expect ~$30–55/mo**. Scale-up to provisioned 1 vCore once duty cycle exceeds ~50%.

### Cold-start concern for HIPAA audit continuity

Auto-resume latency: **~1 minute typical, first-query 20–40 sec** to rehydrate buffer pool ([Microsoft Learn — Serverless tier overview](https://learn.microsoft.com/en-us/azure/azure-sql/database/serverless-tier-overview)).

**This does NOT compromise HIPAA audit continuity** because:
- Audit writes do not depend on the database being warm. The gateway emits audit events to **Log Analytics + WORM blob asynchronously** via the OpenTelemetry exporter — both have independent SLAs and are not gated on Azure SQL availability.
- The chain-hash audit entries live in a dedicated `audit_*` table that the gateway writes to (and only writes to). A 30-second cold start delays the *write* but does not break the chain — the prior digest is read from blob, the new entry hashes prior + payload, append succeeds when DB resumes.
- HIPAA §164.312(b) requires audit *recording*, not real-time persistence. Buffered async writes with durable queue (Azure Service Bus, ~$10/mo Basic) are HIPAA-defensible.

**Recommendation: Azure SQL Database, Serverless General Purpose, Gen5, 0.5–2 vCore range, auto-pause = 60 minutes, 32 GB storage. Estimated cost: $50/mo (with headroom to $75).** Verify 6-year audit retention is on the WORM blob, not SQL — SQL's role is operational data, not legal-hold archive.

### HIPAA / BAA coverage
Azure SQL is BAA-covered under the standard Microsoft Online Services BAA. No tier distinction for BAA — Basic, Serverless, GP, BC, Hyperscale are all covered. Source: [Microsoft HIPAA / HITECH Act Implementation Guidance](https://learn.microsoft.com/en-us/compliance/regulatory/offering-hipaa-hitech).

---

## 2. TDE-only Story for RESTRICTED columns — HIPAA-defensible

### The defense, restated

Five-layer leak boundary still holds without Always Encrypted:

1. **Schema permissions** — agent identity has zero `SELECT` on `raw_*.*`. RESTRICTED columns are unreachable by the agent's SQL token.
2. **AI-safe views** — `ai_zone.*` views are the only objects granted to agent. Views project pseudonymized columns only; RESTRICTED columns are physically excluded from view definitions.
3. **Typed tool functions** — agent does not write SQL, calls `get_customer_snapshot(cw_company_id)` etc.
4. **Gateway scrubbing** — Presidio + canary detection on every prompt and completion.
5. **Per-prompt audit** — chain-hash + WORM mirror.

**Encryption at rest:** Azure SQL TDE is on by default for all tiers, uses AES-256, service-managed keys covered by Microsoft BAA. Source: [Transparent Data Encryption for Azure SQL Database](https://learn.microsoft.com/en-us/azure/azure-sql/database/transparent-data-encryption-tde-overview).

### HIPAA Security Rule §164.312 mapping

| HIPAA Control | Standard | Implementation |
|---------------|----------|----------------|
| §164.312(a)(1) Access Control | Required | Entra ID + per-service managed identities + schema permissions (RESTRICTED columns physically inaccessible to agent identity) |
| §164.312(a)(2)(iii) Automatic Logoff | Addressable | Conditional Access session timeout 15 min for admin; agent tokens 1h max |
| **§164.312(a)(2)(iv) Encryption/Decryption** | **Addressable** | **Azure SQL TDE (AES-256, Microsoft BAA-covered keys); column-level encryption assessed and documented as not-required given schema-isolation architecture** |
| §164.312(b) Audit Controls | **Required** | Chain-hash audit log → Log Analytics + WORM blob (6-year retention-locked) |
| §164.312(c)(1) Integrity | Required | TDE + chain-hash audit; ledger digest publication optional defensive depth |
| §164.312(d) Authentication | Required | Entra ID with phishing-resistant MFA on privileged roles |
| §164.312(e)(1) Transmission Security | Required | TLS 1.2+ enforced (Azure SQL minimum TLS), private network for SQL traffic |

**Key point on §164.312(a)(2)(iv):** This control is **addressable**, not required. "Addressable" means: assess whether reasonable and appropriate; if not, document why and use equivalent alternative ([HHS HIPAA Security Rule guidance](https://www.hhs.gov/hipaa/for-professionals/security/laws-regulations/index.html)). The HHS guidance and the Tenable HIPAA audit kit ([HIPAA 164.312(a)(2)(iv) — Encryption and Decryption](https://www.tenable.com/audits/items/HIPAA_MS_OS.audit:0693dc6eafdb883eaca69db8f9bbce17)) both treat strong at-rest encryption (TDE-class AES-256) as satisfying this control. Always Encrypted is *additional* defense against a compromised DBA threat — it's not a HIPAA requirement and was previously sized for CMMC L2 (now out of scope).

**Defensibility argument for an auditor:** "RESTRICTED data is encrypted at rest with AES-256 (TDE). The threat model that Always Encrypted addresses (compromised DBA reading plaintext) is mitigated architecturally by Entra-ID-only authentication, JIT PIM admin grants with dual control, no standing admin grants on `raw_*` schemas, and complete absence of SQL authentication / contained-DB users with passwords. The ePHI never leaves the encrypted boundary in plaintext to any identity that the agent path can reach."

This is HIPAA-defensible. SOC 2 reviewers may push for column-level encryption later — that's a future-tier upgrade and architecture supports it (CMK in customer Key Vault was already documented as the upgrade path in COMP-04).

**Update to PROJECT.md ENC-01:** "Always Encrypted on RESTRICTED columns" should be revised to "TDE on all storage, schema permissions enforce RESTRICTED isolation, Always Encrypted deferred (architecture-compatible) until SOC 2 audit pursuit or specific customer demand."

---

## 3. FortiGate NVA — Sizing and Topology

### VM SKU recommendation: **Standard_F2s_v2** (compute-optimized, 2 vCPU / 4 GB)

| SKU | vCPU | RAM | Monthly | Suitable? |
|-----|------|-----|---------|-----------|
| **Standard_F2s_v2** | 2 | 4 GB | **~$62/mo** Linux PAYG | **Recommended.** Compute-optimized (3.4 GHz Cascade Lake), accelerated networking, no CPU credit budget. Fortinet's default template SKU for FortiGate-VM02. |
| Standard_B2s_v2 | 2 | 8 GB | ~$60/mo | Burstable — has CPU credit budget that can throttle under sustained NVA load. **Not recommended for a perimeter firewall.** $2/mo savings not worth the throttle risk on packet path. |
| Standard_DS2_v2 | 2 | 7 GB | ~$110/mo | Older D-series, no benefit over F2s_v2 for this workload |
| Standard_F4s_v2 | 4 | 8 GB | ~$124/mo | Overprovisioned — FGT-VM02 is licensed for 2 vCPU; extra cores wasted |

### License match (BYOL, Gravity Fortinet MSSP)
- **FGT-VM02 BYOL** = 2 vCPU license, RAM unlimited. Pairs with Standard_F2s_v2.
- Fortinet datasheet rates FGT-VM02 at **15 Gbps firewall throughput, 2.5 Gbps IPS, 1.5 Gbps SSL inspection** ([FortiGate VM on Microsoft Azure Data Sheet](https://www.fortinet.com/content/dam/fortinet/assets/data-sheets/FortiGate_VM_Azure.pdf)).
- Barycenter peak: **maybe 50 Mbps** (Anthropic streaming completions + ETL bursts). Headroom is 300x.
- **License cost: $0** (covered under Gravity MSSP BYOL).

### HA tradeoff
Fortinet's reference architecture uses two FortiGate VMs in active-passive HA. For Barycenter v1 — internal tool, business-hours operation, accepted RTO of 1–2 hours for firewall failure — **single VM is acceptable**. HA doubles the compute cost ($124/mo) and adds a load balancer ($25/mo). Defer until ops maturity demands it.

### Topology: Hub-and-spoke, one spoke for Barycenter

```
                 Internet
                    |
        +----------------------+
        |   Hub VNet           |
        |   ┌────────────────┐ |
        |   │ FortiGate-VM02 │ |    Egress: Anthropic API + Azure
        |   │   F2s_v2       │ |    Service Tags only
        |   └────────────────┘ |
        +----------|-----------+
                   | UDR (0.0.0.0/0 → FGT internal NIC)
        +----------|-----------+
        |   Spoke VNet (Barycenter)        |
        |   ┌─────────────────────────────┐|
        |   │ snet-data (10.1.1.0/24)    │|  → Azure SQL private endpoint
        |   │ snet-compute (10.1.2.0/24) │|  → Container Apps env
        |   │ snet-admin (10.1.3.0/24)   │|  → JIT bastion / PIM admin path
        |   └─────────────────────────────┘|
        +----------------------------------+
```

**Why one spoke, not three:**
- Three spokes would force cross-spoke traffic through the FortiGate, doubling east-west firewall load and adding ~$30–60/mo in inter-VNet peering charges (peering is $0.01/GB each direction).
- NSG-level segmentation between subnets in a single spoke is sufficient for the threat model (ETL identity ≠ agent identity at Entra layer; subnet NSG enforces the boundary at network layer).
- Single VNet simplifies private DNS zone management (one zone per Azure service, not three).

---

## 4. Private Endpoints vs Service Endpoints vs FortiGate Perimeter

The decision rule: **a private endpoint is required when a service is the data store for RESTRICTED/SENSITIVE/PHI data**. Service endpoints suffice when the service is auxiliary or when data inside it is already encrypted/scoped.

| Azure Service | Recommendation | Why |
|---------------|---------------|-----|
| **Azure SQL Database** | **Private Endpoint** ($7/mo) | The crown jewel. PE pins traffic to a private IP inside the spoke; combined with `publicNetworkAccess = Disabled` it is the strongest NetSec control. Non-negotiable. |
| **Azure Key Vault** | **VNet Service Endpoint** (free) | Service endpoint + IP allowlist + Entra-only auth + `publicNetworkAccess = Disabled` is HIPAA-defensible. Microsoft *recommends* PE for sensitive workloads but service endpoint with FortiGate egress filter and Entra RBAC is materially equivalent for this threat model. **Saves $7/mo.** |
| **Azure Storage (Blob — WORM audit)** | **VNet Service Endpoint** (free) | Audit blobs are write-once-read-many; data inside is application-encrypted (chain-hash payload). Service endpoint + storage firewall + RBAC sufficient. **Saves $7/mo.** |
| **Azure Storage (Blob — raw archive after retention)** | **VNet Service Endpoint** (free) | Same as above. If a customer demands PE later, upgrade then. |
| **Azure Container Apps** | Internal-only Container Apps Environment (built-in private networking, no separate PE) | The CA env itself is VNet-injected; `external = false` makes it reachable only from inside the spoke. No additional PE needed. |
| **Container Registry (ACR)** | VNet Service Endpoint (free) | Image pulls happen inside Azure backbone via service endpoint. Premium tier required for service endpoint; stay on Standard if you accept public-with-RBAC for image pulls (still BAA-covered). **Recommend Service Endpoint on Premium ACR for cleanliness — adds $1.67/mo.** |
| **Microsoft Graph** | N/A (egress through FortiGate to public Graph endpoint, Entra-authenticated) | No private endpoint product for Graph. |
| **ConnectWise / Pax8 / etc. SaaS APIs** | N/A (egress through FortiGate allowlist) | FortiGate FQDN-based outbound rule per provider. |
| **Anthropic API** | N/A (egress through FortiGate allowlist) | FortiGate outbound rule for `api.anthropic.com` only. |

**Summary:** **One private endpoint (Azure SQL) at $7/mo. Everything else uses VNet service endpoints (free) plus FortiGate egress allowlisting.**

This is HIPAA-defensible because the perimeter is enforced at the network layer (FortiGate), the identity layer (Entra + managed identities, no long-lived secrets), and the service-firewall layer (service endpoint + IP allowlist + `publicNetworkAccess = Disabled`).

---

## 5. Audit Trail — Log Analytics + WORM Blob, Sentinel Deferred

### Architecture
- **Hot tier:** Log Analytics workspace, 90-day retention. Queryable, KQL-driven, Workbooks for dashboards.
- **Cold tier:** Azure Storage Blob (Cool), immutable container with **time-based retention policy locked to 2190 days (6 years) + legal hold capability**. Cohasset-validated for SEC 17a-4(f), HIPAA-equivalent. Source: [Overview of immutable storage for blob data](https://learn.microsoft.com/en-us/azure/storage/blobs/immutable-storage-overview).
- **Audit-of-audit:** Log Analytics workspace `_LogOperation` table captures workspace queries; mirrored to the same WORM container.

### Cost at 50–100 MB/day audit volume

| Component | Volume | Rate | Monthly |
|-----------|--------|------|---------|
| LA ingestion (Analytics tier) | 100 MB/day × 30 = 3 GB/mo | First 5 GB free | **$0** |
| LA retention 32–90 days | 3 GB × 60 days × $0.10/GB-month / 30 | $0.10/GB-month interactive | **~$0.60** |
| Blob Cool storage growing | ~3 GB/mo accreting → 36 GB y1, 216 GB y6 | $0.01/GB-month | **$0.03 y1 → $2.16 y6** |
| Blob write transactions | ~3000/mo (one append per audit batch) | ~$0.05/10K | **negligible** |
| **Total audit Y1** | | | **~$1/mo** |
| **Total audit Y6** | | | **~$3/mo** |

Sources: [Azure Monitor pricing](https://azure.microsoft.com/en-us/pricing/details/monitor/), [Azure Blob Storage pricing](https://azure.microsoft.com/en-us/pricing/details/storage/blobs/).

Allocate **$10/mo budget** to absorb growth + occasional verbose tracing during incident investigation.

### Does Sentinel add anything HIPAA-required that LA + WORM doesn't?

**No.** HIPAA §164.312(b) requires *recording and examining activity* — both are satisfied by Log Analytics (KQL queries = examination, ingestion = recording). HIPAA does not mandate a SIEM by name or a specific anomaly-detection engine.

What Sentinel adds:
- Prebuilt analytics rules (anomaly detection, threat intel correlation)
- Incident management workflow
- HIPAA Compliance Solution (preview) — prebuilt dashboards and assessment workbooks
- UEBA, SOAR playbooks

What Sentinel costs at Barycenter scale: $5.20/GB ingestion **on top of** Log Analytics ingestion (i.e., the Sentinel surcharge), so 3 GB/mo = ~$15.60/mo. Plus prebuilt-rule maintenance burden.

**Decision:** Defer Sentinel. Add it when (a) a customer's HIPAA security questionnaire explicitly requires SIEM, (b) Gravity has ops capacity to triage Sentinel alerts, or (c) audit volume crosses ~10 GB/mo and the Sentinel HIPAA Solution becomes worth the surcharge. Architecture is forward-compatible — turn Sentinel on top of the existing Log Analytics workspace.

Sources: [Plan costs and understand pricing — Microsoft Sentinel](https://learn.microsoft.com/en-us/azure/sentinel/billing), [Audit Microsoft Sentinel queries and activities](https://learn.microsoft.com/en-us/azure/sentinel/audit-sentinel-data).

---

## 6. Owned AI Gateway — FastAPI in Container Apps

### Why owned, not APIM
- APIM Standard v2 ≈ $250/mo, dwarfs the rest of the budget.
- Barycenter has *one* LLM provider (Anthropic), *one* set of policies, *one* tenant boundary. APIM's value is multi-API governance — wasted here.
- The `llm-*` policies in APIM (token-limit, content-safety, semantic-cache) are 50–100 LOC each in Python.
- Owning the gateway removes the BAA fan-out concern (APIM is BAA-covered, but custom transforms running in APIM are still your code that you'd audit anyway).

### Architecture (~250–400 LOC FastAPI)

```
Client (typed tool function service)
  │  [HTTPS, Entra workload identity JWT]
  ▼
FastAPI app (Container Apps, internal-only, snet-compute)
  ├─ Middleware 1: Entra JWT validation (azure-identity verify)
  ├─ Middleware 2: Per-identity token-bucket rate limit (in-memory + Redis fallback)
  ├─ Middleware 3: Per-tenant per-day token budget (Redis or SQL audit table lookup)
  ├─ Middleware 4: Request audit emit (chain-hash entry: prior_digest + request_meta)
  ├─ Middleware 5: Presidio inbound scan — block on PII match in prompt
  ├─ Middleware 6: Canary token scan — block on canary string in prompt (VER-01)
  │
  ▼
Anthropic SDK call (anthropic>=0.42, messages.create, streaming, prompt caching)
  │
  ▼
  ├─ Middleware 7: Presidio outbound scan — block + alert on PII in completion
  ├─ Middleware 8: Canary token scan — block + alert on canary in completion (VER-01)
  ├─ Middleware 9: Output schema validation (Pydantic) for structured outputs
  ├─ Middleware 10: Response audit emit (chain-hash entry: request_id + completion_meta + tokens)
  │
  ▼
Return to caller
```

### Concrete library stack

| Library | Version | Purpose |
|---------|---------|---------|
| `fastapi` | `>=0.115` | HTTP framework |
| `uvicorn[standard]` | `>=0.32` | ASGI server |
| `anthropic` | `>=0.42, <1.0` | Claude SDK with `cache_control` typing |
| `azure-identity` | `>=1.19` | Workload identity for outbound (Anthropic key from Key Vault) and JWT validation |
| `azure-keyvault-secrets` | `>=4.10` | Anthropic API key retrieval at startup (rotated quarterly) |
| `azure-monitor-opentelemetry` | `>=1.7` | Structured logging into Log Analytics; OTel GenAI semantic conventions emit token counts |
| `azure-storage-blob` | `>=12.24` | Audit chain mirror to WORM container |
| `presidio-analyzer` + `presidio-anonymizer` | `>=2.2.358` | PII detection inbound + outbound |
| `pydantic` | `>=2.10` | Request/response models, structured-output validation |
| `pyjwt[crypto]` | `>=2.10` | Entra JWT signature validation |
| `redis` (optional) | `>=5.2` | Rate-limit counters (Container Apps Redis or in-memory if single replica) |

### HIPAA per-prompt audit fields (§164.312(b))

Per-request audit entry (chain-linked, written sync to LA + async-mirrored to WORM):

```json
{
  "audit_id": "uuid-v7",
  "prior_digest": "sha256(prior entry)",
  "current_digest": "sha256(prior_digest || canonical(this entry))",
  "ts_utc": "2026-05-02T14:32:01.123Z",
  "actor": {
    "principal_id": "managed-identity-object-id",
    "principal_type": "agent | etl | admin",
    "tenant_id": "internal-uuid",
    "request_ip": "10.1.2.x"
  },
  "action": {
    "verb": "llm.completion.request | llm.completion.response | tool.invoke",
    "tool_function": "get_customer_snapshot",
    "model": "claude-sonnet-4-5",
    "request_id": "anthropic-msg-id"
  },
  "subject": {
    "cw_company_id": "...",
    "person_pid": "...",
    "phi_tagged": true
  },
  "outcome": {
    "status": "success | denied_pii_match | denied_canary | denied_budget | error",
    "denial_reason": "presidio:EMAIL_ADDRESS | canary:CANARY_001 | null"
  },
  "tokens": {
    "input": 1234,
    "output": 567,
    "cache_read": 8000,
    "cache_creation": 0
  },
  "data_class_summary": {
    "restricted_columns_touched": [],
    "sensitive_columns_touched": ["company_name"]
  },
  "completion_excerpt_hash": "sha256(first 500 chars of completion)"
}
```

**Why these fields, mapped to HIPAA §164.312(b):**
- `actor.principal_id` + `actor.tenant_id` → **WHO**
- `action.verb` + `action.tool_function` + `action.model` → **WHAT**
- `ts_utc` (UTC, NTP-synced) → **WHEN**
- `actor.request_ip` → **WHERE**
- `subject.cw_company_id` + `subject.person_pid` + `subject.phi_tagged` → **PATIENT/RECORD ID** (pseudonymized; salt-resolution requires PIM admin grant + dual control)
- `outcome.status` → **SUCCESS/FAILURE**
- `prior_digest` + `current_digest` → tamper evidence
- `completion_excerpt_hash` → integrity of completion without storing PHI in audit log

**Important:** the audit log itself MUST NOT contain RESTRICTED data. The `completion_excerpt_hash` lets you detect tampering with the completion via canary re-test, without persisting PHI in a long-retention store.

Source: [HIPAA 164.312(b) — Audit Controls](https://docs.alertlogic.com/analyze/reports/compliance/HIPAA-164.312-audit-controls.htm), [HIPAA Technical Safeguards 164.312](https://www.accountablehq.com/post/hipaa-technical-safeguards-list-164-312-quick-reference-checklist-for-access-audit-integrity-authentication-amp-transmission-security).

### Container Apps cost for the gateway

Single replica, 0.5 vCPU / 1 GiB, target 5–10 RPS during business hours, scale-to-zero off-hours.
- Active vCPU-seconds: ~6h × 3600s × 0.5 vCPU × 22 business days = ~237K vCPU-s/mo
- Idle: minimal
- Free grant: 180K vCPU-s, 360K GiB-s
- **Net: ~$0–3/mo for the gateway**, fits comfortably under free grant for ETL workers + tool-function service combined.

Sources: [Azure Container Apps Pricing](https://azure.microsoft.com/en-us/pricing/details/container-apps/), [Billing in Azure Container Apps](https://learn.microsoft.com/en-us/azure/container-apps/billing).

---

## 7. Final Itemized Cost Breakdown

### Identity inventory (no cost line, structural)
- **3 managed identities:**
  1. `mi-barycenter-etl` — assigned to ETL Container App jobs. Has `db_datawriter` on `raw_*` schemas, Key Vault `Sign` on per-tenant salt keys, Storage `Blob Data Contributor` on raw-zone container.
  2. `mi-barycenter-agent` — assigned to gateway + tool-function service Container Apps. Has `db_datareader` on `ai_zone.*` views ONLY (zero grants on `raw_*`), Key Vault `Get` on Anthropic API key secret only, Storage `Blob Data Contributor` on audit container.
  3. `mi-barycenter-admin` — PIM-eligible, activated on demand, full DB owner + Key Vault administrator. Dual-control on activation.
- **1 Key Vault** with RBAC scoping: salt keys (HMAC sign) accessible only by ETL identity at `/keys/salt-tenant-*`; Anthropic API key accessible only by agent identity at `/secrets/anthropic-api-key`; admin identity has full access only when PIM-activated.

### Monthly cost table (East US, PAYG, May 2026)

| Item | SKU / Config | Monthly | Confidence |
|------|--------------|---------|------------|
| FortiGate-VM02 BYOL VM compute | Standard_F2s_v2, single instance, no HA | **$62** | HIGH |
| FortiGate-VM02 BYOL license | Gravity MSSP coverage | **$0** | HIGH |
| Azure SQL Database | Serverless GP, Gen5, 0.5–2 vCore auto-pause, 32 GB | **$50** (envelope $30–75) | HIGH |
| Azure SQL private endpoint | 1 PE × $0.01/hr | **$7** | HIGH |
| Container Apps Environment | Internal-only, VNet-injected, workload profile | **$0** (consumption) | HIGH |
| Container Apps consumption | gateway + tool service + ETL workers, mostly within free grant | **$5** | MEDIUM |
| Azure Container Registry | Standard, ~5 GB images | **$5** | HIGH |
| Azure Key Vault | Standard, RBAC, soft-delete + purge protection, ~10K ops/mo | **$1** | HIGH |
| Log Analytics workspace | 3 GB/mo ingestion (within free 5 GB), 90-day retention | **$1** | HIGH |
| Azure Storage WORM (audit, Cool, immutable) | 36 GB Y1 → 216 GB Y6, GRS | **$3** Y1 ($10 Y6) | HIGH |
| Azure Storage (raw-zone archive, Cool) | 5–50 GB GRS | **$2** | HIGH |
| Service Bus Basic (audit queue) | 1M ops/mo | **$0.05** | HIGH |
| Defender for SQL | Per server enablement | **$15** | HIGH |
| Defender for Storage | Per account, malware scan optional | **$10** | HIGH |
| Bandwidth (Azure → Anthropic + Graph) | ~10 GB/mo egress | **$0.87** | HIGH |
| VNet peering (hub ↔ spoke) | ~10 GB/mo each direction | **$0.20** | HIGH |
| Bastion / JIT admin path | Azure Bastion Developer SKU (per-use) or skip in v1 with break-glass via PIM + Conditional Access | **$5** | MEDIUM |
| **Subtotal v1** | | **$166** | |
| **Headroom** | | **$34** | |
| **Budget ceiling** | | **$200** | |

**Notes on the spend:**
- Defender for SQL ($15) is non-optional for HIPAA threat-detection evidence — Microsoft Defender for Cloud HIPAA control mapping requires it.
- Defender for Storage ($10) likewise. If audit data ever lands in a non-WORM container, you want Defender malware scanning on the upload path.
- The $34 headroom absorbs: SQL duty cycle exceeding 25%, audit volume growth past 100 MB/day, brief Container Apps overage during sync storms, PE on a second service if needed.

**Items deferred (not in v1 budget but architecture-compatible):**
- Microsoft Sentinel (~$15/mo at 3 GB) — turn on when HIPAA SIEM evidence needed
- FortiGate HA second VM (~$62/mo) — turn on when ops maturity demands
- APIM Standard v2 ($250/mo) — never, owned gateway suffices
- Drata ($600+/mo) — defer until SOC 2 pursuit decision
- Always Encrypted with secure enclaves ($300+/mo SQL premium for DC-series) — defer or use VBS enclaves on standard tier if column-level needed later (free, weaker hardware isolation)
- ACR Premium for service endpoint (~$1.67/mo more than Standard) — upgrade if image-pull surface becomes a concern

---

## What NOT to Use (revised)

| Avoid | Why |
|-------|-----|
| **Azure SQL DC-series** | $300+/mo for a feature (Always Encrypted secure enclaves) we don't need with HIPAA-only posture. |
| **Always Encrypted on RESTRICTED columns (v1)** | Defensive depth, not HIPAA-required. Schema permissions + TDE + AI-safe views satisfy the threat model. Architecture-compatible for future upgrade. |
| **APIM Standard v2** | $250/mo for one LLM provider with one policy bundle. Owned FastAPI gateway is 300 LOC and free under Container Apps consumption. |
| **Microsoft Sentinel as primary SIEM (v1)** | $15+/mo Sentinel surcharge + ops triage burden, unjustified at v1 scale. Log Analytics + WORM blob satisfies §164.312(b). |
| **6 managed identities + 3 Key Vaults** | Three identities (etl, agent, admin) and one Key Vault with RBAC scoping is sufficient for the threat model and simpler to audit. |
| **Drata / Vanta (v1)** | $7.5K+/yr for a HIPAA-only posture. Wire in when SOC 2 pursuit begins. |
| **Three spokes** | Doubles east-west firewall load and adds peering charges. NSG segmentation in one spoke is sufficient. |
| **Per-service private endpoints across the board** | $7/mo each. Only SQL needs PE; FortiGate + service endpoints + service firewalls suffice for the rest. |
| **Standard_B2s_v2 for FortiGate** | Burstable CPU credit can throttle the packet path. F2s_v2 is $2/mo more for guaranteed perf. |
| **Anthropic Batch API / Files API / Code Execution / Computer Use / Web Fetch** | Not BAA-covered. Same as v1 research — unchanged. |
| **Public network access on any data-plane service** | `publicNetworkAccess = Disabled` on SQL, Key Vault, Storage. FortiGate is the *only* path to the public internet. |

---

## Decisions for Roadmap Consumption

1. **Azure SQL SKU:** Serverless GP, Gen5, 0.5–2 vCore auto-pause, 32 GB, ~$50/mo.
2. **FortiGate VM SKU:** Standard_F2s_v2, BYOL FGT-VM02, single instance v1, ~$62/mo VM compute.
3. **Managed identity count:** 3 (etl, agent, admin).
4. **Key Vault count:** 1 (RBAC-scoped per key/secret).
5. **Service endpoint vs PE:** PE for SQL only; service endpoints for Key Vault + Storage + ACR.
6. **Gateway middleware stack:** FastAPI + Entra JWT + token bucket + Presidio (in/out) + canary scan + Anthropic SDK + Pydantic structured-output validation + chain-hash audit emit (LA + WORM).
7. **Total v1 cost:** $166/mo with $34/mo headroom under $200 ceiling.
8. **PROJECT.md updates needed:**
   - ENC-01: revise from "Always Encrypted on RESTRICTED columns" to TDE-only with column-encryption deferred and architecture-compatible.
   - AUDIT-01: revise "mirrored to Azure Sentinel" to "mirrored to Azure Storage WORM and Log Analytics; Sentinel deferred."
   - COMP-02: SOC 2 controls platform (Drata/Vanta) explicitly deferred until SOC 2 pursuit decision.

---

## Sources

**Authoritative — HIGH confidence:**
- [Pricing - Azure SQL Database Single Database](https://azure.microsoft.com/en-us/pricing/details/azure-sql-database/single/) — Serverless $0.5218/vCore-hr, GP storage $0.115/GB.
- [Serverless compute tier - Azure SQL Database](https://learn.microsoft.com/en-us/azure/azure-sql/database/serverless-tier-overview) — auto-pause semantics, ~1 min resume latency, 20–40 sec first-query warmup.
- [Transparent Data Encryption for Azure SQL Database](https://learn.microsoft.com/en-us/azure/azure-sql/database/transparent-data-encryption-tde-overview) — TDE on by default, AES-256.
- [FortiGate VM on Microsoft Azure Data Sheet](https://www.fortinet.com/content/dam/fortinet/assets/data-sheets/FortiGate_VM_Azure.pdf) — FGT-VM02 throughput 15 Gbps, default Azure SKU F2s_v2.
- [Instance type support — FortiGate Public Cloud 7.6.0](https://docs.fortinet.com/document/fortigate-public-cloud/7.6.0/azure-administration-guide/562841/instance-type-support) — Azure SKU compatibility matrix.
- [Standard_F2s_v2 specs and pricing](https://cloudprice.net/vm/Standard_F2s_v2) — ~$62/mo Linux PAYG East US.
- [Standard_B2s_v2 specs and pricing](https://instances.vantage.sh/azure/vm/b2s-v2) — ~$60/mo, but burstable.
- [Pricing - Azure Monitor](https://azure.microsoft.com/en-us/pricing/details/monitor/) — LA Analytics $2.30/GB after 5 GB free, retention $0.10/GB/mo beyond 31 days.
- [Azure Blob Storage pricing](https://azure.microsoft.com/en-us/pricing/details/storage/blobs/) — Cool tier $0.01/GB/mo.
- [Overview of immutable storage for blob data](https://learn.microsoft.com/en-us/azure/storage/blobs/immutable-storage-overview) — container-level WORM, time-based retention up to 400 years, Cohasset SEC 17a-4(f) validation.
- [Pricing - Azure Container Apps](https://azure.microsoft.com/en-us/pricing/details/container-apps/) — 180K vCPU-s + 360K GiB-s + 2M req free grant per subscription per month.
- [Virtual network service endpoints for Azure Key Vault](https://learn.microsoft.com/en-us/azure/key-vault/general/overview-vnet-service-endpoints) — service endpoint architecture, no per-hour cost.
- [Integrate Key Vault with Azure Private Link](https://learn.microsoft.com/en-us/azure/key-vault/general/private-link-service) — PE option ~$7/mo.
- [Plan costs and understand pricing — Microsoft Sentinel](https://learn.microsoft.com/en-us/azure/sentinel/billing) — Sentinel surcharge $5.20/GB on top of LA ingestion.
- [HIPAA / HITECH Act Implementation Guidance — Microsoft Compliance](https://learn.microsoft.com/en-us/compliance/regulatory/offering-hipaa-hitech) — Microsoft BAA covers all listed Azure services.

**Regulatory — HIGH confidence:**
- [eCFR 45 CFR § 164.312 — Technical safeguards](https://www.ecfr.gov/current/title-45/subtitle-A/subchapter-C/part-164/subpart-C/section-164.312) — primary HIPAA Security Rule text.
- [HIPAA 164.312(a)(2)(iv) — Encryption and Decryption (Tenable)](https://www.tenable.com/audits/items/HIPAA_MS_OS.audit:0693dc6eafdb883eaca69db8f9bbce17) — addressable, not required; TDE-class encryption satisfies.
- [HIPAA 164.312(b) — Audit Controls (AlertLogic)](https://docs.alertlogic.com/analyze/reports/compliance/HIPAA-164.312-audit-controls.htm) — required audit field set.
- [HIPAA Technical Safeguards List 164.312 (Accountable)](https://www.accountablehq.com/post/hipaa-technical-safeguards-list-164-312-quick-reference-checklist-for-access-audit-integrity-authentication-amp-transmission-security) — checklist mapping.

**MEDIUM confidence — verify at procurement:**
- Defender for SQL ($15) and Defender for Storage ($10) — list pricing, verify in Azure pricing calculator at deployment time.
- Container Apps actual consumption above free grant — measure at v1 deployment; estimate is conservative.
- Azure Bastion Developer SKU pricing — newer SKU, pricing model evolving.

---

*Stack research (revised, cost-simplified) for: Barycenter MSP data platform*
*Researched: 2026-05-02*
*Total v1 monthly cost: $166 / $200 ceiling*
