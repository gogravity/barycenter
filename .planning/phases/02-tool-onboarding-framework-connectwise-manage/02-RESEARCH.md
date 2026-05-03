# Phase 2: Tool Onboarding Framework + ConnectWise Manage — Research

**Researched:** 2026-05-02
**Domain:** Python ETL framework + ConnectWise Manage REST adapter + Azure SQL T-SQL primitives + HMAC pseudonymization + CUI canary detection
**Confidence:** HIGH (CW Manage API, Python library versions, existing repo patterns); MEDIUM (CW field-level rate-limit nuance, exact attachment scan behavior — verify at integration time)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01 (Sync Mode):** Full-sync on schedule — truncate-and-reload each `raw_cw.*` table on a nightly cron. No watermark or soft-delete tracking. Deletion detection is automatic (missing row = deleted). Correctness easy to prove for INT-01 framework proof.
- **D-02 (Sync Cadence + Failure):** Nightly, table-isolated fail-closed. Each table syncs independently. If a table errors (CW API error, schema mismatch, audit write failure), it errors out and fires an alert without rolling back or blocking other tables. `raw_cw` remains in last-good state for the failed table.
- **D-03 (Job Runtime):** Sync job runs as a GitHub Actions scheduled workflow (cron trigger). Uses existing OIDC federated credential on `mi-bary-etl`. No new Azure infra for job execution.

### Claude's Discretion

- **ETL framework package layout:** Follow `packages/barycenter-audit/` pattern. New `packages/barycenter-etl/` package — adapter base class, primitives, CW adapter all live there.
- **T-SQL transformation primitives residence (TOOL-02):** Implementation choice open. Python functions producing parameterized SQL (UPSERT/MERGE) are consistent with existing Python-heavy codebase and unit-testable without SQL server. Deploy as Python, not stored procs.
- **AI-zone shape materialization (TOOL-03):** ETL-populated staging tables (not live views) for Phase 2 — auditable, can carry `synced_at`. Phase 3 adds typed functions over these.
- **CW Manage API auth:** OAuth 2.0 client credentials (CW REST v2024.x). Credentials in Key Vault, retrieved at runtime by `mi-bary-etl` via managed identity. *(Note: CW Manage commonly ships with HTTP Basic auth using `clientId + Company+publicKey:privateKey`; OAuth client-credentials is supported on CW Cloud. Verify the specific tenant during implementation — see Pitfall A2 below.)*
- **Retry behavior:** Exponential backoff with cap on transient errors; permanent failures (schema mismatch, CUI block) raise immediately without retry.
- **`source_etag` usage:** Store CW record `lastUpdated` as `source_etag` for future incremental migration without schema changes.

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within Phase 2 scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description (from REQUIREMENTS.md) | Research Support |
|----|------------------------------------|------------------|
| TOOL-01 | Standardized Tool Onboarding Spec template — every new tool fills the same intake doc (field map, raw schema, ETL recipe, AI-zone contributions, retention, erasure) | §Standard Stack (template format), §Architecture (adapter-base class pattern) |
| TOOL-02 | Eight standard transformation primitives — drop, hash, pseudonymize, aggregate, bucket, score, keyword_flags, as_is. Tools compose ETL from these. | §Architecture Patterns Pattern 2 (composable primitives), §Code Examples (primitive signatures) |
| TOOL-03 | Four canonical AI-zone shapes — `customer_snapshot`, `customer_features_*`, `timeseries_aggregate`, `customer_memory`. Tools contribute into these; tools cannot invent new AI-zone tables. | §Architecture Patterns Pattern 3 (shape-builder), §Don't Hand-Roll (no per-tool AI-zone tables) |
| TOOL-04 | Tool category taxonomy — productivity, RMM, security, backup, docs, distributors, CW. New tools slot into existing category, ETL recipe inherits. | §Architecture Patterns Pattern 5 (category-base class), §Standard Stack (category enum) |
| INT-01 | ConnectWise Manage — companies, agreements, tickets (metadata only, NO body content), configurations, time entries (aggregates only) | §Standard Stack (CW REST API), §Code Examples (auth + pagination), §Common Pitfalls (rate limit, body strip) |
| COMP-03 | CUI exclusion boundary — per-customer `cui_handling_required` flag, reduced sync surface for flagged customers, default `ai_opt_out=true` for CUI customers, regex CUI marker detection in synced text | §Architecture Patterns Pattern 4 (framework-level CUI gate), §Common Pitfalls Pitfall 3 |
| COMP-07 | CUI canary detection extended to email subjects, filenames, and attachments — attachments refused for CUI-flagged adapters | §Architecture Patterns Pattern 4 (multi-field canary scanner), §Code Examples (attachment refusal) |
| ENC-02 | Salt rotation runbook — documented and tested procedure for rotating per-tenant HMAC salts (versioned pepper IDs, online rebuild steps, rollback). Runbook in repo; rotation fire drill completed before v1.0. | §Architecture Patterns Pattern 6 (versioned salt + dual-write), §Code Examples (KV secret versioning) |
| RET-01 | Per-class retention policy — RESTRICTED 13-month default (extendable per-customer per-regulation), aggregates 5 years, audit log 6 years for HIPAA-tagged customers | §Architecture Patterns Pattern 7 (retention sweeper job), §Standard Stack (Azure SQL TTL via scheduled DELETE) |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

These directives are mandatory and override conflicting recommendations:

- **Audit path:** `from barycenter.audit import AuditClient, AuditEvent` is the ONLY audit path. `AuditClient.emit()` is synchronous and fail-closed. No try/except/pass. No fire-and-forget. Three failure modes (LA, WORM, chain_state lock) MUST raise `AuditEmitError` and roll back the parent transaction.
- **Python package layout:** `packages/{name}/src/`, `packages/{name}/tests/`, `pyproject.toml` (hatchling). Mirror `packages/barycenter-audit/`.
- **CI (D-08):** GitHub Actions only. All gates run there. OIDC subject claims are env-scoped per Pitfall 11 (no wildcards).
- **Mono-repo (D-07):** Single repository. Branch protection on `main`. Signed commits required.
- **SQL migrations:** Numbered files in `sql/00-schemas/` (DDL), `sql/10-grants/` (grants). Every new column gets a `compliance/field-class-registry.yaml` entry — VER-02 CI gate (`scripts/ci/field_class_check.py`) fails the build otherwise.
- **No bypass paths:** Adapters CANNOT bypass the primitive layer (Phase 2 success criterion 1) — enforced in code review and via a CI test that imports adapter modules and asserts their ETL recipes are composed only from `barycenter.etl.primitives`.

## Summary

Phase 2 builds `packages/barycenter-etl/` — a Python ETL framework with eight composable transformation primitives, four canonical AI-zone shape builders, an adapter base class, a CUI gate, and a CW Manage adapter that exercises the full chain end-to-end. All ETL writes go through the existing `AuditClient.emit()` fail-closed audit path (no parallel audit). The CW adapter pulls from `/company/companies`, `/finance/agreements`, `/service/tickets` (metadata only), `/company/configurations`, `/time/entries` (aggregated client-side) using HTTP Basic auth or OAuth client-credentials, paginates the CW way (`page`/`pageSize`, max 1000, last-page detection by short page), respects the 60 req/min default rate limit with token-bucket + exponential backoff, and writes to `raw_cw.*` via parameterized MERGE/UPSERT statements composed from the primitives. The ticket-body-stripping rule is enforced architecturally: `raw_cw.tickets` has no body column (CI test), and the adapter projects only metadata fields before write. CUI enforcement happens at the framework layer (not in adapter code) — a decorator on the adapter base reads `companies.cui_handling_required` and skips/reduces the sync surface; canary phrases are scanned across text fields, subjects, filenames, and attachment metadata, with attachments refused outright for CUI-flagged tenants. Salt rotation uses Key Vault secret versioning ("versioned pepper IDs"): each `salt-{tenant_id}` secret carries a version; pseudonyms are stored as `(pid, salt_version)` so a rotation re-pseudonymizes new writes immediately while a backfill job migrates historical pseudo-map rows under a documented dual-write window.

