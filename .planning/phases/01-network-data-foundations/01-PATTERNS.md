# Phase 1: Network & Data Foundations - Pattern Map

**Mapped:** 2026-05-02
**Files analyzed:** 47 (all net-new — greenfield phase)
**Analogs found:** 0 / 47

## Greenfield Notice

This is a **greenfield mono-repo**. The repository contains only `.planning/` documents and `.git`. There is **no existing source code**, no `infra/`, no `packages/`, no `sql/`, no `.github/workflows/`, no `compliance/` directory, and no prior Bicep, Python, or SQL files to extract patterns from.

CONTEXT.md §`<code_context>` confirms: "None — greenfield project. No existing src/ directory" and "None yet — Phase 1 establishes the patterns all subsequent phases inherit."

**Implication for the planner:** Every file in Phase 1 is a pattern *progenitor*, not a pattern *consumer*. There is no codebase analog to mimic. Instead, each file plan must reference:

1. **`01-RESEARCH.md` §Code Examples** (sections A–D) — concrete Bicep + Python excerpts with Microsoft Learn citations, designed to be copied directly into the new files.
2. **`01-RESEARCH.md` §Architecture Patterns** (Patterns 1–5) — the five canonical patterns this phase establishes.
3. **`01-RESEARCH.md` §Recommended Project Structure** — the authoritative directory layout.
4. **`/Users/craig/.claude/CLAUDE.md` §Security** — Azure default-private rules (mandatory `publicNetworkAccess: Disabled`, private endpoints, network ACLs).
5. **`.planning/PROJECT.md`** and **`.planning/research/ARCHITECTURE.md`** — five-layer defense, identifier hierarchy, hub-and-spoke topology.

The planner should treat RESEARCH.md's code blocks as the equivalent of "extract from analog" excerpts: copy them verbatim into the relevant plan actions.

## File Classification

Files are extracted from CONTEXT.md decisions D-01 through D-08 and RESEARCH.md §Recommended Project Structure. Match Quality is "no-analog" for every file (greenfield).

### IaC — Bicep (D-01, D-02, D-03)

| New File | Role | Data Flow | Analog | Match Quality |
|----------|------|-----------|--------|---------------|
| `infra/networking/main.bicep` | infra-orchestrator | declarative-deploy | none | no-analog → use RESEARCH §Code Example A |
| `infra/networking/modules/hub-vnet.bicep` | infra-module | declarative-deploy | none | no-analog → RESEARCH §Architecture Diagram + §Pattern 1 |
| `infra/networking/modules/fortigate-vm.bicep` | infra-module | declarative-deploy | none | no-analog → STACK.md §3 + Open Question 3 |
| `infra/networking/modules/spoke-vnet.bicep` | infra-module | declarative-deploy | none | no-analog → RESEARCH §Code Example A (verbatim) |
| `infra/networking/modules/udr-policies.bicep` | infra-module | declarative-deploy | none | no-analog → RESEARCH §Code Example A (UDR section) |
| `infra/networking/modules/nsg.bicep` | infra-module | declarative-deploy | none | no-analog → ARCHITECTURE.md NSG patterns |
| `infra/networking/main.dev.bicepparam` | config | parameters | none | no-analog → D-03 + RESEARCH structure |
| `infra/networking/main.prod.bicepparam` | config | parameters | none | no-analog → D-03 |
| `infra/data/main.bicep` | infra-orchestrator | declarative-deploy | none | no-analog → RESEARCH §Code Example B |
| `infra/data/modules/sql-serverless.bicep` | infra-module | declarative-deploy | none | no-analog → RESEARCH §Code Example B (verbatim) |
| `infra/data/modules/key-vault.bicep` | infra-module | declarative-deploy | none | no-analog → RESEARCH §Pattern 4 + STACK §Key Vault |
| `infra/data/modules/private-endpoint.bicep` | infra-module | declarative-deploy | none | no-analog → RESEARCH §Code Example B (PE section) |
| `infra/data/main.dev.bicepparam` | config | parameters | none | no-analog |
| `infra/identity/main.bicep` | infra-orchestrator | declarative-deploy | none | no-analog → RESEARCH §Identity Topology |
| `infra/identity/modules/managed-identity.bicep` | infra-module | declarative-deploy | none | no-analog → IDENT-03 (4 MIs) |
| `infra/identity/modules/pim-role-assignment.bicep` | infra-module | declarative-deploy | none | no-analog → IDENT-02/05 |
| `infra/identity/modules/federated-credential.bicep` | infra-module | declarative-deploy | none | no-analog → RESEARCH §Pattern 2 |
| `infra/identity/main.dev.bicepparam` | config | parameters | none | no-analog |
| `infra/audit/main.bicep` | infra-orchestrator | declarative-deploy | none | no-analog → RESEARCH §Audit Chain Architecture |
| `infra/audit/modules/log-analytics.bicep` | infra-module | declarative-deploy | none | no-analog → STACK §Log Analytics |
| `infra/audit/modules/worm-storage.bicep` | infra-module | declarative-deploy | none | no-analog → RESEARCH §Code Example C (verbatim) |
| `infra/audit/modules/data-collection-rule.bicep` | infra-module | declarative-deploy | none | no-analog → RESEARCH §Pattern 3 + DCR docs |
| `infra/audit/main.dev.bicepparam` | config | parameters | none | no-analog |
| `bicepconfig.json` | config | linter | none | no-analog → RESEARCH §Validation Architecture |

