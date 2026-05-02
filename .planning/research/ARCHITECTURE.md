# Architecture Research

**Domain:** MSP operations data platform with strong AI-safety boundary (Azure SQL two-zone, agent-consumed)
**Researched:** 2026-05-01
**Confidence:** HIGH on the load-bearing structural decisions; MEDIUM on AI gateway product selection (build-vs-buy is genuinely open)

---

## Standard Architecture

### System Overview

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                          SOURCE TOOLS (External)                             │
│   ConnectWise │ Pax8 │ MS Graph │ RMM │ SentinelOne │ Backup │ Docs │ ...   │
└─────────────────────────────────┬────────────────────────────────────────────┘
                                  │ HTTPS (egress allowlist + per-tool secret)
                                  ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                  SYNC PLANE  (Azure Container Apps Jobs / VNet)              │
│  ┌─────────────┐ ┌──────────┐ ┌──────────────┐ ┌────────────────────────┐   │
│  │ Scheduler   │→│ Adapter  │→│ Staging Loader│→│ DLQ + Retry Manager    │   │
│  │ (cron jobs) │ │ (per src)│ │ (BULK INSERT) │ │ (Service Bus + alerts) │   │
│  └─────────────┘ └──────────┘ └──────────────┘ └────────────────────────┘   │
│              ETL Managed Identity (zero grants on ai_zone)                   │
└─────────────────────────────────┬────────────────────────────────────────────┘
                                  │ Private Endpoint
                                  ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                       AZURE SQL DATABASE (single instance)                   │
│  ┌────────────────────────────┐  ┌────────────────────────────────────────┐ │
│  │   RAW ZONE (per-tool)      │  │           AI ZONE                      │ │
│  │   raw_cw.*                 │  │           ai_zone.*                    │ │
│  │   raw_pax8.*               │  │   customer_snapshot                    │ │
│  │   raw_graph.*              │  │   customer_features_*                  │ │
│  │   raw_rmm.*                │  │   timeseries_aggregate                 │ │
│  │   ...                      │  │   customer_memory                      │ │
│  │                            │  │   (indexed views OR refreshed tables)  │ │
│  │   Always Encrypted on      │  │                                        │ │
│  │   RESTRICTED columns       │  │   No RESTRICTED. SENSITIVE only via    │ │
│  │                            │  │   pseudonym (person_pid). Field-class  │ │
│  │   Agent identity: 0 grants │  │   composition documented per view.     │ │
│  └────────────────────────────┘  └────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │   PSEUDONYM PLANE (etl-only schema)  pseudo.person_map, pseudo.audit    ││
│  │   Salt service writes here. Agent identity: 0 grants. ETL: write.       ││
│  └─────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────┬────────────────────────────────────────────┘
                                  │ Private Endpoint
                                  ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│         TYPED TOOL FUNCTION LAYER  (Azure Container Apps, internal)          │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │  HTTP API: get_customer_snapshot(cw_company_id) → DTO                  │ │
│  │           list_renewals_due(window_days, tenant_id) → DTO[]            │ │
│  │           emit_action({action, company, recipient_role, template, …})  │ │
│  │  Identity: tool-runtime managed identity (read-only on ai_zone.*)      │ │
│  │  All queries use Data API Builder semantics (RLS + session context)    │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────┬────────────────────────────────────────────┘
                                  │ HTTPS (internal VNet)
                                  ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│              AI GATEWAY  (Azure Container Apps, internal)                    │
│  ┌─────────┐ ┌────────┐ ┌──────────┐ ┌───────────┐ ┌──────────────────────┐ │
│  │ Input   │→│ Token  │→│ Anthropic│→│ Output    │→│ Audit Writer         │ │
│  │ scrub   │ │ budget │ │ (BAA,    │ │ filter +  │ │ (chained SHA-256,    │ │
│  │ + canary│ │ + cap  │ │  zero-   │ │ canary    │ │  Service Bus → WORM) │ │
│  │ check   │ │ enforce│ │  retain) │ │ check     │ │                      │ │
│  └─────────┘ └────────┘ └──────────┘ └───────────┘ └──────────────────────┘ │
└─────────────────────────────────┬────────────────────────────────────────────┘
                                  │
                                  ▼
                       AGENT RUNTIME (downstream — not Barycenter)
                       Network egress allowlist: gateway, SQL, storage only

┌──────────────────────────────────────────────────────────────────────────────┐
│              AUDIT & EVIDENCE PLANE (cross-cuts everything)                  │
│  Service Bus (audit topic) ──► WORM Storage (immutable, retention-locked)    │
│                            └─► Microsoft Sentinel (alerts, queries)          │
│                            └─► Drata/Vanta connector (read-only evidence)    │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│              IDENTITY & KEY PLANE (cross-cuts everything)                    │
│   Entra ID  ─►  Managed Identities: etl, salt, tool, gateway, admin (PIM)    │
│                                                                              │
│   Key Vault: salt-vault (per-tenant HMAC salts; salt-service identity only)  │
│              cmk-vault  (Always-Encrypted CMK; admin identity rotates)       │
│              api-vault  (per-tool API secrets; etl identity reads)           │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Recommended Implementation |
|-----------|----------------|----------------------------|
| **Adapter (per source tool)** | Pull from source API, normalize to staging row shape, hand off to loader. One per tool. | Python container, shared base class with hooks (`fetch_page`, `to_staging_row`, `delta_cursor`). Deployed as Azure Container Apps **Job**. |
| **Scheduler** | Cron-style invocation of adapter jobs (e.g., CW every 30 min, Graph every 60 min). | Container Apps Jobs scheduled triggers, or Service Bus timer messages → manual invocation. |
| **Staging Loader** | BULK INSERT raw payload from adapter into `raw_<tool>.staging_*` tables, then MERGE into versioned raw tables. | T-SQL stored procs invoked from adapter; per-tool. |
| **DLQ + Retry Manager** | Failed pulls re-queued with exponential backoff; permanent failures dead-lettered with diagnostic context; alerts to Sentinel. | Azure Service Bus DLQ + a dead-letter handler Function that writes to audit + ops alert channel. |
| **Salt Service** | Single source of truth for per-tenant HMAC salts. Issues `person_pid` for an `(email, tenant_id)` pair on demand. **No other component reads salts.** | Small .NET or Python container; one managed identity (`salt-runtime`); **only** identity with `get` on `salt-vault`. Stateless; deterministic outputs. |
| **Pseudonymizer (in ETL)** | For each row landing in `raw_*` that contains an email, calls Salt Service to materialize `person_pid` and writes to `pseudo.person_map`. Email itself stays in raw zone (Always Encrypted). | T-SQL CLR procedure or Python ETL step calling Salt Service over internal HTTPS. |
| **AI-Zone Builder** | Periodic job that refreshes `ai_zone.*` indexed views or rebuilds materialized tables from raw + pseudo. | T-SQL stored procs invoked by Container Apps Job on a schedule (every 15 min for hot views, hourly for snapshots). |
| **Typed Tool Function Layer** | The agent's only contract. HTTP service exposing typed functions; never raw SQL. | **Azure Data API Builder** sitting on `ai_zone.*` views with session-context RLS, fronted by FastAPI (Python) or .NET minimal API for action-emission endpoints that DAB doesn't cover. |
| **Action Dispatcher** | Receives structured agent actions (`{action, company, recipient_role, template, fields}`), resolves recipient email from raw zone, sends. | .NET or Python Container App. Sole component (other than ETL) with read access to raw zone email columns. Logs every dispatch to audit. |
| **AI Gateway** | Input scrub → token-budget enforce → call Anthropic → output filter (canary, PII patterns, identifier regex) → audit write. | **Build a thin .NET or Python Container App** rather than adopt LiteLLM/Portkey. See decision below. |
| **Audit Writer** | Receives audit events from every other component over Service Bus topic. Computes SHA-256 chain, writes to WORM storage and Sentinel. | Azure Function with Service Bus trigger; only identity with append access to audit container; immutable container policy locked. |
| **Compliance Connector** | Read-only consumer for Drata/Vanta evidence collection. | Drata/Vanta's existing Azure connector — managed identity with `Reader` on subscription + `Sentinel Reader`. **No write paths.** |