**Primary recommendation:** Build `packages/barycenter-etl/` with three sub-modules — `primitives/` (eight pure-function primitives + parameterized SQL emitters), `framework/` (`AdapterBase`, `CUIGate`, `ShapeBuilder`, `RetentionSweeper`), and `adapters/connectwise/` (CW Manage REST client + ETL recipe) — wire the nightly sync as a GitHub Actions scheduled workflow that authenticates to Azure via the existing OIDC federation and runs `python -m barycenter.etl.run --adapter connectwise`. Use `httpx` (sync) + `tenacity` for retries + `pyodbc` for SQL (already in `barycenter-audit`) + `pydantic` v2 for schema models + `azure-keyvault-secrets` for salt fetch + `azure-identity` for managed identity. The body-strip rule, the CUI gate, the canary scanner, and the primitive-only enforcement all become CI gates so the framework's load-bearing properties cannot regress silently.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| CW REST API I/O (auth, paging, retry, rate limit) | ETL Worker (Python, `barycenter-etl.adapters.connectwise`) | — | Network-side concern; lives in adapter, not in framework or SQL |
| Field selection (body strip, allowlist) | ETL Worker (adapter-declared schema model) | CI Gate (column-presence test) | Architectural enforcement: schema in code AND in DB DDL |
| Transformation primitives (drop, hash, pseudonymize, etc.) | ETL Worker (Python pure functions) | Azure SQL (parameterized MERGE the primitive emits) | Primitives are Python (testable) but produce SQL (where the data actually moves) |
| Pseudonymization HMAC | ETL Worker (inline; Key Vault sign or local HMAC with KV-fetched salt) | Key Vault (salt material storage; versioned secrets for ENC-02) | Salt never in SQL; HMAC computed in process; salt scope ends at function exit |
| CUI gate (`cui_handling_required` lookup + scope reduction) | ETL Framework (decorator on AdapterBase) | Azure SQL (`raw_cw.companies.cui_handling_required` is the source-of-truth read) | Framework-level enforcement (Pitfall 7 mitigation); adapter cannot bypass |
| CUI canary detection | ETL Framework (regex scanner module, called pre-write) | CI Gate (canary insertion fixture per adapter) | Detection is per-record; canary fixture is per-PR |
| Attachment refusal for CUI tenants | ETL Framework (adapter base method `should_sync_attachment(tenant)`) | — | Defaults closed; adapter cannot opt in for a CUI tenant |
| AI-zone shape population (4 canonical shapes) | ETL Worker (`ShapeBuilder` class) | Azure SQL (truncate-and-load `ai_zone.*` staging tables) | ETL-populated staging tables (per Discretion); shapes auditable with `synced_at` |
| Audit write per ETL operation | ETL Worker (calls `AuditClient.emit()`) | Azure SQL `audit.chain_state` + Service Bus + WORM (existing Phase 1 plumbing) | Single audit path (CLAUDE.md mandate) |
| Field-class registry tagging | CI Gate (`scripts/ci/field_class_check.py`) | Repo (`compliance/field-class-registry.yaml`) | VER-02 — fails PR if a column lacks a class tag |
| Grant assertions | CI Gate (`scripts/ci/grant_drift_check.py`) | Repo (`sql/10-grants/`) | Grant drift detection from Phase 1 covers any new grants |
| Retention sweep | ETL Worker (scheduled GH Action; per-class TTL DELETE) | Azure SQL (parameterized DELETE WHERE synced_at < cutoff) | RET-01 enforced by sweep job, not by SQL TTL (Azure SQL has no native row TTL) |
| Salt rotation | ETL Framework (rotation runbook + dual-write logic) | Key Vault (versioned secrets per tenant) | Versioned secret = "versioned pepper ID" |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `httpx` | `0.28.1` (2024-12-06) [VERIFIED: PyPI] | Sync HTTP client for CW Manage REST | Modern, sync+async unified API; mature retry-able transport; widely used in 2026 Python data tooling |
| `tenacity` | `9.1.4` (2026-02-07) [VERIFIED: PyPI] | Retry / exponential backoff | De-facto standard for declarative retry; integrates with httpx |
| `pyodbc` | `5.3.0` (2025-10-17) [VERIFIED: PyPI] | Azure SQL access | Already a `barycenter-audit` dependency — reuse driver to avoid pool fragmentation |
| `pydantic` | `2.13.3` (2026-04-20) [VERIFIED: PyPI] | Schema models for raw_cw rows + adapter spec validation | Already a `barycenter-audit` dependency; fail-fast validation on inbound CW JSON |
| `azure-identity` | `1.25.3` (2026-03-13) [VERIFIED: PyPI] | Managed identity token acquisition | Phase 1 standard; `DefaultAzureCredential` works for both GH Actions OIDC and local dev |
| `azure-keyvault-secrets` | `4.10.x` [CITED: docs.microsoft.com/azure-keyvault-secrets-python] | Per-tenant salt fetch | Versioned secret retrieval = "versioned pepper IDs" for ENC-02 |
| `azure-keyvault-keys` | `4.11.0` [VERIFIED: PyPI] | Optional: KV `sign` operation if salt-as-key approach is preferred over salt-as-secret | Already a `barycenter-audit` dependency for chain integrity |
| `pyyaml` | `6.0.3` [VERIFIED: PyPI] | Tool Onboarding Spec parser, field-class registry parser | Already used by VER-02 gate |
| `barycenter-audit` | `0.1.0` (in-repo) [VERIFIED: file:packages/barycenter-audit] | The only audit path | CLAUDE.md mandate; `AuditClient.emit()` is synchronous and fail-closed |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pytest` | `>=8.3` (already pinned in barycenter-audit) | Unit + integration tests | All Phase 2 test files |
| `pytest-mock` | `>=3.14` (already pinned) | Mocking CW API and KV in unit tests | Adapter unit tests, primitive tests |
| `respx` | `>=0.22` [CITED: pypi.org/project/respx] | httpx response mocking | CW REST contract tests without hitting live API |
| `freezegun` | `>=1.5` [CITED: pypi.org/project/freezegun] | Deterministic `synced_at` testing | ShapeBuilder tests where `synced_at` matters |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Python primitives emitting parameterized SQL | T-SQL stored procedures | Stored procs are harder to unit test, harder to version-control diffably, and would require a SQL instance for CI. Discretion D-04 already chose Python emitters. |
| `httpx` | `requests` + `urllib3.util.Retry` | `requests` lacks first-class HTTP/2 and modern timeout granularity; `httpx` is the 2026 default for new code |
| `tenacity` | hand-rolled `time.sleep` loop | "Don't hand-roll retry" — see §Don't Hand-Roll |
| OAuth 2.0 client credentials | HTTP Basic Auth (`Company+pubkey:privkey`) | CW Manage's *primary* documented auth is API Member key (Basic Auth). OAuth client-credentials exists for CW Cloud but is less universally enabled. The Discretion choice locks OAuth — keep that, but prepare a Basic-Auth fallback path in the auth module since the tenant capability is verified at integration time. |
| Truncate-and-load | Watermark / `lastUpdated > cursor` incremental sync | D-01 already locked truncate-and-reload. Future-proof by storing `source_etag = lastUpdated` so incremental migration is a code change, not a schema change. |
| ETL-populated AI-zone staging tables | Live indexed views | Discretion D-04 chose staging tables for auditability + `synced_at`. Indexed views deferred to Phase 3 if performance demands it. |

**Installation:** New `packages/barycenter-etl/pyproject.toml`:

```toml
[project]
name = "barycenter-etl"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
  "httpx>=0.28",
  "tenacity>=9.1",
  "pyodbc>=5.2",
  "pydantic>=2.10",
  "azure-identity>=1.19",
  "azure-keyvault-secrets>=4.9",
  "azure-keyvault-keys>=4.10",
  "pyyaml>=6.0",
  "barycenter-audit",  # local path dep
]
[project.optional-dependencies]
dev = ["pytest>=8.3", "pytest-mock>=3.14", "respx>=0.22", "freezegun>=1.5"]
```

**Version verification:** All versions above were confirmed against PyPI on 2026-05-02. Re-verify at implementation time if more than ~30 days have elapsed.

## Architecture Patterns

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  GitHub Actions scheduled workflow (cron, OIDC → mi-bary-etl)               │
│  python -m barycenter.etl.run --adapter connectwise                         │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  AdapterBase.run()  (framework, packages/barycenter-etl/src/.../framework)  │
│   1. Acquire mi-bary-etl token (azure-identity)                             │
│   2. Read CW credentials from Key Vault (api-cw-* secrets)                  │
│   3. For each table in adapter.TABLES:                                      │
│       a. CUI Gate ─── reads raw_cw.companies.cui_handling_required          │
│       b. Open SQL transaction (serializable, per CLAUDE.md fail-closed)     │
│       c. Begin AuditClient transaction (locks audit.chain_state)            │
│       d. Truncate raw_cw.<table>  (D-01)                                    │
│       e. Stream from CW API ──┐                                             │
│       f. CanaryScanner.scan(record)  ◄─── refuses or strips                 │
│       g. Apply primitives (drop body fields, etc.)                          │
│       h. Pseudonymizer.derive(email) ◄── KV salt-{tenant} (versioned)       │
│       i. Parameterized MERGE INTO raw_cw.<table>                            │
│       j. AuditClient.emit(verb='etl.write', resource='raw_cw.<table>', ...) │
│       k. Commit (or roll back on any error → table-isolated D-02)           │
└──────────┬───────────────────────────────────────┬──────────────────────────┘
           │                                       │
           ▼                                       ▼
┌────────────────────────┐         ┌─────────────────────────────────────┐
│  CW Manage REST API    │         │  Azure SQL (private endpoint)       │
│  /company/companies    │         │   raw_cw.* (truncate+load)          │
│  /finance/agreements   │         │   pseudo.person_map (upsert)        │
│  /service/tickets      │         │   audit.chain_state (lock+update)   │
│   (metadata only)      │         │   audit.events (insert)             │
│  /company/configurat.. │         └─────────────────────────────────────┘
│  /time/entries         │
│  HTTP Basic / OAuth    │
│  60 rpm rate limit     │
└────────────────────────┘
                                              ▼ (after all raw_cw tables done)
                                   ┌─────────────────────────────────────┐
                                   │  ShapeBuilder.run()                 │
                                   │  Truncate+populate ai_zone.*        │
                                   │  - customer_snapshot                │
                                   │  - customer_features_cw             │
                                   │  - timeseries_aggregate             │
                                   │  - customer_memory                  │
                                   │  Each row carries synced_at         │
                                   └─────────────────────────────────────┘
```

### Recommended Project Structure

