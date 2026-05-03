# Phase 2: Tool Onboarding Framework + ConnectWise Manage - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-02
**Phase:** 02-tool-onboarding-framework-connectwise-manage
**Areas discussed:** CW Manage sync strategy

---

## CW Manage Sync Strategy

### Q1: Sync mode

| Option | Description | Selected |
|--------|-------------|----------|
| Full sync on schedule | Truncate-and-reload each table nightly. Simple state machine, easy correctness proof, automatic deletion detection. | ✓ |
| Incremental delta (modified-since) | Fetch only records modified since last run using CW lastUpdated filter. Efficient at scale but requires persisting watermark and handling soft-deletes. | |
| Incremental + full weekly reconcile | Delta runs hourly; weekly full sync reconciles drift. More complex. | |

**User's choice:** Full sync on schedule

---

### Q2: Cadence and failure behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Nightly, fail-closed per table | Each table syncs independently; failure alerts without blocking other tables. | ✓ |
| Nightly, all-or-nothing transaction | All tables in one transaction; any failure rolls back entire sync. | |
| Every 4h, fail-closed per table | More frequent freshness; still isolated per table. | |

**User's choice:** Nightly, fail-closed per table

---

### Q3: Job execution environment

| Option | Description | Selected |
|--------|-------------|----------|
| GitHub Actions scheduled workflow | Cron trigger. Consistent with D-08 (GitHub Actions only). Uses existing OIDC federated credential. No new infra. | ✓ |
| Azure Container Instance / Function | Runs in Azure directly. Better for long-running / high-frequency syncs but adds infra complexity. | |

**User's choice:** GitHub Actions scheduled workflow

---

## Claude's Discretion

- ETL framework package layout (new `packages/barycenter-etl/`)
- T-SQL primitives residence (Python functions vs. stored procs)
- AI-zone shape materialization (ETL-populated tables vs. SQL views)
- CW Manage API auth approach
- Retry / backoff behavior
- `source_etag` usage

## Deferred Ideas

None.