---

## Recommended Project Structure

This is a **multi-component repo** (not a single app). Each top-level directory is a deployable unit.

```
barycenter/
├── infra/                              # Terraform / Bicep
│   ├── network/                        # VNet, subnets, private endpoints, NSGs
│   ├── sql/                            # Azure SQL server, database, AE keys
│   ├── identity/                       # Managed identities, role assignments, PIM rules
│   ├── keyvault/                       # salt-vault, cmk-vault, api-vault (separate vaults)
│   ├── storage/                        # WORM container with immutability policy
│   ├── servicebus/                     # audit topic, etl-dlq queue
│   └── containerapps/                  # apps + jobs definitions
│
├── sql/                                # Source-of-truth schema (idempotent migrations)
│   ├── 00-schemas/                     # CREATE SCHEMA raw_cw, raw_pax8, ai_zone, pseudo
│   ├── 10-raw/                         # Per-tool raw tables (raw_cw/, raw_pax8/...)
│   │   └── raw_cw/
│   │       ├── companies.sql           # Each table file declares field-class tags in comments
│   │       └── tickets.sql
│   ├── 20-pseudo/                      # pseudo.person_map, pseudo.audit
│   ├── 30-ai-zone/                     # ai_zone views and indexed views
│   ├── 40-grants/                      # Schema-level GRANT/DENY per identity
│   ├── 50-rls-policies/                # Security policies, predicates
│   └── 99-leak-test-fixtures/          # Synthetic markers for VER-01
│
├── adapters/                           # One subfolder per source tool
│   ├── _base/                          # Shared adapter framework (Python)
│   │   ├── adapter.py                  # AdapterBase with hooks
│   │   ├── retry.py                    # Exponential backoff, circuit breaker
│   │   ├── pagination.py               # RFC 5988 link-header pagination
│   │   └── delta.py                    # Cursor checkpointing
│   ├── connectwise/
│   │   ├── adapter.py
│   │   ├── field_map.yaml              # Source field → raw column → field class
│   │   └── etl_recipe.yaml             # Composition of 8 transformation primitives
│   ├── pax8/
│   ├── graph/
│   └── ...
│
├── etl/                                # T-SQL ETL recipes (raw → ai_zone)
│   ├── primitives/                     # The 8 transformation primitives as reusable procs
│   │   ├── drop.sql
│   │   ├── hash.sql
│   │   ├── pseudonymize.sql
│   │   ├── aggregate.sql
│   │   ├── bucket.sql
│   │   ├── score.sql
│   │   ├── keyword_flags.sql
│   │   └── as_is.sql
│   ├── builders/                       # Per-shape builders
│   │   ├── customer_snapshot.sql
│   │   ├── customer_features_<aspect>.sql
│   │   └── timeseries_aggregate.sql
│   └── orchestrator/                   # Job that calls builders on schedule
│
├── services/
│   ├── salt-service/                   # The pseudonymization HMAC service
│   ├── tool-functions/                 # Typed function HTTP API (DAB + custom endpoints)
│   ├── action-dispatcher/              # Resolves agent actions to outbound communications
│   ├── ai-gateway/                     # LLM gateway (scrub, budget, filter, audit)
│   └── audit-writer/                   # Service Bus → WORM + Sentinel
│
├── compliance/                         # Evidence and policy artifacts
│   ├── field-class-registry.yaml       # ALL columns × class. CI source of truth.
│   ├── ai-zone-view-manifest.yaml      # ALL views × field-class composition. CI checks.
│   ├── policies/                       # Written policies (IR, change mgmt, access review)
│   ├── runbooks/                       # Breach notification, key rotation, mass erasure
│   └── adversarial-corpus/             # Prompt-injection test cases (COMP-05)
│
├── tests/
│   ├── leak-test/                      # VER-01: end-to-end with synthetic markers
│   ├── field-class-drift/              # VER-02: schema vs registry diff
│   ├── adapter-contract/               # Each adapter's field_map.yaml validates
│   └── gateway/                        # Canary detection, output-filter regression
│
└── docs/
    ├── tool-onboarding-spec-template.md   # TOOL-01
    ├── identifier-hierarchy.md
    ├── threat-model.md
    └── decisions/                          # ADRs
```

### Structure Rationale

- **`infra/` separated by domain**, not by environment. One folder per concern (network, sql, identity) so a security review can audit each axis without spelunking.
- **`sql/` is a numbered idempotent migration tree.** Field-class tags live as structured comments in `10-raw/` table definitions, parsed by CI for the field-class registry. The leak-test fixtures are version-controlled because the VER-01 test must be auditable.
- **`adapters/_base/` is the framework**, individual adapter folders are configuration + hooks. New tool onboarding = create a folder, fill `field_map.yaml` and `etl_recipe.yaml`, implement the API-specific `fetch_page`. No bespoke architecture per tool.
- **`services/` are deployable units**, each its own container, identity, and trust boundary. Boundaries match identities — when reviewing "what can the salt service do?", everything is in one folder.
- **`compliance/` is in-repo**, not in a wiki. Field-class registry, view manifest, runbooks all version-controlled because they are tested by CI (VER-02).
- **Tests are organized by guarantee, not by component.** The leak test cuts across every layer; putting it in `services/ai-gateway/tests/` would be wrong.

---

## Architectural Patterns

### Pattern 1: Schema-per-Tool in the Raw Zone (Recommended)

**What:** Each source tool gets its own SQL schema (`raw_cw`, `raw_pax8`, `raw_graph`, `raw_rmm_ninja`, …). Each schema owns the staging tables, raw versioned tables, source-fidelity ETL metadata, and the per-tool retention policy.

**When to use:** Multi-source ingest where tools evolve independently and field-class tagging needs per-tool review.

**Trade-offs:**
- **Pro: Grants are per-schema.** Revoking ETL access to one tool doesn't touch the others.
- **Pro: Schema drift is local.** Pax8 adding a column doesn't ripple into a shared `raw.subscriptions` table.
- **Pro: Field-class review boundary matches the onboarding boundary.** A new tool's PR touches one schema; reviewers know exactly what surface area is in scope.
- **Pro: Per-tool retention is straightforward.** `raw_cw.tickets` keeps 13 months; `raw_graph.audit_signins` might keep 90 days.
- **Con: More schemas to manage** — but schemas are cheap; the alternative (shared raw with a `source_tool` column) is the anti-pattern (see below).