```
packages/barycenter-etl/
├── pyproject.toml
├── README.md
├── src/barycenter/etl/
│   ├── __init__.py
│   ├── primitives/
│   │   ├── __init__.py        # exports the eight primitives
│   │   ├── drop.py            # drop(field) → SQL projection emitter
│   │   ├── hash.py            # hash(field, algo) → SHA-256 column
│   │   ├── pseudonymize.py    # pseudonymize(email_field, tenant) → person_pid
│   │   ├── aggregate.py       # aggregate(field, fn, group_by)
│   │   ├── bucket.py          # bucket(field, ranges) → bucketed value
│   │   ├── score.py           # score(fields, formula) → numeric
│   │   ├── keyword_flags.py   # keyword_flags(field, dict) → boolean cols
│   │   └── as_is.py           # as_is(field) → passthrough (PUBLIC/INTERNAL only)
│   ├── framework/
│   │   ├── __init__.py
│   │   ├── adapter_base.py    # AdapterBase ABC
│   │   ├── cui_gate.py        # CUIGate decorator + scope-reduction logic
│   │   ├── canary.py          # CanaryScanner (text + subject + filename + attachment)
│   │   ├── pseudonymizer.py   # KV salt fetch + HMAC; never caches salt
│   │   ├── shape_builder.py   # ShapeBuilder for the four canonical shapes
│   │   ├── retention.py       # RetentionSweeper for RET-01
│   │   ├── salt_rotation.py   # versioned-pepper rotation logic
│   │   └── recipe.py          # ETLRecipe = composition of primitives; enforces no-bypass
│   ├── adapters/
│   │   ├── __init__.py
│   │   └── connectwise/
│   │       ├── __init__.py
│   │       ├── adapter.py         # CWManageAdapter(AdapterBase)
│   │       ├── client.py          # CWManageClient (httpx + tenacity + rate limit)
│   │       ├── models.py          # pydantic models for CW JSON shapes
│   │       └── recipes/
│   │           ├── companies.py
│   │           ├── agreements.py
│   │           ├── tickets.py     # metadata only; body NOT in projection
│   │           ├── configurations.py
│   │           └── time_entries.py
│   └── run.py                 # entry point: python -m barycenter.etl.run --adapter X
├── tests/
│   ├── conftest.py
│   ├── test_primitives_*.py
│   ├── test_cui_gate.py
│   ├── test_canary.py
│   ├── test_pseudonymizer.py
│   ├── test_salt_rotation.py
│   ├── test_shape_builder.py
│   ├── test_recipe_no_bypass.py    # CI-load-bearing
│   ├── test_no_body_column.py      # CI-load-bearing (Success Criterion 2)
│   ├── test_no_novel_ai_zone.py    # CI-load-bearing (Success Criterion 4)
│   ├── adapters/connectwise/
│   │   ├── test_client.py          # respx-mocked
│   │   ├── test_adapter.py
│   │   └── test_recipes.py
│   └── integration/
│       └── test_e2e_synthetic.py   # synthetic CW → raw_cw → ai_zone

sql/00-schemas/
  005_create_raw_cw_remaining.sql   # agreements, tickets (NO body), configurations, time_entries
  006_create_pseudo_person_map.sql  # (cw_company_id, email_lower) → (person_pid, salt_version)
  007_create_ai_zone_shapes.sql     # 4 canonical staging tables

sql/10-grants/
  001_etl_grants.sql                # extend grants to new schemas (pseudo, ai_zone for ETL writer)

compliance/
  field-class-registry.yaml         # extend with all new columns
  tool-onboarding-spec.template.md  # TOOL-01 template
  cui-canary-phrases.yaml           # COMP-07 marker dictionary
  retention-policy.yaml             # RET-01 per-class TTLs
  salt-rotation-runbook.md          # ENC-02 runbook + fire-drill log

.github/workflows/
  etl-cw-nightly.yml                # cron: '0 6 * * *'  (D-03)
  etl-tests.yml                     # extends python-tests.yml
```

### Pattern 1: Adapter Base Class (TOOL-01 backbone)

**What:** Abstract base class declaring the contract every adapter implements. CUI gate, canary scanner, audit emit, and primitive-only enforcement live here — adapters cannot opt out.
**When to use:** Every new tool integration. Even one-off scripts that touch raw_* go through AdapterBase.
**Example:**

```python
# Source: project pattern, mirrors barycenter.audit.client design
from abc import ABC, abstractmethod
from barycenter.audit import AuditClient, AuditEvent, AuditOutcome
from barycenter.etl.framework.recipe import ETLRecipe
from barycenter.etl.framework.cui_gate import CUIGate
from barycenter.etl.framework.canary import CanaryScanner

class AdapterBase(ABC):
    CATEGORY: str  # TOOL-04 taxonomy: 'productivity'|'rmm'|'security'|'backup'|'docs'|'distributors'|'cw'
    TABLES: list[str]  # ordered list of raw_<tool>.<table> names
    CUI_SENSITIVE_TABLES: list[str]  # tables skipped entirely for CUI tenants
    CUI_CANARY_FIELDS: dict[str, list[str]]  # per-table fields to scan

    @abstractmethod
    def fetch_table(self, table: str) -> Iterator[dict]: ...

    @abstractmethod
    def recipe_for(self, table: str) -> ETLRecipe: ...

    def run(self, audit: AuditClient, sql_conn, kv_client) -> None:
        for table in self.TABLES:
            try:
                # Table-isolated fail-closed (D-02)
                with sql_conn.serializable_tx() as tx:
                    if CUIGate.should_skip(table, self.CUI_SENSITIVE_TABLES, sql_conn):
                        continue
                    sql_conn.execute(f"TRUNCATE TABLE raw_{self.CATEGORY}.{table}")  # D-01
                    for record in self.fetch_table(table):
                        if CanaryScanner.refuse(record, self.CUI_CANARY_FIELDS.get(table, [])):
                            raise CUIBoundaryViolation(f"canary in {table}")
                        recipe = self.recipe_for(table)
                        sql_stmt, params = recipe.compile(record)  # primitives → SQL
                        sql_conn.execute(sql_stmt, params)
                    audit.emit(AuditEvent(
                        verb="etl.write", resource=f"raw_{self.CATEGORY}.{table}",
                        outcome=AuditOutcome.SUCCESS, ...
                    ))  # FAIL-CLOSED — raises AuditEmitError on failure
            except Exception as exc:
                audit.emit(AuditEvent(verb="etl.write", resource=f"raw_{self.CATEGORY}.{table}",
                                      outcome=AuditOutcome.FAILURE, error=repr(exc)))
                alert(table, exc)  # D-02: alert without blocking other tables
                continue  # next table
```

### Pattern 2: Eight Composable Primitives (TOOL-02)

**What:** Each primitive is a Python function that returns a SQL projection fragment + parameter dict. ETLRecipe composes them; the resulting MERGE statement is what actually moves data. Primitives are the only allowed transformations.
**When to use:** Every column derivation in every recipe.
**Example:**

```python
# Source: project pattern; primitives produce parameterized SQL
from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class PrimitiveResult:
    expr: str           # SQL projection expression
    params: dict[str, Any]
    field_class: str    # RESTRICTED|SENSITIVE|INTERNAL|PUBLIC — VER-02 self-tag

def drop(field: str) -> PrimitiveResult:
    """drop: explicit non-projection. Used for body fields, attachments, etc."""
    return PrimitiveResult(expr="", params={}, field_class="DROPPED")

def hash_(field: str, value: str) -> PrimitiveResult:
    """hash: SHA-256 of field. One-way; not reversible."""
    return PrimitiveResult(
        expr="CONVERT(CHAR(64), HASHBYTES('SHA2_256', ?), 2)",
        params={"_": value}, field_class="INTERNAL")

def pseudonymize(field: str, email: str, tenant_id: str, kv_client, salt_version: int = None
                ) -> PrimitiveResult:
    """pseudonymize: HMAC(email, salt) → person_pid. Versioned salt for ENC-02."""
    salt, ver = fetch_salt(kv_client, tenant_id, salt_version)  # never cached
    pid = hmac_sha256(salt, email.lower().encode()).hexdigest()
    del salt
    return PrimitiveResult(expr="?, ?", params={"pid": pid, "salt_ver": ver},
                           field_class="SENSITIVE")

def aggregate(field: str, fn: str, values: list) -> PrimitiveResult: ...
def bucket(field: str, value, ranges: list) -> PrimitiveResult: ...
def score(fields: dict, formula: str) -> PrimitiveResult: ...
def keyword_flags(field: str, value: str, kw_dict: dict) -> PrimitiveResult: ...
def as_is(field: str, value, *, only_classes=("PUBLIC","INTERNAL")) -> PrimitiveResult:
    """as_is: passthrough. Refuses if column class is RESTRICTED or SENSITIVE."""
    ...
```

**No-bypass enforcement:** A CI test imports every recipe module and asserts every column derivation traces back to one of the eight primitives:

```python
# tests/test_recipe_no_bypass.py
def test_recipes_only_use_primitives():
    from barycenter.etl.framework.recipe import ETLRecipe
    for recipe in iter_all_recipes():
        for col, deriv in recipe.derivations.items():
            assert deriv.primitive_name in PRIMITIVE_REGISTRY, \
                f"{recipe.name}.{col} bypasses primitive layer"
```

### Pattern 3: Four Canonical AI-Zone Shapes (TOOL-03)

**What:** Tools contribute INTO four fixed shapes. The shape-builder layer is the only writer to `ai_zone.*`. A test asserts no `ai_zone.<novel_table>` exists outside the four canonical names.
**When to use:** Every Phase 2+ adapter.

