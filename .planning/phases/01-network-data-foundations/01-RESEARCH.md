# Phase 1: Network & Data Foundations - Research

**Researched:** 2026-05-02
**Domain:** Azure infrastructure-as-code (Bicep) + HIPAA-grade network/identity/audit substrate
**Confidence:** HIGH (stack and architecture pre-decided in CONTEXT and project research); MEDIUM (specific Bicep module wiring patterns and chain-state SQL implementation, both design choices)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Use **Bicep** as the IaC tool for all Azure resource definitions (FortiGate, SQL, Key Vault, VNets, managed identities, Log Analytics, WORM blob). Azure-native, no state file, tight ARM integration, best fit for a single-Azure small-team project.

- **D-02:** Organize Bicep in **layered modules by concern**, not a single monolithic file:
  - `infra/networking/` — FortiGate NVA, hub VNet, spoke VNets, UDRs, NSGs
  - `infra/data/` — Azure SQL Serverless, Key Vault, private endpoints
  - `infra/identity/` — 4 managed identities, PIM role assignments
  - `infra/audit/` — Log Analytics workspace, WORM blob storage, diagnostic settings
  Each module deploys independently; NETW-02 drift detection runs per-module.

- **D-03:** Manage environment parameters via **per-env Bicep parameter files** committed to the repo (e.g., `main.dev.bicepparam`, `main.prod.bicepparam`). Secrets are not stored in param files — they reference Key Vault. This makes infra changes reviewable in PRs.

- **D-04:** All audit events are emitted by a **shared Python audit SDK** (`barycenter.audit` package). The SDK hashes the prior event, writes to Log Analytics via the DCR ingestion API, and writes synchronously. Every caller (ETL, gateway, admin tooling) imports this package — there is no parallel audit path.