**Implementation note:** Within each tool schema, a consistent sub-pattern:
- `raw_cw.staging_companies` — landing zone, truncated each pull, no constraints.
- `raw_cw.companies` — append-only versioned table with `_synced_at`, `_source_payload_hash`, `_etl_run_id`. MERGE'd from staging by ETL.
- `raw_cw.companies_current` — view returning latest version per natural key.

**Schema drift handling:** Adapter validates source response against `field_map.yaml`. New fields: warn (added to staging as `_unmapped_extras` JSON column), require explicit field-class tagging PR before propagating. Removed fields: warn, then keep column but mark `deprecated_at`.

### Pattern 2: ELT Inside Azure SQL (Not Outside It)

**What:** The transformation primitives (drop/hash/pseudonymize/aggregate/bucket/score/keyword_flags/as_is) live as T-SQL stored procedures. Adapters do *only* extract + load. All transformation runs server-side.

**When to use:** When the security boundary is the database itself. When pulling data out for transformation would require re-establishing the security perimeter externally.

**Trade-offs:**
- **Pro: PII never leaves the SQL trust boundary** during transformation. The pseudonymization step, which is the most sensitive operation, runs inside the same VNet/identity boundary as the data.
- **Pro: Field-class tags can be enforced in the same place they're declared** (column metadata, extended properties, or a registry table joined at ETL time).
- **Pro: Refresh of indexed views is automatic** when raw tables change — T-SQL can use `CREATE INDEX ... WITH SCHEMABINDING` for zero-staleness ai_zone views where math allows.
- **Con: T-SQL is less expressive than Python** for complex transforms. Mitigation: keyword_flags and score primitives can call out to a Python service if needed (rare); 90% of transforms are pure SQL.
- **Con: DTU pressure during ETL.** Mitigation: production sizing baseline (OPS-01) accounts for this; ETL runs scheduled, not concurrent with peak agent traffic.

### Pattern 3: Salt Service as Crown-Jewel Microservice

**What:** Pseudonymization is **not** a SQL function and **not** an inline ETL step that reads salts. It is a separate HTTP service with its own managed identity (`salt-runtime`), its own Key Vault (`salt-vault`), and exclusive access to the salt material.

**When to use:** When the cryptographic key for pseudonymization is itself the trust boundary. If anyone with database access can read salts, the pseudonyms collapse.

**Trade-offs:**
- **Pro: Salt access is a single-component blast radius.** Compromise of the ETL identity, the agent identity, the admin identity — none expose salts.
- **Pro: One-way property is enforceable.** Agent identity and Tool Function Layer have **zero** network reachability to the salt service (NSG denies). They can only see materialized pseudonyms.
- **Pro: Erasure is mechanically clean.** ERAS-01 = "delete the salt for tenant X, all downstream pseudonyms become non-reversible by anyone." A column in `pseudo.person_map` per-tenant indicates erased state; the salt service refuses to issue new pids for erased tenants.
- **Pro: Audit choke point.** Every pseudonym issuance is logged through the salt service.
- **Con: Adds a network hop to ETL.** Mitigation: pseudonymization is bulk and infrequent; not on hot path for agent queries.

**Concrete contract:**
```
POST /pid    { tenant_id, email_lower } → { person_pid }   # idempotent
POST /erase  { tenant_id }              → { erased_at }    # privileged
GET  /audit  …                                              # privileged
```

The salt service is **stateless except for Key Vault**. The map of `(tenant, email) → pid` lives in `pseudo.person_map`, written by ETL, **not** by the salt service. The salt service computes; ETL persists.

### Pattern 4: Indexed Views for Hot AI-Zone Shapes, Refreshed Tables for Cold

**What:** `ai_zone.*` is a mix of two physical realizations:
- **Indexed views (`SCHEMABINDING + UNIQUE CLUSTERED INDEX`)** for shapes that map directly to raw rows with simple aggregates: e.g., `ai_zone.customer_snapshot` if it's a join + light aggregation. Updates are automatic; query performance is fast.
- **Refreshed tables (built by stored procs on schedule)** for shapes that require cross-tool joins, time-windowed aggregates, scoring, or `customer_memory` (which is by definition a derived narrative): e.g., `ai_zone.customer_features_renewal_risk`, `ai_zone.timeseries_aggregate`.

**When to use:** Indexed views when the shape is a deterministic function of raw rows that can be expressed in a single SELECT and the underlying tables aren't too churn-heavy. Refreshed tables for everything else.

**Trade-offs:**
- **Pro: Best of both.** Hot, simple shapes are zero-stale and fast. Heavy shapes don't pay write-amplification on every raw insert.
- **Pro: The four-shape constraint (`customer_snapshot`, `customer_features_*`, `timeseries_aggregate`, `customer_memory`) is enforceable in the manifest.** New tools contribute *into* these; the manifest CI fails any view that doesn't fit one of the four.
- **Con: Indexed views have constraints** (no outer joins, no UNION, etc.). Some shapes will have to be refreshed tables even if they "feel hot."
- **Con: Refresh cadence is a choice.** Recommendation: 15-min cadence for `customer_snapshot` and `customer_features_*`; hourly for `timeseries_aggregate`; on-event for `customer_memory` (when an agent action emits a memory write).

**Refresh strategy:** Single orchestrator stored proc per shape, idempotent, with a `_refresh_log` row capturing run_id, start, end, rows touched, hash of result. CI runs the refresh in tests against synthetic data.

### Pattern 5: Data API Builder + Custom API for Typed Tool Functions

**What:** The typed tool function layer is **two services in one VNet**:
1. **Data API Builder (DAB)** for read-only typed function endpoints over `ai_zone.*` views. DAB exposes REST/GraphQL with declarative entity config; session context propagates the calling agent's claims so RLS policies in SQL filter rows by tenant/customer.
2. **A small custom HTTP service** (FastAPI or .NET minimal API) for endpoints DAB can't model: `emit_action()` (writes to action queue, not SQL), `get_customer_memory()` (which may want to merge structured + free-form), and any function that orchestrates multiple SQL calls behind one DTO.

**When to use:** When agents need a typed, validated, RLS-enforced contract and SQL can express most of it but not all of it.

