# Phase 2: Tool Onboarding Framework + ConnectWise Manage - Context

**Gathered:** 2026-05-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 2 delivers the reusable ETL framework that all future tool integrations inherit from,
exercised end-to-end against ConnectWise Manage (INT-01) as the first proof integration.
Scope: eight T-SQL transformation primitives (TOOL-02), four canonical AI-zone shapes
(TOOL-03), tool intake spec template (TOOL-01), tool category taxonomy (TOOL-04), CW Manage
adapter for companies / agreements / tickets (metadata only) / configurations / time-entry
aggregates (INT-01), CUI enforcement and canary detection (COMP-03, COMP-07), and salt
rotation runbook + fire drill (ENC-02). Per-class retention policy enforcement (RET-01).

Phase 2 does NOT add: agent access layer, typed functions, gateway, VER-01 leak test, or
integrations beyond CW Manage.

</domain>

<decisions>
## Implementation Decisions

### CW Manage Sync Strategy

- **D-01:** Sync mode is **full-sync on schedule** — truncate-and-reload each `raw_cw.*`
  table on a nightly cron. No watermark or soft-delete tracking needed. Correctness is
  easy to prove for the INT-01 framework proof. Deletion detection is automatic (missing
  row = deleted).

- **D-02:** Sync cadence is **nightly**, table-isolated fail-closed. Each table syncs
  independently; if one table's sync fails (CW API error, schema mismatch, audit write
  failure), it errors out and fires an alert without rolling back or blocking other
  tables. `raw_cw` remains in last-good state for the failed table.

- **D-03:** Sync job runs as a **GitHub Actions scheduled workflow** (cron trigger).
  Consistent with D-08 from Phase 1 (GitHub Actions only). Uses the existing OIDC
  federated credential on `mi-bary-etl`; no new Azure infra required for job execution.

### Claude's Discretion

The following areas were not discussed — Claude has full discretion within the Phase 1
architectural constraints:

- **ETL framework package layout:** Follow the `packages/barycenter-audit/` pattern.
  A new `packages/barycenter-etl/` package is the natural fit; adapter base class,
  primitive functions, and CW adapter all live there.

- **T-SQL transformation primitives residence (TOOL-02):** The ROADMAP calls these
  "T-SQL primitives" but implementation choice is open. Python functions that produce
  parameterized SQL (UPSERT / MERGE statements) are consistent with the existing
  Python-heavy codebase and allow unit testing without a SQL server. Deploy as Python,
  not stored procs, unless there's a clear performance or enforcement reason for SQL.

- **AI-zone shape materialization (TOOL-03):** ETL-populated staging tables (not live
  views) for Phase 2 so the shapes are auditable and can carry a `synced_at` timestamp.
  Phase 3 can expose typed functions over these tables.

- **CW Manage API auth:** OAuth 2.0 client credentials (CW REST v2024.x). Credentials
  stored in Key Vault, retrieved at runtime by `mi-bary-etl` via managed identity.

- **Retry behavior:** Exponential backoff with cap on transient API errors; permanent
  failures (schema mismatch, CUI block) raise immediately without retry.

- **`source_etag` usage:** Store the CW record `lastUpdated` timestamp as `source_etag`
  to enable future incremental migration without schema changes.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase Requirements
- `.planning/REQUIREMENTS.md` — Full requirement text for TOOL-01, TOOL-02, TOOL-03,
  TOOL-04, INT-01, COMP-03, COMP-07, ENC-02, RET-01

### Project Context
- `.planning/PROJECT.md` — Two-zone model, identifier hierarchy, five-layer defense,
  constraint rationale ($166/mo budget, owned gateway, FortiGate BYOL, HIPAA-only)
- `.planning/ROADMAP.md` §Phase 2 — Phase goal, success criteria 1–5, requirement list

### Phase 1 Outputs (load-bearing for Phase 2)
- `.planning/phases/01-network-data-foundations/01-CONTEXT.md` — D-04 (audit SDK as
  only audit path), D-05 (chain_state table), D-06 (fail-closed writes), D-07 (mono-repo),
  D-08 (GitHub Actions only), D-03 (OIDC / managed identity auth pattern)

### Existing SQL Schema
- `sql/00-schemas/001_create_raw_cw.sql` — raw_cw table definitions (companies,
  agreements, raw_cw.tickets must NOT have a body column — verify and enforce)
- `sql/00-schemas/002_create_ai_zone.sql` — ai_zone schema (empty; Phase 2 adds tables)
- `sql/00-schemas/004_create_pseudo.sql` — pseudo schema for pseudonym map

### No external CW Manage spec committed yet
CW Manage REST API documentation is online; adapter should pin to a specific API version
in config.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `packages/barycenter-audit/` — `AuditClient`, `AuditEvent`, `AuditEmitError`: ETL must
  call `AuditClient.emit()` for every `raw_cw.*` write. No parallel audit path.
- `scripts/ci/field_class_check.py` — VER-02 gate already wired; new `raw_cw` columns
  must be added to `compliance/field-class-registry.yaml` or CI fails.
- `scripts/ci/grant_drift_check.py` — Grant drift detection already live; any new grants
  needed by `mi-bary-etl` must be in `sql/10-grants/001_etl_grants.sql`.

### Established Patterns
- Python package layout: `packages/{name}/src/`, `packages/{name}/tests/`, `pyproject.toml`
- CI: GitHub Actions OIDC with `mi-bary-etl` managed identity as the ETL identity
- SQL migrations: numbered files in `sql/00-schemas/` (schema DDL), `sql/10-grants/` (grants)
- Field-class tagging: every new column gets a `field-class-registry.yaml` entry

### Integration Points
- `raw_cw.*` tables (exist from Phase 1 schema) ← Phase 2 ETL writes here
- `ai_zone` schema (exists, empty) ← Phase 2 ETL creates and populates 4 canonical tables
- `audit.chain_state` (exists) ← AuditClient.emit() locks and updates this per write
- Key Vault `mi-bary-etl` HMAC sign permission (granted Phase 1) ← pseudonymization calls this
- GitHub Actions OIDC federated credential (created Phase 1) ← sync workflow uses this

</code_context>

<specifics>
## Specific Ideas

No specific implementation references cited during discussion beyond the architectural
constraints already captured above.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within Phase 2 scope.

</deferred>

---

*Phase: 02-tool-onboarding-framework-connectwise-manage*
*Context gathered: 2026-05-02*