| Shape | Grain | Columns (illustrative) | CW contribution |
|-------|-------|------------------------|-----------------|
| `customer_snapshot` | one row per cw_company_id | tier, industry_bucket, employee_band, region, lifecycle_stage, ai_opt_out, cui_flag, synced_at | company + agreement summary |
| `customer_features_cw` | one row per cw_company_id | open_ticket_count, avg_age_days_bucket, top_ticket_keyword_flags, time_entries_h_last_30 (bucketed) | tickets metadata + time entries |
| `timeseries_aggregate` | one row per (cw_company_id, month, metric) | metric_name, value_bucketed, synced_at | monthly ticket counts, hours, agreement value |
| `customer_memory` | one row per (cw_company_id, memory_kind) | summary_text (PUBLIC, no PII), source_kind, last_observed_month, synced_at | (sparse for CW Phase 2; populated in Phase 3+) |

**Example:**

```python
# Source: project pattern
class ShapeBuilder:
    CANONICAL = {"customer_snapshot", "customer_features_cw", "timeseries_aggregate", "customer_memory"}

    def populate(self, shape: str, sql_conn) -> None:
        if shape not in self.CANONICAL:
            raise ValueError(f"refusing novel ai_zone shape: {shape}")
        sql_conn.execute(f"TRUNCATE TABLE ai_zone.{shape}")
        sql_conn.execute(self._build_sql(shape))
```

A CI test scans `sql/00-schemas/*.sql` for `CREATE TABLE ai_zone.X` and fails if X is not in `CANONICAL`.

### Pattern 4: Framework-Level CUI Gate (COMP-03 + COMP-07)

**What:** The CUI check runs in `AdapterBase`, never in adapter code. Fields-to-scan are declared per-table in the adapter spec; the actual scanner is shared. Attachments are refused outright for CUI-flagged tenants.
**When to use:** Every adapter, every record, every PR.

```python
# Source: project pattern; pitfall-7 mitigation
import re
import yaml

class CanaryScanner:
    def __init__(self, phrases_yaml: str = "compliance/cui-canary-phrases.yaml"):
        self.phrases = yaml.safe_load(open(phrases_yaml))["phrases"]
        # phrases include: CUI, CONTROLLED UNCLASSIFIED INFORMATION, FOUO, FEDCON,
        # ITAR, EAR99, SECRET//NOFORN, plus per-customer test canaries
        self.regex = re.compile("|".join(re.escape(p) for p in self.phrases), re.IGNORECASE)

    def scan_text(self, value: str) -> bool: return bool(self.regex.search(value or ""))
    def scan_filename(self, fn: str) -> bool: return self.scan_text(fn)
    def scan_subject(self, s: str) -> bool: return self.scan_text(s)

    def refuse_attachment(self, tenant_cui_flag: bool) -> bool:
        # COMP-07: attachments refused outright for CUI-flagged adapters
        return tenant_cui_flag

class CUIGate:
    @staticmethod
    def should_skip(table: str, sensitive_tables: list[str], sql_conn) -> bool:
        # If ANY currently-flagged tenant exists, framework skips the entire sensitive table
        # for those tenants. (Per-tenant filtering happens inside fetch_table.)
        return table in sensitive_tables and \
               sql_conn.scalar("SELECT 1 FROM raw_cw.companies WHERE cui_handling_required = 1") is not None
```

**End-to-end CUI test (Phase 2 success criterion 3):** Synthetic CUI customer + canary in subject/filename/attachment → assert (a) no tickets/configurations/time entries land in raw_cw for that customer, (b) `ai_opt_out=true` is defaulted, (c) attachment is refused with audit event, (d) canary phrase in subject triggers `CUIBoundaryViolation` and the table sync errors out (D-02 isolation).

### Pattern 5: Tool Category Taxonomy (TOOL-04)

**What:** A `Category` enum + per-category default recipe template. New tools choose a category; the category provides default field maps + retention defaults; the tool overrides only what's specific.
**When to use:** Every new adapter.

```python
from enum import StrEnum
class Category(StrEnum):
    PRODUCTIVITY = "productivity"
    RMM = "rmm"
    SECURITY = "security"
    BACKUP = "backup"
    DOCS = "docs"
    DISTRIBUTORS = "distributors"
    CW = "cw"

# Each category gets a default ETL recipe that subclasses override
class CWCategoryDefaults:
    default_retention_class = "SENSITIVE"  # 13-month default
    default_canary_fields = ["subject", "summary", "notes"]
    forbidden_fields = []  # CW-specific: see below
```

For CW specifically, `tickets` extends `forbidden_fields = ["body", "internalAnalysis", "resolution"]` so a copy-paste of an RMM adapter recipe cannot accidentally project a body field.

### Pattern 6: Versioned-Pepper Salt Rotation (ENC-02)

**What:** Each tenant's salt is stored as a Key Vault Secret with versioning enabled. Pseudonyms are stored as `(person_pid, salt_version)`. Rotation creates a new secret version; the next sync writes new rows tagged with the new version. Historical pseudo-map rows are migrated by a controlled backfill that re-pseudonymizes with the new salt and updates the row in-place (or, if the source email is unavailable in audit because emails never enter audit, marks old rows as `migrated=false` and lets erasure rules retire them).
**When to use:** Quarterly, plus on any suspected compromise.

**Rotation runbook outline:**

