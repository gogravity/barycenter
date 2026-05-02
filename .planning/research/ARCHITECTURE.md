# Architecture Research (Revised — Cost-Simplified, FortiGate Hub-and-Spoke)

**Domain:** MSP operations data platform with strong AI-safety boundary (Azure SQL two-zone, agent-consumed)
**Researched:** 2026-05-01 (revised from initial design)
**Confidence:** HIGH on structural decisions; MEDIUM on FortiGate sizing (depends on real throughput) and gateway LOC estimate
**Budget target:** under $200/mo total Azure spend including FortiGate BYOL VM compute

---

## Why This Revision

The initial architecture was over-engineered for Gravity's actual scale (2–5 employees, ~50 customers, internal tool). This revision keeps **all five layers of defense intact** while collapsing components, identities, and Azure SKUs to fit a small-MSP budget. The substantive changes:

| Original | Revised | Reason |
|----------|---------|--------|
| Private Endpoints + NSG-only egress | **FortiGate NVA in hub VNet, all traffic UDR'd through it** | Single perimeter device gives IDS/IPS, outbound allowlisting, and inter-subnet inspection — replaces several Azure-native controls with one license already familiar to MSP staff |
| Always Encrypted + Secure Enclaves on RESTRICTED columns | **TDE + schema permissions + AE deterministic where joins required** | Enclave-capable SKUs (DC-series) are expensive and add operational burden. TDE + schema-grant isolation is the load-bearing control; AE is supplemental |
| Azure API Management fronting Anthropic | **Owned FastAPI gateway (~200–400 LOC)** | APIM at ~$0.07/hr = $50/mo minimum and policy XML is the wrong shape for cryptographic audit + canary detection |
| Microsoft Sentinel as primary SIEM | **Log Analytics workspace (90-day hot) + WORM blob (6-yr retention)** | Sentinel is ~$2/GB ingestion plus per-node fees; LAW alone is ~$2.30/GB and gives query without the SIEM premium |
| 6 managed identities | **3–4 managed identities** | Smaller blast-radius surface to reason about; identities consolidated by trust class, not by component |
| Drata/Vanta connector | **Out — manual evidence collection in `compliance/` until SOC 2 pursuit begins** | $5–15k/yr is dead weight pre-SOC-2 |
| Salt service as separate Container App | **Salt fetch inside ETL worker (Key Vault reference, never cached)** | At 50 customers + bulk syncs, the network hop and dedicated identity buy little; Key Vault access policy + audit is the chokepoint |
| Container Apps always-on | **Container Apps Consumption plan, scale-to-zero** | Idle services cost $0; cold-start latency irrelevant for ETL and acceptable for gateway |