### Python — Audit SDK (D-04, D-05, D-06)

| New File | Role | Data Flow | Analog | Match Quality |
|----------|------|-----------|--------|---------------|
| `packages/barycenter-audit/pyproject.toml` | config | package-metadata | none | no-analog → standard pyproject |
| `packages/barycenter-audit/src/barycenter/audit/__init__.py` | package-init | exports | none | no-analog |
| `packages/barycenter-audit/src/barycenter/audit/client.py` | service | request-response (synchronous, fail-closed) | none | no-analog → RESEARCH §Pattern 3 (verbatim pseudocode) |
| `packages/barycenter-audit/src/barycenter/audit/chain.py` | service | transform (SHA-256 + SQL UPDATE) | none | no-analog → RESEARCH §Pattern 3 + D-05 |
| `packages/barycenter-audit/src/barycenter/audit/models.py` | model | schema-validation | none | no-analog → CONTEXT Discretion (audit event schema) + Pitfall 9 (`metadata: Dict[str, Any]`) |
| `packages/barycenter-audit/src/barycenter/audit/sinks.py` | service | streaming-write (LA + WORM) | none | no-analog → RESEARCH §Pattern 3 (LA + WORM split) |
| `packages/barycenter-audit/tests/conftest.py` | test-fixture | test-setup | none | no-analog → standard pytest fixtures |
| `packages/barycenter-audit/tests/test_chain_integrity.py` | test | adversarial | none | no-analog → RESEARCH §Code Example D (verbatim) |
| `packages/barycenter-audit/tests/test_fail_closed.py` | test | failure-mode | none | no-analog → RESEARCH §Code Example D (verbatim) + Pitfall 10 |

### SQL — Schemas, Grants, Seed (FOUND-01, FOUND-04, D-05)

| New File | Role | Data Flow | Analog | Match Quality |
|----------|------|-----------|--------|---------------|
| `sql/00-schemas/001_create_raw_cw.sql` | migration | DDL | none | no-analog → PROJECT.md two-zone model |
| `sql/00-schemas/002_create_ai_zone.sql` | migration | DDL | none | no-analog → PROJECT.md two-zone model |
| `sql/00-schemas/003_create_audit.sql` | migration | DDL (incl. `audit.chain_state`) | none | no-analog → D-05 single-row table |
| `sql/00-schemas/004_create_pseudo.sql` | migration | DDL | none | no-analog → FOUND-03 identifier hierarchy |
| `sql/10-grants/001_etl_grants.sql` | migration | RBAC | none | no-analog → FOUND-04 layer 1 |
| `sql/10-grants/002_audit_grants.sql` | migration | RBAC | none | no-analog → D-05 (audit.chain_state UPDATE only) |
| `sql/10-grants/003_admin_revoke.sql` | migration | RBAC | none | no-analog → Pitfall 1 (zero standing grants) |
| `sql/20-seed/001_chain_genesis.sql` | migration | DML (1 row) | none | no-analog → §Runtime State Inventory |

### Compliance + CI Scripts (VER-02, NETW-02, AUDIT-01, COMP-06, IDENT-04)