1. **Pre-flight (T-7 days):** confirm KV diagnostic logs are healthy; confirm no in-flight sync; confirm the dual-write test fixture passes.
2. **Create new secret version:** `az keyvault secret set --vault $V --name salt-{tenant} --value $(openssl rand -hex 32)` — KV auto-versions; the URI now resolves to the latest version.
3. **Dual-write window opens:** for the duration of the window, every pseudonymization writes BOTH `(pid_old, ver_old)` and `(pid_new, ver_new)` rows in `pseudo.person_map`. Window default: 24h (one full nightly cycle). Window is governed by a feature flag in `compliance/salt-rotation-state.yaml`.
4. **Verify:** `pseudo.person_map` contains both versions for every active email; downstream `customer_snapshot` etc. resolve via the latest version.
5. **Cut over:** flip the feature flag to "new only"; subsequent writes use only the new version.
6. **Backfill (asynchronous):** for tenants where the source data still contains the email (raw_cw.companies has no email; this is for adapters that do — Pax8/Graph in Phase 4), re-derive pids with new salt and replace old rows.
7. **Retire old version (T+30 days):** disable old KV secret version; old pseudonyms in `pseudo.person_map` are now unverifiable (this is intentional — it's also the erasure path).
8. **Audit:** every step emits `AuditEvent(verb='salt.rotate.*')`. Runbook execution logged in `compliance/salt-rotation-state.yaml` with the operator identity.

**Fire drill (Phase 2 success criterion 5):** Execute the runbook on a non-production tenant. Verify pseudonyms remain valid through the dual-write window. Commit the runbook AND the fire-drill log. The fire-drill outcome is the gate for Phase 2 exit.

### Pattern 7: Per-Class Retention Sweeper (RET-01)

**What:** Azure SQL has no native row-TTL. Implement RET-01 as a scheduled GitHub Action (daily, separate from the sync) that runs `DELETE FROM raw_<tool>.<table> WHERE synced_at < DATEADD(MONTH, -13, SYSUTCDATETIME())` per RESTRICTED-classed table, with per-customer overrides read from `compliance/retention-policy.yaml`. Aggregates (5-year), audit log (6-year for HIPAA-tagged) and audit data are owned by the audit subsystem (Phase 1) and out of scope for this sweeper.
**When to use:** Daily, for every raw_* table containing RESTRICTED data.

```yaml
# compliance/retention-policy.yaml
default:
  RESTRICTED: {ttl_months: 13}
  SENSITIVE:  {ttl_months: 60}
  INTERNAL:   {ttl_months: 60}
  PUBLIC:     {ttl_months: 60}
overrides:
  - tenant_id: <hipaa-cust-uuid>
    classes: {RESTRICTED: {ttl_months: 84}}  # 7-yr extended
```

The sweeper emits an `AuditEvent(verb='retention.sweep', resource='raw_cw.<table>', deleted_rows=N)` per table.

### Anti-Patterns to Avoid

- **Adapter writes directly to raw_cw bypassing primitives.** Every column must go through a primitive — even `as_is`. Enforced by `test_recipes_only_use_primitives`.
- **Body field reaches raw_cw.tickets.** Not just policy — schema enforcement. The DDL has no `body` column; CI test asserts column-presence.
- **Hand-rolled retry loop in the CW client.** Use `tenacity`. See §Don't Hand-Roll.
- **Caching the salt across sync calls.** Salt fetched per-tenant per-table; lifetime ends at function exit; never assigned to a module/class attribute.
- **Per-tool AI-zone tables.** Adapters contribute to four canonical shapes only. CI scans for `CREATE TABLE ai_zone.<X>` and fails if X is novel.
- **Try/except/pass around `AuditClient.emit()`.** Forbidden by CLAUDE.md. Audit failure → adapter table sync fails → alert (per D-02).
- **Synthetic data in production CW tenant.** Test canaries live in a dedicated synthetic customer record (cw_company_id reserved for testing); CI test verifies no canary-phrase substring appears in any non-synthetic-customer text field after sync.
- **Permissive JSON parsing of CW responses.** Use pydantic strict mode; unknown fields go to a structured drift log, not silently accepted (Pitfall 8 mitigation).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTTP retry / backoff | custom `time.sleep` loops | `tenacity` decorators | Tenacity handles jitter, exception filtering, max attempts, deadline. Hand-rolled loops always lose one of these. |
| HTTP client with timeouts, HTTP/2, retries | `urllib`, raw `http.client` | `httpx` | First-class timeouts (read/write/connect/pool), modern transport, sync+async parity. |
| HMAC | inline `hashlib.sha256(salt + email)` | `hmac.new(salt, email, sha256)` | Length-extension safety; constant-time ops; standard. |
| JSON canonicalization for audit | hand-rolled `json.dumps(sort_keys=True)` | `barycenter.audit._canonicalize.canonicalize_json` | Already in the audit SDK; ensures chain digests are reproducible. |
| Per-tenant secret retrieval | parsing `.env` files, environment variables | `azure-keyvault-secrets` with managed identity | Versioning, access logging, RBAC, rotation all in one place. |
| Pagination state machines | hand-rolled "while next_page" loops | iterator function `def paginate(client, path) -> Iterator[dict]` that handles last-page detection (page < pageSize) ONCE | One source of truth for pagination logic; tested independently of any specific endpoint. |
| Rate limiting | sleep-on-429 inline in adapter | a single `RateLimiter` in `client.py` (token bucket, default 60 rpm = 1 req/s sustained, burst of 10) | CW's 60 rpm default needs respect; bursts to 1000-page fetches without throttling will trip auth-level lockouts. |
| YAML schema validation | `yaml.safe_load` + isinstance checks | pydantic `BaseModel` over the YAML | Same model class doubles as documentation. |
| Field-class enforcement | reviewer eyeballing PRs | `scripts/ci/field_class_check.py` (already exists from Phase 1) | Already wired; just add new columns to the registry. |
| CUI canary phrases | regex strings inlined per file | a single `compliance/cui-canary-phrases.yaml` loaded by `CanaryScanner` | One place to update; canary rotation is a YAML edit + rebuild. |
| ETL job orchestration | manual `cron` scripts | GitHub Actions `schedule:` trigger with OIDC auth | Per D-08, GitHub Actions is the only orchestration. |

**Key insight:** every "deceptively simple" piece of plumbing in an ETL pipeline (retry, pagination, rate limit, JSON canonicalization, secret fetching, schema validation) has at least one nasty edge case that bites in production. The repo already commits to the right libraries; Phase 2's job is to compose them, not re-implement them.

## Runtime State Inventory

> Phase 2 is mostly greenfield code, but several runtime systems WILL hold state that subsequent phases (and rotation runbook execution) depend on.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | `raw_cw.companies` already has rows from Phase 1 schema/grants tests (likely empty). `pseudo.person_map` is created in Phase 2 — empty. `ai_zone.*` tables created in Phase 2 — empty. `audit.chain_state` has `head_digest` advancing with each ETL emit. | None pre-Phase-2; Phase 2 sync writes are the first real population. |
| Live service config | ConnectWise Manage instance (Gravity's prod) — a CW API Member account + API Keys must be created OR an OAuth app registered. This config lives in CW's UI, NOT in git. The Onboarding Spec must record (a) which CW Member account, (b) creation date, (c) revocation procedure. | Manual (CW UI); credential lands in Key Vault `api-cw-*` secrets. Plan must include this as an operator step. |
| OS-registered state | None (sync runs in GH Actions ephemeral runners). | None. |
| Secrets / env vars | New KV secrets: `api-cw-public-key`, `api-cw-private-key`, `api-cw-client-id`, `api-cw-server-url` (or OAuth equivalents). Per-tenant `salt-{tenant_id}` secrets created on first encounter — versioned for ENC-02. KV access policy on `mi-bary-etl` MUST grant `secrets/get` on `salt-*` and `api-cw-*`; verify Phase 1 grants cover this. | KV secret creation step + access-policy verification step in plan. |
| Build artifacts / installed packages | `barycenter-etl` installed via `pip install -e packages/barycenter-etl` in CI; venv cache invalidates if pyproject.toml changes. | Standard CI cache key on `pyproject.toml` hash. |

**Salt rotation has its own runtime state:** `compliance/salt-rotation-state.yaml` records the dual-write window and active version per tenant. This file IS in git. The KV secret versions are NOT in git (secrets), but their version IDs (non-secret metadata) are referenced from the state YAML for audit reproducibility.

## Common Pitfalls

### Pitfall 1: Body content slips into `raw_cw.tickets` (LOAD-BEARING — Pitfall 2 from PITFALLS.md)

**What goes wrong:** A future PR adds a `body` or `internalAnalysis` column "for debugging." Indirect prompt injection becomes possible the moment that field is read by any AI-zone shape.
**Why it happens:** Body-stripping is treated as policy not architecture; the CW API returns body fields by default, and a developer who doesn't know the rule projects them.
**How to avoid:**
- DDL has no body columns; that's the architectural rule.
- CI test (`test_no_body_column.py`) iterates `INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA='raw_cw' AND TABLE_NAME='tickets'` and asserts none of `body|internalAnalysis|resolution|notes` appear.
- pydantic model for the CW ticket response uses `model_config = ConfigDict(extra='ignore')` AND explicitly omits body fields — drift log captures any unexpected.
- Field-class registry has no entry for body fields; any addition forces a registry update which forces reviewer attention.
**Warning signs:** PR adds a column to `raw_cw.tickets`; raw size grows unexpectedly.

### Pitfall 2: ConnectWise auth model varies between tenants

**What goes wrong:** Discretion locks "OAuth 2.0 client credentials" but Gravity's CW Manage instance may only support API Member key (HTTP Basic). Plan execution stalls trying to provision OAuth app.
**Why it happens:** CW's documented "API authentication" page covers BOTH methods; OAuth is more visible in newer docs but Member key is more universally enabled. [CITED: developers.cloudservices.connectwise.com/Guides/Authentication]
**How to avoid:**
- Build the auth module with a strategy interface: `CWAuthStrategy` with `BasicAuthStrategy` and `OAuthClientCredsStrategy` implementations.
- Configuration selects strategy via a YAML key. Plan includes a verification step BEFORE first nightly run: confirm with Gravity's CW admin which auth method is enabled, store appropriate KV secrets, set the strategy.
- If only Basic Auth is available, that's still acceptable per the locked decision spirit (credentials in Key Vault, retrieved via managed identity at runtime). The locked decision is about secret management, not the wire-format.
**Warning signs:** First adapter run fails with 401; OAuth token endpoint returns 404.

### Pitfall 3: CUI flag set late, or a new adapter copy-pasted from a pre-flag adapter (LOAD-BEARING — Pitfall 7 from PITFALLS.md)

**What goes wrong:** A customer is created without `cui_handling_required=1` set; sync runs for hours; CUI content lands in raw_cw.
**Why it happens:** Flag is sales-side metadata; ETL is engineering-side; lag is real.
**How to avoid:**
- CUI gate is in `AdapterBase`, not adapter code — adapters cannot bypass.
- The gate runs at every record (cheap: a single SQL lookup of `cui_handling_required` per company, cached per-run).
- Default is closed: an adapter MUST declare `CUI_SENSITIVE_TABLES`; missing declaration fails CI (decorator inspection).
- Quarterly review: COMP-03 verification sample of 50 records.
**Warning signs:** Adapter's `CUI_SENSITIVE_TABLES` is empty; new tenant created same day as detection of CUI marker.

### Pitfall 4: CW pagination silently truncates (LOAD-BEARING — Pitfall 9 from PITFALLS.md)

**What goes wrong:** Adapter caught a 429 mid-paging, retried 3x, exited with "no more pages" — but actually rate-limit-truthy. raw_cw has 60% of tickets; nothing alerts.
**Why it happens:** "End of pages" detection is "next page < pageSize"; that's also true if the last successful page returned mid-rate-limit.
**How to avoid:**
- Pagination iterator emits a `SyncResult` carrying `pages_fetched`, `total_records`, `last_page_size`, `terminal_reason` ("short_page"|"empty_page"|"http_error"|"rate_limit_exhausted").
- Adapter ASSERTs `terminal_reason in {"short_page","empty_page"}` before commit; otherwise raises and table-sync fails (D-02).
- Daily structural checksum: count of rows in `raw_cw.tickets` is logged and a 50%+ drop triggers alert.
**Warning signs:** Sync succeeds but row counts vary >20% night-over-night.

### Pitfall 5: HMAC pid reversibility (LOAD-BEARING — Pitfall 3 from PITFALLS.md)

**What goes wrong:** Salt leaks to log/script/Slack; attacker with AI-zone access reverses pids via dictionary attack on email convention.
**Why it happens:** Salt fetched once and assigned to a module-level variable; logged in error traceback; cached on disk for "perf."
**How to avoid:**
- `Pseudonymizer.derive(email, tenant_id)` fetches salt fresh, uses it, `del`s it, returns pid only.
- Salt fetch logged in KV diagnostic logs (existing Phase 1 plumbing).
- Salt never appears in `__repr__`, `logging.debug`, or any `AuditEvent` payload.
- Per-tenant salt: never global pid namespace.
- Ruff/mypy lint: a custom check that flags any module-level assignment to `salt = ...`.

### Pitfall 6: Schema drift in CW responses (LOAD-BEARING — Pitfall 8 from PITFALLS.md)

**What goes wrong:** CW v2024.3 renames `lastUpdated` to `_info.lastUpdated`. ETL accepts unknown fields; raw schema becomes stale; AI-zone derivations break silently.
**Why it happens:** Permissive JSON parsing.
**How to avoid:**
- pydantic models use strict field declarations; `extra='ignore'` but every "ignored" field is logged with a sample value to a drift log.
- Daily drift report posted to alerts channel; >0 unknown fields = open ticket (not auto-fail unless field count > threshold).
- `source_etag` (lastUpdated) field is required in models; missing → fail.

### Pitfall 7: Canary phrases cover text but not subjects/filenames/attachments (PITFALLS.md Pitfall 11; expanded by COMP-07)

**What goes wrong:** CUI marker appears in a ticket subject or PDF filename; text-only regex misses it.
**How to avoid:**
- `CanaryScanner` has separate methods: `scan_text`, `scan_subject`, `scan_filename`. All run.
- For CUI-flagged tenants, `refuse_attachment` returns `True` regardless of canary scan — attachments are dropped before fetch.
- For non-CUI tenants, attachment metadata (filename, content-type, size) is canary-scanned; marker → refuse + alert.
- CI fixture: synthetic ticket with CUI phrase in subject, filename, AND a binary "attachment" stub → assert all three are detected.

### Pitfall 8: Attempt to add a novel ai_zone shape

**What goes wrong:** An adapter author creates `ai_zone.tickets_summary` because `customer_features_*` "doesn't fit." The novel-table tests pass review (because nobody noticed). Five layers of defense are now incomplete for that table.
**How to avoid:**
- `test_no_novel_ai_zone.py`: parses every `sql/00-schemas/*.sql` for `CREATE TABLE ai_zone.*` and asserts table name ∈ canonical four.
- `ShapeBuilder.populate(shape)` raises if `shape ∉ CANONICAL`.
- Code review checklist item.

### Pitfall 9: Table-isolated fail-closed turns into orchestration failure (D-02)

**What goes wrong:** D-02 says each table syncs independently; an exception in `tickets` should not block `time_entries`. But a naive `for table in TABLES: table.sync()` propagates exceptions and aborts the run.
**How to avoid:**
- `AdapterBase.run()` wraps each table in `try/except Exception` (NOT in the `audit.emit` — that must propagate). On exception: emit failure audit event, alert, continue. On success: emit success event.
- `AuditEmitError` MUST propagate if it ever fires (CLAUDE.md mandate). The `try/except` covers CW API errors, network errors, schema-mismatch errors — not audit errors.

### Pitfall 10: Retention sweep races with the nightly sync

**What goes wrong:** Sweep deletes a row at the same moment sync is repopulating; row-level lock contention or worse, deleted-then-re-inserted dance creates spurious audit events.
**How to avoid:**
- Sweep runs at a different time-of-day from sync (e.g., 12:00 UTC vs 06:00 UTC sync).
- Sweep uses `READ COMMITTED SNAPSHOT` and skips tables whose `synced_at` is within the last 6 hours (sync window).
- Sweep is its own GH Actions workflow (`etl-retention-sweep.yml`).

## Code Examples

### Example 1: CW Manage authenticated client with rate limit + retry

```python
# packages/barycenter-etl/src/barycenter/etl/adapters/connectwise/client.py
# Source: synthesis of httpx + tenacity standard patterns; CW auth per developers.cloudservices.connectwise.com/Guides/Authentication
import httpx, time, base64
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from typing import Iterator

class CWManageClient:
    """ConnectWise Manage REST client. 60 rpm rate limit, page=25 default,
    pageSize max 1000. Last page detected by len(records) < pageSize.
    [CITED: rollout.com/integration-guides/connect-wise-manage/api-essentials]"""

    def __init__(self, server_url: str, company: str, public_key: str,
                 private_key: str, client_id: str, *, rpm: int = 60):
        auth_user = f"{company}+{public_key}"
        auth_token = base64.b64encode(f"{auth_user}:{private_key}".encode()).decode()
        self._headers = {
            "Authorization": f"Basic {auth_token}",
            "clientId": client_id,
            "Accept": "application/vnd.connectwise.com+json; version=2024.1",
        }
        self._client = httpx.Client(base_url=f"{server_url}/v4_6_release/apis/3.0",
                                    headers=self._headers, timeout=30.0)
        self._min_interval = 60.0 / rpm  # token bucket: simple sustained rate
        self._last = 0.0

    def _throttle(self):
        elapsed = time.monotonic() - self._last
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last = time.monotonic()

    @retry(stop=stop_after_attempt(5),
           wait=wait_exponential(multiplier=1, min=2, max=60),
           retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.TransportError)))
    def _get(self, path: str, params: dict) -> httpx.Response:
        self._throttle()
        r = self._client.get(path, params=params)
        if r.status_code == 429:
            # CW 429 → respect Retry-After if present, else exponential
            ra = int(r.headers.get("Retry-After", "5"))
            time.sleep(ra)
            r.raise_for_status()  # triggers tenacity
        r.raise_for_status()
        return r

    def paginate(self, path: str, *, page_size: int = 1000,
                 conditions: str | None = None) -> Iterator[dict]:
        page = 1
        while True:
            params = {"page": page, "pageSize": page_size}
            if conditions: params["conditions"] = conditions
            r = self._get(path, params)
            records = r.json()
            yield from records
            if len(records) < page_size:
                return  # last page (per CW pagination contract)
            page += 1
```

### Example 2: Pseudonymizer with versioned salt fetch

```python
# packages/barycenter-etl/src/barycenter/etl/framework/pseudonymizer.py
import hmac, hashlib
from azure.keyvault.secrets import SecretClient

class Pseudonymizer:
    def __init__(self, kv_client: SecretClient):
        self._kv = kv_client

    def derive(self, email: str, tenant_id: str, salt_version: str | None = None
              ) -> tuple[str, str]:
        """Returns (person_pid, salt_version_used). Salt never cached."""
        secret_name = f"salt-{tenant_id}"
        secret = self._kv.get_secret(secret_name, version=salt_version)  # latest if None
        try:
            pid = hmac.new(
                secret.value.encode(),
                email.lower().encode(),
                hashlib.sha256
            ).hexdigest()
            return pid, secret.properties.version
        finally:
            del secret  # ensure salt material is dereferenced
```

### Example 3: ETL recipe composition (companies)

```python
# packages/barycenter-etl/src/barycenter/etl/adapters/connectwise/recipes/companies.py
from barycenter.etl.primitives import as_is, drop, keyword_flags
from barycenter.etl.framework.recipe import ETLRecipe

def companies_recipe() -> ETLRecipe:
    return ETLRecipe(
        target_table="raw_cw.companies",
        derivations={
            "cw_company_id":          ("as_is",         {"field": "id"}),
            "company_name":           ("as_is",         {"field": "name"}),
            "billing_address_line1":  ("as_is",         {"field": "addressLine1"}),
            "billing_address_city":   ("as_is",         {"field": "city"}),
            "billing_address_region": ("as_is",         {"field": "state"}),
            "cui_handling_required":  ("keyword_flags", {"field": "types[].name",
                                                          "kw_dict": {"defense":"1","federal":"1"}}),
            "ai_opt_out":             ("as_is",         {"field": "customFields.ai_opt_out",
                                                          "default": False}),
            "source_etag":            ("as_is",         {"field": "_info.lastUpdated"}),
            # Body-like fields explicitly dropped:
            "_dropped_notes":         ("drop",          {"field": "notes"}),
        },
    )
```

### Example 4: Tickets recipe (no body)

```python
# packages/barycenter-etl/src/barycenter/etl/adapters/connectwise/recipes/tickets.py
def tickets_recipe() -> ETLRecipe:
    return ETLRecipe(
        target_table="raw_cw.tickets",
        derivations={
            "ticket_id":          ("as_is", {"field": "id"}),
            "cw_company_id":      ("as_is", {"field": "company.id"}),
            "summary":            ("as_is", {"field": "summary"}),  # subject only — canary scanned
            "status_name":        ("as_is", {"field": "status.name"}),
            "priority_name":      ("as_is", {"field": "priority.name"}),
            "type_name":          ("as_is", {"field": "type.name"}),
            "date_entered":       ("as_is", {"field": "_info.dateEntered"}),
            "last_updated":       ("as_is", {"field": "_info.lastUpdated"}),
            "source_etag":        ("as_is", {"field": "_info.lastUpdated"}),
            # CRITICAL: body fields explicitly dropped — this is also enforced by DDL absence
            "_dropped_initial_description":  ("drop", {"field": "initialDescription"}),
            "_dropped_resolution":           ("drop", {"field": "resolution"}),
            "_dropped_initial_internal":     ("drop", {"field": "initialInternalAnalysis"}),
        },
    )
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `requests` + manual retry | `httpx` + `tenacity` | 2022+ | Modern projects use httpx; tenacity is the de-facto retry decorator |
| Salt as a single static value | Versioned KV secrets per tenant | NIST SP 800-63B / ENISA 2018+ guidance [CITED: enisa.europa.eu Pseudonymisation Recommendations] | Enables rotation without breaking historical pseudonyms |
| Permissive JSON parsing for forward-compat | pydantic strict + drift log | 2023+ | Drift becomes a tracked event, not a silent regression |
| Stored-procedure-only ETL | Python-emitted parameterized SQL | 2020+ for CI-testability | SP-only ETL hard to unit-test; Python emitters give same semantics with mockable layers |
| Single global pepper | Per-tenant salt | GDPR/HIPAA segregation requirements | Cross-tenant correlation impossible from AI zone |

**Deprecated/outdated:**
- Hand-rolled cron on a VM — replaced by GH Actions schedule (D-08).
- `try/except: pass` around audit writes — forbidden (CLAUDE.md).
- Storing salts as env vars — replaced by KV with diagnostic logging.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | OAuth 2.0 client-credentials is enabled on Gravity's CW Manage tenant. | User Constraints / Standard Stack | Plan must include a verification step + Basic Auth fallback path. Mitigation: build auth as a strategy interface (Pitfall 2). |
| A2 | CW Manage `/time/entries` returns a row per entry, allowing client-side aggregation to bucketed totals. | Architecture (CW recipe set) | If CW only exposes pre-aggregated totals through a different endpoint, the time-entries recipe must use that endpoint instead. Confirm at first integration test. |
| A3 | `mi-bary-etl` already has KV `secrets/get` permission on `salt-*` and `api-cw-*` secret prefixes. | Runtime State Inventory | If not, Phase 2 plan must include an access-policy migration. Phase 1 grants likely cover `salt-*` (created Phase 1) but `api-cw-*` may be new. |
| A4 | `barycenter-audit` SDK supports the verbs Phase 2 needs (`etl.write`, `salt.rotate.*`, `retention.sweep`, `cui.boundary_violation`). | Architecture | If verbs are an enum requiring extension, plan needs a barycenter-audit version bump. Verify in `models.py` `AuditEvent.verb` typing. |
| A5 | Azure SQL `TRUNCATE TABLE` is permitted for `mi-bary-etl` on `raw_cw.*` (DROP+CREATE rights or specific TRUNCATE grant). Truncate-and-load (D-01) requires this. | Architecture | If only DELETE is granted, full-sync becomes `DELETE` + `INSERT`, slower and noisier in audit. Verify against `sql/10-grants/001_etl_grants.sql`. |
| A6 | CW Manage 60 rpm rate limit applies per API Member, not per tenant — adapter is single-threaded so a single token bucket is sufficient. | Pattern (rate limit) | If per-endpoint limits exist, a per-endpoint bucket is needed. Verify at integration. |
| A7 | The four canonical AI-zone shape names are exactly `customer_snapshot`, `customer_features_*`, `timeseries_aggregate`, `customer_memory` (from REQUIREMENTS.md TOOL-03 verbatim). The `customer_features_*` glob means one table per category (e.g., `customer_features_cw`); shape names are pre-declared, not arbitrary. | Architecture (Pattern 3) | If TOOL-03 intends literally one `customer_features` table with mixed contributions, the no-novel-shape test logic differs. Lock during plan-checker review. |
| A8 | Attachment refusal for CUI tenants means dropping at fetch (don't download) rather than fetch-then-discard. | Pattern 4 | CW's API may inline small attachment metadata in ticket responses; ensure pagination filters do not request attachment expansion. Verify CW API parameters at integration. |

## Open Questions (RESOLVED)

> All five questions raised during research were closed by plan decisions and the Plan 06 human-action gate. RESOLVED markers cite the implementing plan/task per Dimension 11.

1. **CW Manage auth mode in Gravity's instance — OAuth or API Member key?**
   - What we know: Both are documented; CW's developer portal lists OAuth Client Credentials for cloud, and API Member key (Basic) is the most universally enabled.
   - What's unclear: Which is enabled for Gravity's specific instance.
   - Recommendation: Build auth as strategy interface; first plan task is "verify auth mode with CW admin and store credentials in KV." If OAuth: store `client_id` + `client_secret` + token endpoint URL. If Basic: store `company`, `public_key`, `private_key`, `client_id`. The strategy class abstracts the difference.
   - **RESOLVED:** Plan 06 Task 1 (human-action gate) confirms auth mode with CW admin and stores the matching KV secrets; Plan 05 `client.py` implements both `BasicAuthStrategy` and `OAuthClientCredsStrategy` selectable via YAML config. The strategy interface absorbs whichever is enabled.

2. **Per-tenant vs per-CW-company salt scope.**
   - What we know: `pseudo.person_map` keys are `(cw_company_id, email)`. PROJECT.md says "per-tenant salt". In the MSP context, "tenant" means an MSP customer = a `cw_company_id`.
   - What's unclear: Should salt be per-cw_company_id (most isolated) or per-Gravity-MSSP-tenant (one salt for all MSP customers)?
   - Recommendation: Per `cw_company_id`. Maximizes isolation; matches the "per-tenant pid, never global" anti-pattern in PITFALLS.md. Each customer relationship is its own pseudonym namespace.
   - **RESOLVED:** Plan 02 `pseudonymizer.py` and Plan 04 `salt_rotation.py` both treat `tenant_id` as the `cw_company_id`. KV secret naming convention `salt-{tenant_id}` (= `salt-{cw_company_id}`) is locked into Plan 04 Task 2 implementation.

3. **Time-entry aggregation grain.**
   - What we know: REQUIREMENTS specifies "time entries (aggregates only)."
   - What's unclear: Aggregation grain (per-day per-company, per-week per-company, per-month per-ticket-type).
   - Recommendation: Per-day per-company, with rollups happening in `ai_zone.timeseries_aggregate`. Keep raw aggregation as conservative as possible (highest grain that is not a per-entry row).
   - **RESOLVED:** Plan 05 `recipes/time_entries.py` implements per-day per-company aggregation; Plan 04 `shape_builder.py` `_build_sql("timeseries_aggregate")` rolls up to per-month for the AI zone.

4. **Salt rotation frequency before fire-drill.**
   - What we know: Quarterly rotation per pitfall guidance.
   - What's unclear: Exact cadence and whether the fire drill counts as the first quarterly rotation.
   - Recommendation: Fire drill is the first rotation; quarterly cadence starts thereafter, scheduled in `compliance/salt-rotation-state.yaml`.
   - **RESOLVED:** Plan 01 Task 3 commits `compliance/salt-rotation-runbook.md` with the fire drill as step-zero; Plan 06 Task 2 (human-action) executes the fire drill and records outcome in `compliance/salt-rotation-state.yaml` `fire_drill` block. Quarterly cadence begins on the next Q boundary thereafter.

5. **CW v2024.x API version pinning.**
   - What we know: Adapter pins to a specific version in the `Accept` header.
   - What's unclear: Which version is current in Gravity's instance.
   - Recommendation: Pin to `2024.1` initially; verify at first run; bump as needed in a tracked PR. Drift log catches surprises.
   - **RESOLVED:** Plan 05 `adapters/connectwise/client.py` pins `Accept: application/vnd.connectwise.com+json; version=2024.1` as the default; drift log + Pitfall 6 schema-strict pydantic catches mismatches at first run.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12+ | All Phase 2 code | ✓ | 3.14.4 (homebrew) | — |
| `uv` | Local development | ✓ | 0.11.7 | `pip install -e` |
| `pytest` | All tests | ✓ | (system) | — |
| `ruff` | Lint | ✓ | (system) | — |
| `pyodbc` (driver: ODBC Driver 18 for SQL Server) | Azure SQL access | (system has pyodbc; ODBC driver is a separate install — verify at first integration) | — | Use `pymssql` fallback only if ODBC blocked; document. |
| `gh` CLI | GH Actions auth, OIDC verification | ✓ | 2.89.0 | — |
| `az` CLI | Local dev for KV access; not used in CI (OIDC) | ✓ | 2.84.0 | — |
| `sqlcmd` | Manual SQL inspection | ✓ | (homebrew) | Use `python -m barycenter.etl.tools.sqlcmd` wrapper |
| Bicep CLI | Phase 1 territory; unused in Phase 2 | ✓ | 0.42.1 | — |
| ConnectWise Manage tenant access | INT-01 | UNVERIFIED | — | Plan-time blocker: confirm with Gravity admin |
| KV access policy on `mi-bary-etl` for `api-cw-*` | adapter auth | UNVERIFIED | — | Plan must include policy verification/extension |

**Missing dependencies with no fallback:**
- ConnectWise Manage tenant credentials and confirmed auth mode — first plan task.

**Missing dependencies with fallback:**
- ODBC Driver 18 verification — confirm in CI image before first sync; `pymssql` is a fallback if blocked.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | `pytest >=8.3` |
| Config file | `packages/barycenter-etl/pyproject.toml` `[tool.pytest.ini_options]` (Wave 0 if not present) |
| Quick run command | `pytest packages/barycenter-etl/tests -x -q` |
| Full suite command | `pytest packages/barycenter-audit packages/barycenter-etl --maxfail=3 && python scripts/ci/field_class_check.py && python scripts/ci/grant_drift_check.py` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TOOL-01 | Onboarding spec template exists, validates against pydantic model | unit | `pytest packages/barycenter-etl/tests/test_onboarding_spec.py -x` | ❌ Wave 0 |
| TOOL-02 | All 8 primitives present; recipe composition can only use them | unit | `pytest packages/barycenter-etl/tests/test_primitives_*.py packages/barycenter-etl/tests/test_recipe_no_bypass.py -x` | ❌ Wave 0 |
| TOOL-03 | 4 canonical shape names enforced; novel-table introduction fails | unit | `pytest packages/barycenter-etl/tests/test_no_novel_ai_zone.py -x` | ❌ Wave 0 |
| TOOL-04 | Category enum exists; adapter declares category; recipe inheritance works | unit | `pytest packages/barycenter-etl/tests/test_category.py -x` | ❌ Wave 0 |
| INT-01 | CW client paginates, retries, respects rate limit; recipes write to raw_cw.* | integration (respx) | `pytest packages/barycenter-etl/tests/adapters/connectwise -x` | ❌ Wave 0 |
| INT-01 / Success Criterion 2 | `raw_cw.tickets` has no body column | unit (DB schema) | `pytest packages/barycenter-etl/tests/test_no_body_column.py -x` | ❌ Wave 0 |
| COMP-03 | CUI gate skips sensitive tables for flagged tenants; defaults `ai_opt_out=true` | unit + integration | `pytest packages/barycenter-etl/tests/test_cui_gate.py -x` | ❌ Wave 0 |
| COMP-07 | Canary phrase in subject/filename/attachment triggers refusal | unit | `pytest packages/barycenter-etl/tests/test_canary.py -x` | ❌ Wave 0 |
| ENC-02 | Salt rotation produces new pseudonyms; dual-write window valid; runbook executable | integration (KV mocked) | `pytest packages/barycenter-etl/tests/test_salt_rotation.py -x` | ❌ Wave 0 |
| ENC-02 / Fire drill | Documented runbook execution log committed | manual + checklist | (operator-driven; outcome committed to `compliance/salt-rotation-state.yaml`) | ❌ Wave 0 |
| RET-01 | Sweeper deletes rows older than per-class TTL with per-customer overrides | unit | `pytest packages/barycenter-etl/tests/test_retention.py -x` | ❌ Wave 0 |
| Phase Success #1 | Adapters can only compose recipes from primitives | unit (CI gate) | `pytest packages/barycenter-etl/tests/test_recipe_no_bypass.py` | ❌ Wave 0 |
| Phase Success #4 | New `ai_zone.X` outside canonical fails review/CI | unit (CI gate) | `pytest packages/barycenter-etl/tests/test_no_novel_ai_zone.py` | ❌ Wave 0 |
| Phase Success #5 | Salt rotation runbook committed + fire-drill log present | doc check | `python scripts/ci/check_salt_runbook.py` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest packages/barycenter-etl/tests -x -q` (target < 30s)
- **Per wave merge:** full suite (above) + `scripts/ci/field_class_check.py` + `scripts/ci/grant_drift_check.py` + `etl-cw-nightly.yml` `workflow_dispatch` dry-run
- **Phase gate:** full suite green + fire drill executed + runbook committed before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `packages/barycenter-etl/pyproject.toml` — package skeleton with pytest config
- [ ] `packages/barycenter-etl/tests/conftest.py` — shared fixtures (mock KV, mock SQL, mock CW server via respx)
- [ ] `packages/barycenter-etl/tests/test_no_body_column.py` — INFORMATION_SCHEMA assertion
- [ ] `packages/barycenter-etl/tests/test_recipe_no_bypass.py` — primitive-only enforcement
- [ ] `packages/barycenter-etl/tests/test_no_novel_ai_zone.py` — canonical shape enforcement
- [ ] `compliance/cui-canary-phrases.yaml` — phrase dictionary
- [ ] `compliance/retention-policy.yaml` — per-class TTL config
- [ ] `compliance/tool-onboarding-spec.template.md` — TOOL-01 template
- [ ] `compliance/salt-rotation-runbook.md` — ENC-02 runbook
- [ ] `compliance/salt-rotation-state.yaml` — rotation state tracker
- [ ] `scripts/ci/check_salt_runbook.py` — CI gate verifying runbook + drill log present
- [ ] `.github/workflows/etl-cw-nightly.yml` — schedule trigger
- [ ] `.github/workflows/etl-retention-sweep.yml` — daily TTL sweep
- [ ] Framework install: `pip install -e packages/barycenter-etl[dev]` — added to `.github/workflows/python-tests.yml`

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | OAuth client-creds OR API Member Basic Auth, secrets in Key Vault, retrieved via mi-bary-etl managed identity |
| V3 Session Management | partial | Stateless (no user session); token TTL bounded by OAuth lifetime; managed identity tokens auto-refresh |
| V4 Access Control | yes | `mi-bary-etl` granted ONLY raw_cw + pseudo + ai_zone (write); explicit DENY on other schemas (existing Phase 1 grants) |
| V5 Input Validation | yes | pydantic strict models on every CW JSON response; drift logged for unknown fields |
| V6 Cryptography | yes | `hmac` stdlib (never hand-rolled); SHA-256; salt material from KV only; `del` after use |
| V7 Error Handling & Logging | yes | `AuditClient.emit()` fail-closed; salt never in `__repr__` or logs; canary hits emit critical event |
| V8 Data Protection | yes | RESTRICTED columns tagged in field-class registry; body fields not projected; attachments refused for CUI tenants |
| V9 Communications | yes | TLS 1.2+ enforced by httpx default + Azure SQL connection string; CW endpoint over HTTPS only |
| V10 Malicious Code | partial | No external code execution from CW responses; pydantic prevents object instantiation surprises |
| V14 Configuration | yes | All config in YAML, version-controlled; secrets in KV; OIDC env-scoped per Pitfall 11 |

### Known Threat Patterns for {Python ETL + CW REST + Azure SQL}

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| SQL injection via CW field values | Tampering | Parameterized statements only; recipes emit parameter dicts, never f-strings |
| Indirect prompt injection via ticket body | Information Disclosure | Body fields architecturally not projected; CI test on schema |
| Salt leakage via logs/exceptions | Information Disclosure | `del` after use; ruff lint against module-level `salt = `; KV diagnostic logging of every fetch |
| CUI marker bypassing text-only scan | Information Disclosure | Multi-field scanner (text, subject, filename, attachment); attachment refusal for CUI tenants |
| Schema drift hiding renamed fields | Tampering / DoS | Strict pydantic + drift log; daily structural checksum |
| 429 retry exhaustion silent truncation | DoS / Repudiation | `terminal_reason` enforced; row-count drop alert |
| Audit emit silent failure | Repudiation | Fail-closed by `AuditClient` design (CLAUDE.md mandate); rollback parent transaction |
| Cross-tenant pseudonym correlation | Information Disclosure | Per-cw_company_id salt; no global pid namespace |
| Stale salt after compromise | Spoofing | Versioned KV secrets; rotation runbook + fire drill |
| Adapter bypassing primitive layer | Tampering | CI gate (`test_recipe_no_bypass`); reviewer checklist |
| Novel ai_zone table introduction | Information Disclosure | CI gate (`test_no_novel_ai_zone`); ShapeBuilder.populate guard |
| OIDC subject claim wildcard | Spoofing | Env-scoped subject per Phase 1 Pitfall 11 (already enforced) |

## Sources

### Primary (HIGH confidence)

- File: `packages/barycenter-audit/` (entire package) — audit SDK API surface, pyproject patterns, test conventions
- File: `sql/00-schemas/001_create_raw_cw.sql`, `002_create_ai_zone.sql`, `003_create_audit.sql`, `004_create_pseudo.sql` — existing schema baseline
- File: `sql/10-grants/001_etl_grants.sql` — existing ETL grant model (CRUD on raw_cw, DENY elsewhere)
- File: `compliance/field-class-registry.yaml` — VER-02 source of truth for column tagging
- File: `scripts/ci/field_class_check.py`, `scripts/ci/grant_drift_check.py` — existing CI gates from Phase 1
- File: `.planning/research/PITFALLS.md` — pitfalls 2 (body), 3 (HMAC), 7 (CUI), 8 (drift), 9 (pagination), 11 (canary)
- File: `.planning/research/ARCHITECTURE.md` §13–14 — eight primitives + four shapes already specified
- File: `.planning/research/STACK.md` — confirmed CW egress through FortiGate FQDN allowlist
- File: `CLAUDE.md` — audit path, mono-repo, CI, security mandates
- PyPI registry — confirmed library versions on 2026-05-02

### Secondary (MEDIUM confidence)

- [CW Developer Portal — Authentication](https://developers.cloudservices.connectwise.com/Guides/Authentication) — OAuth + Basic Auth options
- [CW Manage API Essentials — Rollout](https://rollout.com/integration-guides/connect-wise-manage/api-essentials) — 60 rpm default rate limit, page/pageSize defaults
- [How CW Manage Pagination Works (Lazy Administrator)](https://www.thelazyadministrator.com/2024/06/06/how-the-connectwise-manage-api-handles-pagination-with-powershell/) — last-page detection by short page
- [ENISA Pseudonymisation Recommendations](https://www.anonos.com/hubfs/ENISA_Pseudonymisation_Recomendations_GDPR_November_2018.pdf) — versioned salt + rotation guidance
- [ENISA Data Pseudonymisation: Advanced Techniques](https://www.enisa.europa.eu/sites/default/files/publications/ENISA%20Report%20-%20Data%20Pseudonymisation%20-%20Advanced%20Techniques%20and%20Use%20Cases.pdf) — HMAC reversibility on low-entropy inputs

### Tertiary (LOW confidence — needs validation at implementation)

- CW Manage time-entry endpoint exact response shape (assumption A2)
- CW Manage `Accept` header version-pinning string format (assumption — verify against Gravity's specific instance)
- Whether CW rate limit is per-Member or per-tenant (assumption A6)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all library versions verified against PyPI 2026-05-02; CW REST patterns confirmed against multiple independent sources
- Architecture: HIGH (structural) / MEDIUM (CW-specific endpoint behavior) — patterns 1–7 are direct extensions of Phase 1 conventions; CW endpoint pagination/auth confirmed but tenant-specific quirks remain
- Pitfalls: HIGH — directly inherited from validated `.planning/research/PITFALLS.md`; Phase 2 versions are concrete instantiations
- ENC-02 rotation strategy: MEDIUM — the dual-write window is a design choice; alternative is hard-cutover with backfill. Plan-checker should confirm.
- Validation architecture: HIGH — pytest already in use; gates already in `scripts/ci/`

**Research date:** 2026-05-02
**Valid until:** 2026-06-01 (30 days; library ecosystem stable, CW API versioning slow)