The five layers (schema permissions → AI-safe views → typed functions → gateway scrubbing → per-prompt audit) **all still hold** — they are mapped explicitly in the [Defense-Layer Map](#defense-layer-map) section.

---

## 1. Hub-and-Spoke VNet Topology

### Topology

```
                          Internet
                              │
                              ▼
            ┌──────────────────────────────────┐
            │   HUB VNet  (10.10.0.0/22)       │
            │                                  │
            │   ┌──────────────────────────┐   │
            │   │ FortiGate NVA            │   │
            │   │ (BYOL, single VM-Series) │   │
            │   │   trust-nic: 10.10.1.4   │   │
            │   │   untrust-nic: 10.10.0.4 │   │
            │   │   mgmt-nic:  10.10.2.4   │   │
            │   └──────────────────────────┘   │
            │   AzureFirewallSubnet-equiv:     │
            │     untrust  10.10.0.0/27        │
            │     trust    10.10.1.0/27        │
            │     mgmt     10.10.2.0/27        │
            └────────────────┬─────────────────┘
                             │ VNet Peering (use-remote-gateways=false,
                             │  allow-forwarded-traffic=true)
                             ▼
            ┌──────────────────────────────────┐
            │  SPOKE VNet (10.20.0.0/22)       │
            │  Barycenter                      │
            │                                  │
            │   etl-subnet     10.20.0.0/26    │  Container Apps env A (ETL jobs)
            │   services-sub   10.20.0.64/26   │  Container Apps env B (gateway, dispatcher)
            │   data-subnet    10.20.0.128/27  │  Azure SQL Private Endpoint NIC
            │   pe-subnet      10.20.0.160/27  │  Other Private Endpoints (KV, Storage, SB)
            │   admin-subnet   10.20.1.0/27    │  PIM JIT bastion / break-glass jump
            │                                  │
            │  All subnets carry UDR forcing   │
            │  0.0.0.0/0 → 10.10.1.4           │
            │  (FortiGate trust NIC)           │
            └──────────────────────────────────┘
```

### Subnets (Spoke)

| Subnet | CIDR | What runs here | Why isolated |
|--------|------|----------------|--------------|
| `etl-subnet` | 10.20.0.0/26 (64 IPs) | Container Apps environment A: adapter Jobs, AI-zone builder Job, pseudonymizer | ETL identity has CRUD on raw_*; isolation prevents lateral movement to gateway |
| `services-subnet` | 10.20.0.64/26 (64 IPs) | Container Apps environment B: AI gateway, action dispatcher, typed-function service | Platform identity here can reach Anthropic; ETL must not |
| `data-subnet` | 10.20.0.128/27 (32 IPs) | Azure SQL Private Endpoint NIC | Smallest possible blast radius; only PE traffic |
| `pe-subnet` | 10.20.0.160/27 (32 IPs) | Private Endpoints for Key Vault, Storage (WORM), Service Bus | Same isolation rationale |
| `admin-subnet` | 10.20.1.0/27 (32 IPs) | Azure Bastion (Developer SKU) for PIM JIT human access | Human break-glass path stays separate from any service path |

Container Apps requires a **delegated subnet** (the env's "infrastructure subnet"); each Container Apps environment burns one /23 minimum on Workload Profiles or a /27 on Consumption-only. **Use Consumption-only** for both environments to fit /26 each. (Workload Profiles dedicated plan is ~$70/mo per environment — too expensive.)

### FortiGate Routing & UDRs

**Hub side:**
- FortiGate has three NICs: `untrust` (Internet-facing public IP), `trust` (toward spokes), `mgmt` (RDP/HTTPS to admin only).
- A `RouteTable-Hub-to-Spoke` is associated with the `trust` subnet pushing 10.20.0.0/22 → next-hop = (no override; in-VNet routing handles peered destinations).
- IP forwarding **must be enabled** on the FortiGate trust NIC (Azure NIC property + FortiOS config).

**Spoke side — UDR `RouteTable-Spoke-Forced-Tunnel` attached to every subnet except `data-subnet` and `pe-subnet`:**

| Address Prefix | Next Hop Type | Next Hop Address | Purpose |
|----------------|---------------|------------------|---------|
| `0.0.0.0/0` | Virtual Appliance | 10.10.1.4 | Force ALL outbound through FortiGate |
| `10.20.0.0/22` | VNet | — | Keep intra-spoke local (no FW hairpin needed for SQL PE traffic if same VNet) |
| `10.10.0.0/22` | VNet Peering | — | Hub-direct (FortiGate management) |

**Important nuance for `data-subnet` and `pe-subnet`:** Private Endpoint NICs do **not** honor UDRs by default for PE-targeted traffic, and forcing PE traffic through an NVA breaks DNS/cert validation in some configurations. Best practice: **leave PE subnets without 0/0 UDR**; their only inbound is from the spoke services anyway, which already came through the FortiGate. Outbound from PEs is irrelevant.

For PE-from-FortiGate inspection: enable **"Network Policies for Private Endpoints"** at the subnet level if you want NSG enforcement on PE traffic; do **not** UDR PE traffic out to the FortiGate (recursion risk).

**Inter-subnet traffic between `etl-subnet` and `services-subnet`:** Currently routes locally (same VNet). To force it through FortiGate for inspection, add a UDR: `10.20.0.64/26 → 10.10.1.4` on etl-subnet, and the symmetric reverse. This is the **subnet isolation** layer — it makes "ETL identity reaches gateway" a FortiGate-visible event. **Recommended: enable.** Cost is one extra hop (~1ms); benefit is full inter-subnet visibility.

### FortiGate Policies (illustrative)

| # | Src | Dst | Service | Action | Note |
|---|-----|-----|---------|--------|------|
| 1 | etl-subnet | api.connectwisedev.com, api.pax8.com, graph.microsoft.com (FQDN objects) | HTTPS | ALLOW + IPS | Source-tool egress allowlist |
| 2 | services-subnet | api.anthropic.com | HTTPS | ALLOW + IPS | LLM egress (only services subnet) |
| 3 | etl-subnet | api.anthropic.com | any | DENY + LOG | ETL must never reach LLM |
| 4 | services-subnet | source-tool FQDNs | any | DENY + LOG | Gateway must never reach source tools directly |
| 5 | any | Internet (catch-all) | any | DENY + LOG | Default deny |
| 6 | etl-subnet | services-subnet | HTTPS | ALLOW (only specific inter-service paths) | Granular inter-subnet |
| 7 | admin-subnet | any | restricted set | ALLOW + LOG | Break-glass |

### Cost — VNet/FortiGate

| Item | SKU | $/mo |
|------|-----|------|
| FortiGate VM | Standard_F2s_v2 (2 vCPU, 4 GB) BYOL | ~$60 (Linux compute pricing; license already owned) |
| FortiGate public IP | Standard, static | ~$4 |
| VNet peering | hub↔spoke, 1 GB/mo egress | ~$1 |
| Bastion Developer | per-session | ~$0–7 (free tier covers light use) |
| **Subtotal** | | **~$65–72/mo** |

If F2s_v2 throughput becomes the bottleneck, F4s_v2 is ~$120/mo — still inside budget with other savings.

---

## 2. Azure SQL Placement & Cost

### Recommended: Private Endpoint in `data-subnet`

**Why Private Endpoint over VNet service endpoint:**
- VNet service endpoints route to the public SQL endpoint over Microsoft backbone — DNS still resolves to a public IP, SQL firewall rules allow the VNet, but the data path is "Microsoft network" not "your VNet." NIST/HIPAA auditors increasingly want **truly private** data paths.
- Private Endpoint puts a NIC in your VNet with a private IP; SQL becomes addressable only via that IP. Public network access can be **disabled entirely** on the SQL server (`publicNetworkAccess = Disabled`).
- **HIPAA technically does not mandate Private Endpoint** — the Security Rule is technology-neutral. But the global instruction in CLAUDE.md is explicit: *"Azure SQL: disable public network access; use private endpoint or VNet rule."* Private Endpoint is the cleaner answer because it survives the "is it really not on the internet?" question without further argument.

### Cost — Azure SQL

| SKU | vCore | Storage | $/mo (approximate) | Notes |
|-----|-------|---------|---------|-------|
| **General Purpose Serverless, 1 vCore, auto-pause 1hr** | 0.5–1 (auto) | 32 GB | **~$15–35** | **Recommended.** Auto-pauses overnight, scales to 1 vCore on demand. Adequate for ~50 customers, light query load |
| GP Provisioned, 1 vCore | 1 | 32 GB | ~$185 | No auto-pause; same compute always-on |
| Hyperscale, 1 vCore | 1 | first 100 GB free | ~$220 | Overkill |
| **Always Encrypted with Secure Enclaves (DC-series)** | 2 | — | ~$370+ | **Rejected.** Cost not justified pre-SOC-2 |

**Private Endpoint cost:** ~$7.30/mo per PE + small data processing fee. One PE for SQL.

**Encryption posture:**
- TDE: on by default, free.
- Always Encrypted (deterministic) on the `email_encrypted` column in raw zone — required so ETL can decrypt for pseudonymization but DBAs cannot. Free; no enclave required for deterministic AE on equality-only.
- AE on other RESTRICTED columns: optional; schema permissions are the load-bearing control.
- Schema grants are how RESTRICTED data is gated: `etl-identity` has CRUD on `raw_*`, `platform-identity` has **zero** grant on `raw_*`. This is the architectural moat.

### Subtotal (data tier): ~$23–43/mo (SQL + PE)

---

## 3. Simplified Identity Plane (3–4 Managed Identities)

### Proposed Identities

| Identity | Used by (components) | Reads | Writes | Calls | Key Vault access |
|----------|---------------------|-------|--------|-------|------------------|
| **etl-identity** | Adapter Jobs, AI-zone builder Job, pseudonymizer | Source-tool secrets (KV), `raw_*` (R/W), `pseudo.person_map` (R/W) | `raw_*`, `pseudo.person_map`, Service Bus audit topic, audit blob via topic | Source APIs, Salt fetch from KV (ephemeral) | `api-vault` (per-tool secrets, GET), `salt-vault` (per-tenant salts, GET) |
| **platform-identity** | AI gateway, typed-function service, action dispatcher | `ai_zone.*` (SELECT only), narrow grant on `raw_cw.contacts` for dispatcher only | Service Bus action queue, audit topic | Anthropic API (gateway only), Graph mail / SMTP (dispatcher only) | `api-vault` (Anthropic key, GET) |
| **audit-identity** | Audit-writer Function | Service Bus audit topic (Receive) | WORM blob (Append-only), Log Analytics ingestion API | — | none (no secrets) |
| **admin-identity** (PIM JIT) | Human break-glass via Bastion | `raw_*` (full), `pseudo.*`, ai_zone.*, KV management | All (during JIT window) | All | All vaults (during JIT) |

Total = **4 identities**. Down from 6 (etl, salt, tool, gateway, dispatcher, audit-writer).

### Consolidations Made

- **salt-identity → folded into etl-identity**: salts are fetched directly from `salt-vault` by ETL workers. Justified in §4.
- **tool, gateway, dispatcher → platform-identity**: all three are the "agent-serving" trust class. None of them touch raw_*  except dispatcher's narrow `raw_cw.contacts` grant. They share an outbound trust profile (can reach Anthropic, can reach SQL via PE, cannot reach source tools).

### Blast-Radius Analysis (Honest)

**If `platform-identity` is compromised:**
- Attacker gets: read of all `ai_zone.*` views (pseudonymized data only — no email, no PII per architectural commitment), read of `raw_cw.contacts` (recipient resolution — contains names + emails of customer contacts), Anthropic API key (gateway can call Anthropic), Service Bus send to action queue (can emit fake actions).
- Attacker does NOT get: `raw_*` outside contacts, salts (in `salt-vault`, which etl-identity holds), audit log mutation (audit-identity is the only writer), ability to issue new pseudonyms, source-tool credentials.
- **Realistic damage:** can drain Anthropic budget; can read ai_zone (pseudonymized; bounded leak); can read customer contact emails (real PII — this is the worst part); can emit fake renewal emails to real customers. Cannot exfiltrate raw PHI/PII at scale because raw schemas are not granted.
- **Mitigation:** dispatcher's `raw_cw.contacts` grant is the single weak point of consolidation. Treat it as: the dispatcher should be a separate Container App with its own *application-level* authentication (signed action envelopes from the gateway) so attacker who pwns the gateway container cannot directly query contacts — they must produce a valid signed action. This is **app-layer separation, not identity-layer separation** — cheaper and tractable.

**If `etl-identity` is compromised:**
- Attacker gets: source-tool API keys (can re-pull data from source — but source data is what they'd be exfiltrating from raw_* anyway), salts (can re-derive person_pid from any email — significant), `raw_*` write (can poison data, can write spoofed records), `pseudo.person_map` write.
- Attacker does NOT get: ai_zone reads (no SELECT grant on ai_zone), Anthropic API, action emission.
- **Realistic damage:** worst case. Salts are the crown jewel. Compromise = pseudonymization is reversible for any tenant whose salt was accessed.
- **Mitigation:** etl-identity reads salts from KV with a logged GET. Every salt access is in KV diagnostic logs (forwarded to LAW + WORM). The compromised attacker leaves a perfect audit trail of which tenants they touched. **This is acceptable for the threat model** — Gravity is not protecting against APT; it is protecting against accidental leak, malicious insider, and prompt injection.
- **Tradeoff acknowledged:** the salt service in the original design gave a separate identity boundary. The simplified design says: KV access policies, KV diagnostic logging, and the small attack surface of an internal ETL worker are sufficient when the budget is $200/mo.

**Verdict on consolidation:** safe given the threat model and the documented compensating control (signed action envelopes between gateway and dispatcher; KV audit logging of every salt fetch).

---

## 4. Salt Handling — Inline in ETL, No Dedicated Service

### Decision: ETL fetches salt from Key Vault per-sync, computes HMAC inline, never caches

### Concrete pattern

```python
# Inside the pseudonymizer step, called once per (tenant, batch)
async def pseudonymize_emails(tenant_id: UUID, emails: list[str]) -> dict[str, str]:
    # Fetch salt for this tenant — KV access logged
    secret_name = f"salt-{tenant_id}"
    salt = await kv_client.get_secret(secret_name)  # ephemeral; never assigned to module-level var

    pids = {
        email_lower: hmac_sha256(salt.value, email_lower.encode()).hexdigest()
        for email_lower in (e.lower().strip() for e in emails)
    }
    # salt goes out of scope at function exit; del explicitly for clarity
    del salt
    return pids
```

### HIPAA Risk Assessment

- **What we lose vs separate salt service:** no dedicated identity boundary, no separate VNet-enforced reachability check, no choke-point audit beyond KV's own diagnostic log.
- **What we keep:** salt material is in Key Vault (HSM-backed at the Standard tier; one-way; access requires the etl-identity managed-identity token); every fetch is logged in KV diagnostic logs (forwarded to LAW); etl-identity has no SELECT grant on `ai_zone.*` and cannot directly reverse pseudonyms it has materialized (it writes `(tenant, email_hash, pid)` to pseudo.person_map and email itself stays in raw zone Always Encrypted).
- **HIPAA framing:** HIPAA Security Rule §164.312(a)(2)(iv) requires encryption "where reasonable and appropriate." Salts in KV with managed-identity-only access, audit logging, and no caching is **reasonable and appropriate** at this scale. There is no HIPAA requirement for a separate microservice — it is a defense-in-depth pattern, not a regulatory mandate.
- **Re-evaluate when:** customer count > 200, OR a customer specifically demands separation of duty for cryptographic material, OR Gravity pursues SOC 2 Type II and the auditor flags it.

### What this saves

- 1 Container App (no idle compute, no scale-out cost).
- 1 managed identity.
- 1 internal HTTPS hop per pseudonymization.
- Maintenance of a 200-LOC microservice + its CI/CD pipeline.

---

## 5. Owned AI Gateway — Concrete Design

### Tech: FastAPI (Python) on Container Apps Consumption

Estimated size: **200–400 LOC** for the core handler + middleware. Python because Presidio is Python-native; FastAPI for the typed request/response models.

### Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/v1/messages` | Anthropic-compatible passthrough (mimics Anthropic's Messages API for downstream agent ergonomics) |
| `GET` | `/health` | Liveness + readiness (KV reachable, SQL reachable, Anthropic reachable) |
| `GET` | `/budget/{tenant_id}` | Optional: agent introspects remaining token budget |

The gateway exposes the **Anthropic Messages API shape** so agent code can target `https://gateway.barycenter.internal/v1/messages` instead of `https://api.anthropic.com/v1/messages` with no other change. This makes swapping in/out trivial for testing and avoids inventing a bespoke contract.

### Middleware Pipeline (request → response)

```
[Inbound POST /v1/messages from agent runtime]
   │
   ▼
1. AUTH: validate caller managed-identity token (JWT) → extract tenant_id, agent_id from claims
   │
   ▼
2. RATE-LIMIT / BUDGET CHECK:
   - SELECT remaining_tokens FROM ai_zone.tenant_token_budget WHERE tenant_id=? AND date=today
   - If < estimate(prompt_tokens), 429 with Retry-After
   │
   ▼
3. INPUT PRESIDIO SCAN:
   - Run Presidio analyzer against full prompt body
   - Detected entities (PHONE, EMAIL, US_SSN, custom CW_COMPANY_NAME, etc.) → score
   - If score > threshold for category → BLOCK (return 400, audit a "blocked_input" event)
   - Below threshold → allow but tag the event
   │
   ▼
4. CANARY-TOKEN CHECK (input):
   - Compare prompt against canary list (synthetic-marker strings loaded into raw zone for VER-01)
   - If prompt contains a canary → BLOCK + HIGH-SEVERITY audit event ("canary_in_input" — should be impossible by design; indicates raw-zone leak upstream)
   │
   ▼
5. UPSTREAM CALL:
   - HTTP POST to PINNED Anthropic endpoint (https://api.anthropic.com/v1/messages)
   - PINNED model version (claude-sonnet-4-5-20250929 or whatever is current; never "latest")
   - Stream OFF for v1 (simpler audit; revisit if latency demands streaming)
   - Anthropic API key from KV (see §Secrets)
   │
   ▼
6. OUTPUT PRESIDIO SCAN:
   - Run analyzer over completion text
   - PHI/PII detected → REDACT or BLOCK depending on entity class
   │
   ▼
7. CANARY-TOKEN CHECK (output):
   - If completion contains a canary → CRITICAL audit event ("canary_in_output" — five layers failed, full alert)
   - Block the response; return 502 to agent with sanitized error
   │
   ▼
8. AUDIT EMIT (async, non-blocking):
   - Send to Service Bus audit topic; do NOT block response on success
   - If Service Bus is down: write to local /tmp queue file + critical metric; gateway continues but health check goes amber
   │
   ▼
9. RESPONSE: return completion (or filtered/blocked stub) to agent
```

### Why this order

- **Auth first:** zero-trust; never run expensive scans on unauthenticated traffic.
- **Budget before scan:** scanning costs CPU; budget rejection is cheap.
- **Input scan before upstream call:** the cheapest, highest-leverage scrub. Stops obvious injection attempts before they reach the LLM.
- **Canary check after Presidio:** Presidio's regex/ML runs are fast; canary check is a string-membership test. Order is cosmetic but Presidio result feeds into the audit event so it goes first.
- **Upstream call BEFORE output scans:** obvious — must have output to scan.
- **Output Presidio THEN output canary:** Presidio identifies entity classes (broad); canary identifies specific known markers (narrow). Both required; either alone is insufficient.
- **Audit emit LAST and ASYNC:** never block the user-facing response on audit-system health. Service Bus topic absorbs back-pressure; audit-writer Function drains independently.

### Audit Emit Payload (HIPAA-relevant fields)

```json
{
  "event_id": "uuid-v7",
  "event_type": "llm_completion",
  "schema_version": "1",
  "occurred_at": "2026-05-02T14:33:21.123Z",
  "tenant_id": "uuid",
  "agent_id": "agent-renewal-mgr",
  "caller_managed_identity": "platform-identity",
  "request": {
    "prompt_sha256": "hex...",
    "prompt_tokens": 1234,
    "tools_offered": ["get_customer_snapshot", "list_renewals_due", "emit_action"],
    "input_presidio_findings": [{"entity": "EMAIL", "score": 0.43, "redacted": false}],
    "input_canary_hit": false
  },
  "model": {
    "provider": "anthropic",
    "model_id": "claude-sonnet-4-5-20250929",
    "endpoint": "https://api.anthropic.com/v1/messages"
  },
  "response": {
    "completion_sha256": "hex...",
    "completion_tokens": 567,
    "tools_called": [{"name": "get_customer_snapshot", "params_sha256": "hex...", "rows_returned": 1}],
    "output_presidio_findings": [],
    "output_canary_hit": false,
    "blocked": false,
    "block_reason": null
  },
  "budget": {
    "tokens_consumed": 1801,
    "tokens_remaining_today": 48199
  },
  "chain": {
    "prior_event_sha256": "hex...",
    "this_event_sha256": "hex..."
  }
}
```

**Why these fields:**
- `tenant_id` — required for HIPAA accounting of disclosures (164.528).
- `prompt_sha256` / `completion_sha256` — store hashes, not content, in the searchable Log Analytics table; full content goes to WORM blob only. (Reduces LAW ingestion cost; preserves forensic completeness in WORM.)
- `caller_managed_identity` + `agent_id` — who initiated.
- `tools_called[].params_sha256` + `rows_returned` — chain-of-custody for what data was accessed via tool functions.
- `input/output_canary_hit` — VER-01 detection signal, queryable in LAW.
- `chain.prior_event_sha256` — cryptographic chaining; tampering with the WORM blob breaks the chain mathematically.

### Anthropic API Key Storage

- Stored in Azure Key Vault `api-vault` as secret `anthropic-api-key`.
- Gateway container env spec uses **Key Vault reference**, not literal value:
  ```yaml
  secrets:
    - name: anthropic-api-key
      keyVaultUrl: https://api-vault.vault.azure.net/secrets/anthropic-api-key
      identity: system  # platform-identity managed identity
  env:
    - name: ANTHROPIC_API_KEY
      secretRef: anthropic-api-key
  ```
- Container Apps re-resolves the KV reference on revision creation. Rotation = update KV secret + bump revision.
- **Never** in env-var literal, never in image, never in Git.

---

## 6. Component List (Simplified — 6 Components)

| # | Component | Hosted on | Identity | Reads | Writes | Calls |
|---|-----------|-----------|----------|-------|--------|-------|
| 1 | **Adapter Jobs** (one config per source tool, shared base image) | Container Apps **Job**, Consumption, scheduled cron | etl-identity | `api-vault` (source secrets), `salt-vault` (salts at sync), `raw_*` (R for delta cursors) | `raw_*`, `pseudo.person_map`, audit topic | source-tool APIs (via FortiGate egress allow) |
| 2 | **AI-Zone Builder** (single job; runs all `etl.builders.*` stored procs on schedule) | Container Apps **Job**, Consumption, cron every 15 min | etl-identity | `raw_*`, `pseudo.*` | `ai_zone.*` (refreshed tables only — indexed views are auto), audit topic | SQL stored procs only |
| 3 | **Typed-Function Service** (FastAPI; ~300 LOC; exposes `get_customer_snapshot`, `list_renewals_due`, `emit_action`, etc.) | Container App, Consumption, scale-to-zero | platform-identity | `ai_zone.*` (SELECT) | Service Bus action queue (for emit_action), audit topic | SQL (via PE) |
| 4 | **AI Gateway** (FastAPI; ~300 LOC; LLM proxy with Presidio + canary + budget + audit) | Container App, Consumption, scale-to-zero | platform-identity | `api-vault` (Anthropic key), `ai_zone.tenant_token_budget` | audit topic | Anthropic (via FortiGate egress allow), typed-function service (for tool calls) |
| 5 | **Action Dispatcher** (Python; ~200 LOC; consumes action queue, resolves recipients, sends) | Container App, Consumption, KEDA-scaled on Service Bus | platform-identity | `raw_cw.contacts` (narrow grant for recipient resolution), Service Bus action queue | audit topic, sent message log | Microsoft Graph mail (or SMTP) — via FortiGate allow |
| 6 | **Audit Writer** (Azure Function, Python; consumes audit topic, chains, writes WORM + LAW) | Azure Functions, Consumption (Service Bus trigger) | audit-identity | Service Bus audit topic (Receive) | WORM blob (append), Log Analytics workspace | none |

**Cross-cutting infra (not "components" but listed for completeness):**
- Azure SQL DB (GP Serverless 1 vCore)
- Azure Key Vault (single vault, three logical secret prefixes: `salt-*`, `cmk-*`, `api-*`) — collapsed from three vaults to one to save on PE costs; access control via secret-name-prefix on the access policy
- Azure Service Bus (Basic tier: audit topic + action queue)
- Storage Account (WORM container with immutability policy, 6-yr retention for HIPAA-tagged days)
- Log Analytics workspace (90-day retention, Pay-As-You-Go)
- FortiGate VM (hub VNet)
- Bastion (admin access)

### Cost Roll-Up

| Item | $/mo |
|------|------|
| FortiGate VM + public IP | ~$65 |
| Azure SQL GP Serverless 1 vCore (auto-pause, 32 GB) | ~$25 |
| SQL Private Endpoint | ~$8 |
| Container Apps Consumption (6 components, mostly idle) | ~$15 |
| Azure Functions Consumption (audit writer) | ~$2 |
| Service Bus Basic | ~$0.05/M msgs — ~$1 |
| Key Vault Standard + 3 PEs collapsed to 1 | ~$8 |
| Storage WORM + Storage PE | ~$5 |
| Log Analytics (90-day, ~5 GB/mo) | ~$12 |
| Bastion Developer | ~$0–7 |
| VNet peering, DNS zones, public IPs | ~$5 |
| **Total** | **~$146–153/mo** |

Headroom: ~$45–55/mo for unexpected ingestion spikes, FortiGate scale-up to F4s_v2 if needed, or future Sentinel add-on.

---

## 7. Build Order (4 Phases)

### Phase 1 — Network + Data Foundations (must exist before any data flows)

1. Hub VNet + FortiGate VM deployed; UDRs in place; baseline policies (default deny + management).
2. Spoke VNet with all five subnets; peering established; UDRs forcing 0/0 through FortiGate.
3. Azure SQL GP Serverless provisioned; Private Endpoint in `data-subnet`; public network access disabled.
4. Schemas created: `raw_cw`, `raw_pax8`, `raw_graph` (placeholder), `ai_zone`, `pseudo`. Schema-level grants applied (etl-identity CRUD on raw_*; platform-identity SELECT on ai_zone only; etc.).
5. Single Key Vault provisioned with PE; access policies for etl-identity (salt-* + api-*), platform-identity (api-anthropic only), admin-identity (all, JIT).
6. Storage account + WORM container with immutability policy (test with a 1-day retention first; lock to 6-yr only after policy validated).
7. Log Analytics workspace; diagnostic settings on KV, SQL, Container Apps, FortiGate → LAW.
8. Service Bus namespace + audit topic + action queue.
9. Field-class registry committed to repo (`compliance/field-class-registry.yaml`); CI gate enforced.
10. Audit Writer Function deployed and tested with synthetic events (chain integrity verified end-to-end).

**Lock-early decisions (irreversible without rework):** schema-per-tool, single SQL DB, schema-isolation grants, audit chain format, identity topology (4 identities), WORM retention period.

### Phase 2 — Tool Onboarding Framework + First Tool

11. Eight T-SQL transformation primitives implemented and tested.
12. Adapter base image (Python) with hooks: `fetch_page`, `to_staging_row`, `delta_cursor`. Pseudonymizer step inline in base.
13. ConnectWise adapter (tool #1 — issues cw_company_id, the root identifier). Field map and ETL recipe in `adapters/connectwise/`.
14. AI-Zone Builder Job with first two shapes: `customer_snapshot` (indexed view) and `timeseries_aggregate` (refreshed table).
15. End-to-end smoke test: synthetic CW data → raw_cw → ai_zone.customer_snapshot. No agent yet.

**Lock-early:** the eight primitives, the four AI-zone shapes, the adapter base contract, the cursor convention.

### Phase 3 — Agent-Safe Access Layer (the five layers all turn on)

16. Typed-Function Service deployed; first three functions (`get_customer_snapshot`, `list_renewals_due`, `emit_action`); RLS predicates active; platform-identity grants validated.
17. Action Dispatcher deployed; signed-action-envelope contract between Typed-Function Service and Dispatcher (app-layer separation since they share platform-identity).
18. AI Gateway deployed with Presidio, canary list, budget enforcement, audit emission. Initial canary list seeded with synthetic markers.
19. Per-tenant per-class opt-out enforced at gateway and tool functions.
20. **VER-01 leak test** wired into CI: synthetic markers in raw_cw → run agent flows → grep audit for marker hits → fail on any hit.
21. Adversarial prompt-injection corpus in CI (COMP-05).

**Lock-early:** typed-function naming, action envelope schema, canary token format, audit payload schema, leak-test marker format.

### Phase 4 — Tools 2–4 + Compliance Posture

22. Pax8 adapter (subscriptions domain).
23. Microsoft Graph adapter (pseudonymization at scale — every M365 user).
24. Email-derived signals adapter (last; hardest correctness — keyword_flags + score on free text).
25. CUI exclusion controls (per-customer flag, sync-time filters, regex CUI marker detection).
26. Customer erasure workflow end-to-end + leak-test re-run after erasure.
27. Subprocessor inventory + DPA template + change-notification workflow.
28. Production sizing review: monthly partitioning on high-volume tables; cold archive to Parquet on Blob after retention thresholds.

**Compliance items deferred to "when we pursue SOC 2":** Drata/Vanta connector, formal evidence collection automation, quarterly access review tooling. Documented and scriptable in `compliance/runbooks/` until then.

---

## 8. ASCII Data Flow Diagrams

### (a) ETL Sync — Source Tool → Raw Zone → AI Zone

```
[Source API e.g. ConnectWise]
       │  HTTPS
       ▼
┌──────────────┐    Adapter scheduled (cron)
│ FortiGate    │    egress policy: etl-subnet → CW FQDN ALLOW
│ (hub)        │    NOT to anthropic, NOT to graph (this adapter)
└──────┬───────┘
       │ inspected, IPS
       ▼
┌──────────────────────────────────────┐
│ etl-subnet (10.20.0.0/26)            │
│  ┌────────────────────────────────┐  │
│  │ Adapter Job (Container App)    │  │
│  │ identity: etl-identity         │  │
│  │ 1. KV GET api-cw-secret        │──┼──► Key Vault (via PE)
│  │ 2. fetch_page() loop           │  │
│  │ 3. KV GET salt-{tenant} for    │──┼──► Key Vault (each tenant batch)
│  │    each tenant in batch        │  │
│  │ 4. HMAC inline → person_pids   │  │
│  │ 5. SQL BULK INSERT staging     │──┼──► SQL PE (data-subnet)
│  │ 6. SQL EXEC merge proc         │  │
│  │ 7. SQL UPSERT pseudo.person_map│  │
│  │ 8. Service Bus SEND audit evt  │──┼──► SB (audit topic)
│  └────────────────────────────────┘  │
└──────────────────────────────────────┘
       │
       ▼ (separate scheduled trigger)
┌──────────────────────────────────────┐
│ AI-Zone Builder Job                  │
│ identity: etl-identity               │
│  - SQL EXEC etl.builders.snapshot    │──► SQL PE
│  - SQL EXEC etl.builders.timeseries  │
│  - audit emit                        │──► SB
└──────────────────────────────────────┘

[Audit topic] ──► [Audit Writer Function, audit-identity]
                     │
                     ├──► WORM blob (append, chained)
                     └──► Log Analytics workspace
```

### (b) Agent Query — Agent → Gateway → Anthropic → Tool Function → SQL

```
[Downstream Agent Runtime]
       │ POST /v1/messages
       ▼
┌──────────────┐
│ FortiGate    │ services-subnet inbound from agent VNet OK; outbound to anthropic.com OK
└──────┬───────┘
       ▼
┌──────────────────────────────────────────────────┐
│ services-subnet (10.20.0.64/26)                  │
│  ┌────────────────────────────────────────────┐  │
│  │ AI Gateway (Container App)                 │  │
│  │ identity: platform-identity                │  │
│  │ 1. AUTH: validate caller MI token          │  │
│  │ 2. BUDGET: SELECT remaining FROM ai_zone   │──┼──► SQL PE
│  │ 3. INPUT Presidio + canary scan            │  │
│  │ 4. POST anthropic /v1/messages             │──┼──► FortiGate ──► api.anthropic.com
│  │    (key from KV ref)                       │  │
│  │ 5. Anthropic returns tool_use:             │  │
│  │    get_customer_snapshot(cw_company_id=X)  │  │
│  │ 6. GET typed-function-svc/customers/X/snap │──┼──┐
│  │ 7. Forward tool_result to Anthropic        │  │  │
│  │ 8. Anthropic returns final completion      │  │  │
│  │ 9. OUTPUT Presidio + canary scan           │  │  │
│  │ 10. SB SEND audit event (async)            │──┼──┼──► SB audit topic
│  │ 11. Return completion to agent             │  │  │
│  └────────────────────────────────────────────┘  │  │
│                                                  │  │
│  ┌────────────────────────────────────────────┐  │  │
│  │ Typed-Function Service (Container App)     │◄─┼──┘
│  │ identity: platform-identity                │  │
│  │ - sp_set_session_context tenant_id         │──┼──► SQL PE
│  │ - SELECT ai_zone.customer_snapshot WHERE   │  │
│  │   RLS predicate filters by tenant claim    │  │
│  │ - return DTO (no email, only person_pid)   │  │
│  │ - SB SEND audit event                      │──┼──► SB
│  └────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────┘
```

### (c) Agent Action Emission — Agent → Tool Function → Dispatcher → Customer

```
[Agent (via Anthropic via Gateway)]
       │ tool_use: emit_action({action, company, role, template, fields})
       ▼
┌────────────────────────────────────────────┐
│ Typed-Function Service                     │
│ identity: platform-identity                │
│ - validate action shape vs schema          │
│ - SIGN action envelope with HMAC(svc-key)  │  ← signed envelope = app-layer
│ - SB SEND signed action to action queue    │    separation between gateway-side
│ - return action_id (no email to agent)     │    and dispatcher-side
└────────────────┬───────────────────────────┘
                 │
                 ▼ (Service Bus action queue)
                 │
┌────────────────▼───────────────────────────┐
│ Action Dispatcher (Container App, KEDA)    │
│ identity: platform-identity                │
│ - VERIFY signature (reject if invalid)     │
│ - SELECT email FROM raw_cw.contacts        │──► SQL PE (narrow grant)
│   WHERE company_id=? AND role=?            │
│ - render template + fields                 │
│ - send via Graph mail / SMTP               │──► FortiGate ──► graph.microsoft.com
│ - SB SEND audit event                      │      (only allowed for services-subnet)
│   {action_id, recipient_hash, sent_at}     │──► SB audit topic
└────────────────────────────────────────────┘

[Decision-reversal path]
- Every action_id has registered reversal contract in compliance/runbooks/
- Audit log retains full trail for HIPAA disclosure accounting
```

---

## Defense-Layer Map

Each of the five layers, mapped to specific simplified-design components.

| # | Layer | Enforced by | Failure mode if breached |
|---|-------|-------------|--------------------------|
| 1 | **SQL schema permissions** | `platform-identity` has zero grants on `raw_*` and `pseudo.*`; `etl-identity` has zero grants on `ai_zone.*`. Enforced in `sql/40-grants/` migrations. | Grant drift — VER-02 CI gate detects; periodic grant audit query |
| 2 | **AI-safe views** | `ai_zone.*` views and refreshed tables — every column tagged in `compliance/ai-zone-view-manifest.yaml`; CI fails if any view exposes a RESTRICTED-tagged source column or unhashed SENSITIVE column | Manifest drift — VER-02; manual review on every view PR |
| 3 | **Typed tool functions** | Typed-Function Service is the *only* path agent can use to read SQL; agents are given `tools=[get_customer_snapshot, list_renewals_due, emit_action]` only. No DAB mutation, no raw query. | Function shape too broad — review every new function for parameter types and return DTOs |
| 4 | **Gateway scrubbing** | AI Gateway: Presidio input + output, canary lists, per-tenant budget, opt-out enforcement, pinned model, pinned endpoint | Bypass = direct call to Anthropic — but FortiGate egress policy denies anthropic.com from any subnet *except* services-subnet, and only the gateway runs there |
| 5 | **Per-prompt audit** | Audit Writer Function: SHA-256 chained, WORM-locked, mirrored to LAW. Every gateway call, every typed function call, every action dispatch emits an audit event | Tampering = chain breaks (mathematically detectable); WORM immutability prevents deletion within retention window |

**The five layers all hold under simplification.** None of them depend on the dropped components (APIM, Sentinel SIEM, dedicated salt service, Drata).

---

## Anti-Patterns Retained from Original (Still Apply)

These remain wrong in the simplified design too — see the prior architecture document's anti-pattern section for full reasoning. Brief restatement:

1. **Shared raw schema with `source_tool` column** — schema-per-tool stays.
2. **Pseudonymization as SQL view function** — even simplified, salt material does not live in SQL. KV-only access.
3. **Agent constructs SQL freely** — typed functions only; no DAB raw query exposure to agents.
4. **APIM policy soup as gateway** — explicitly rejected; owned FastAPI.
5. **LLM-based identity reconciliation** — never; deterministic HMAC only.
6. **AI-zone derived data outside Azure SQL** — single store; revisit only on agent demand for vector recall.
7. **ETL identity reused as admin identity** — admin-identity is PIM-JIT only; etl-identity is service-only.

**New anti-pattern relevant to simplified design:**

8. **Letting `platform-identity` directly query `raw_cw.contacts` from any code path.** The dispatcher needs it; no other component does. Enforce by application-layer signed envelopes, not just SQL grants — because the grant is on the identity and three components share that identity.

---

## Decisions That Must Be Locked Early (Revised)

| Decision | Reversal cost | Lock in phase |
|----------|---------------|---------------|
| Hub-and-spoke topology + FortiGate placement | Multi-week network rework | Phase 1 |
| 4-identity consolidation | Identity changes ripple through grants, RLS, KV access policies | Phase 1 |
| Salt-in-ETL (no salt service) | Refactor to extract salt service is ~1 week; tractable | Phase 1, but reversible |
| Single Key Vault with secret-name-prefix access | Splitting later is straightforward; mostly an audit/clarity loss | Phase 1, reversible |
| Owned FastAPI gateway shape | Replace with vendor product later if needed; audit format compatibility is the hard part | Phase 3 |
| Audit chain format + WORM retention | Cannot retroactively change | Phase 1 |
| Schema-per-tool + 8 primitives + 4 shapes | Tool re-onboarding cost | Phase 2 |
| Signed-action-envelope between gateway-side and dispatcher | Cheap to add; expensive to retrofit if compromise occurs first | Phase 3 |

---

## Quality-Gate Self-Check

- [x] All five defense layers explicitly mapped to specific components ([Defense-Layer Map](#defense-layer-map))
- [x] FortiGate placement and UDR configuration concrete (subnet table + UDR table + policy table)
- [x] Identity consolidation blast-radius analysis honest (worst case: etl-identity compromise = salt access; mitigation: KV diagnostic logging)
- [x] Owned gateway middleware order argued (each step justified; auth-first, budget-cheap, scan-before-LLM, audit-async-last)
- [x] Salt service simplification decision argued with HIPAA risk assessment (reasonable-and-appropriate framing; revisit triggers identified)
- [x] Build order explicit and dependency-correct (4 phases; lock-early decisions called out per phase)
- [x] Total design under $200/mo (rolled up to ~$146–153/mo with ~$50 headroom)

---

## Sources

Carried forward from initial research (still authoritative):

**Azure SQL & Networking (HIGH — Microsoft Learn):**
- https://learn.microsoft.com/en-us/azure/azure-sql/database/private-endpoint-overview
- https://learn.microsoft.com/en-us/azure/azure-sql/database/serverless-tier-overview
- https://learn.microsoft.com/en-us/sql/relational-databases/security/encryption/always-encrypted-database-engine
- https://learn.microsoft.com/en-us/azure/virtual-network/virtual-networks-udr-overview

**Container Apps & Functions (HIGH — Microsoft Learn):**
- https://learn.microsoft.com/en-us/azure/container-apps/networking
- https://learn.microsoft.com/en-us/azure/container-apps/jobs
- https://learn.microsoft.com/en-us/azure/container-apps/manage-secrets

**FortiGate on Azure (MEDIUM — Fortinet docs):**
- https://docs.fortinet.com/document/fortigate-public-cloud/azure-administration-guide
- https://docs.fortinet.com/document/fortigate-public-cloud/sdn-connector-azure

**Storage WORM (HIGH — Microsoft Learn):**
- https://learn.microsoft.com/en-us/azure/storage/blobs/immutable-storage-overview

**Presidio (HIGH — Microsoft):**
- https://microsoft.github.io/presidio/

**Anthropic API + HIPAA (HIGH — vendor):**
- https://www.anthropic.com/legal/baa
- https://docs.anthropic.com/en/api/messages

---
*Architecture (revised, simplified, FortiGate hub-and-spoke) for Barycenter*
*Researched: 2026-05-01; revised 2026-05-02*