| New File | Role | Data Flow | Analog | Match Quality |
|----------|------|-----------|--------|---------------|
| `compliance/field-class-registry.yaml` | config | source-of-truth-manifest | none | no-analog → RESEARCH §Pattern 5 (verbatim) |
| `compliance/baa-inventory.md` | doc | static | none | no-analog → COMP-06 |
| `compliance/baa/microsoft-baa-reference.md` | doc | static | none | no-analog → COMP-06 |
| `compliance/baa/anthropic-baa.pdf` | binary-doc | static | none | no-analog → COMP-06 (signed copy) |
| `compliance/baa/anthropic-zdr-confirmation.md` | doc | static | none | no-analog → COMP-06 |
| `compliance/runbooks/chain-validate.md` | doc | runbook | none | no-analog → AUDIT-01 |
| `scripts/ci/field_class_check.py` | utility | batch-validation | none | no-analog → RESEARCH §Pattern 5 (verbatim) |
| `scripts/ci/chain_validate.py` | utility | batch-validation | none | no-analog → AUDIT-01 + RESEARCH §Pattern 3 |
| `scripts/ci/fortigate_drift.py` | utility | batch-comparison | none | no-analog → NETW-02 + FortiOS REST docs |
| `scripts/deploy/bootstrap-oidc.sh` | utility | one-time-setup | none | no-analog → RESEARCH §Pattern 2 (verbatim federated cred snippet) + Open Question 4 |
| `.github/workflows/infra-deploy.yml` | ci-workflow | event-driven | none | no-analog → RESEARCH §Pattern 1 + §Pattern 2 |
| `.github/workflows/infra-drift.yml` | ci-workflow | scheduled-cron | none | no-analog → NETW-02 |
| `.github/workflows/field-class-check.yml` | ci-workflow | event-driven (PR) | none | no-analog → VER-02 |
| `.github/workflows/audit-chain-validate.yml` | ci-workflow | event-driven | none | no-analog → AUDIT-01 |
| `.github/CODEOWNERS` | config | branch-protection | none | no-analog → IDENT-04 |
| `CLAUDE.md` | doc | project-instructions | none | no-analog → project conventions |
| `pyproject.toml` (root) | config | workspace-metadata | none | no-analog |

## Pattern Assignments

Every file's "analog" is RESEARCH.md content. The planner should reference these sources directly. Below are the exact pointers.

### Group 1: Bicep Networking Files

**Source patterns:**
- **Spoke VNet + UDR:** `01-RESEARCH.md` §Code Examples A — the complete `spoke-vnet.bicep` example with UDR forcing `0.0.0.0/0` through FortiGate trust NIC, plus the rule that PE/data subnets get `routeTable: null` to avoid recursion.
- **Hub-and-spoke topology:** `01-RESEARCH.md` §Architecture Patterns — the System Architecture Diagram (CIDR allocations: hub `10.10/22`, spoke `10.20/22`, etl `10.20.0.0/26`, services `10.20.0.64/26`, data `10.20.0.128/27`, pe `10.20.0.160/27`, admin `10.20.1.0/27`).
- **FortiGate VM:** `.planning/research/STACK.md` §3 (FortiOS 7.4+ on Standard_F2s_v2) + `01-RESEARCH.md` Open Question 3 (license delivery via Key Vault secret + Bicep `customData`).
- **Anti-pattern guard:** `01-RESEARCH.md` §Anti-Patterns — no hardcoded subscription IDs / RG names; use parameters per D-03.

**Apply Pattern 1 (Bicep Layered-Module Deployment):** Each module deploys via `az deployment group create` against its own resource group. PR runs `what-if`; merge to main runs `create`.

### Group 2: Bicep Data Files

**Source patterns:**
- **Azure SQL Serverless:** `01-RESEARCH.md` §Code Examples B — the verbatim `sql-serverless.bicep` example. Critical fields: `publicNetworkAccess: 'Disabled'`, `minimalTlsVersion: '1.2'`, `azureADOnlyAuthentication: true`, explicit TDE resource, SKU `GP_S_Gen5_2`, `autoPauseDelay: 60`, `minCapacity: json('0.5')`, `maxSizeBytes: 34359738368` (32 GB).
- **Private endpoint:** `01-RESEARCH.md` §Code Examples B — `pe` resource with `groupIds: [ 'sqlServer' ]`, attached to data-subnet.
- **Key Vault:** `.planning/research/STACK.md` §Key Vault row + `01-RESEARCH.md` §Pattern 4 — RBAC mode, `oct-HSM` keys for HMAC-via-`sign`, key never returned plaintext.
- **CLAUDE.md global enforcement:** `publicNetworkAccess: Disabled` + private endpoint + network ACL `defaultAction: Deny`.