- **D-05:** Chain state (the latest event's SHA-256 hash) lives in a **dedicated SQL table in the audit schema** (`audit.chain_state`, single row). Written atomically with each audit event in the same transaction. Accessible only to the audit identity.

- **D-06:** The audit write is **fail closed**: if the audit event cannot be written (Log Analytics unreachable, WORM mirror unavailable, `chain_state` locked), the parent operation is rejected. PII writes without audit coverage do not happen. An ops alert fires immediately on audit write failure.

- **D-07:** Barycenter lives in a **mono-repo**: IaC (Bicep), Python packages (audit SDK, ETL framework, gateway), SQL migrations, and CI workflows all in one repository. Branch protection (IDENT-04) is enforced once. A change touching SQL schema and the audit SDK is a single reviewable PR.

- **D-08:** CI platform is **GitHub Actions**. All gates run there: VER-02 field-class check, NETW-01 Bicep lint + `az deployment what-if`, IDENT-04 branch protection, PR-gating.

### Claude's Discretion

- **GitHub Actions Azure auth:** OIDC federated workload identity (no stored secrets, no rotation burden, aligns with IDENT-03). Claude to configure the federated credential on the deployment managed identity.
- **Audit event schema:** Field names, event types, and metadata structure — Claude designs to satisfy AUDIT-01 chaining and HIPAA §164.312(b) minimum fields.
- **VER-02 source-of-truth format:** How column field-class tags are stored (YAML manifest alongside migrations vs SQL extended properties) — Claude picks the format that makes the CI gate straightforward to implement and maintain.
- **FortiGate subnet layout:** Exact CIDR allocation, spoke count, UDR routing table design within the hub-and-spoke topology.

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within Phase 1 scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| FOUND-01 | Two-zone Azure SQL with `raw_*` and `ai_zone.*` schema isolation | §SQL Schema Topology; grant model in §Identity Topology |
| FOUND-02 | Field classification (RESTRICTED/SENSITIVE/INTERNAL/PUBLIC), drives storage/encryption/AI exposure | §Field-Class Registry & VER-02 |
| FOUND-03 | Identifier hierarchy (tenant_id, cw_company_id, serial_number, person_pid via HMAC) — Phase 1 delivers the salt service plumbing | §Salt-in-Key-Vault (HMAC sign operation) |
| FOUND-04 | Five-layer defense — Phase 1 establishes layers 1 (schema permissions) and 5 (audit chain) | §SQL Schema Topology, §Audit Chain Architecture |
| NETW-01 | FortiGate config-as-code; zero console-only rules | §FortiGate Config-as-Code; Bicep + FortiOS API |
| NETW-02 | Nightly drift detection vs config-as-code | §FortiGate Drift Detection (GitHub Actions cron) |
| NETW-03 | FortiGate logs (IDS/IPS, traffic, deny) → Log Analytics | §FortiGate Log Forwarding (FortiAnalyzer-Cloud or syslog→LA agent) |
| AUDIT-01 | SHA-256 chained audit; LA hot 90d + WORM blob 6yr | §Audit Chain Architecture |
| AUDIT-02 | Audit-of-audit (queries against audit log are themselves logged) | §Audit-of-Audit pattern (LA `_LogOperation` + audit SDK wrapper) |
| AUDIT-03 | WORM 6-year retention locked at container creation | §WORM Container Setup |
| IDENT-01 | MFA mandatory; phishing-resistant on privileged | §Conditional Access Policy stub (out-of-Bicep, scripted) |
| IDENT-02 | Entra PIM JIT; dual-control on key/schema/erasure changes | §PIM Configuration |
| IDENT-03 | 4 managed identities (etl, platform, audit, admin); no long-lived secrets | §Identity Topology |
| IDENT-04 | Branch protection + signed commits + required CI | §Repo & CI Setup |
| IDENT-05 | PIM dual-approval for `raw_*` access | §PIM Configuration |
| EGRESS-01 | FortiGate FQDN allowlist; ETL spoke and agent spoke isolated from each other | §FortiGate Policy Rules |
| ENC-01 | TDE on Azure SQL (AES-256, default-on); TLS 1.2+; AE upgrade path preserved | §Azure SQL Configuration |
| VER-02 | Field-class drift CI gate fails any PR adding column without tag | §Field-Class Registry & VER-02 |
| COMP-06 | BAA inventory (Microsoft + Anthropic + ZDR confirmation) committed to repo | §BAA Inventory Document |
</phase_requirements>

## Summary

Phase 1 is greenfield Azure infrastructure provisioning plus the load-bearing audit-chain SDK, both delivered via Bicep + Python in a fresh mono-repo. Every architectural decision has already been made in the project's two pre-existing research documents (`STACK.md`, `ARCHITECTURE.md`) and locked in CONTEXT.md — this phase's research adds (1) the specific Bicep patterns and module wiring needed to express the architecture as code, (2) the GitHub Actions OIDC configuration needed for credential-free deployment, (3) the concrete audit-chain SQL/SDK implementation, and (4) the BAA inventory deliverables.

**Primary recommendation:** Build in this order — Bicep skeleton + GitHub Actions OIDC first (so every subsequent change deploys via CI, not manual `az` commands), then network module (hub + spoke + FortiGate), then identity module (4 MIs + PIM rules), then data module (SQL + Key Vault + private endpoint), then audit module (LA + WORM + audit SDK). Lock WORM retention and audit chain format last in the phase to avoid retroactive rework. Test deny-rule provability and chain-validity provability before marking the phase complete; both are listed in success criteria.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Network perimeter / egress allowlist | FortiGate NVA (hub VNet) | Azure NSG | NVA enforces FQDN-based outbound + IDS/IPS at L7; NSG provides per-subnet L4 belt-and-suspenders |
| Data store (raw + AI zones) | Azure SQL Serverless GP | — | Single DB, schema-isolated, private-endpoint only |
| Secrets / cryptographic material | Azure Key Vault | — | HMAC-via-sign for per-tenant salts; never plaintext to caller |
| Identity boundary (service-to-service) | Entra ID managed identities | — | No long-lived secrets; workload identity for service auth |
| Identity boundary (human) | Entra PIM JIT | Conditional Access (MFA) | Standing access prohibited on `raw_*`; dual-approval gate |
| Audit recording | Python audit SDK (in-process) | Log Analytics + WORM blob | SDK is the synchronous fail-closed gate; LA + WORM are the durable destinations |
| Audit chain integrity | SQL `audit.chain_state` table | SHA-256 hash chain | Single-row table, atomic UPDATE in same tx as audit emit |
| Configuration drift detection | GitHub Actions nightly job | `az deployment what-if` + FortiOS API diff | CI is the only enforcement — no human-runnable drift check |
| Build / deploy | GitHub Actions OIDC → ARM | — | No stored secrets in GitHub; federated credential on deploy MI |
| Compliance evidence (BAAs) | `compliance/` directory in repo | — | Plaintext markdown + signed PDFs committed; reviewed annually |

## Standard Stack

### Core

| Component | Version | Purpose | Why Standard |
|-----------|---------|---------|--------------|
| Bicep CLI | 0.32+ | IaC compilation to ARM | `[CITED: learn.microsoft.com/azure/azure-resource-manager/bicep/install]` Azure-native, no state file, current-best for greenfield Azure |
| Azure CLI | 2.67+ | Deploy + drift check (`az deployment sub create`, `az deployment group what-if`) | `[CITED: learn.microsoft.com/cli/azure/install-azure-cli]` Standard CI invocation surface |
| Azure SQL Database | Serverless GP, Gen5, 0.5–2 vCore, 32 GB | Two-zone data store | `[VERIFIED: project STACK.md §1]` Tier sized for 25% duty cycle, ~$50/mo; TDE on by default |
| FortiGate-VM02 BYOL | FortiOS 7.4+ on Standard_F2s_v2 | Network perimeter | `[VERIFIED: project STACK.md §3]` Gravity holds MSSP license; 15 Gbps L3 (300x headroom) |
| Azure Key Vault | Standard tier, RBAC mode | Per-tenant HMAC salts + Anthropic API key | `[CITED: learn.microsoft.com/azure/key-vault/keys/about-keys]` HMAC-via-`sign` operation never returns plaintext key material |
| Azure Storage (Blob) | Cool tier, GRS, immutable container | WORM audit mirror | `[VERIFIED: project STACK.md §5]` Cohasset-validated SEC 17a-4(f) for 6-year retention |
| Log Analytics Workspace | Pay-as-you-go, 90-day retention | Hot audit tier + FortiGate log sink + KV/SQL diagnostics | `[CITED: learn.microsoft.com/azure/azure-monitor/logs/log-analytics-overview]` Standard for HIPAA §164.312(b) recording |
| Azure Monitor Data Collection Rule (DCR) + Logs Ingestion API | API version 2023-01-01 | Custom-table audit ingestion from Python SDK | `[CITED: learn.microsoft.com/azure/azure-monitor/logs/logs-ingestion-api-overview]` Modern replacement for HTTP Data Collector API; AAD-authenticated |
| GitHub Actions | — | CI/CD platform; OIDC federation to Azure | `[VERIFIED: D-08]` Per CONTEXT.md decision |
| Entra PIM | P2 license required | JIT admin + dual approval | `[CITED: learn.microsoft.com/entra/id-governance/privileged-identity-management/pim-configure]` Required for IDENT-02/IDENT-05 |

### Supporting (Python)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `azure-identity` | >=1.19 | Managed-identity token acquisition | All Azure SDK callers in audit SDK and ETL |
| `azure-monitor-ingestion` | >=1.0 | Logs Ingestion API client (Python) | Audit SDK writes to LA custom table |
| `azure-keyvault-keys` | >=4.10 | Key Vault `sign` operation for HMAC | Salt service (etl-identity HMACs email via KV sign) |
| `azure-storage-blob` | >=12.24 | WORM container append-blob writes | Audit SDK mirror path |
| `pyodbc` or `aioodbc` | >=5.2 / >=0.5 | Azure SQL connection (managed-identity-auth) | Audit SDK chain_state UPDATE; later phases for ETL |
| `pydantic` | >=2.10 | Audit event schema validation | Audit SDK request/response models |
| `pytest` | >=8.3 | Test framework | Audit SDK unit tests, Bicep `what-if` snapshot tests, chain-validity test |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Bicep | Terraform | Terraform is multi-cloud and has richer ecosystem; Bicep is pre-decided in D-01. Terraform's state file also adds operational burden a small team avoids. |
| GitHub Actions OIDC | Service principal + client secret | Secret rotation burden + secret-in-CI risk; OIDC eliminates both `[CITED: github.com/Azure/login#login-with-openid-connect-oidc-recommended]` |
| FortiGate REST API for config push | FortiManager (Fortinet's own config orchestrator) | FortiManager is another VM (~$60/mo more) — overkill for a single FortiGate. REST API + version-controlled JSON in repo is sufficient. |
| Logs Ingestion API + DCR | Legacy HTTP Data Collector API | HTTP Data Collector API is deprecated September 2026 `[CITED: learn.microsoft.com/azure/azure-monitor/logs/data-collector-api]` — must use Logs Ingestion API |
| WORM blob append-only | Azure Confidential Ledger | Confidential Ledger gives blockchain-style tamper-evidence but costs ~$50/mo + scope; WORM + SHA-256 chain provides equivalent mathematical tamper-evidence at ~$3/mo |
| YAML field-class manifest | SQL extended properties (`sp_addextendedproperty`) | Extended properties live with the schema (no drift), but tooling (linting, diffs) is poor; YAML is reviewable in PRs and easy to grep — recommended (see §Field-Class Registry) |

**Installation (project bootstrap):**

```bash
# Local dev tooling
brew install azure-cli bicep
pip install pre-commit

# Python project bootstrap (in repo root)
python -m venv .venv && source .venv/bin/activate
pip install azure-identity azure-monitor-ingestion azure-keyvault-keys \
            azure-storage-blob pyodbc pydantic pytest
```

**Version verification (perform during Wave 0 of plan execution):**
```bash
az version --output json | jq '.["azure-cli"]'
az bicep version
pip index versions azure-monitor-ingestion azure-identity
```

## Architecture Patterns

### System Architecture Diagram

```
                                      Internet
                                         │
                                         ▼
                            ┌────────────────────────┐
                            │   HUB VNet (10.10/22)  │
                            │  ┌──────────────────┐  │
                            │  │  FortiGate-VM02  │  │ ← outbound FQDN allowlist
                            │  │  Standard_F2s_v2 │  │   IDS/IPS, deny-by-default
                            │  └────────┬─────────┘  │   FortiOS config = Git
                            └───────────┼────────────┘
                                        │ VNet Peering (UDR 0/0 → FGT trust NIC)
                                        ▼
                ┌────────────────────────────────────────────┐
                │   SPOKE VNet (10.20/22) — Barycenter       │
                │                                            │
                │   etl-subnet     10.20.0.0/26              │ → Container Apps env A (P2+)
                │   services-subnet 10.20.0.64/26            │ → Container Apps env B (P3+)
                │   data-subnet    10.20.0.128/27            │ → SQL Private Endpoint NIC
                │   pe-subnet      10.20.0.160/27            │ → KV / Storage PEs (P1)
                │   admin-subnet   10.20.1.0/27              │ → PIM JIT bastion path
                └────────────────────────────────────────────┘
                                        │
              ┌─────────────────────────┼─────────────────────────────┐
              │                         │                             │
              ▼                         ▼                             ▼
       ┌──────────────┐         ┌──────────────┐            ┌──────────────────┐
       │ Azure SQL    │         │ Key Vault    │            │ Storage (WORM)   │
       │ Serverless   │         │ (1 vault,    │            │ + Log Analytics  │
       │ GP, PE only  │         │  RBAC, PE)   │            │ (audit sinks)    │
       │ TDE always   │         │ HMAC sign    │            │ 6-yr retention   │
       │              │         │ for salts    │            │ locked at create │
       └──────┬───────┘         └──────┬───────┘            └────────┬─────────┘
              │                        │                             ▲
              │                        │                             │
              └──────── audit.chain_state ─── (audit SDK ────────────┘
                                              writes synchronously,
                                              fail-closed)

  Identities (Entra-managed):
    mi-bary-etl       → Salt sign (KV), raw_* CRUD, audit emit
    mi-bary-platform  → ai_zone SELECT only, audit emit  (Phase 3+)
    mi-bary-audit     → LA ingest, WORM append, chain_state UPDATE
    mi-bary-admin     → PIM-eligible only, dual approval, no standing grants

  CI Pipeline (GitHub Actions, OIDC fed → mi-deploy):
    bicep what-if  → bicep deploy  → field-class CI gate (VER-02)
                                  → drift detect (NETW-02, nightly)
```

### Recommended Project Structure

```
barycenter/                          # Mono-repo root (D-07)
├── .github/
│   ├── workflows/
│   │   ├── infra-deploy.yml         # Bicep deploy on main; what-if on PR
│   │   ├── infra-drift.yml          # NETW-02 nightly drift check
│   │   ├── field-class-check.yml    # VER-02 CI gate
│   │   └── audit-chain-validate.yml # Phase 1 verification: chain-validity test
│   └── CODEOWNERS                   # IDENT-04 enforcement
├── infra/
│   ├── networking/
│   │   ├── main.bicep               # hub VNet + FortiGate VM + spoke + UDRs + NSGs
│   │   ├── modules/
│   │   │   ├── hub-vnet.bicep
│   │   │   ├── fortigate-vm.bicep
│   │   │   ├── spoke-vnet.bicep
│   │   │   └── udr-policies.bicep
│   │   └── main.dev.bicepparam      # D-03
│   ├── data/
│   │   ├── main.bicep               # Azure SQL + KV + private endpoints
│   │   ├── modules/
│   │   │   ├── sql-serverless.bicep
│   │   │   ├── key-vault.bicep
│   │   │   └── private-endpoint.bicep
│   │   └── main.dev.bicepparam
│   ├── identity/
│   │   ├── main.bicep               # 4 MIs + role assignments + PIM eligibility
│   │   ├── modules/
│   │   │   ├── managed-identity.bicep
│   │   │   └── pim-role-assignment.bicep
│   │   └── main.dev.bicepparam
│   └── audit/
│       ├── main.bicep               # LA workspace + WORM container + DCR + DCE
│       ├── modules/
│       │   ├── log-analytics.bicep
│       │   ├── worm-storage.bicep
│       │   └── data-collection-rule.bicep
│       └── main.dev.bicepparam
├── packages/
│   └── barycenter-audit/            # D-04 — shared Python audit SDK
│       ├── pyproject.toml
│       ├── src/barycenter/audit/
│       │   ├── __init__.py
│       │   ├── client.py            # AuditClient (fail-closed emit)
│       │   ├── chain.py             # SHA-256 chain logic + chain_state SQL access
│       │   ├── models.py            # Pydantic event schemas
│       │   └── sinks.py             # LA + WORM blob writers
│       └── tests/
│           ├── test_chain_integrity.py   # adversarial: tamper, missing, replay
│           └── test_fail_closed.py       # all sink failure modes reject parent op
├── sql/
│   ├── 00-schemas/
│   │   ├── 001_create_raw_cw.sql
│   │   ├── 002_create_ai_zone.sql
│   │   ├── 003_create_audit.sql     # incl. audit.chain_state
│   │   └── 004_create_pseudo.sql
│   ├── 10-grants/
│   │   ├── 001_etl_grants.sql       # raw_* CRUD, no ai_zone
│   │   ├── 002_audit_grants.sql     # audit.chain_state UPDATE only
│   │   └── 003_admin_revoke.sql     # zero standing grants on raw_*
│   └── 20-seed/
│       └── 001_chain_genesis.sql    # initial row in audit.chain_state
├── compliance/
│   ├── field-class-registry.yaml    # VER-02 source of truth
│   ├── baa-inventory.md             # COMP-06
│   ├── baa/
│   │   ├── microsoft-baa-reference.md   # link + signature date
│   │   ├── anthropic-baa.pdf            # signed copy
│   │   └── anthropic-zdr-confirmation.md # written ZDR scope confirmation
│   └── runbooks/
│       └── chain-validate.md        # how to verify chain integrity end-to-end
├── scripts/
│   ├── ci/
│   │   ├── field_class_check.py     # VER-02 implementation
│   │   ├── chain_validate.py        # AUDIT-01 verification
│   │   └── fortigate_drift.py       # NETW-02 implementation
│   └── deploy/
│       └── bootstrap-oidc.sh        # one-time GitHub OIDC fed credential setup
└── CLAUDE.md                        # Project-specific Claude instructions
```

### Pattern 1: Bicep Layered-Module Deployment with `what-if` PR Gate

**What:** Each `infra/<module>/main.bicep` deploys independently. PRs trigger `az deployment group what-if`; main-branch merges trigger actual `az deployment group create`. State lives entirely in ARM (no Terraform-style state file) `[VERIFIED: D-01]`.

**When to use:** Every infra change in this project — no manual `az` commands after Wave 0.

**Example:** `[CITED: learn.microsoft.com/azure/azure-resource-manager/bicep/deploy-cli]`

```bash
# PR check (in GitHub Actions, after OIDC login)
az deployment group what-if \
  --resource-group rg-barycenter-dev \
  --template-file infra/networking/main.bicep \
  --parameters infra/networking/main.dev.bicepparam

# Merge to main
az deployment group create \
  --resource-group rg-barycenter-dev \
  --template-file infra/networking/main.bicep \
  --parameters infra/networking/main.dev.bicepparam
```

### Pattern 2: GitHub Actions OIDC Federation (no stored secrets)

**What:** A deploy-only managed identity (`mi-bary-deploy`) has a federated credential pointing at `repo:gravity/barycenter:ref:refs/heads/main` (and `:pull_request` for PR what-if). The workflow uses `azure/login@v2` with `client-id` + `tenant-id` + `subscription-id` (no client secret).

**When to use:** All workflows that touch Azure. No exceptions; no service-principal secrets in GitHub Secrets.

**Example:** `[CITED: github.com/Azure/login#login-with-openid-connect-oidc-recommended]`

```yaml
permissions:
  id-token: write
  contents: read
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: azure/login@v2
        with:
          client-id: ${{ vars.AZURE_DEPLOY_CLIENT_ID }}
          tenant-id: ${{ vars.AZURE_TENANT_ID }}
          subscription-id: ${{ vars.AZURE_SUBSCRIPTION_ID }}
      - run: az deployment group create --template-file infra/networking/main.bicep ...
```

**Federated credential setup (one-time bootstrap):** `[CITED: learn.microsoft.com/entra/workload-id/workload-identity-federation-create-trust-github]`

```bash
az identity federated-credential create \
  --name "github-main" \
  --identity-name mi-bary-deploy \
  --resource-group rg-barycenter-identity \
  --issuer https://token.actions.githubusercontent.com \
  --subject "repo:gravity/barycenter:ref:refs/heads/main" \
  --audience api://AzureADTokenExchange
```

### Pattern 3: Audit Chain via SQL `chain_state` + LA Logs Ingestion API

**What:** Each audit event is hashed `SHA256(prior_digest || canonical_json(payload))`. The new digest replaces `audit.chain_state.head_digest` in the same SQL transaction, then the event is sent to LA via the Logs Ingestion API and mirrored to the WORM blob (append-blob, one block per event). All three steps must succeed; any failure aborts and the parent op is rejected `[VERIFIED: D-04, D-05, D-06]`.

**When to use:** Every audit emit, in every component (ETL, gateway, admin tooling, CI). No parallel audit path.

**Example (audit SDK pseudocode):**

```python
# packages/barycenter-audit/src/barycenter/audit/client.py
class AuditClient:
    def __init__(self, sql, la_ingestion, worm_blob):
        self.sql = sql              # pyodbc connection, audit-identity
        self.la = la_ingestion      # azure.monitor.ingestion.LogsIngestionClient
        self.worm = worm_blob       # azure.storage.blob.AppendBlobClient

    def emit(self, event: AuditEvent) -> None:
        canonical = canonicalize_json(event.model_dump())
        with self.sql.transaction():  # serializable isolation
            cur = self.sql.cursor()
            cur.execute("SELECT head_digest FROM audit.chain_state WITH (UPDLOCK, ROWLOCK)")
            prior = cur.fetchone()[0]
            new_digest = sha256(prior + canonical.encode()).hexdigest()
            event.prior_digest = prior
            event.this_digest = new_digest
            payload_with_chain = canonicalize_json(event.model_dump())
            # Both downstream writes must succeed BEFORE we commit the chain_state update
            self.la.upload(rule_id=DCR_ID, stream_name="Custom-AuditEvents",
                           logs=[event.model_dump()])
            self.worm.append_block(payload_with_chain.encode())
            cur.execute("UPDATE audit.chain_state SET head_digest = ?", new_digest)
            # commit on context exit; any exception → rollback → fail closed
```

**Source:** Logs Ingestion API client `[CITED: learn.microsoft.com/python/api/overview/azure/monitor-ingestion-readme]`. Append-blob immutability semantics `[CITED: learn.microsoft.com/azure/storage/blobs/immutable-storage-overview]`.

### Pattern 4: HMAC via Key Vault `sign` Operation (no plaintext salt)

**What:** Per-tenant salts are stored as Key Vault **keys** (not secrets) of type `oct-HSM` or `oct`, with `sign` operation permission. The ETL identity calls `key.sign(algorithm='HS256', data=email_bytes)` — Key Vault returns the HMAC, the salt material never leaves KV `[CITED: learn.microsoft.com/azure/key-vault/keys/about-keys]`.

**When to use:** Phase 1 establishes the keys + RBAC; Phase 2+ ETL consumes the sign operation.

**Example:**

```python
from azure.identity import DefaultAzureCredential
from azure.keyvault.keys.crypto import CryptographyClient, SignatureAlgorithm

credential = DefaultAzureCredential()  # uses mi-bary-etl token
crypto_client = CryptographyClient(
    key=f"https://kv-bary-prod.vault.azure.net/keys/salt-tenant-{tenant_id}",
    credential=credential)
result = crypto_client.sign(SignatureAlgorithm.hs256, email.lower().strip().encode())
person_pid = result.signature.hex()
```

**Note:** This is a Phase 1 *capability* — the ETL identity gets `sign` permission, the keys are created (one per tenant during onboarding, or one bootstrap key for testing). Actual ETL code lives in Phase 2.

### Pattern 5: Field-Class Registry (YAML) + CI Gate (VER-02)

**What:** A single YAML file (`compliance/field-class-registry.yaml`) lists every column in every `raw_*` schema with its field class. CI parses both (a) the live SQL schema (via `INFORMATION_SCHEMA.COLUMNS`) and (b) the registry, fails the build if any column is missing a tag or any class assignment changed without an explicit reviewer comment.

**When to use:** Every PR that touches `sql/` or adds a column.

**Example:**

```yaml
# compliance/field-class-registry.yaml
version: 1
schemas:
  raw_cw:
    companies:
      cw_company_id: INTERNAL
      company_name: SENSITIVE
      billing_address: RESTRICTED
      cui_handling_required: INTERNAL
    contacts:
      cw_contact_id: INTERNAL
      email: RESTRICTED
      first_name: SENSITIVE
      last_name: SENSITIVE
```

**CI script:**

```python
# scripts/ci/field_class_check.py
def check():
    registry = yaml.safe_load(open("compliance/field-class-registry.yaml"))
    for schema in raw_schemas_in_db():
        for table, col in columns_in(schema):
            if col not in registry["schemas"][schema][table]:
                fail(f"VER-02: column {schema}.{table}.{col} has no field-class tag")
            cls = registry["schemas"][schema][table][col]
            if cls not in {"RESTRICTED", "SENSITIVE", "INTERNAL", "PUBLIC"}:
                fail(f"VER-02: column {schema}.{table}.{col} has invalid class {cls}")
```

**Why YAML over SQL extended properties:** Reviewable in PRs (diff is meaningful), grep-able, no DB round-trip in CI for the registry side. Trade-off: registry can drift from schema if a migration is merged without registry update — exactly what the CI gate catches.

### Anti-Patterns to Avoid

- **Manual `az` commands after Wave 0:** Bypasses GitHub Actions audit + branch protection. All infra changes go through PR + CI.
- **Storing the FortiGate license/token in GitHub Secrets:** Use Key Vault + managed-identity retrieval at deploy time.
- **Audit emit as fire-and-forget:** Violates D-06 (fail-closed). Audit must be synchronous in the parent transaction; if LA or WORM is down, the parent op is rejected.
- **Hardcoded subscription IDs / resource group names in Bicep:** Use parameters (D-03). Subscription ID lives in GitHub repo variables.
- **Single Azure environment for dev + prod:** Even at small scale, separate resource groups per env (`rg-barycenter-dev`, `rg-barycenter-prod`) with separate parameter files.
- **Granting `Contributor` to the deploy identity at subscription scope:** Use scoped role assignments (Contributor on each RG, User Access Administrator only where role-assignment creation is needed).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HMAC of email for pseudonymization | Python `hmac.new(salt, email)` with salt fetched as plaintext secret | Key Vault `sign` operation on an `oct-HSM` key | Salt material never reaches application memory; KV access is logged centrally |
| WORM enforcement | App-level "don't delete" convention | Azure Storage immutable container with locked time-based retention policy | Auditor demands cryptographic + provider enforcement, not app convention |
| Audit chain hash storage | In-process counter or Redis | SQL `audit.chain_state` row with `UPDLOCK` + same-tx commit (D-05) | Atomicity with the parent SQL transaction; no race conditions; one source of truth |
| Logs Ingestion to LA | Direct REST POSTs with custom auth | `azure-monitor-ingestion` SDK | Handles AAD token, retries, batching, schema validation against DCR |
| FortiGate config diff | Custom Python parsing of FortiOS show output | FortiOS REST API `GET /api/v2/cmdb/...` JSON returns + git diff | Stable JSON schema; diff against checked-in canonical file |
| GitHub→Azure auth | Service principal client secret | OIDC federated workload identity | No secret to rotate, no secret to leak |
| Bicep "what-if" diffing | Custom ARM template diff | `az deployment group what-if` | Microsoft-supported; understands Bicep semantics; outputs reviewable summary |
| MFA enforcement | Per-app login flow | Conditional Access policy at tenant level (IDENT-01) | Tenant-wide; covers SSMS, PowerShell, Azure CLI, browser uniformly |
| PIM dual approval | Manual ticketing system | Entra PIM "approval required" + 2 approvers (IDENT-02/05) | Native to Entra, audit-trail in Sign-In logs, no integration needed |

**Key insight:** This phase is heavy on standard Azure-native primitives. Resist any urge to reinvent — the only "custom" code that ships in Phase 1 is the audit SDK (~300 LOC) and the CI gates (~200 LOC each). Everything else is configuration.

## Runtime State Inventory

> Greenfield phase. Skip the migration-style inventory. Below is the equivalent forward-looking inventory: what state Phase 1 *creates* that subsequent phases will inherit and that the project must protect.

| Category | Items Created | Action Required (this phase) |
|----------|---------------|------------------------------|
| Stored data (none yet) | `audit.chain_state` (1 row, genesis hash) | Seed via `sql/20-seed/001_chain_genesis.sql` during Wave 0 |
| Live service config | FortiGate policies, KV access policies, SQL grants, PIM role assignments | All version-controlled in `infra/` and `sql/`; nightly drift detection (NETW-02) |
| OS-registered state | None — no persistent VMs except the FortiGate; Container Apps and Azure Functions arrive in later phases | — |
| Secrets/env vars | Anthropic API key (KV `secret/anthropic-api-key`, populated empty in Phase 1; real value in Phase 3); per-tenant salt **keys** (KV `keys/salt-tenant-{id}`, created in Phase 2 onboarding) | Phase 1 creates the KV + access policies; secrets created empty placeholders or deferred |
| Build artifacts | `barycenter-audit` Python package — installed editable in dev, built into wheel for downstream phases | Wheel built and pushed to a GitHub Packages registry (or installed from git in early phases) |

**Nothing found in OS-registered category:** Verified — no scheduled tasks, no systemd units, no pm2 processes (greenfield Azure-only deployment).

## Common Pitfalls

> The project's `research/PITFALLS.md` documents 15 LOAD-BEARING pitfalls across the full v1.0 build. Phase 1 directly addresses pitfalls 1, 3, 6, 7, 11, 13. Below are the Phase-1-specific subset plus implementation-specific gotchas.

### Pitfall 1 (project-LOAD-BEARING): Standing dev grants on raw_* become permanent
**What goes wrong:** Developer grants themselves `db_datareader` on `raw_cw` "for an hour"; never revoked.
**Why it happens:** Operational pressure; PIM JIT feels slow.
**How to avoid:** PIM JIT with dual approval is the *only* path (IDENT-05); the `mi-bary-admin` identity is PIM-eligible only — no standing role assignment. Nightly drift job queries `sys.database_principals` against the manifest and auto-revokes unknown grantees. Implement in Phase 1 — do not defer.
**Warning signs:** Any `GRANT` in commit history not generated from the manifest; PIM activations >1h or after-hours.

### Pitfall 3 (project-LOAD-BEARING): HMAC salt in plaintext anywhere = pseudonym universe reversed
**What goes wrong:** Salt logged in stack trace, copied into deployment script, or pulled as plaintext secret and held in app memory.
**How to avoid:** Use Key Vault `sign` operation (Pattern 4) — the salt key never leaves KV. KV diagnostic logs forward to LA; every `sign` call is auditable. Add a CI grep that fails on any string matching the salt key naming pattern in committed code.

### Pitfall 6 (project-LOAD-BEARING): Audit log volume crushes storage; truncation gets proposed
**What goes wrong:** 6 months in, someone proposes "sample 10% of prompts."
**How to avoid:** Tiered storage from day one — LA hot 90d (~$1/mo at v1 volume), WORM cold 6yr (~$3/mo growing to ~$10/mo). Budget alarm at 50% of forecast, not 100%. Make truncation architecturally impossible: WORM container has locked retention policy.

### Pitfall 7 (Phase-1 specific): WORM retention policy locked too early to wrong value
**What goes wrong:** AUDIT-03 says retention is locked at container creation. If you lock to 6 years on the test container, you cannot delete the test data for 6 years.
**How to avoid:** During Wave 0, create a *separate test container* with 1-day retention to validate the lock mechanism end-to-end (try to delete a blob, observe the refusal). Lock the production container to 6 years only after Bicep + audit SDK end-to-end test is green.

### Pitfall 8 (Phase-1 specific): Bicep deployment partial-failure leaves orphaned resources
**What goes wrong:** A multi-resource Bicep deployment fails halfway; some resources exist, some don't, and the next deploy attempt complains about name conflicts.
**How to avoid:** Use `--mode Complete` deployment **only at module boundary** (e.g., the entire `infra/data/` module is replaced atomically) — never at subscription scope (would delete everything else). Use `--mode Incremental` (the default) within modules. Always `what-if` before `create`.
**Warning signs:** "Resource already exists" errors on re-deploy; manual `az resource delete` commands appearing in runbooks.

### Pitfall 9 (Phase-1 specific): Logs Ingestion API DCR schema lock prevents adding fields
**What goes wrong:** DCR (Data Collection Rule) defines the custom-table schema. Adding a column to the audit event later means updating the DCR, the LA custom table, and the Python Pydantic model in lock-step.
**How to avoid:** Design the audit event schema with a `metadata: Dict[str, Any]` JSON column for forward extensibility. New fields go into `metadata` initially; promote to first-class columns only with a coordinated DCR + table + SDK release.

### Pitfall 10 (Phase-1 specific): Audit chain "fail closed" silently failing open in tests
**What goes wrong:** The audit SDK's fail-closed assertion is mocked in unit tests; real LA outage in dev never tested.
**How to avoid:** Wave 0 includes a chaos test: temporarily revoke `mi-bary-audit`'s LA ingestion role and assert the audit SDK raises and the parent operation aborts. Repeat for WORM blob and `chain_state` UPDATE failures. Three failure modes, three test cases.

### Pitfall 11 (Phase-1 specific): GitHub OIDC subject claim too permissive
**What goes wrong:** Federated credential subject is `repo:gravity/barycenter:*` (wildcard) — any branch, any PR can deploy to prod.
**How to avoid:** Separate federated credentials per environment: `repo:gravity/barycenter:ref:refs/heads/main` for prod deploy MI, `repo:gravity/barycenter:pull_request` for what-if MI (with read-only role). `[CITED: learn.microsoft.com/entra/workload-id/workload-identity-federation-create-trust-github]`

### Pitfall 12 (Phase-1 specific): Branch protection not actually enforced on admins
**What goes wrong:** Branch protection allows admin bypass by default; an admin pushing directly to main bypasses CI.
**How to avoid:** "Do not allow bypassing the above settings" must be checked. Verify by attempting a direct push as admin and observing the rejection (one-time test).

## Code Examples

### A. Bicep — Spoke VNet with UDR forcing 0/0 through FortiGate

```bicep
// infra/networking/modules/spoke-vnet.bicep
param location string = resourceGroup().location
param vnetName string
param vnetCidr string
param subnets array
param fortigateTrustNicIp string  // e.g., '10.10.1.4'

resource udr 'Microsoft.Network/routeTables@2024-01-01' = {
  name: 'rt-${vnetName}-fgt'
  location: location
  properties: {
    routes: [
      {
        name: 'default-via-fortigate'
        properties: {
          addressPrefix: '0.0.0.0/0'
          nextHopType: 'VirtualAppliance'
          nextHopIpAddress: fortigateTrustNicIp
        }
      }
    ]
  }
}

resource vnet 'Microsoft.Network/virtualNetworks@2024-01-01' = {
  name: vnetName
  location: location
  properties: {
    addressSpace: { addressPrefixes: [ vnetCidr ] }
    subnets: [for s in subnets: {
      name: s.name
      properties: {
        addressPrefix: s.cidr
        // PE subnets get no UDR (recursion risk per ARCHITECTURE.md §1)
        routeTable: contains(s.name, 'pe-') || contains(s.name, 'data-')
          ? null
          : { id: udr.id }
      }
    }]
  }
}
```

Source: `[CITED: learn.microsoft.com/azure/templates/microsoft.network/virtualnetworks]`, project `ARCHITECTURE.md` §1.

### B. Bicep — Azure SQL Serverless with private endpoint, public access disabled

```bicep
// infra/data/modules/sql-serverless.bicep
param sqlServerName string
param adminLoginName string  // Entra ID group object ID (no SQL auth)
param adminLoginType string = 'Group'
param dataSubnetId string
param privateDnsZoneId string

resource sqlServer 'Microsoft.Sql/servers@2024-05-01-preview' = {
  name: sqlServerName
  location: resourceGroup().location
  identity: { type: 'SystemAssigned' }
  properties: {
    publicNetworkAccess: 'Disabled'   // CLAUDE.md global instruction
    minimalTlsVersion: '1.2'          // ENC-01
    administrators: {
      administratorType: 'ActiveDirectory'
      principalType: adminLoginType
      login: 'sg-bary-sql-admins'
      sid: adminLoginName            // Entra group object ID
      tenantId: subscription().tenantId
      azureADOnlyAuthentication: true // no SQL logins
    }
  }
}

resource sqlDb 'Microsoft.Sql/servers/databases@2024-05-01-preview' = {
  parent: sqlServer
  name: 'barycenter'
  location: resourceGroup().location
  sku: { name: 'GP_S_Gen5_2', tier: 'GeneralPurpose', family: 'Gen5', capacity: 2 }
  properties: {
    autoPauseDelay: 60
    minCapacity: json('0.5')
    maxSizeBytes: 34359738368   // 32 GB
    zoneRedundant: false
  }
}

// TDE is on by default for all Azure SQL DBs since 2017; explicit confirmation:
resource tde 'Microsoft.Sql/servers/databases/transparentDataEncryption@2024-05-01-preview' = {
  parent: sqlDb
  name: 'current'
  properties: { state: 'Enabled' }
}

resource pe 'Microsoft.Network/privateEndpoints@2024-01-01' = {
  name: 'pe-${sqlServerName}'
  location: resourceGroup().location
  properties: {
    subnet: { id: dataSubnetId }
    privateLinkServiceConnections: [{
      name: 'sql-pe-conn'
      properties: {
        privateLinkServiceId: sqlServer.id
        groupIds: [ 'sqlServer' ]
      }
    }]
  }
}
```

Sources: `[CITED: learn.microsoft.com/azure/templates/microsoft.sql/servers]`, `[CITED: learn.microsoft.com/azure/azure-sql/database/private-endpoint-overview]`.

### C. Bicep — WORM blob container with locked retention

```bicep
// infra/audit/modules/worm-storage.bicep
param storageAccountName string
param retentionDays int = 2190  // 6 years for AUDIT-03

resource sa 'Microsoft.Storage/storageAccounts@2024-01-01' = {
  name: storageAccountName
  location: resourceGroup().location
  sku: { name: 'Standard_GRS' }
  kind: 'StorageV2'
  properties: {
    accessTier: 'Cool'
    allowBlobPublicAccess: false
    minimumTlsVersion: 'TLS1_2'
    publicNetworkAccess: 'Disabled'   // PE only
    networkAcls: { defaultAction: 'Deny', bypass: 'AzureServices' }
  }
}

resource container 'Microsoft.Storage/storageAccounts/blobServices/containers@2024-01-01' = {
  name: '${storageAccountName}/default/audit'
  properties: {
    immutableStorageWithVersioning: { enabled: true }
  }
}

// CRITICAL: locked policy. Once locked, even subscription owner cannot shorten retention.
// Per Pitfall 7: validate against test container with 1-day retention BEFORE locking prod.
resource immutabilityPolicy 'Microsoft.Storage/storageAccounts/blobServices/containers/immutabilityPolicies@2024-01-01' = {
  name: '${container.name}/default'
  properties: {
    immutabilityPeriodSinceCreationInDays: retentionDays
    allowProtectedAppendWrites: true   // append-blob writes allowed within retention window
  }
}
```

Sources: `[CITED: learn.microsoft.com/azure/storage/blobs/immutable-policy-configure-container-scope]`.

### D. Audit SDK — chain integrity test (adversarial)

```python
# packages/barycenter-audit/tests/test_chain_integrity.py
def test_chain_breaks_on_tamper(audit_client, sql_conn):
    audit_client.emit(AuditEvent(verb="test.event.1"))
    audit_client.emit(AuditEvent(verb="test.event.2"))
    # Simulate WORM blob tampering: read entries, change one, re-validate
    entries = read_worm_audit_entries()
    entries[0]["payload"] = "tampered"
    with pytest.raises(ChainIntegrityError):
        validate_chain(entries)

def test_fail_closed_on_la_outage(audit_client, mock_la):
    mock_la.upload.side_effect = ServiceRequestError("LA unreachable")
    with pytest.raises(AuditEmitError):
        audit_client.emit(AuditEvent(verb="test.event.1"))
    # Critical assertion: chain_state was NOT updated
    head = sql_conn.execute("SELECT head_digest FROM audit.chain_state").fetchone()[0]
    assert head == GENESIS_HASH
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| HTTP Data Collector API for custom logs to LA | Logs Ingestion API + DCR + DCE | Deprecated Sept 2026 | Use `azure-monitor-ingestion` SDK; DCR defines schema; AAD auth `[CITED: learn.microsoft.com/azure/azure-monitor/logs/data-collector-api]` |
| Service principal + client secret for GitHub→Azure | OIDC federated credentials | GA mid-2023 | No stored secrets in GH; `azure/login@v2` `[CITED: github.com/Azure/login]` |
| ARM JSON templates | Bicep | Bicep 1.0 (2021); current 0.32+ | Bicep is the recommended IaC for Azure-only `[CITED: learn.microsoft.com/azure/azure-resource-manager/bicep/overview]` |
| SQL authentication | Entra ID-only authentication | Available since 2018; Microsoft-recommended for HIPAA | `azureADOnlyAuthentication: true` on the SQL server resource — set in Phase 1 |
| Azure SQL public endpoint + firewall rules | Private endpoint + `publicNetworkAccess: Disabled` | Best practice since 2020 | CLAUDE.md global instruction is explicit |

**Deprecated/outdated:**
- HTTP Data Collector API for LA — deprecated, use Logs Ingestion API
- Sentinel as primary audit sink for HIPAA — deferred per project research; LA + WORM is sufficient
- Always Encrypted with secure enclaves (DC-series SQL) — deferred per project research; TDE is HIPAA-defensible

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| Azure subscription with Owner role | All Bicep deploys | ✓ assumed | — | — |
| Entra ID tenant with P2 license | PIM (IDENT-02, IDENT-05) | ✓ assumed (Gravity is M365-centric) | — | None — P2 is required for PIM approval workflows |
| FortiGate-VM02 BYOL license | NETW-01 | ✓ assumed (Gravity Fortinet MSSP) | FortiOS 7.4+ | None — license is non-negotiable per stack decision |
| Azure CLI 2.67+ | Local + CI deploy | ⚠ verify in Wave 0 | — | Install via brew/apt |
| Bicep CLI 0.32+ | All IaC | ⚠ verify in Wave 0 | — | `az bicep install` |
| Python 3.12+ | Audit SDK + CI gates | ⚠ verify in Wave 0 | — | Install via pyenv |
| GitHub Actions runner with `id-token: write` | OIDC federation | ✓ default | — | — |
| Microsoft + Anthropic BAA documents | COMP-06 | ⚠ unknown — verify before phase exit | — | Phase cannot exit without these in `compliance/baa/` |
| Anthropic ZDR confirmation in writing | COMP-06 | ⚠ unknown — verify before phase exit | — | Email from Anthropic counsel sufficient if signed BAA pending |

**Missing dependencies with no fallback:**
- BAA documents and ZDR confirmation — these are administrative artifacts the planner must surface as a parallel, human-driven track. Phase exit blocks until committed.

**Missing dependencies with fallback:**
- Local CLI versions — installable.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | `pytest >= 8.3` (Python — for audit SDK + CI gate scripts) + `bicep` CLI (for Bicep `lint` + `build`) + `az deployment what-if` (for ARM-level verification) |
| Config file | `pyproject.toml` (per-package); `bicepconfig.json` (Bicep linter rules) — both created in Wave 0 |
| Quick run command | `pytest packages/barycenter-audit/tests -x` + `az bicep build --file infra/<module>/main.bicep` |
| Full suite command | `pytest packages/ -v && for m in infra/*/main.bicep; do az bicep build --file "$m"; done && python scripts/ci/field_class_check.py && python scripts/ci/chain_validate.py` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FOUND-01 | Two-zone schemas exist with correct grants | integration | `pytest packages/barycenter-audit/tests/test_schema_grants.py -x` | ❌ Wave 0 |
| FOUND-02 | Field-class registry covers all raw_* columns | unit | `python scripts/ci/field_class_check.py` | ❌ Wave 0 |
| FOUND-03 | KV `sign` works for HMAC; ETL identity has sign permission | integration | `pytest packages/barycenter-audit/tests/test_kv_sign.py -x` | ❌ Wave 0 |
| FOUND-04 | Layer 1 (schema permissions) tested as platform-identity | integration | `pytest packages/barycenter-audit/tests/test_platform_zero_grants.py -x` | ❌ Wave 0 |
| NETW-01 | Bicep + FortiOS config compiles without errors | unit | `az bicep build` + `python scripts/ci/fortigate_config_validate.py` | ❌ Wave 0 |
| NETW-02 | Drift detection reports zero drift on freshly deployed env | smoke | `python scripts/ci/fortigate_drift.py --resource-group rg-barycenter-dev` | ❌ Wave 0 |
| NETW-03 | FortiGate deny event appears in LA within 5 min of synthetic traffic | manual smoke (cannot fully automate without traffic generator) | `pytest tests/integration/test_fortigate_deny_to_la.py --slow` | ❌ Wave 0 |
| AUDIT-01 | Chain validates from genesis to head | integration | `python scripts/ci/chain_validate.py --container audit` | ❌ Wave 0 |
| AUDIT-02 | Querying audit log produces an audit-of-audit entry | integration | `pytest packages/barycenter-audit/tests/test_audit_of_audit.py -x` | ❌ Wave 0 |
| AUDIT-03 | WORM container retention is locked + cannot be shortened | integration | `pytest tests/integration/test_worm_lock.py -x` | ❌ Wave 0 |
| IDENT-01 | Conditional Access policy template applied at tenant | manual (tenant-level config) | runbook validation | runbook only |
| IDENT-02 | PIM eligibility on `mi-bary-admin`; activation requires approval | integration | `pytest tests/integration/test_pim_dual_approval.py --slow` | ❌ Wave 0 |
| IDENT-03 | All 4 MIs exist with no client secrets | unit | `pytest tests/integration/test_managed_identities.py -x` | ❌ Wave 0 |
| IDENT-04 | Branch protection rules enforced; admin bypass disabled | manual smoke | runbook check via `gh api` | runbook only |
| IDENT-05 | PIM activation for raw_* role requires 2 approvers | integration | included in IDENT-02 test | included |
| EGRESS-01 | Synthetic ETL→Anthropic and services→source-tool denied + logged | smoke | `pytest tests/integration/test_egress_denies.py --slow` | ❌ Wave 0 |
| ENC-01 | TDE state is Enabled on the DB | unit | `pytest tests/integration/test_tde_enabled.py -x` | ❌ Wave 0 |
| VER-02 | CI fails on a PR adding a column without a class tag | meta-test | `python scripts/ci/field_class_check.py --simulate-untagged` | ❌ Wave 0 |
| COMP-06 | BAA inventory file exists with all 3 references | unit | `pytest tests/test_baa_inventory.py -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest packages/barycenter-audit/tests -x` (audit SDK only — fast, runs in seconds)
- **Per wave merge:** Full suite above + `az bicep build` over all modules + field-class check + chain validate
- **Phase gate:** Full suite green + manual checklist items (BAA committed, branch protection verified, FortiGate deny test observed in LA)

### Wave 0 Gaps

- [ ] `pyproject.toml` — root + `packages/barycenter-audit/`
- [ ] `bicepconfig.json` — linter rules (warn on hardcoded literals)
- [ ] `tests/conftest.py` — shared fixtures (Azure SDK clients with managed-identity auth)
- [ ] `tests/integration/` — directory structure
- [ ] `scripts/ci/field_class_check.py` — VER-02 implementation
- [ ] `scripts/ci/chain_validate.py` — AUDIT-01 verification
- [ ] `scripts/ci/fortigate_drift.py` — NETW-02 implementation
- [ ] `.github/workflows/infra-deploy.yml` — Bicep deploy + what-if
- [ ] `.github/workflows/infra-drift.yml` — nightly cron for NETW-02
- [ ] `.github/workflows/field-class-check.yml` — VER-02 CI gate
- [ ] `compliance/field-class-registry.yaml` — initial empty schemas (filled as `raw_*` schemas land)
- [ ] `compliance/baa-inventory.md` — template; populated by phase exit
- [ ] Framework install: `pip install -e packages/barycenter-audit[dev]`

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V1 Architecture | yes | Five-layer defense documented in PROJECT.md; Phase 1 establishes layers 1 + 5 |
| V2 Authentication | yes | Entra ID-only on SQL (`azureADOnlyAuthentication: true`); managed identities for service-to-service (no client secrets); MFA tenant-wide |
| V3 Session Management | yes | Conditional Access 15-min idle for admin sessions (IDENT-01); PIM JIT max 4-hour activation |
| V4 Access Control | yes | RBAC at every Azure resource; SQL schema-level grants; PIM dual-approval for `raw_*` |
| V5 Input Validation | partial | Phase 1 has minimal user input; the audit SDK validates Pydantic event schema |
| V6 Cryptography | yes | TDE (AES-256, default); HMAC via KV `sign` (no plaintext salt); SHA-256 chain hash; never hand-roll |
| V7 Error Handling & Logging | yes | Audit SDK is the structured-logging spine; secrets never logged (filtered logger); fail-closed on emit failure |
| V8 Data Protection | yes | Two-zone schema isolation; field-class registry; private endpoints; WORM retention |
| V9 Communications | yes | TLS 1.2+ enforced (SQL `minimalTlsVersion`); FortiGate deep packet inspection; private network for SQL |
| V10 Malicious Code | yes | Defender for SQL + Defender for Storage (per stack research); branch protection + signed commits |
| V14 Configuration | yes | All config in Bicep + version-controlled; secrets only in Key Vault; `publicNetworkAccess: Disabled` everywhere |

### Known Threat Patterns for Azure IaC + HIPAA Data Plane

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Compromised CI deploys backdoor infra | Tampering, EoP | OIDC scoped to `main`; PR-only deploys via what-if; branch protection requires 2 reviewers; signed commits |
| SQL public endpoint left open during initial bring-up | Information Disclosure | `publicNetworkAccess: Disabled` from first commit (CLAUDE.md global instruction); Bicep linter rule fails build if missing |
| Standing admin grants on raw_* | Elevation of Privilege, Information Disclosure | PIM JIT only; no standing grants; nightly drift detector |
| Audit log tampering | Tampering, Repudiation | WORM container with locked retention; SHA-256 chain; chain_state in SQL with restricted UPDATE grant; chain-validate CI |
| Salt material leak | Information Disclosure | KV `sign` operation only (key never returned); KV diagnostic logging; CI grep blocks salt-key references in code |
| FortiGate config drift via console | Tampering | NETW-02 nightly drift job; alert + auto-rollback PR |
| Service principal secret leak | Spoofing, EoP | OIDC federation eliminates the secret entirely |
| WORM container deletion before retention expiry | Tampering | Locked time-based retention policy + container-level legal hold capability; cannot be shortened by any role |
| Cross-tenant Azure AD attack via misconfigured federation | Spoofing | Federated credential subject locked to specific repo + branch (Pitfall 11) |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Gravity holds an active FortiGate-VM02 BYOL license under MSSP agreement | Standard Stack | If wrong, must use Azure Firewall (~$1,200/mo) or pay for FortiGate license — breaks $200/mo budget |
| A2 | Entra P2 licensing is in place for PIM | Identity / IDENT-02 | If wrong, IDENT-02 + IDENT-05 cannot be implemented as designed; may need Conditional Access alternatives that are weaker |
| A3 | Anthropic BAA + written ZDR confirmation can be obtained during Phase 1 (administrative) | COMP-06 | If wrong, Phase 1 cannot fully exit; project research already flagged this as a Phase 3 blocker but COMP-06 makes it Phase 1 |
| A4 | Azure subscription has sufficient quota for FortiGate VM in the chosen region | Network module | Quota requests can take days; verify in Wave 0 |
| A5 | The signing-key approach (KV `oct-HSM` with `sign` permission) produces a stable, deterministic HMAC across SDK versions | Pattern 4 | Risk: if KV's HMAC implementation changes, historical pids become unverifiable. Mitigation: pin KV API version; document in compliance/ |
| A6 | GitHub Actions OIDC subject claim format is stable | Pattern 2 | Microsoft-published format `[CITED: learn.microsoft.com/entra/workload-id/workload-identity-federation-create-trust-github]` — low risk |
| A7 | YAML field-class registry is preferred over SQL extended properties | Pattern 5 | Marked as Claude's discretion in CONTEXT.md; trade-offs documented in §Alternatives Considered |
| A8 | DCR + Logs Ingestion API supports the audit event schema with arbitrary `metadata` JSON column | Pitfall 9 | DCR allows `dynamic` columns in custom tables — verified per Microsoft docs `[CITED: learn.microsoft.com/azure/azure-monitor/essentials/data-collection-rule-overview]` |

## Open Questions

1. **Will all four MIs sit in the same resource group as the resources they access, or in a dedicated identity RG?**
   - What we know: Common pattern is dedicated `rg-barycenter-identity` so identity lifecycle is independent of data lifecycle.
   - What's unclear: Whether RBAC role assignments cross-RG complicate `what-if` output.
   - Recommendation: Dedicated `rg-barycenter-identity`. Document as a planning decision.

2. **Is the audit SDK called from Bicep deployment scripts (e.g., to log infra changes) or only from runtime services?**
   - What we know: HIPAA §164.312(b) covers PHI access — infra deploys don't access PHI directly.
   - What's unclear: Whether there's value in chaining infra-deploy events into the same audit chain.
   - Recommendation: No — keep infra-deploy logs in GitHub Actions audit + Azure Activity Log; the application-level chain is for PHI-access events only.

3. **How is the FortiGate license file delivered to the VM during Bicep deployment?**
   - What we know: BYOL FortiGate accepts the license via `customData` (cloud-init equivalent) or post-deploy `execute restore license` via SSH.
   - What's unclear: Storing the license file securely in Key Vault vs. CI secret vs. manual one-time install.
   - Recommendation: Key Vault secret + Bicep `customData` reference. Plan-level decision.

4. **What is the bootstrap path for the very first deployment when `mi-bary-deploy` doesn't exist yet?**
   - What we know: Chicken-and-egg — `mi-bary-deploy` is created by Bicep, but you need an identity to run Bicep.
   - Recommendation: One-time bootstrap script (`scripts/deploy/bootstrap-oidc.sh`) run by a human admin via `az login` interactively, creating `mi-bary-deploy` + the federated credential + initial role assignments. After bootstrap, all subsequent deploys are CI-only.

## Sources

### Primary (HIGH confidence)

**Project research (already completed and authoritative):**
- `.planning/research/STACK.md` — Stack research (cost-simplified), 2026-05-02. Contains all SKU pricing, HIPAA mapping, BAA scope.
- `.planning/research/ARCHITECTURE.md` — Architecture research (FortiGate hub-and-spoke), 2026-05-02. Contains topology, identity blast-radius, defense-layer map.
- `.planning/research/PITFALLS.md` — 15 LOAD-BEARING pitfalls, 2026-05-01. Phase 1 addresses pitfalls 1, 3, 6, 7, 11, 13.
- `.planning/PROJECT.md` — Five-layer defense commitment, identifier hierarchy, key decisions.

**Microsoft Learn (HIGH confidence):**
- https://learn.microsoft.com/en-us/azure/azure-resource-manager/bicep/overview — Bicep IaC overview
- https://learn.microsoft.com/en-us/azure/azure-resource-manager/bicep/deploy-cli — `az deployment` + `what-if`
- https://learn.microsoft.com/en-us/azure/azure-sql/database/serverless-tier-overview — Serverless pricing + auto-pause
- https://learn.microsoft.com/en-us/azure/azure-sql/database/transparent-data-encryption-tde-overview — TDE always-on, AES-256
- https://learn.microsoft.com/en-us/azure/azure-sql/database/private-endpoint-overview — SQL PE
- https://learn.microsoft.com/en-us/azure/azure-monitor/logs/logs-ingestion-api-overview — DCR + Logs Ingestion API
- https://learn.microsoft.com/en-us/azure/azure-monitor/essentials/data-collection-rule-overview — DCR concepts
- https://learn.microsoft.com/en-us/azure/storage/blobs/immutable-storage-overview — WORM container, locked retention
- https://learn.microsoft.com/en-us/azure/storage/blobs/immutable-policy-configure-container-scope — locked policy syntax
- https://learn.microsoft.com/en-us/azure/key-vault/keys/about-keys — Key Vault key types and `sign` operation
- https://learn.microsoft.com/en-us/entra/id-governance/privileged-identity-management/pim-configure — PIM setup
- https://learn.microsoft.com/en-us/entra/workload-id/workload-identity-federation-create-trust-github — OIDC federated credentials

**GitHub (HIGH confidence):**
- https://github.com/Azure/login — `azure/login@v2` action with OIDC

### Secondary (MEDIUM confidence)

- HTTP Data Collector API deprecation notice — verified at https://learn.microsoft.com/azure/azure-monitor/logs/data-collector-api (deprecation Sept 2026)
- FortiGate REST API for config-as-code — Fortinet docs (verify exact endpoint paths during Wave 0)

### Tertiary (LOW confidence)

- None — Phase 1 stack and architecture are entirely from HIGH-confidence sources (the project's own pre-completed research) and authoritative Microsoft Learn citations.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — pre-decided in CONTEXT.md and validated by the project's stack research
- Architecture: HIGH — pre-decided in `ARCHITECTURE.md` (canonical reference per CONTEXT.md)
- Pitfalls: HIGH — Phase-1 subset comes from project's PITFALLS.md (Anthropic-verified, HHS-verified, EDPS-verified); Phase-1-specific implementation pitfalls are MEDIUM (one author's experience with these patterns)
- Bicep specifics: MEDIUM — example snippets are illustrative; final syntax to be confirmed against current Bicep version during Wave 0

**Research date:** 2026-05-02
**Valid until:** 2026-06-02 (30 days for stable Azure-native primitives; sooner if Logs Ingestion API or Bicep schema versions change materially)
