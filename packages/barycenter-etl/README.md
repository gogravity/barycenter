# barycenter-etl

Tool onboarding framework and ConnectWise Manage adapter for Barycenter (Phase 2).

This package provides:

- Eight composable transformation primitives (TOOL-02): `drop`, `hash`, `pseudonymize`,
  `aggregate`, `bucket`, `score`, `keyword_flags`, `as_is`.
- Framework layer (`AdapterBase`, `CUIGate`, `CanaryScanner`, `Pseudonymizer`,
  `ShapeBuilder`, `RetentionSweeper`, `SaltRotation`).
- ConnectWise Manage adapter (`adapters/connectwise/`) — companies, agreements,
  tickets (metadata only), configurations, time-entry aggregates (INT-01).
- Four canonical AI-zone shape builders (TOOL-03).

All ETL writes go through the existing `barycenter.audit.AuditClient` fail-closed
audit path (no parallel audit). Adapters cannot bypass primitives, the body-strip
rule, or the CUI gate — these are framework-level constraints enforced by CI gates.

See `.planning/phases/02-tool-onboarding-framework-connectwise-manage/02-RESEARCH.md`
for architecture, primitive contracts, salt rotation runbook design, and the full
list of pitfalls and mitigations.