### Group 3: Bicep Identity Files

**Source patterns:**
- **4 managed identities (IDENT-03):** `mi-bary-etl`, `mi-bary-platform`, `mi-bary-audit`, `mi-bary-admin` — capabilities listed in `01-RESEARCH.md` §System Architecture Diagram. Add a fifth `mi-bary-deploy` for the OIDC federation per Pattern 2 (the deploy MI is created before resources by the bootstrap script — see `scripts/deploy/bootstrap-oidc.sh`).
- **PIM role assignments (IDENT-02, IDENT-05):** `01-RESEARCH.md` §PIM Configuration cite — Entra P2 required; `mi-bary-admin` is PIM-eligible only with no standing grants; `raw_*` access requires 2-approver workflow.
- **Federated credential (Pattern 2):** `01-RESEARCH.md` §Pattern 2 — verbatim `az identity federated-credential create` snippet. Per Pitfall 11, separate creds per environment: `repo:gravity/barycenter:ref:refs/heads/main` for prod-deploy, `:pull_request` for what-if.

### Group 4: Bicep Audit Files

**Source patterns:**
- **WORM container with locked retention:** `01-RESEARCH.md` §Code Examples C — verbatim `worm-storage.bicep`. Critical: `immutableStorageWithVersioning.enabled: true`, `immutabilityPeriodSinceCreationInDays: 2190`, `allowProtectedAppendWrites: true`, `publicNetworkAccess: 'Disabled'`, `networkAcls.defaultAction: 'Deny'`. Per Pitfall 7, deploy a *test* container with 1-day retention first to validate the lock.
- **Log Analytics Workspace:** `.planning/research/STACK.md` §Log Analytics row — Pay-as-you-go, 90-day retention.
- **DCR + Logs Ingestion API:** `01-RESEARCH.md` §Pattern 3 — DCR API version `2023-01-01`. Per Pitfall 9, audit event table schema includes `metadata` dynamic JSON column for forward extensibility.

### Group 5: Audit SDK (Python)

**Source patterns:**
- **`client.py` (AuditClient):** `01-RESEARCH.md` §Pattern 3 — verbatim pseudocode. The `emit()` method opens a SQL transaction with `SELECT ... WITH (UPDLOCK, ROWLOCK)`, computes `SHA256(prior + canonical_json(payload))`, calls `la.upload(...)` and `worm.append_block(...)` *inside* the transaction, then `UPDATE audit.chain_state SET head_digest = ?`. Any exception in any step rolls back and raises `AuditEmitError`.
- **`chain.py`:** Implements canonical JSON serialization, SHA-256 hashing, and `chain_state` row-locking. Functions: `canonicalize_json(dict) -> str`, `compute_digest(prior_hex: str, canonical: str) -> str`, `read_head_locked(cursor) -> str`, `update_head(cursor, new_digest) -> None`. Per D-05, only the audit identity has UPDATE permission on `audit.chain_state`.
- **`models.py`:** Pydantic models — `AuditEvent` with required HIPAA §164.312(b) fields (`event_id: UUID`, `occurred_at: datetime`, `actor_id: str`, `actor_type: Literal['user','service']`, `verb: str`, `resource_type: str`, `resource_id: str | None`, `outcome: Literal['success','failure','denied']`, `tenant_id: str | None`, `prior_digest: str | None`, `this_digest: str | None`, `metadata: Dict[str, Any] = {}`). The `metadata` field absorbs forward extensions (Pitfall 9).
- **`sinks.py`:** Two writer classes — `LogsAnalyticsSink` wraps `azure.monitor.ingestion.LogsIngestionClient.upload(rule_id, stream_name, logs)`; `WormBlobSink` wraps `azure.storage.blob.AppendBlobClient.append_block(payload_bytes)`. Both raise on any exception (no swallowing).
- **`tests/test_chain_integrity.py`:** `01-RESEARCH.md` §Code Examples D — verbatim adversarial tests: `test_chain_breaks_on_tamper` (mutate WORM entry, validate raises `ChainIntegrityError`).
- **`tests/test_fail_closed.py`:** `01-RESEARCH.md` §Code Examples D — verbatim `test_fail_closed_on_la_outage` (mock LA `ServiceRequestError`, assert `audit_client.emit()` raises `AuditEmitError` AND `chain_state.head_digest == GENESIS_HASH`). Replicate for WORM blob outage and `chain_state` lock-timeout (three failure modes per Pitfall 10).

