# Stack Research

**Domain:** MSP-internal AI data platform (Azure-native, HIPAA-floor, SOC 2-aspirational, Anthropic Claude as LLM)
**Researched:** 2026-05-01
**Confidence:** HIGH (Azure platform services, Anthropic SDK, identity stack); MEDIUM (LLM-gateway pattern, ETL framework choice — both have legitimate alternatives)

---

## Executive Summary

The 2026-current stack for Barycenter is **Azure-native everywhere it touches data, identity, or audit**, with two well-justified non-Azure choices:

1. **Anthropic Claude API + BAA + ZDR** as the LLM (constraint-given, but verified BAA terms below).
2. **Drata** as the continuous-controls platform (Azure Purview Compliance Manager doesn't currently produce auditor-ready SOC 2 evidence at the depth a B2B questionnaire demands).

The key opinionated calls in this stack:

- **Azure SQL Database (single instance, General Purpose vCore Gen5, DC-series for Always Encrypted secure enclaves)** — not Hyperscale, not Managed Instance. Schema isolation is sufficient; DC-series is required if you want enclave-backed `JOIN` and range queries on encrypted columns.
- **Custom Python workers in Azure Container Apps**, not Azure Data Factory or Synapse — for 20–50 SaaS APIs each with bespoke auth/pagination/rate-limit semantics, ADF's connector model is a poor fit and dbt sits below ingestion. Use **dbt-fabric/dbt-sqlserver for in-database transformations** (raw → AI zone), not for ingestion.
- **Azure API Management AI Gateway** as the LLM gateway — not LiteLLM, not a custom Function. APIM has first-class `llm-token-limit`, `llm-emit-token-metric`, `llm-content-safety`, and managed-identity authentication to non-Azure-OpenAI providers (including Anthropic), with Azure-native HIPAA defensibility. PII scrubbing layered in via Azure AI Content Safety + a custom Presidio-backed inbound/outbound transform.
- **Azure SQL Ledger (append-only) + WORM blob mirror + Microsoft Sentinel** — three-tier audit. Ledger gives in-database tamper evidence with cryptographic chain; WORM blob is the cold legal-hold archive; Sentinel is the off-system observability/SIEM plane. The chain hash you write yourself (FOUND-04 / AUDIT-01) lives inside ledger rows.
- **Entra ID + PIM + FIDO2 + Conditional Access + per-service managed identities** — no surprises here; this is the 2026 Azure-native identity baseline and what HIPAA / SOC 2 auditors expect to see.

What this stack explicitly avoids: GCC High (out of scope per PROJECT.md), public OpenAI / OpenAI-SDK direct, generic Postgres on Azure, LiteLLM-as-gateway (operational ownership concerns), Microsoft Fabric (overkill, half the surface is irrelevant), Azure AD B2C (wrong product), and any LLM provider without a current BAA.

---

## Recommended Stack

### Core Platform Services

| Technology | Version / Tier | Purpose | Why Recommended |
|------------|----------------|---------|-----------------|
| **Azure SQL Database** | General Purpose, vCore Gen5, **DC-series hardware**, 4 vCore start (scale to 8) | Two-zone schema-isolated relational store (`raw_*` + `ai_zone.*`) | DC-series is the **only** SKU that supports Intel SGX enclaves for Always Encrypted with secure enclaves, which is what makes RESTRICTED columns queryable with `JOIN`/range/`LIKE` rather than equality-only. VBS enclaves work on any tier but offer weaker hardware isolation. Single instance + schema permissions matches PROJECT constraint and is cheaper to operate than two databases. **Confidence: HIGH.** |
| **Azure SQL Ledger** (append-only ledger tables) | Built-in feature, SQL Server 2022+ engine | Tamper-evident audit log inside the database | Append-only ledger tables reject `UPDATE`/`DELETE` at the engine level and emit a database digest you publish to Azure Storage with a tamper-protection policy. This is the *first* layer of AUDIT-01's cryptographic chain — your application-level SHA-256 chain rides on top, which means an attacker has to defeat **both** to forge history. **Confidence: HIGH.** |
| **Azure Storage (Blob, Cool tier)** | Standard GRS, immutable container with **time-based retention policy + legal hold capability** | Cold archive for audit log, raw-zone retention spillover, ledger digest publication | Container-level WORM with a **locked** time-based retention policy (6 years for HIPAA-tagged audit) is Cohasset-validated for SEC 17a-4(f) / FINRA / HIPAA-equivalent immutability. Once locked, *not even the subscription owner* can shorten retention — which is exactly the property you want for audit defensibility. **Confidence: HIGH.** |
| **Microsoft Sentinel** | Pay-As-You-Go ($5.20/GB) at v1 volume, switch to 100GB Commitment Tier ($2.96/GB) once daily ingest > 30GB | SIEM, off-system observability, HIPAA compliance reporting | Sentinel inherits Azure's SOC 2 Type 2 / HIPAA / ISO 27001 attestations, has a **HIPAA Compliance Solution** (preview as of 2026) with prebuilt dashboards, and is the path-of-least-resistance for the "compromised primary system can't tamper its own audit log" property because logs forward via the Log Analytics agent into a separate identity boundary. **Confidence: HIGH.** |
| **Azure Container Apps** (Consumption + Dedicated workload profile) | API 2025-01-01 GA | Hosting for Python ETL workers and the typed-tool-function service | KEDA-based event-driven autoscaling (including scale-to-zero), first-class managed identity, VNet integration for the EGRESS-01 allowlist, and a saner deployment model than Functions for long-running stateful sync jobs. Container Apps is also where Azure Functions itself runs in 2026 if you want the trigger model — but for 20–50 distinct SaaS adapters, plain Container Apps + your own scheduler is cleaner. **Confidence: HIGH.** |
| **Azure API Management** | Standard v2 tier (or Premium if multi-region needed; v1 doesn't need multi-region) | LLM gateway in front of Anthropic; central enforcement of token budgets, content safety, audit | Native `llm-token-limit`, `llm-emit-token-metric`, `llm-content-safety`, `llm-semantic-cache-store/lookup` policies. **Crucially: APIM officially supports OpenAI-compatible and passthrough LLM endpoints from non-Microsoft providers** including Anthropic — managed-identity auth + policies apply. This is the cleanest "Azure-native HIPAA-defensible LLM gateway" pattern available in 2026 and avoids you operating LiteLLM yourself. **Confidence: HIGH.** |
| **Microsoft Entra ID (P2)** + **Privileged Identity Management** + **Conditional Access** | P2 license required for PIM | Identity, JIT admin, MFA, Conditional Access policies | P2 is non-negotiable for PIM (IDENT-02). FIDO2 passkeys are GA in Entra and are the phishing-resistant MFA method for privileged roles (IDENT-01). The Microsoft-recommended pattern is: all admin grants are "eligible" not "active", activation requires FIDO2 + justification + ticket, with 2 break-glass FIDO2 keys in a physical safe. **Confidence: HIGH.** |
| **Azure Key Vault (Standard tier)** | Standard SKU with RBAC, soft-delete, purge protection enabled | Per-tenant HMAC salts (FOUND-03), Always Encrypted column master keys, app secrets | Standard tier is sufficient for v1 (HSM-backed keys deferred per Out-of-Scope). Supports HMAC-SHA256/384/512 sign operations natively, which is what `person_pid = HMAC(email, per_tenant_salt)` needs. RBAC scope at `/keys/<key-name>` lets you give the ETL identity sign-only access to a specific salt, and the agent identity zero access. Purge protection + soft-delete are required for HIPAA defensibility. **Confidence: HIGH.** |
| **Anthropic Claude API** (claude-sonnet-4-5, claude-opus-4-7) | SDK `anthropic>=0.42` | Primary LLM | Constraint-given by project. Anthropic achieved SOC 2 Type II + HIPAA certification in March 2026. BAA is available with the first-party API or Enterprise plan; **ZDR is a separate request and must be confirmed in writing per COMP-01**. Note: BAA covers the Messages API + prompt caching + structured outputs; **does not cover** Batch API, Files API, Code Execution, Computer Use, Web Fetch — exclude these from Barycenter. **Confidence: HIGH.** |
| **Drata** | Foundation tier ($7.5K–$10K/yr) | Continuous controls evidence for SOC 2 + HIPAA | Picks up auditor-ready evidence from Azure (Entra, Defender, Sentinel), GitHub, the HRIS, and the laptop fleet. Vanta is comparable; Drata wins on HIPAA depth and on dual-framework cross-mapping (which you need: SOC 2 + HIPAA + future ISO 27001). **Microsoft Purview Compliance Manager is *not* a substitute** — it's a posture-assessment tool, not an evidence-collection-and-auditor-handoff platform. **Confidence: MEDIUM** — this is a real choice and Vanta is a defensible alternative; see Alternatives below. |

### Supporting Libraries (Python — primary language for ETL workers and tool-function service)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **anthropic** | `>=0.42, <1.0` | Claude SDK with native `cache_control` typing | The tool-function service that calls the LLM via APIM. v0.42+ gives you typed `cache_creation_input_tokens` / `cache_read_input_tokens` in `usage`. |
| **azure-identity** | `>=1.19` | `DefaultAzureCredential`, `ManagedIdentityCredential`, `WorkloadIdentityCredential` | Every service-to-service auth. Never use connection strings or client secrets in app code. |
| **azure-keyvault-secrets** + **azure-keyvault-keys** | `>=4.10` | Salt + secret retrieval; HMAC sign operations | `person_pid` derivation runs as a Key Vault `sign(HS256, ...)` call so the salt material *never enters application memory*. |
| **azure-monitor-opentelemetry** | `>=1.7` | Structured logging + tracing into Application Insights / Log Analytics | Required to feed Sentinel and to satisfy the "audit-of-audit" pattern (AUDIT-02). OpenTelemetry semantic conventions for GenAI emit token counts automatically. |
| **azure-storage-blob** | `>=12.24` | Audit-log mirror writes, ledger-digest publish, retention-tier archive | All audit writes go to a container with `immutability_period_since_creation_in_days=2190` (6 years) and **legal hold** for HIPAA-tagged tenants. |
| **pyodbc** + **azure-identity** AAD-token auth | pyodbc `>=5.2`, MS ODBC Driver 18 | Azure SQL connectivity using Entra workload identity (no passwords) | Always Encrypted column-level decrypt happens client-side; the ODBC driver supports Always Encrypted with secure enclaves out of the box. |
| **sqlalchemy** | `>=2.0` (typed) | ORM where useful for typed tool functions | Optional. For ETL workers writing to `raw_*` tables, prefer parameterized SQL via pyodbc to keep field-class invariants visible in code review. |
| **pydantic** | `>=2.10` | Field-class tagged DTOs; agent-emitted action validation | Every typed tool function returns a Pydantic model. ACCESS-03 agent actions are Pydantic-validated before the dispatcher runs. |
| **alembic** | `>=1.14` | Schema migrations for `raw_*` and `ai_zone.*` | Schema changes are dual-control change-management events (per IDENT-02); Alembic migrations get reviewed + signed off in PRs. |
| **dbt-core** + **dbt-sqlserver** | dbt `>=1.9`, dbt-sqlserver `>=1.8` | Raw → AI zone transformations as code (the eight standard primitives encoded as dbt macros) | dbt is for *in-database* transformations from `raw_*` to `ai_zone.*` views/tables. Not for ingestion. dbt-sqlserver is the maintained adapter; dbt-fabric is the Fabric-targeted alternative if you ever migrate to Fabric Warehouse. |
| **presidio-analyzer** + **presidio-anonymizer** | `>=2.2.358` | PII detection + redaction inside the APIM custom policy + canary scanner | Microsoft's open-source, Microsoft-supported PII engine. Used (a) in the APIM inbound/outbound policy for ACCESS-04 gateway scrubbing, (b) by VER-01 leak test runner. |
| **msgraph-sdk** + **azure-identity** | msgraph-sdk `>=1.16` | Microsoft Graph ingestion (INT-03) | Official Microsoft SDK; async-friendly; works with `ClientSecretCredential` or workload identity. |
| **pyconnectwise** | `>=0.5` | ConnectWise Manage API client (INT-01) | Type-annotated, OpenAPI-generated client — pick this over `connectpyse` because the typing helps enforce field-class tagging at the adapter layer. **Confidence: MEDIUM** — pin the version because the upstream is small-team. |
| **httpx** | `>=0.28` | Generic SaaS API client for tools without a maintained Python SDK (Pax8, Ninja RMM, Datto, SentinelOne, Duo, FortiQuote) | Use one shared `httpx.AsyncClient` per adapter with retry + rate-limit middleware. Standardize the per-tool ETL recipe (TOOL-02) on top of httpx. |
| **tenacity** | `>=9.0` | Retries with exponential backoff + jitter for SaaS APIs | Every adapter wraps its `httpx` calls; rate-limit-aware retry is a standard primitive. |

### Development & Operations Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| **uv** (or **poetry**) | Python dependency / virtualenv management | `uv` is faster and is Astral's 2026 standard; either works. Lockfile committed. |
| **ruff** | Linter + formatter | Replaces black + isort + flake8 + pylint. Fast enough to run pre-commit. |
| **mypy** in `--strict` | Static typing | Field-class invariants get encoded in `Annotated[str, FieldClass.RESTRICTED]` types; mypy enforces. |
| **pytest** + **pytest-asyncio** | Test framework | Standard. |
| **GitHub Actions** | CI/CD | Runs VER-01 leak test on every PR touching `raw_*` schemas, views, ETL, or grants. Workload identity federation to Azure (no long-lived secrets per IDENT-03). |
| **Bicep** (or Terraform) | IaC for Azure resources | Bicep recommended for an Azure-only stack — first-party, ARM-native, and PR-reviewable. Terraform is fine if you already have multi-cloud habits. |
| **GitHub Advanced Security** | Code scanning, secret scanning, dependency review | Required-control evidence for Drata. Catches accidental secret commits before they hit any audit. |
| **Microsoft Defender for Cloud** | CSPM + workload protection | Feeds Sentinel. Defender for SQL on the Azure SQL DB is mandatory for HIPAA threat-detection control evidence. |
| **Azure Monitor Workbooks / Log Analytics** | Operational dashboards | Token spend per tenant, agent activity, ETL freshness, leak-test results. |
| **Microsoft Purview Data Map** (optional) | Field-class tagging surface for auditors | Optional; the source-of-truth for FOUND-02 / VER-02 lives in the codebase, but Purview can mirror it for auditor-friendly reporting. |

---

## Installation

```bash
# Core Python runtime + tooling
uv venv && uv pip install --upgrade pip

# Application dependencies
uv pip install \
  "anthropic>=0.42,<1.0" \
  "azure-identity>=1.19" \
  "azure-keyvault-secrets>=4.10" \
  "azure-keyvault-keys>=4.10" \
  "azure-storage-blob>=12.24" \
  "azure-monitor-opentelemetry>=1.7" \
  "pyodbc>=5.2" \
  "sqlalchemy>=2.0" \
  "pydantic>=2.10" \
  "alembic>=1.14" \
  "presidio-analyzer>=2.2.358" \
  "presidio-anonymizer>=2.2.358" \
  "msgraph-sdk>=1.16" \
  "pyconnectwise>=0.5" \
  "httpx>=0.28" \
  "tenacity>=9.0"

# Transformation layer (separate venv for dbt — it has tight pin requirements)
uv pip install "dbt-core>=1.9" "dbt-sqlserver>=1.8"

# Dev dependencies
uv pip install --group dev \
  "ruff>=0.8" \
  "mypy>=1.13" \
  "pytest>=8.3" \
  "pytest-asyncio>=0.24" \
  "pytest-cov>=6.0"

# OS-level: Microsoft ODBC Driver 18 for SQL Server (required for Always Encrypted)
# Install per platform from https://learn.microsoft.com/sql/connect/odbc/
```

---

## Alternatives Considered

| Recommended | Alternative | When the Alternative Wins |
|-------------|-------------|---------------------------|
| **Azure SQL Database (single instance, DC-series)** | Azure SQL Managed Instance | If a customer demands physically separate storage per tenant or a cross-database query pattern emerges. SQL MI is more expensive and operationally heavier; Barycenter doesn't need it. |
| **Azure SQL Database General Purpose** | Hyperscale | If raw-zone storage exceeds ~1 TB. At 5–50 GB / 5-year horizon you're well inside General Purpose. Hyperscale also doesn't currently support Always Encrypted with secure enclaves on Intel SGX hardware as of 2026 — this is a hard dealbreaker. |
| **Custom Python workers (Container Apps)** | Azure Data Factory | If your ingestion was 3-5 sources with first-party ADF connectors (e.g., Salesforce, ServiceNow). For 20–50 bespoke MSP-tool APIs each with weird auth/pagination, ADF's connector model is more friction than help. |
| **Custom Python workers** | Microsoft Fabric Data Pipelines | If you commit to Fabric end-to-end (Warehouse + OneLake + dbt-fabric). For Barycenter, Fabric is a much bigger surface than needed and the security model around Fabric workspaces is less battle-tested than Azure SQL schema permissions. |
| **dbt-sqlserver for transformations** | Stored procedures + Alembic | If your team is more SQL-native than Python-native. dbt is winning the modern-data-stack race because models are versioned, testable, and PR-reviewable — which directly serves SOC 2 change-management. |
| **Azure API Management AI Gateway** | LiteLLM proxy (self-hosted on Container Apps) | LiteLLM has the broadest provider support and richer Presidio/Pillar guardrail integrations *out of the box*. **Choose LiteLLM if** Anthropic adds new features (like Files API or Computer Use) that APIM doesn't proxy fast enough, or if you want streaming-native semantic caching that APIM's policy can't yet express. The HIPAA tradeoff: you operate it, you patch it, you write the BAA-relevant runbook. For a single-LLM internal platform, APIM wins on ops-burden. |
| **Azure API Management AI Gateway** | Custom Azure Function gateway | Don't. You'll reimplement token-limit, content-safety, semantic-cache, emit-token-metric, OAuth, and circuit-breaker policies — and your auditor will ask you to prove each one works. APIM has them as one-line policy XML with managed observability. |
| **Drata** | Vanta | Vanta has wider integrations (400+) and better AI-agent-driven control narratives in 2026. Choose Vanta if you anticipate >5 frameworks (SOC 2 + ISO 27001 + ISO 42001 + HIPAA + PCI), or if the auditor you've selected is part of Vanta's auditor network. Drata wins if HIPAA evidence depth and pricing are the dominant factors. |
| **Drata** | Hyperproof | If you have a controls-heavy parent company already on Hyperproof. Hyperproof is more "GRC platform" than "fast SOC 2 startup tool"; for Gravity, Drata is more right-sized. |
| **Drata** | Microsoft Purview Compliance Manager | **Never as the primary**. Purview is for posture assessment inside Microsoft 365 / Azure; it does not produce auditor-ready SOC 2 evidence packages, doesn't ingest from non-Microsoft sources, and isn't auditor-network-integrated. Use it as a *supplementary* signal feeding Drata. |
| **Anthropic Claude API direct** | Anthropic via Amazon Bedrock | Bedrock would route via AWS, which adds an entire second cloud BAA, second identity plane, and second egress story. Project constraint pins Azure + Anthropic-direct; this is the right call. |
| **Microsoft Sentinel** | Splunk / Datadog SIEM | If you already have a Splunk/Datadog footprint at Gravity. For greenfield Azure, Sentinel is cheapest and Azure-native; the SOC 2 and HIPAA reporting solutions are first-party. |
| **FIDO2 hardware keys (YubiKey, Feitian)** | Microsoft Authenticator passkey on phone | Phone passkeys are fine for general user MFA. Privileged roles (PIM-eligible admin, key rotation, schema change approver) should require *hardware* FIDO2 — a phone is in your pocket near the work laptop, which is a weaker isolation boundary than a separate physical key. |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| **Direct OpenAI Python SDK calls (`openai.ChatCompletion.create`)** | Bypasses APIM gateway → no token budgets, no content safety, no audit, no PII scrubbing, no canary detection. Even if you're calling Anthropic via OpenAI-compatible mode, the call should go through APIM. | All LLM calls route through the APIM gateway endpoint, including dev/test traffic. |
| **Anthropic SDK in `messages.batches` (Batch API), Files API, Computer Use, Web Fetch, Code Execution with network** | **Not covered by Anthropic's BAA in 2026.** Using these with PHI is a HIPAA violation. | Stick to `messages.create` (sync/streaming), structured outputs, and prompt caching — these are BAA-covered. If you need batch behavior, batch your own calls in your worker. |
| **Azure SQL Basic / Standard DTU tiers in production** | Already flagged in PROJECT.md as dev-only (5 DTU collapses under real ingestion load). Also: DTU tiers don't offer DC-series hardware → no Intel SGX enclaves → degraded Always Encrypted ergonomics. | vCore General Purpose, Gen5, **DC-series** for production. |
| **Public network access enabled on Azure SQL** | Surfaces the database to the public internet by default. Conflicts with global instructions and HIPAA threat model. | `publicNetworkAccess = Disabled`; private endpoint inside the agent VNet; firewall rule allowlist for break-glass admin only. |
| **SQL authentication / contained-DB users with passwords for application identities** | Long-lived secrets violate IDENT-03. Rotation is procedural, not architectural. | Microsoft Entra authentication only; per-service managed identity; AAD tokens via `azure-identity`. |
| **LiteLLM as the *primary* LLM gateway** | You take on operational ownership of an open-source proxy in your HIPAA boundary — patching, BAA fan-out, scaling, audit-evidence collection. APIM gives you Microsoft-attested compliance inheritance and managed observability. | APIM AI Gateway. (Use LiteLLM in dev to test multi-provider portability if needed, not in prod path.) |
| **Microsoft Fabric (full stack)** | Two of the four Fabric pillars (Real-Time Intelligence, Data Science / Notebooks) are irrelevant for Barycenter, the workspace identity model is less mature than Azure SQL schema permissions for the leak-boundary property, and Fabric ingestion is still rougher than purpose-built Python workers. | Azure SQL DB + Container Apps + dbt-sqlserver. Revisit Fabric if Gravity's analytics needs grow beyond Barycenter. |
| **Azure AD B2C / Entra External ID** | Wrong product — that's customer-facing identity. Barycenter is internal-only, Gravity-employees-only. | Entra ID (employees) + service-principals/managed-identities (services). |
| **Premium Key Vault / Managed HSM (FIPS 140-2 Level 3)** | Explicitly out of scope per PROJECT.md. Adds ~$3K/month + RBAC complexity for a property no current customer demands. | Standard Key Vault with RBAC, soft-delete, purge protection. Architecture allows the upgrade later. |
| **Azure Confidential Containers (confidential computing)** | Out of scope per PROJECT.md. Bleeding-edge, expensive, defensive-depth-only, no current threat model justifies it. | Standard Container Apps. |
| **Public-internet-accessible APIM developer portal** | Discoverable, scannable, attack surface for a tool that has no external developers. | APIM internal-only deployment, or developer portal disabled entirely. APIs surfaced to internal agents via private endpoint. |
| **Connection-string-style secrets in App Configuration / env vars** | All long-lived secrets violate IDENT-03 + COMP-02. Even Key-Vault-backed env vars are weaker than a sign-time reference. | Key Vault references resolved at request-time via managed identity; HMAC operations performed *inside* Key Vault, never with extracted key material. |
| **Generic OpenAI-style "PII filter" middleware (regex-only)** | Catches obvious patterns, misses the long tail (foreign address formats, MRNs, internal IDs). High false-negative rate. | Microsoft Presidio (recognizers + custom recognizers per tool) layered with regex for structured tokens (CW IDs, serial numbers, canary tokens). |
| **Synchronous chain-hash audit-write inline with the prompt path** | Adds tail latency to every LLM call; chain becomes a single-writer bottleneck. | Async append into a queue (Service Bus or Event Hubs) → single writer drains into ledger table + WORM blob mirror. AUDIT-01 chain integrity is preserved by single-writer; AUDIT-02 audit-of-audit covers the queue path. |

---

## Stack Patterns by Variant

**If a customer demands physical storage isolation:**
- Move that customer's `raw_*` schemas into a separate Azure SQL DB on the same logical server.
- AI-zone views and the agent identity stay on the primary; cross-DB queries via elastic query.
- Cost: ~2x baseline DB cost per isolated tenant. Don't volunteer this; build for it when asked.

**If a customer demands customer-managed keys (CMK):**
- Already architected per ENC-01: Azure SQL TDE with customer-managed key in their Key Vault.
- For Always Encrypted column master keys, the key lives in Gravity's Key Vault by default; CMK shifts CMK ownership to the customer's Key Vault with cross-tenant access policy. Operationally heavy but documented.

**If raw-zone volume blows past ~200 GB before year 5:**
- Switch to Hyperscale **only if** Intel SGX enclaves are GA on Hyperscale by then (verify at the time — was not GA as of 2026-05).
- Otherwise: monthly partitioning + cold-archive-to-Parquet on Blob (already in OPS-01).

**If Anthropic releases a feature that's not BAA-covered but you want it (e.g., Batch API):**
- Don't use it on PHI-tagged tenants. Period.
- Build a parallel non-PHI path that goes through the same APIM gateway with a different policy bundle, and gate it on `cui_handling_required = false AND has_phi = false` at the dispatcher.

**If SOC 2 audit pursuit begins:**
- Drata enters "evidence-collection mode" (it's already wired in per COMP-02).
- Add quarterly access-review automation, vendor-risk module, employee onboarding/offboarding triggers from the HRIS, and laptop-fleet posture (Defender for Endpoint).
- Auditor selection: pick from Drata's auditor network for fastest evidence handoff (Prescient Assurance, Johanson Group, A-LIGN are common). 6-month observation window starts at evidence-collection start.

---

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| `anthropic >= 0.42` | Python 3.10+ | Native `cache_control` typing requires 0.40+; `usage` field typing tightened in 0.42. **Pin <1.0** until a 1.0 release is announced — major version may rename fields. |
| `pyodbc >= 5.2` | MS ODBC Driver 18 | Driver 17 lacks Always Encrypted with secure enclaves attestation flow. **Use Driver 18 in production**. |
| `dbt-sqlserver >= 1.8` | dbt-core >= 1.9 | Adapter version tracks dbt-core minor versions tightly. Don't mix major versions. Run dbt in its own venv. |
| `azure-identity >= 1.19` | Azure Container Apps managed identity | `WorkloadIdentityCredential` is the right choice on Container Apps + Entra workload identity federation; `DefaultAzureCredential` works but is slower (chain probing). |
| `presidio-analyzer >= 2.2.358` | spaCy `>=3.7` | Presidio uses spaCy NER under the hood. Pin spaCy version explicitly to avoid model-download surprises in CI. |
| `msgraph-sdk >= 1.16` | `azure-identity >= 1.18` | The SDK auto-uses azure-identity credentials. Service-principal auth requires `Directory.Read.All` + relevant per-resource scopes granted in app registration. |
| Azure SQL DB DC-series | Always Encrypted with secure enclaves (Intel SGX) | DC-series is the only SKU with Intel SGX. VBS enclaves work on any tier but offer weaker isolation properties. |
| Azure API Management Standard v2 | `llm-*` policies | All `llm-*` policies (token-limit, emit-token-metric, content-safety, semantic-cache) are GA on Standard v2 and Premium tiers. Basic / Developer tiers are not for production. |

---

## HIPAA / BAA Coverage Matrix

| Service | BAA Status | Notes |
|---------|------------|-------|
| Azure SQL Database | Covered under Microsoft BAA (HIPAA + HITECH) | Auto-included with Azure subscription BAA via Microsoft Online Services Terms. |
| Azure Storage (Blob) | Covered | Same as above. Immutable WORM containers count as HIPAA-grade audit retention. |
| Azure Container Apps | Covered | Same as above. |
| Azure API Management | Covered | Same as above. |
| Microsoft Sentinel | Covered | Same as above. HIPAA Compliance Solution available in preview as of 2026. |
| Microsoft Entra ID (incl. P2 / PIM) | Covered | Same as above. |
| Azure Key Vault | Covered | Same as above. |
| Azure Monitor / Log Analytics | Covered | Same as above. |
| Microsoft Defender for Cloud / SQL | Covered | Required for COMP-01 threat-detection evidence. |
| **Anthropic Claude (Messages API + prompt caching + structured outputs)** | **Covered under Anthropic BAA** | Requires explicit BAA + Zero Data Retention requests. ZDR confirmation in writing per COMP-01. |
| **Anthropic Claude (Batch API, Files API, Code Execution, Computer Use, Web Fetch)** | **NOT covered under BAA** | Don't use these with PHI. |
| **Drata** | BAA available with paid tier | Drata signs BAAs; they're a subprocessor. Listed in COMP-04 inventory. |
| **GitHub (Enterprise Cloud)** | BAA available with Enterprise + Advanced Security | If source code repos contain test fixtures with PHI patterns. Typical recommendation: keep PHI out of the repo entirely. |
| **OpenAI / direct OpenAI SDK** | Not used in this stack | N/A |
| **Anthropic Workbench / Console / Pro / Team / Free** | NOT BAA-covered | Don't paste PHI into these UIs ever. |

---

## Sources

**Authoritative (Microsoft Learn — HIGH confidence):**
- [AI gateway in Azure API Management](https://learn.microsoft.com/en-us/azure/api-management/genai-gateway-capabilities) — verified `llm-*` policies, Anthropic / non-Microsoft LLM support, semantic caching, token-limit policy semantics, content-safety policy.
- [Plan for Always Encrypted with secure enclaves — Azure SQL Database](https://learn.microsoft.com/en-us/azure/azure-sql/database/always-encrypted-enclaves-plan) — verified DC-series requirement for Intel SGX, VBS availability across all tiers.
- [Overview of immutable storage for blob data](https://learn.microsoft.com/en-us/azure/storage/blobs/immutable-storage-overview) — verified container-level WORM, time-based retention up to 400 years, legal hold, Cohasset SEC 17a-4(f) validation.
- [Ledger Overview (SQL Server / Azure SQL)](https://learn.microsoft.com/en-us/sql/relational-databases/security/ledger/ledger-overview) — verified append-only ledger tables reject UPDATE/DELETE at engine level; database digest publication.
- [Plan costs and understand pricing — Microsoft Sentinel](https://learn.microsoft.com/en-us/azure/sentinel/billing) — pricing tiers verified.
- [vCore purchasing model — Azure SQL Database](https://learn.microsoft.com/en-us/azure/azure-sql/database/service-tiers-sql-database-vcore) — General Purpose / Hyperscale / Business Critical tier semantics.
- [Microsoft Sentinel HIPAA Compliance Solution announcement](https://techcommunity.microsoft.com/blog/microsoftsentinelblog/new-compliance-solutions-in-microsoft-sentinel-hipaa--gdpr-reports/4470452) — preview availability of HIPAA Compliance Solution.
- [Azure Container Apps — Functions hosting overview](https://learn.microsoft.com/en-us/azure/azure-functions/functions-container-apps-hosting) — Container Apps as the 2026 home for both Functions and bespoke containers.
- [Microsoft Graph Python SDK](https://github.com/microsoftgraph/msgraph-sdk-python) — current package, async-friendly, azure-identity integration.
- [How to enable passkeys (FIDO2) in Microsoft Entra ID](https://learn.microsoft.com/en-us/entra/identity/authentication/how-to-authentication-passkeys-fido2) — passkey GA, profiles preview Nov 2025.
- [Require phishing-resistant MFA for Entra admin roles](https://learn.microsoft.com/en-us/entra/identity/conditional-access/policy-admin-phish-resistant-mfa) — Conditional Access pattern for privileged roles.
- [Managed HSM data plane role management](https://learn.microsoft.com/en-us/azure/key-vault/managed-hsm/role-management) — RBAC scopes for HMAC sign operations.
- [Key types, algorithms, and operations — Azure Key Vault](https://learn.microsoft.com/en-us/azure/key-vault/keys/about-keys-details) — HS256/384/512 HMAC support.

**Authoritative (Anthropic — HIGH confidence):**
- [Prompt caching — Claude API Docs](https://platform.claude.com/docs/en/docs/build-with-claude/prompt-caching) — verified 2048-token min for Sonnet 4.5, 5-minute / 1-hour TTL options, cache_control breakpoint placement strategy, 4-breakpoint maximum, cost ratios.
- [Business Associate Agreements (BAA) for Commercial Customers — Anthropic Privacy Center](https://privacy.claude.com/en/articles/8114513-business-associate-agreements-baa-for-commercial-customers) — verified BAA coverage matrix; Messages API + prompt caching + structured outputs covered; Batch / Files / Computer Use / Web Fetch / Code Execution NOT covered.
- [API and data retention — Claude API Docs](https://platform.claude.com/docs/en/build-with-claude/api-and-data-retention) — ZDR semantics.
- [Migrating to Claude 4.5 — Claude API Docs](https://console.anthropic.com/docs/en/about-claude/models/migrating-to-claude-4) — model name `claude-sonnet-4-5`.

**Industry / verified secondary (MEDIUM confidence):**
- [Drata vs Vanta: Complete 2026 Comparison — Comp AI](https://trycomp.ai/vanta-vs-drata) — pricing tiers, integration counts, framework coverage as of 2026.
- [Top Vanta Alternatives — Drata blog](https://drata.com/blog/vanta-alternatives-and-competitors) — vendor self-reporting; cross-check with Comp AI source.
- [PII Masking LLM calls using LiteLLM proxy — Microsoft Presidio docs](https://microsoft.github.io/presidio/samples/docker/litellm/) — confirms Presidio-as-PII-engine pattern for LLM gateway scrubbing.
- [Azure SQL MI Security Blueprint: SOC2 & PCI-DSS 4.0 (2026) — mytechmantra](https://www.mytechmantra.com/sql-server/azure-sql-mi-security-compliance-blueprint/) — SOC 2 control mapping (cross-checked against Microsoft Learn).

**LOW confidence — should be revalidated at phase entry:**
- Drata vs Vanta detailed pricing. Pricing pages move; confirm at procurement time.
- LiteLLM-vs-APIM specific feature parity. APIM is moving fast; revalidate at the LLM-gateway-build phase.
- pyconnectwise vs connectpyse — small upstreams, confirm maintainer activity at the CW Manage adapter phase.

---

*Stack research for: MSP-internal AI data platform (Barycenter)*
*Researched: 2026-05-01*