**Trade-offs:**
- **Pro: DAB does the boring 80%** (CRUD-shaped reads with row-level filtering) for free, with battle-tested session-context RLS and OpenAPI spec generation.
- **Pro: Custom service handles the irreducible 20%** without forcing every interaction through DAB's model.
- **Pro: Both run in the same VNet, both authenticate the agent identity once.**
- **Con: Two codebases.** Mitigation: they share a typed schema (Pydantic / C# records generated from `ai-zone-view-manifest.yaml`).
- **Anti-temptation:** Do **not** expose DAB's mutation operations to agents. Reads only. Mutations (action emission) go through the custom service which validates the structured action shape before any side-effect.

### Pattern 6: AI Gateway as Thin Owned Service (Not Off-the-Shelf)

**What:** Build a small (~1-2k LOC) gateway in .NET or Python rather than adopting LiteLLM, Portkey, Bifrost, or fronting Anthropic with Azure API Management.

**When to use:** When the gateway's job description includes (a) HIPAA-grade audit logging with a specific chain format, (b) canary detection against tokens that are domain-specific to your raw zone, (c) per-tenant per-class opt-out enforcement (ACCESS-05), and (d) per-tenant per-day budgets that map to your tenant identity hierarchy.

**Trade-offs:**
- **Pro: Audit format is exactly what your WORM chain expects.** No translation layer between the gateway's "this is what I logged" and your audit_writer's "this is what I sign."
- **Pro: Canary detection logic is domain-specific** (real customer names, real serial numbers, real PO numbers as canaries) and is closer to a config file than a product feature. Off-the-shelf gateways are generic.
- **Pro: Per-tenant per-class opt-out is a 50-line policy check** that's natural to write inline; off-the-shelf gateways generally lack this granularity.
- **Pro: BAA is between Gravity and Anthropic directly** — you don't introduce a third vendor between you and the LLM.
- **Pro: ~2k LOC is small enough to security-review fully** and to evolve as the threat model evolves.
- **Con: You write and maintain it.** Mitigation: it's not a hot-path performance problem (LLM latency dwarfs gateway overhead); it's a correctness problem, and correctness is exactly what you want to own.
- **Con: You miss model routing / multi-provider features** of LiteLLM. But Constraint says Anthropic is the LLM. If that changes, revisit.

**Verdict:** **Build it.** This is a load-bearing security component; it's small; off-the-shelf is generic where you need specific.

If you want the *option* of pluggable model providers later, structure the gateway with a clean `LLMProvider` interface internally. That's a 2-day investment, not a product adoption.

### Pattern 7: Audit Plane on Service Bus → WORM + Sentinel

**What:** Every component writes audit events to a single Service Bus topic. A dedicated audit-writer Function consumes the topic, computes the SHA-256 chain (each event includes the SHA of the prior), appends to an immutable WORM blob (one append-blob per day), and forwards to Sentinel for query/alerting.

**When to use:** When you need both immutability (regulatory) and queryability (operations).

**Trade-offs:**
- **Pro: Single chokepoint** for the cryptographic chain — only one writer, only one identity with append rights to the WORM container.
- **Pro: Components don't talk to WORM directly.** They publish to Service Bus and forget. Failure of WORM doesn't block the producing component (only delays audit landing).
- **Pro: Sentinel forwarding is independent.** Tampering with WORM is detectable (chain breaks); tampering with Sentinel doesn't help if the chain is intact. Tampering with both is detectable because they're written from the same canonical source.
- **Pro: Audit-of-audit (AUDIT-02)** is natural — queries against audit data are themselves Service Bus events from the query layer.
- **Con: Service Bus adds latency** between event and durable storage. Mitigation: WORM is for forensic completeness, not real-time alerting; Sentinel handles real-time. ~seconds latency to WORM is acceptable.
- **Con: Append-blob immutability has a per-blob retention period** locked at write. Daily rotation matches HIPAA retention math (6 years × 366 days = 2196 blobs).

### Pattern 8: Container Apps Jobs for Sync, Container Apps for Services

**What:**
- **Sync layer = Azure Container Apps Jobs** (scheduled or manual triggers, run-to-completion semantics).
- **Always-on services (salt service, tool functions, AI gateway, action dispatcher) = Azure Container Apps** (HTTP-triggered, scale-to-zero where workload allows, scale-out on demand).
- **Audit writer = Azure Function** (Service Bus trigger, simple consumer pattern).

**When to use:** When sync workloads are bounded, batch-shaped, and benefit from container portability (some adapters will use vendor SDKs that aren't Functions-friendly), and when service workloads are HTTP and want serverless-ish economics.

**Trade-offs:**
- **Pro: Container Apps Jobs are the right shape for ETL.** They run, they finish, they don't pretend to be Functions. They support cron, manual, event triggers.
- **Pro: Same VNet, same identity model, same observability** as the services. One platform.
- **Pro: Functions are still cheap** for the audit-writer's Service Bus trigger pattern.
- **Con: Container Apps cost more than Functions at trivial scale.** Doesn't matter at this volume.

---

## Data Flow

### Flow 1: Sync (Source → Raw Zone)

```
[Adapter triggered]
    │
    ▼
[Adapter reads delta cursor from raw_<tool>._sync_state]
    │
    ▼
[Adapter calls source API, paginates RFC 5988 link headers]
    │
    ▼
[Adapter normalizes rows per field_map.yaml, validates field-class tags exist]
    │
    ▼
[Adapter writes to raw_<tool>.staging_<entity> via BULK INSERT]
    │
    ▼
[Adapter calls stored proc raw_<tool>.merge_<entity> → raw_<tool>.<entity>]
    │
    ▼
[Adapter advances cursor, writes audit event {tool, entity, rows, run_id, hash}]
    │
    ▼
[On exception: Service Bus DLQ; retry budget; alert Sentinel after exhaustion]
```

### Flow 2: Pseudonymization (Raw → Pseudo Map)

```
[ETL job triggered for raw_graph.users (or any tool with email)]
    │
    ▼
[ETL selects new (tenant_id, email_encrypted) pairs not yet in pseudo.person_map]
    │
    ▼
[ETL decrypts email column-side via Always Encrypted client]
    │
    ▼
[ETL POSTs (tenant_id, email_lower) → salt-service /pid]
    │
    ▼
[Salt service: HMAC-SHA-256(salt_<tenant>, email_lower) → person_pid]
[Salt service: writes audit event {tenant_id, salt_version, pid, requested_by_identity}]
    │
    ▼
[ETL writes (tenant_id, email_hash, person_pid, source_tool, first_seen) to pseudo.person_map]
[ETL does NOT write the cleartext email anywhere outside raw zone]
    │
    ▼
[Cross-tool reconciliation: same (tenant_id, email) → same pid by HMAC determinism]
[No fuzzy matching, no LLM — deterministic code only (per Out of Scope)]
```

### Flow 3: AI-Zone Refresh (Raw + Pseudo → AI Zone)

```
[Builder job triggered (15 min for snapshot, hourly for timeseries)]
    │
    ▼
[Builder calls etl.builders.<shape> stored proc]
    │
    ▼
[Stored proc reads raw_*.* (joined to pseudo.person_map for emails)]
[Stored proc applies the 8 primitives:]
[  RESTRICTED columns: drop OR aggregate]
[  SENSITIVE columns: hash OR pseudonymize]
[  INTERNAL/PUBLIC columns: as_is OR bucket OR score]
    │
    ▼
[For indexed views: nothing — they auto-update]
[For refreshed tables: TRUNCATE + INSERT, or MERGE if incremental]
    │
    ▼
[Builder writes to ai_zone._refresh_log {shape, run_id, rows, hash, fk_consistency_check}]
[Builder writes audit event]
    │
    ▼
[CI invariant test: every column produced is in ai-zone-view-manifest.yaml; every value's
 source column's field class is compatible with the view's stated composition]
```

### Flow 4: Agent Query (Agent → AI Zone via Typed Function)

```
[Agent process (downstream) calls AI Gateway: POST /complete {prompt, tenant_context}]
    │
    ▼
[Gateway: input scrub → token budget → call Anthropic with tools={get_customer_snapshot, …}]
    │
    ▼
[Anthropic returns tool_use: get_customer_snapshot(cw_company_id=12345)]
    │
    ▼
[Gateway forwards tool call to Tool Function Layer: GET /customers/12345/snapshot]
    │
    ▼
[Tool Function Layer (DAB): authenticates agent identity, sets sp_set_session_context with
 tenant claim → SQL RLS predicate filters ai_zone.customer_snapshot to that tenant's rows]
    │
    ▼
[Tool Function Layer returns DTO (no RESTRICTED, no email, only person_pid + buckets)]
[Tool Function Layer writes audit event {agent, function, params, tenant, rows_returned}]
    │
    ▼
[Gateway returns DTO to Anthropic as tool_result]
[Anthropic generates completion]
    │
    ▼
[Gateway: output filter (canary regex, identifier regex, PII patterns)]
[Gateway: writes audit event {prompt_hash, completion_hash, tools_used, tenant, blocked?}]
[Gateway returns completion to agent]
```

### Flow 5: Agent Action Emission (Agent → Outbound Communication)

```
[Agent (via Anthropic) emits structured action via Tool Function Layer:]
[  POST /actions {action: "send_renewal_reminder", company: "cw_company_id=12345",]
[                 recipient_role: "billing_admin", template: "renewal_30day", fields: {…}}]
    │
    ▼
[Tool Function Layer validates action shape against schema]
[Tool Function Layer enqueues to action queue (Service Bus)]
[Tool Function Layer returns action_id to agent — agent never sees email]
    │
    ▼
[Action Dispatcher consumes queue]
[Action Dispatcher resolves recipient_role → email via raw_cw.contacts (raw zone read)]
[Action Dispatcher renders template + fields → message]
[Action Dispatcher sends via outbound provider (SMTP, Graph mail, ticket post)]
[Action Dispatcher writes audit event {action_id, agent, resolved_recipient_hash, sent_at}]
    │
    ▼
[Decision-reversal path: every dispatched action has a registered reversal procedure
 documented in compliance/runbooks (per COMP-05). Action records its reversal contract.]
```

### Flow 6: Customer Erasure

```
[Admin via PIM elevates → triggers erasure workflow with dual approval]
    │
    ▼
[Erasure orchestrator:]
[  1. Salt service: erase tenant salt → record erasure timestamp]
[  2. raw_*.*: anonymize or delete tenant rows per retention policy]
[  3. pseudo.person_map: mark tenant entries erased (pids become non-reversible)]
[  4. ai_zone.*: refresh — pids that pointed to nothing now point to nothing more strongly]
[  5. WORM audit: write erasure event (audit log itself is NOT erased — HIPAA requires retention)]
[  6. Drata/Vanta evidence: update]
    │
    ▼
[Verification: leak test (VER-01) re-run with that tenant's markers — must find zero hits]
```

---

## Build Order (Phase Boundary Recommendations)

This is the dependency-ordered sequence the roadmap should encode. Each block is a candidate phase boundary.

### Block A — Foundations (must exist before tool #1)

1. **Field-class registry + field-class CI gate** (FOUND-02, VER-02). Just YAML + a test. Two days. Locks the discipline.
2. **Network + identity infrastructure**: VNet, private endpoints, three Key Vaults (salt, cmk, api), four managed identities (etl, salt, tool, gateway), PIM rules. (IDENT-01, IDENT-02, IDENT-03, EGRESS-01)
3. **Azure SQL provisioned with schemas + grants** (`raw_*` placeholder, `ai_zone`, `pseudo`), Always Encrypted CMK in cmk-vault, RLS policy templates. (FOUND-01, ENC-01)
4. **Audit plane**: Service Bus topic, audit-writer Function, WORM container with retention policy locked, Sentinel forwarding. (AUDIT-01, AUDIT-02)
5. **Salt service** deployed and tested with synthetic tenant. (FOUND-03, supports D-10)

**Why this order:** None of these depend on a specific tool. All of them must be in place before the first real PII row is written. The audit plane comes before the first tool because if the audit format changes after data has flowed, retroactive audit is hard.

**Lock-early decisions in Block A:** schema-per-tool, schema-per-zone-isolation, salt-service-as-microservice, audit chain format, identity topology. Changing any of these later is multi-week work.

### Block B — Tool onboarding framework (must exist before tool #2)

6. **Eight transformation primitives implemented as T-SQL stored procs** with tests. (TOOL-02)
7. **Tool Onboarding Spec template + adapter base class** in `adapters/_base/`. (TOOL-01)
8. **Pseudonymizer ETL step** wired to salt service. (FOUND-03)
9. **Adapter for tool #1: ConnectWise Manage** — exercises every primitive, every shape contribution. CW is the right "tool #1" because it issues `cw_company_id` (the root identifier in the hierarchy). (INT-01)
10. **First two AI-zone shapes**: `ai_zone.customer_snapshot` (indexed view) and `ai_zone.timeseries_aggregate` (refreshed table). Validates both physical patterns. (TOOL-03)

**Why this order:** The framework is built and validated by the first tool. Tool #1 is the framework's regression test.

**Lock-early decisions in Block B:** the eight primitives, the four shapes, the tool onboarding spec format, the cursor/delta-sync convention. Changing the shape contract later forces every tool to be re-onboarded.

### Block C — Agent-safe access layer (must exist before agents can consume)

11. **Tool Function Layer (DAB + custom service)** with first three typed functions: `get_customer_snapshot`, `list_renewals_due`, `emit_action`. (ACCESS-01, ACCESS-02)
12. **Action Dispatcher** consuming action queue, sending via Graph/SMTP. (ACCESS-03)
13. **AI Gateway** with input scrub, output filter, canary detection, audit emission. (ACCESS-04)
14. **Per-tenant per-class opt-out enforcement** in the gateway and tool functions. (ACCESS-05)
15. **End-to-end leak test (VER-01)** with synthetic markers, wired into CI on every raw/view/grant change.

**Why this order:** Tool function layer first so the gateway has a real backend; gateway last so output filtering is applied to real completions, not mocks. Leak test is the final acceptance gate — if it passes, the architectural moat is verifiable.

**Lock-early decisions in Block C:** the typed function naming convention, the action-emission contract format, the canary token format, the leak-test marker format. These ripple into every agent that ever consumes Barycenter.

### Block D — Onboard tools #2 and #3

16. **Pax8** (INT-02) — exercises the framework on a different domain (subscriptions, not tickets).
17. **Microsoft Graph** (INT-03) — exercises pseudonymization at scale (every M365 user has an email; every customer has 10–500 users).
18. **Email-derived signals adapter** (INT-04) — exercises the keyword_flags and score primitives on free text. Highest pseudonymization risk; do third when the framework is mature.

**Why this order:** Each tool exercises a different framework dimension. Email signals last because the adapter must produce structured extracts (PO numbers, intent, sentiment) without raw bodies; this is the hardest correctness problem and benefits from a hardened framework.

**Lock-early decisions in Block D:** none new — these are framework users, not framework definers.

### Block E — Compliance + operations posture

19. **Drata or Vanta** wired in (read-only managed identity, evidence collectors enabled). (COMP-02)
20. **CUI exclusion controls** (per-customer flag, sync-time filters in adapters, regex CUI marker detection, quarterly verification). (COMP-03)
21. **Subprocessor inventory + DPA template** + change-notification workflow. (COMP-04)
22. **AI-specific posture**: model card, DPIA, prompt-injection adversarial corpus in CI, decision-reversal runbook for every emitted action. (COMP-05)
23. **Erasure workflow** end-to-end: documented + tested + leak-test re-run after erasure. (ERAS-01)
24. **Production sizing baseline + monthly partitioning + cold archive to Parquet.** (OPS-01)

**Why this order:** Drata can collect evidence the moment infra exists; pull it forward. CUI controls land before high-PII tools (Graph, email signals) — block 20 actually overlaps with block D. Subprocessor and AI-specific posture are documentation-heavy and can run in parallel with development.

**Lock-early decisions in Block E:** subprocessor list (changing means customer notification per COMP-04), DPIA structure, retention table.

### Decisions that can iterate (don't lock early)

- **Indexed-view vs refreshed-table choice per shape.** Make per-shape; reversible.
- **Adapter language** — Python is recommended but a tool with a great .NET SDK can be a .NET adapter. Adapter base class abstraction is per-language; not a global commit.
- **Refresh cadence** for AI-zone shapes. Tunable per-shape based on observed staleness needs.
- **Specific gateway scrubbing rules.** Add as you discover patterns.
- **Whether `customer_memory` is in SQL or in a separate store** (e.g., a vector store). Recommendation: start in SQL as JSON; revisit if agents demand semantic recall.

---

## Scaling Considerations

Sized for Gravity's actual scale (single MSP, ~hundreds of customers, ~tens of tools), not generic "data platform" scale.

| Scale | Architecture Adjustments |
|-------|--------------------------|
| **Today (initial):** ~10 customers, 1–3 tools synced, agent traffic light | Single Azure SQL DB on Standard tier (S2/S3). Production sizing baseline OPS-01 mandates Standard or higher; Basic is dev-only. Single Container Apps environment. Audit-writer Function on consumption plan. |
| **Steady state:** ~100 customers, 10–15 tools, multiple agents | Standard S6 or Premium P1 for Azure SQL — DTU pressure mainly from ETL, not agent reads. Monthly partitioning on high-volume tables (ticket time entries, Graph signin events). Indexed views become valuable. Salt service and gateway each scale independently in Container Apps; expect 1–3 replicas. |
| **Outer bound:** ~500 customers, 30+ tools | Consider read replica for ai_zone reads if tool-function-layer load competes with ETL writes. Cold archive to Parquet on Blob after 13-month retention threshold (RET-01). May want partitioned-tables-as-views for raw_*.events-style tables. |

### Scaling Priorities (what breaks first)

1. **First bottleneck: ETL DTU pressure from per-tool full re-syncs.** Mitigation: enforce delta-cursor discipline; full re-sync is opt-in and runs in low-traffic windows. Already designed into Pattern 2.
2. **Second bottleneck: Salt service throughput on bulk Graph user sync.** Mitigation: salt service supports batch endpoint; ETL pseudonymization is a single bulk call per tenant per run, not per row.
3. **Third bottleneck: Audit chain serialization** if event volume spikes (every agent prompt + every tool function + every dispatch). Mitigation: audit-writer Function is single-writer by design (chain integrity), but Service Bus topic supports back-pressure; consider chain segmentation per-day if events ever exceed ~10k/sec (won't happen at this scale).

---

## Anti-Patterns

### Anti-Pattern 1: Shared raw schema with `source_tool` discriminator column

**What people do:** A single `raw.entities` table with a `source_tool` column (or a single `raw` schema with `cw_companies`, `pax8_subscriptions` cohabiting).

**Why it's wrong:**
- Grants are coarse — revoking ETL access to one tool revokes all.
- Schema drift is global — Pax8 adding a column risks breaking CW queries.
- Field-class review is global — every PR touches the shared schema and reviewers lose context.
- Retention policies have to be row-level, not table-level, which is expensive and error-prone.

**Do this instead:** Schema-per-tool. Pattern 1 above.

### Anti-Pattern 2: Pseudonymization as a SQL view function

**What people do:** Create a SQL function `dbo.pseudonymize(email)` that reads the salt from a table and exposes via a view.

**Why it's wrong:**
- Whoever can read the salt table can de-pseudonymize. Salt material in SQL means SQL access ⇒ de-pseudonymization.
- Erasure becomes "delete a row in a salt table" — easy to mis-execute.
- No audit chokepoint — every view access is an implicit pseudonymization.

**Do this instead:** Salt service microservice. Pattern 3 above. Salt material lives in Key Vault, accessed only by `salt-runtime` identity, never by ETL or agent identities directly.

### Anti-Pattern 3: Agent constructs SQL or queries DAB freely

**What people do:** Give the agent broad DAB access ("agents can SELECT from any ai_zone view") in the name of flexibility.

**Why it's wrong:**
- The "typed" in typed tool functions becomes a fiction. Agents drift toward composing SQL-like queries from prompts.
- Audit becomes per-query, not per-intent. "What was the agent trying to do?" is unanswerable.
- The output-filter rules can't be tightened to specific function shapes if the surface is "any view."

**Do this instead:** Each typed function is enumerated, named, parameter-typed, and individually grantable. The `Anthropic tools` list given to the model contains the explicit set, not "query database."

### Anti-Pattern 4: AI gateway as Azure API Management policy soup

**What people do:** Use Azure API Management with a stack of policies (rate limit, token validation, body filter, etc.) instead of a custom gateway.

**Why it's wrong:**
- APIM policies are XML-on-rails. Canary detection logic, cryptographic audit chaining, per-tenant per-class opt-out — these are awkward to express in policy XML and hard to test.
- APIM doesn't naturally express HMAC chaining or structured per-prompt audit.
- Debugging an output filter that lives in APIM policy is materially worse than debugging it in code.

**Do this instead:** Build a small owned gateway (Pattern 6). APIM is fine for consumer API gateway concerns; not for the LLM safety boundary.

### Anti-Pattern 5: Cross-tool person identity reconciled by an LLM

**What people do:** "Pax8 has a contact 'jane.smith@acme.com', CW has 'JaneS@acme.com', let the LLM merge them."

**Why it's wrong:**
- Out of scope per PROJECT.md, but the architectural reason is: LLM sees PII (the emails) before reconciliation. The whole pseudonymization stack assumes PII never reaches the model.
- Non-determinism — same data could produce different reconciliations on re-run, breaking historical aggregates.

**Do this instead:** Deterministic in raw zone. `email_lower` is the merge key. Salt service produces the same `person_pid` for the same `(tenant, email_lower)`. If a customer truly has `JaneS@acme.com` and `jane.smith@acme.com` as the same person, that's a CW/Pax8 data quality fix, with code review, not an AI inference.

### Anti-Pattern 6: Storing AI-zone derived data outside Azure SQL

**What people do:** Push `customer_features_*` into Cosmos DB or a vector store because "agents query it."

**Why it's wrong:**
- Two stores ⇒ two schema-permission boundaries to enforce ⇒ doubled compliance surface.
- Pseudonymization invariants are now two places' problem.
- The architectural claim "agent identity has zero grants on raw_*" is degraded — now there's a second store with a second grant model.

**Do this instead:** Keep ai_zone in Azure SQL alongside raw. The two-zone model is a schema boundary, not a database boundary. (If a future agent workload genuinely needs vector recall on `customer_memory`, add it then, with explicit re-architecture; not preemptively.)

### Anti-Pattern 7: ETL identity reused as admin or dev identity

**What people do:** Single Azure service principal used by ETL pipeline and by humans during development.

**Why it's wrong:**
- "ETL has zero grants on ai_zone" is unenforceable when ETL is also the developer's identity.
- Audit trail conflates human queries with automated ones.
- PIM elevation can't be applied — it's an automation identity, not a human one.

**Do this instead:** Per-service managed identities (IDENT-03). Humans use named Entra accounts elevated through PIM (IDENT-02). No service principal is ever shared between automation and human use.

---

## Integration Points

### External Services

| Service | Integration Pattern | Notes / Gotchas |
|---------|---------------------|-----------------|
| **ConnectWise Manage** | REST API, RFC 5988 link-header pagination, 30-min delta sync. Default 60 req/min rate limit. | Page size up to 1000 with `pageSize` parameter. Use `forward-only` pagination header for large pulls. Store delta cursor in `raw_cw._sync_state`. |
| **Pax8** | REST API, OAuth 2.0. | Rate limits not well-documented; implement defensive backoff. Subscriptions are the primary entity; pull SKU catalog separately. |
| **Microsoft Graph** | Microsoft Graph SDK, delta queries (`/users/delta`). | Delta queries are the primary mechanism for incremental sync. Throttling is per-tenant — back off on 429. Hash users → `person_pid` at ingest, never store email in ai_zone. |
| **RMM (Ninja, Datto, etc.)** | Per-vendor REST APIs. | Heterogeneous; this is where the adapter framework's value is highest. Serial numbers are the asset identity. |
| **SentinelOne / Duo / security** | Per-vendor REST. | Sensitive: alerts may contain raw indicators of compromise. Aggregate to counts and severity buckets in ai_zone; never expose raw alerts. |
| **Anthropic Claude** | Direct API (BAA + zero-retention), via owned AI gateway only. | Enterprise plan + BAA confirmed in writing per COMP-01. Anthropic is the only LLM; gateway abstracts so we *could* swap, but no current plan to. |
| **Microsoft Sentinel** | Log forwarding from audit-writer + Container Apps log analytics. | Sentinel is downstream of the WORM chain — chain is canonical, Sentinel is queryable mirror. |
| **Drata / Vanta** | Their managed identity granted Reader on subscription + Sentinel Reader. **No write access.** | Pick one, lock in — switching costs are control-mapping rework, not technical. Both support Azure equivalently. Drata for depth, Vanta for breadth — recommendation deferred to operations preference. |

### Internal Boundaries

| Boundary | Communication | Considerations |
|----------|---------------|----------------|
| **Adapter ↔ raw zone** | Direct SQL via private endpoint; `etl-runtime` identity. | Schema-bounded grants — etl identity has CRUD on `raw_<tool>` only, write on `pseudo`, **zero** on `ai_zone`. |
| **ETL ↔ Salt service** | Internal HTTPS, mTLS or managed-identity bearer token. | Salt service in same VNet, NSG denies traffic from any non-ETL identity. |
| **AI-zone Builder ↔ raw + pseudo + ai_zone** | Direct SQL; `etl-runtime` identity (same as ETL adapters). | Builder is a different class of job but same identity. RLS not needed at this layer (operates on full tenant set). |
| **Tool Function Layer ↔ ai_zone** | Direct SQL via DAB; `tool-runtime` identity. | Identity has SELECT on `ai_zone.*` only. RLS predicates filter by tenant claim from session context. **Zero** on raw and pseudo. |
| **Action Dispatcher ↔ raw zone** | Direct SQL with narrow grant: SELECT on `raw_cw.contacts` (or equivalent) only. | This is the *only* component besides ETL that reads raw zone. Documented and audited. |
| **AI Gateway ↔ Tool Function Layer** | Internal HTTPS. | Gateway holds the agent identity claim; passes through to tool functions. Tool functions log the agent identity, not the gateway identity. |
| **AI Gateway ↔ Anthropic** | Outbound HTTPS via egress allowlist (anthropic.com on the agent VNet). | The *only* outbound traffic permitted from the agent VNet besides SQL and Storage. |
| **Everything ↔ Audit topic** | Service Bus topic, fire-and-forget. | Every component has Send rights on the topic; only audit-writer has Receive. |
| **Audit-writer ↔ WORM** | Append-blob writes. Identity has *only* this permission, on *only* this container. | Immutability policy locked at container creation; deletion of audit-writer identity does not delete the data. |

---

## Decisions That Must Be Locked Early

These have multi-week reversal cost. Get them right in Block A or B.

| Decision | Why expensive to change | Recommendation |
|----------|------------------------|----------------|
| **Schema-per-tool vs shared raw schema** | Migration touches every adapter, every grant, every audit log entry referencing schema. | Schema-per-tool. |
| **Single SQL DB vs split DBs for raw/ai** | Cross-DB joins force ETL to be cross-DB; doubles operational surface. | Single DB, schema isolation. (Aligns with Constraint.) |
| **Salt service as separate component vs SQL function** | If you start with SQL function, every component that touched salts has to be migrated; salt access auditing has no chokepoint. | Separate microservice, separate Key Vault, separate identity. |
| **HMAC vs random pseudonyms** | Random pids cannot be re-derived; cross-tool reconciliation breaks if you can't re-HMAC. | HMAC with per-tenant salt. (Already in PROJECT.md.) |
| **Audit chain format** | Retroactively re-chaining historical events is ~impossible without invalidating all prior signatures. | Chain format = `event_json + sha256(prior_chain_hash)`, locked day 1. |
| **Field-class registry as source of truth** | Re-tagging columns later requires re-running every CI test against all historical violations. | Registry exists Day 1, CI gate enforces from first PR. |
| **Eight transformation primitives** | Adding a 9th primitive is fine; redefining existing ones forces every tool's ETL recipe to be re-validated. | Lock the eight in Block B. |
| **Four AI-zone shapes** | Adding a 5th is high cost (every agent's tool list changes). | Lock the four in Block B. (Already in PROJECT.md.) |
| **Identifier hierarchy (tenant_id, cw_company_id, serial_number, person_pid)** | Adding a new identifier later means every shape, every typed function, every audit log entry has a new field. | Locked. (Already in PROJECT.md.) |
| **Per-service managed identity topology** | Identity changes ripple through grants, RLS, audit logs, Drata mappings. | Locked Day 1: etl, salt, tool, gateway, dispatcher, audit-writer, admin. |
| **WORM container retention period** | Cannot be shortened once locked (that's the point). Set too long = pay forever for old data. | 6 years for HIPAA-tagged-customer events; 13 months for non-HIPAA. Daily rotation; per-day container isolates the policy choice. |

### Decisions That Can Iterate

These can change without retroactive cost.

- AI-zone refresh cadence per shape.
- Specific gateway scrubbing regex set (additive).
- Adapter language per tool.
- Drata vs Vanta (re-mapping work, not architecture).
- Whether `customer_memory` is JSON-in-SQL or separate (revisit on agent demand).
- Specific RLS predicate logic (tweakable as access patterns evolve).

---

## Recommendations Where PROJECT.md Leaves Architectural Choice Open

The user asked for explicit recommendations on the open questions. Summarized:

1. **Sync layer**: Pluggable adapter pattern with shared scheduler (one base class, per-tool config + hooks). NOT one bespoke worker per tool. Retry/DLQ/rate-limit live in the adapter base class + Service Bus DLQ. Adapters deploy as Container Apps Jobs.
2. **Raw zone**: Schema-per-tool. Reasons enumerated in Anti-Pattern 1 above.
3. **Pseudonymization**: Runs in ETL (not in views). Salt service is a separate microservice with its own identity and Key Vault. Cross-tool reconciliation via deterministic HMAC on `(tenant, email_lower)` — never an LLM.
4. **AI zone**: Mix — indexed views for hot simple shapes (`customer_snapshot`), refreshed tables for heavier shapes (`customer_features_*`, `timeseries_aggregate`, `customer_memory`). Refresh cadence: 15 min hot, hourly cold, on-event for memory.
5. **Typed tool function layer**: Azure Data API Builder for the read 80%, custom FastAPI/.NET service for the action-emission and orchestrating 20%. Both in same VNet. Anthropic calls them via the gateway as tools.
6. **AI gateway**: Build, don't buy. Small owned service (~1-2k LOC). LiteLLM/Portkey/APIM are wrong fit because the requirements are HIPAA audit chain integration, domain-specific canary detection, and per-tenant per-class opt-out — all custom enough that off-the-shelf adds adapters rather than removing work.
7. **Identity boundary**: Six managed identities (etl, salt, tool, gateway, dispatcher, audit-writer) plus admin via Entra PIM. Three Key Vaults (salt, cmk, api). VNet-isolated. Private endpoints for SQL. Egress allowlist on agent VNet (gateway, SQL, storage only).
8. **Compliance plane**: Drata or Vanta connects via read-only managed identity. They consume from Sentinel + Azure resource graph. Evidence is *written* by Barycenter components into audit + Sentinel; Drata/Vanta only *reads*. Decision between Drata/Vanta deferrable to operations preference (both work; Drata depth, Vanta breadth).

---

## Sources

**Azure SQL & Data API Builder (HIGH confidence — official Microsoft Learn):**
- [Implement row-level security with session context — Data API Builder | Microsoft Learn](https://learn.microsoft.com/en-us/azure/data-api-builder/concept/security/row-level-security)
- [SQL MCP Server overview | Microsoft Learn](https://learn.microsoft.com/en-us/azure/data-api-builder/mcp/overview)
- [Always Encrypted cryptography — SQL Server | Microsoft Learn](https://learn.microsoft.com/en-us/sql/relational-databases/security/encryption/always-encrypted-cryptography?view=sql-server-ver16)
- [Always Encrypted — SQL Server | Microsoft Learn](https://learn.microsoft.com/en-us/sql/relational-databases/security/encryption/always-encrypted-database-engine?view=sql-server-ver17)
- [Performance tuning with materialized views — Azure Synapse Analytics | Microsoft Learn](https://learn.microsoft.com/en-us/azure/synapse-analytics/sql/develop-materialized-view-performance-tuning)
- [Virtual network endpoints and rules for databases — Azure SQL Database | Microsoft Learn](https://learn.microsoft.com/en-us/azure/azure-sql/database/vnet-service-endpoint-rule-overview?view=azuresql)
- [ELT design pattern — Azure Synapse Analytics | Azure Docs](https://docs.azure.cn/en-us/synapse-analytics/sql-data-warehouse/design-elt-data-loading)
- [ETL — Azure Architecture Center | Microsoft Learn](https://learn.microsoft.com/en-us/azure/architecture/data-guide/relational-data/etl)

**Compute and orchestration (HIGH confidence — official Microsoft Learn):**
- [Azure Functions on Azure Container Apps overview | Microsoft Learn](https://learn.microsoft.com/en-us/azure/container-apps/functions-overview)
- [Comparing Container Apps with other Azure container options | Microsoft Learn](https://learn.microsoft.com/en-us/azure/container-apps/compare-options)
- [Rethinking Background Workloads with Azure Functions on Azure Container Apps | Microsoft Community Hub](https://techcommunity.microsoft.com/blog/appsonazureblog/rethinking-background-workloads-with-azure-functions-on-azure-container-apps/4496861)
- [Azure Functions Error Handling and Retry Guidance | Microsoft Learn](https://learn.microsoft.com/en-us/azure/azure-functions/functions-bindings-error-pages)

**Storage immutability and audit (HIGH confidence — official Microsoft Learn):**
- [Overview of immutable storage for blob data — Azure Storage | Microsoft Learn](https://learn.microsoft.com/en-us/azure/storage/blobs/immutable-storage-overview)
- [Computer Forensics Chain of Custody in Azure | Microsoft Learn](https://learn.microsoft.com/en-us/azure/architecture/example-scenario/forensics/)
- [Immutable Blobs Inside Azure Storage (WORM) | Microsoft Community Hub](https://techcommunity.microsoft.com/blog/coreinfrastructureandsecurityblog/immutable-blobs-inside-azure-storage-worm/3843611)

**Data architecture patterns (MEDIUM — community best practice + Microsoft Learn):**
- [What is the medallion lakehouse architecture? — Azure Databricks | Microsoft Learn](https://learn.microsoft.com/en-us/azure/databricks/lakehouse/medallion)
- [Prepare your data for GDPR compliance — Azure Databricks | Microsoft Learn](https://learn.microsoft.com/en-us/azure/databricks/security/privacy/gdpr-delta)
- [Using ETL Staging Tables — Tim Mitchell](https://www.timmitchell.net/post/2017/06/14/etl-staging-tables/)
- [SQL Server ETL in 2026 — DEV Community](https://dev.to/kuznetsova/sql-server-etl-in-2026-what-actually-works-and-what-doesnt-4nab)

**LLM gateway landscape (MEDIUM — multiple recent comparisons; product churn high):**
- [HIPAA-Compliant AI: What Developers Need to Know | Aptible](https://www.aptible.com/hipaa/hipaa-compliant-ai)
- [Top 5 LLM Gateways in 2026 | DEV Community](https://dev.to/varshithvhegde/top-5-llm-gateways-in-2026-a-deep-dive-comparison-for-production-teams-34d2)
- [Best LiteLLM Alternative for Enterprises in 2026 | Maxim](https://www.getmaxim.ai/articles/best-litellm-alternative-for-enterprises-in-2026/)
- [6 Best LLM Gateways in 2026 | TrueFoundry](https://www.truefoundry.com/blog/best-llm-gateways)

**Compliance automation (MEDIUM — vendor-aligned but consistent across sources):**
- [Azure Integration Guide | Drata Help Center](https://help.drata.com/en/articles/5032404-azure-integration-guide)
- [Vanta vs Drata: Complete 2026 Comparison | Comp AI](https://trycomp.ai/vanta-vs-drata)

**ConnectWise (HIGH — vendor docs + community libraries):**
- [ConnectWise Manage API Essential Guide | Rollout](https://rollout.com/integration-guides/connect-wise-manage/api-essentials)
- [connectwise-rest npm](https://www.npmjs.com/package/connectwise-rest)
- [ConnectWise PSA REST API Patterns | mcpmarket](https://mcpmarket.com/tools/skills/connectwise-psa-api-patterns)

---
*Architecture research for: Barycenter (MSP operations data platform with two-zone Azure SQL + AI-safety boundaries)*
*Researched: 2026-05-01*