### Group 6: SQL Schemas + Grants

**Source patterns:**
- **Two-zone schemas (FOUND-01):** `.planning/PROJECT.md` two-zone model. `raw_cw` for raw ConnectWise mirror; `ai_zone` for derived/pseudonymized projection.
- **`audit.chain_state` table (D-05):** Single row with columns `(id INT PRIMARY KEY CHECK (id = 1), head_digest CHAR(64) NOT NULL, updated_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(), updated_by NVARCHAR(256))`. Seeded by `001_chain_genesis.sql` with `head_digest = '0' * 64` (genesis).
- **Grant model (FOUND-04 layer 1):** etl identity gets CRUD on `raw_*` only (no `ai_zone`); platform identity gets SELECT on `ai_zone` only (no `raw_*` — verified by `test_platform_zero_grants.py` per Validation Architecture); audit identity gets `UPDATE` on `audit.chain_state` only; admin identity is PIM-eligible (no standing grants).

### Group 7: CI Scripts + Workflows

**Source patterns:**
- **`field_class_check.py` (VER-02):** `01-RESEARCH.md` §Pattern 5 — verbatim Python snippet. Reads `compliance/field-class-registry.yaml`, queries `INFORMATION_SCHEMA.COLUMNS` for every `raw_*` schema, fails on any column missing from registry or with invalid class. Add `--simulate-untagged` flag for the meta-test.
- **`chain_validate.py` (AUDIT-01):** Reads all WORM blob entries in order, recomputes hash chain from genesis, compares each `this_digest`. Fails on any mismatch.
- **`fortigate_drift.py` (NETW-02):** Calls FortiOS REST API `GET /api/v2/cmdb/...`, diffs against checked-in canonical JSON in `infra/networking/fortigate-config/*.json`. Per `01-RESEARCH.md` §Don't Hand-Roll: do NOT parse `show` output; use the REST JSON.
- **`bootstrap-oidc.sh`:** `01-RESEARCH.md` §Pattern 2 — verbatim `az identity federated-credential create` snippet, run once by a human admin via `az login` (chicken-and-egg per Open Question 4).
- **`.github/workflows/infra-deploy.yml`:** `01-RESEARCH.md` §Pattern 2 — verbatim YAML with `permissions.id-token: write`, `azure/login@v2`, `client-id`/`tenant-id`/`subscription-id` from repo `vars` (no secrets). On PR: `az deployment group what-if`. On push to main: `az deployment group create`.
- **`.github/workflows/infra-drift.yml`:** Cron schedule (e.g., `0 6 * * *`); runs `fortigate_drift.py` + `az deployment group what-if` for each module.
- **CODEOWNERS (IDENT-04):** Per Pitfall 12 — must check "Do not allow bypassing the above settings" in branch protection. Verified by manual smoke per Validation Architecture.

## Shared Patterns

These cross-cutting patterns apply to multiple new files. The planner should ensure each plan's actions reference the source.

### Shared Pattern A: CLAUDE.md Global Security (Default Private)

**Source:** `/Users/craig/.claude/CLAUDE.md` §Security
**Applies to:** Every Bicep module that creates a cloud resource (SQL, Key Vault, Storage, Log Analytics, FortiGate, Container Apps env in later phases).

**Required properties on every public-capable resource:**
```bicep
publicNetworkAccess: 'Disabled'
networkAcls: { defaultAction: 'Deny', bypass: 'AzureServices' }
// Plus a private endpoint or VNet integration on the dedicated `pe-subnet` or `data-subnet`.
```

**Bicep linter rule (in `bicepconfig.json`):** Add a custom rule (or fail in CI) if any `publicNetworkAccess` property is set to `'Enabled'` or absent on a supported resource. Cite this enforcement in PR descriptions per CLAUDE.md §Security.

### Shared Pattern B: GitHub Actions OIDC Login

**Source:** `01-RESEARCH.md` §Pattern 2
**Applies to:** Every workflow in `.github/workflows/` that touches Azure.

**Required workflow header (verbatim):**
```yaml
permissions:
  id-token: write
  contents: read
jobs:
  <job>:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: azure/login@v2
        with:
          client-id: ${{ vars.AZURE_DEPLOY_CLIENT_ID }}
          tenant-id: ${{ vars.AZURE_TENANT_ID }}
          subscription-id: ${{ vars.AZURE_SUBSCRIPTION_ID }}
```

