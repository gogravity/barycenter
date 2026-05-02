---
phase: 2
slug: tool-onboarding-framework-connectwise-manage
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-02
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | `packages/barycenter-etl/pyproject.toml` — Wave 0 installs |
| **Quick run command** | `cd packages/barycenter-etl && uv run pytest tests/ -x -q` |
| **Full suite command** | `cd packages/barycenter-etl && uv run pytest tests/ -v` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd packages/barycenter-etl && uv run pytest tests/ -x -q`
- **After every plan wave:** Run `cd packages/barycenter-etl && uv run pytest tests/ -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 2-01-01 | 01 | 1 | TOOL-01 | — | Primitives enforce allow-list; no bypass path | unit | `uv run pytest tests/test_primitives.py -x -q` | ❌ W0 | ⬜ pending |
| 2-01-02 | 01 | 1 | TOOL-01 | — | Recipe composition validates all columns map to primitives | unit | `uv run pytest tests/test_recipe_no_bypass.py -x -q` | ❌ W0 | ⬜ pending |
| 2-02-01 | 02 | 1 | TOOL-02/INT-01 | — | raw_cw.tickets schema has no body column | unit | `uv run pytest tests/test_no_body_column.py -x -q` | ❌ W0 | ⬜ pending |
| 2-02-02 | 02 | 1 | INT-01 | — | CW adapter syncs companies, agreements, ticket metadata, configurations, time-entry aggregates | integration | `uv run pytest tests/test_cw_adapter.py -x -q` | ❌ W0 | ⬜ pending |
| 2-03-01 | 03 | 2 | COMP-03/COMP-07 | — | CUI-flagged tenant: no tickets, no asset details, ai_opt_out=true | unit | `uv run pytest tests/test_cui_gate.py -x -q` | ❌ W0 | ⬜ pending |
| 2-03-02 | 03 | 2 | COMP-07 | — | CUI canary in subject/filename/attachment triggers detection and refusal | unit | `uv run pytest tests/test_canary_scanner.py -x -q` | ❌ W0 | ⬜ pending |
| 2-04-01 | 04 | 2 | TOOL-03 | — | Four canonical AI-zone shapes populate from CW data | unit | `uv run pytest tests/test_ai_zone_shapes.py -x -q` | ❌ W0 | ⬜ pending |
| 2-04-02 | 04 | 2 | TOOL-03 | — | Novel AI-zone table attempt fails CI | unit | `uv run pytest tests/test_no_novel_ai_zone.py -x -q` | ❌ W0 | ⬜ pending |
| 2-05-01 | 05 | 3 | ENC-02 | — | Salt rotation: versioned pepper IDs roll forward, downstream pseudonyms valid | unit | `uv run pytest tests/test_salt_rotation.py -x -q` | ❌ W0 | ⬜ pending |
| 2-05-02 | 05 | 3 | ENC-02 | — | Fire-drill log committed to repo | manual | `check_salt_runbook.py` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `packages/barycenter-etl/tests/test_primitives.py` — stubs for TOOL-01 primitive allow-list
- [ ] `packages/barycenter-etl/tests/test_recipe_no_bypass.py` — stubs for TOOL-01 recipe enforcement
- [ ] `packages/barycenter-etl/tests/test_no_body_column.py` — stubs for TOOL-02 body-strip gate
- [ ] `packages/barycenter-etl/tests/test_cw_adapter.py` — stubs for INT-01 adapter sync
- [ ] `packages/barycenter-etl/tests/test_cui_gate.py` — stubs for COMP-03/COMP-07 CUI enforcement
- [ ] `packages/barycenter-etl/tests/test_canary_scanner.py` — stubs for COMP-07 canary detection
- [ ] `packages/barycenter-etl/tests/test_ai_zone_shapes.py` — stubs for TOOL-03 shape population
- [ ] `packages/barycenter-etl/tests/test_no_novel_ai_zone.py` — stubs for TOOL-03 novel-shape CI gate
- [ ] `packages/barycenter-etl/tests/test_salt_rotation.py` — stubs for ENC-02 rotation
- [ ] `packages/barycenter-etl/tests/conftest.py` — shared fixtures (synthetic CW data, CUI tenant, mock KV)
- [ ] `packages/barycenter-etl/pyproject.toml` — package + pytest config
- [ ] `scripts/check_salt_runbook.py` — ENC-02 fire-drill verification

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Salt rotation fire drill on non-production tenant | ENC-02 | Requires live KV + real tenant connection | Execute `scripts/salt_rotation_runbook.md` against dev tenant, commit log to repo |
| CW OAuth auth mode confirmation (Gravity tenant) | INT-01 | Depends on Gravity tenant configuration | Check KV for `api-cw-client-id` + `api-cw-client-secret`; if absent, verify Basic Auth fallback |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
