# Project State

## Project Reference

**Building:** Barycenter — MSP-internal AI-safe data platform (Azure-native, two-zone PII architecture)
**Core Value:** Make it architecturally impossible for AI agents to leak customer PII or CUI.

## Current Position

- **Phase:** Not started (defining requirements → roadmap next)
- **Plan:** —
- **Status:** Milestone v1.0 started; requirements defined; roadmap pending

## Progress

`[█░░░░░░░░░] 10%` — initialization + research complete

## Recent Decisions

See PROJECT.md "Key Decisions" — 12 architectural decisions logged (two-zone schema isolation, HMAC pid, five-layer defense, etc.). All currently `Pending` until validated by phase outcomes.

Research surfaced spine: Foundations → Tool Onboarding Framework + Tool #1 → Agent-Safe Access Layer + Leak Test → Tools #2/#3 → Compliance Posture.

## Pending Todos

None captured.

## Blockers / Concerns

7 LOAD-BEARING pitfalls front-loaded by research (see `research/PITFALLS.md`):
1. Indirect prompt injection via tool-sourced free text
2. HMAC pid reversibility
3. Multi-hop reasoning re-identification
4. Anthropic BAA / ZDR scope misunderstood
5. CUI exclusion flag enforcement gaps
6. Audit log volume / truncation
7. Temporary developer raw-zone access becoming permanent

## Session Continuity

- **Last session:** 2026-05-01 — research completed and committed (`9181f9c docs: complete project research`)
- **This session:** 2026-05-02 — milestone v1.0 started; architecture revised (cost-simplified, FortiGate, owned gateway); research re-run; requirements defined
- **Stopped at:** REQUIREMENTS.md written; roadmap not yet created
- **Resume file:** none

## Artifacts Present

- `.planning/PROJECT.md` ✓
- `.planning/research/SUMMARY.md` ✓ (plus STACK / FEATURES / ARCHITECTURE / PITFALLS)
- `.planning/ROADMAP.md` ✗ — not yet created
- `.planning/phases/` ✗ — not yet created