Per Pitfall 11, the `client-id` differs by env: PR what-if uses a read-only MI with `:pull_request` subject; main-branch deploy uses the deploy MI with `:ref:refs/heads/main` subject.

### Shared Pattern C: Bicep Parameter File per Environment (D-03)

**Source:** CONTEXT.md D-03
**Applies to:** Every `infra/<module>/main.bicep`.

Each module ships `main.dev.bicepparam` and `main.prod.bicepparam` referencing Key Vault for secrets — no plaintext secrets in param files. Resource group names, CIDRs, retention days, SKUs are explicit parameters (no hardcoded values per §Anti-Patterns).

### Shared Pattern D: Audit SDK Import Convention (D-04)

**Source:** CONTEXT.md D-04
**Applies to:** Every Python service in this and future phases that performs PHI-touching operations.

Single canonical import:
```python
from barycenter.audit import AuditClient, AuditEvent
```

The SDK is the *only* path to audit emission. Any service that performs PHI access without instantiating `AuditClient` is a defect. Code review (CODEOWNERS) enforces.

### Shared Pattern E: Fail-Closed Error Discipline (D-06)

**Source:** CONTEXT.md D-06 + Pitfall 10
**Applies to:** `client.py`, `sinks.py`, `chain.py`, all callers in later phases.

No `try / except / pass`. No fire-and-forget. Any exception in `AuditClient.emit()` propagates as `AuditEmitError`; the parent transaction must roll back. Tests in `test_fail_closed.py` cover all three failure modes (LA outage, WORM outage, chain_state lock).

### Shared Pattern F: Pydantic v2 Schema Validation

**Source:** RESEARCH §Standard Stack (`pydantic >= 2.10`)
**Applies to:** `models.py` and any future request/response models.

Use `BaseModel` with `model_dump()` (not v1 `.dict()`). Every audit event is validated on construction; invalid events never reach the chain. The `metadata: Dict[str, Any]` extension field absorbs forward-compatible additions (Pitfall 9).

### Shared Pattern G: Two-Zone Grant Discipline (FOUND-01, FOUND-04)

**Source:** PROJECT.md two-zone model + Pitfall 1
**Applies to:** Every `sql/10-grants/*.sql` file and every future migration.

Grants are explicit and minimal:
- etl identity → `raw_*` CRUD, no `ai_zone`, no `audit.*`
- platform identity → `ai_zone` SELECT, no `raw_*`, no `audit.*`
- audit identity → `UPDATE` on `audit.chain_state` only
- admin identity → no standing grants (PIM JIT activation only, dual approval)

The drift detector (`fortigate_drift.py` companion: a SQL grant drift check is implied by Pitfall 1) reconciles `sys.database_principals` against the manifest and auto-revokes unknown grantees.

## No Analog Found (All Files)

Every file listed in §File Classification has match quality `no-analog` because the repository is greenfield. The planner should:

1. Treat `01-RESEARCH.md` §Code Examples (A–D) as the canonical source patterns to copy verbatim.
2. Treat `01-RESEARCH.md` §Architecture Patterns (Patterns 1–5) as the conceptual templates each plan references.
3. Treat `.planning/PROJECT.md`, `.planning/research/ARCHITECTURE.md`, `.planning/research/STACK.md`, and `.planning/research/PITFALLS.md` as authoritative architectural context.
4. Treat the seven Shared Patterns above as cross-cutting concerns to apply uniformly.

After Phase 1 ships, future-phase pattern mappers will find rich analogs here: every Bicep module, the audit SDK, the SQL grant model, and the GitHub Actions workflows become the canonical templates Phase 2+ extends.

## Metadata

**Analog search scope:**
- Searched: repository root, `.planning/`, `infra/`, `packages/`, `sql/`, `compliance/`, `scripts/`, `.github/`, `src/`
- Files scanned: 0 source files (all paths except `.planning/` and `.git/` are absent)
- Tool calls: directory listing + `find -type f` confirmed greenfield state.

**Pattern extraction date:** 2026-05-02

**Pattern source-of-truth:** `01-RESEARCH.md` §Code Examples and §Architecture Patterns. Re-validate against current Bicep / Azure SDK versions in Wave 0 per RESEARCH §Environment Availability.
