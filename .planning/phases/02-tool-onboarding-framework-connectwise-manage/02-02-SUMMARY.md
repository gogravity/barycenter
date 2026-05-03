---
phase: 02
plan: 02
subsystem: barycenter-etl/primitives + framework
tags: [TOOL-01, TOOL-02, ENC-02, no-bypass, pseudonymizer]
requires:
  - barycenter-etl scaffold (Plan 02-01)
  - barycenter-audit (exceptions analog)
provides:
  - barycenter.etl.primitives.PRIMITIVE_REGISTRY (8 primitives)
  - barycenter.etl.framework.recipe.ETLRecipe (no-bypass invariant)
  - barycenter.etl.framework.pseudonymizer.Pseudonymizer (Pitfall 5 mitigated)
  - barycenter.etl.framework.exceptions (ETLError hierarchy)
affects:
  - All future adapter recipes (must compose only from PRIMITIVE_REGISTRY)
tech-stack:
  added: []
  patterns:
    - Pure-function primitive modules + barrel registry (mirrors audit.chain pattern)
    - pydantic field_validator for construction-time invariant enforcement
    - Fresh-fetch + finally-del pattern for KV salt material (Pitfall 5)
key-files:
  created:
    - packages/barycenter-etl/src/barycenter/etl/primitives/_result.py
    - packages/barycenter-etl/src/barycenter/etl/primitives/drop.py
    - packages/barycenter-etl/src/barycenter/etl/primitives/hash.py
    - packages/barycenter-etl/src/barycenter/etl/primitives/pseudonymize.py
    - packages/barycenter-etl/src/barycenter/etl/primitives/aggregate.py
    - packages/barycenter-etl/src/barycenter/etl/primitives/bucket.py
    - packages/barycenter-etl/src/barycenter/etl/primitives/score.py
    - packages/barycenter-etl/src/barycenter/etl/primitives/keyword_flags.py
    - packages/barycenter-etl/src/barycenter/etl/primitives/as_is.py
    - packages/barycenter-etl/src/barycenter/etl/framework/exceptions.py
    - packages/barycenter-etl/src/barycenter/etl/framework/pseudonymizer.py
    - packages/barycenter-etl/src/barycenter/etl/framework/recipe.py
  modified:
    - packages/barycenter-etl/src/barycenter/etl/__init__.py
    - packages/barycenter-etl/src/barycenter/etl/primitives/__init__.py
    - packages/barycenter-etl/src/barycenter/etl/framework/__init__.py
    - packages/barycenter-etl/tests/test_primitives_*.py (8 files)
    - packages/barycenter-etl/tests/test_pseudonymizer.py
    - packages/barycenter-etl/tests/test_recipe_no_bypass.py
decisions:
  - "score primitive uses sanitized eval (char allowlist, empty builtins/locals) — sufficient for numeric formulas; rejects identifier carry-through after substitution"
  - "as_is requires explicit field_class declaration; default ('PUBLIC') with default only_classes ('PUBLIC','INTERNAL') is the safe path; RESTRICTED requires opting both knobs"
  - "pseudonymize primitive emits {field}_salt_version param so the audit log can replay the derivation under salt rotation"
  - "ETLRecipe.compile returns parameterized SQL only; primitives never execute SQL"
metrics:
  duration: ~12 min
  completed: 2026-05-02
  tests_passing: 40
  tasks_completed: 2
---

# Phase 2 Plan 02: Primitives + Framework Core Summary

Implemented the inviolable transformation layer (TOOL-02): eight pure-function
primitives, a registry-enforced ETLRecipe model, the ETL exception hierarchy,
and the per-call Key Vault Pseudonymizer that mitigates Pitfall 5.

## What Was Built

### Task 1 — Primitives package (commit eda9068)
- `PrimitiveResult` dataclass (frozen) with `field_class` invariant against
  `{RESTRICTED, SENSITIVE, INTERNAL, PUBLIC, DROPPED}`.
- Eight primitive modules, each with a single function and a docstring tying
  it to its TOOL-02 contract:
  - `drop` → `field_class='DROPPED'`, empty expr; recipe compiler skips it.
  - `hash_` → SQL Server `HASHBYTES('SHA2_256', ?)` parameterized expression.
  - `pseudonymize` → delegates to framework Pseudonymizer; emits pid + salt
    version under `SENSITIVE`.
  - `aggregate` (SUM/COUNT/AVG/MAX/MIN), `bucket` (range labels), `score`
    (sanitized eval), `keyword_flags`, `as_is` (only_classes guardrail).
- `primitives/__init__.py` exports `PRIMITIVE_REGISTRY` — single source of
  truth that the no-bypass CI gate references.

### Task 2 — Framework: ETLRecipe + Pseudonymizer + exceptions (commit 63be666)
- `ETLRecipe` (pydantic, `extra='forbid'`) with `field_validator` that walks
  every derivation and asserts `primitive_name in PRIMITIVE_REGISTRY`. Raises
  `ValueError` containing the literal phrase `bypasses primitive layer` —
  matched by the CI gate test.
- `ETLRecipe.compile(record, *, kv_client, tenant_id)` dispatches per
  primitive name, skips DROPPED columns, builds an `INSERT INTO target_table
  (cols) VALUES (?, ?, ...)` template with a parameter dict. Values never
  enter the SQL string (T-02-06).
- `Pseudonymizer.derive(email, tenant_id, salt_version=None)` fetches
  `salt-{tenant_id}` fresh from Key Vault every call (verified by test:
  call_count == 2 after two derives). Email lowercased before HMAC-SHA256.
  `salt_bytes` dereferenced in `finally`; `__repr__` excludes salt material.
- `framework/exceptions.py` declares `ETLError` + `CUIBoundaryViolation`,
  `SchemaDriftError`, `RateLimitExhausted`, `PaginationTruncated`.
- Top-level `barycenter.etl` barrel re-exports the public surface so adapter
  authors import from one place (mirrors `barycenter.audit` convention).

## Verification Results

```
40 passed in 0.09s
  tests/test_primitives_drop.py            (3)
  tests/test_primitives_hash.py            (3)
  tests/test_primitives_pseudonymize.py    (3)
  tests/test_primitives_aggregate.py       (4)
  tests/test_primitives_bucket.py          (4)
  tests/test_primitives_score.py           (4)
  tests/test_primitives_keyword_flags.py   (3)
  tests/test_primitives_as_is.py           (4)
  tests/test_pseudonymizer.py              (7)
  tests/test_recipe_no_bypass.py           (5)
```

Public barrel verification:
```python
from barycenter.etl import (ETLRecipe, Pseudonymizer, ETLError,
    CUIBoundaryViolation, SchemaDriftError, RateLimitExhausted,
    PaginationTruncated, PRIMITIVE_REGISTRY)
# all imports succeed; PRIMITIVE_REGISTRY has the 8 expected keys.
```

No-bypass invariant verified (registry membership + literal error message):
```
ValueError: recipe column 'a' bypasses primitive layer:
'nonexistent_primitive' not in PRIMITIVE_REGISTRY
```

## Threat Model Coverage

| Threat ID | Mitigation Implemented |
|-----------|------------------------|
| T-02-06 (Tampering, SQL emission) | `compile` builds `INSERT ... VALUES (?, ...)` with values bound via params; expr fragments are static or `?` placeholders only. |
| T-02-07 (Salt leak / Pitfall 5) | Salt fetched per call; `salt_bytes` dereferenced in `finally`; `__repr__` excludes salt material; never assigned to a class attribute. Test asserts repr excludes the salt string. |
| T-02-08 (`as_is` on RESTRICTED) | `as_is(only_classes=...)` raises `ValueError` when `field_class` not in allowed set. Test covers this. |
| T-02-09 (`score` eval) | Char allowlist applied AFTER field-name substitution; eval runs with empty builtins and empty locals. Tests cover `__import__` rejection and unknown-identifier rejection. |
| T-02-10 (Recipe bypass) | `ETLRecipe.validate_no_bypass` field_validator raises at construction. Test asserts the literal "bypasses primitive layer" phrase. |
| T-02-11 (Cross-tenant pid correlation) | Salt fetched per `salt-{tenant_id}` secret name; `tenant_id` required. Test asserts `mock_kv_client.get_secret` is called with `salt-tenant-abc`. |

## Deviations from Plan

None — plan executed as written. Two minor refinements within the spirit
of the plan:

1. **Task 1, score primitive**: substitute field names by descending length
   to prevent shorter-prefix shadowing (e.g., a field named `a` clobbering
   `ab`). Plan's example replace loop was order-undefined; this avoids a
   subtle bug.

2. **Task 2, ETLRecipe.compile**: when a primitive's source value resolves
   to `None` (missing field in record), the dispatcher passes appropriate
   defaults (empty list to `aggregate`, empty string to `hash_`/`keyword_flags`).
   Plan's pseudo-code implied this; made it explicit and consistent.

## Auth Gates

None.

## Known Stubs

- `iter_all_recipes()` returns `[]` until Plan 05 lands the
  `barycenter.etl.adapters.connectwise.recipes` module. This is intentional
  — documented in the docstring; the no-bypass test calls it but exits the
  empty loop. Plan 05 populates it.

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1    | eda9068 | Eight primitives + PRIMITIVE_REGISTRY + PrimitiveResult |
| 2    | 63be666 | ETLRecipe, Pseudonymizer, exceptions, public barrel |

## Self-Check: PASSED

- All listed created files exist on disk (verified via test pass + write succeeded).
- Both commits exist in git log:
  - `eda9068 feat(02-02): implement eight TOOL-02 primitives + PRIMITIVE_REGISTRY`
  - `63be666 feat(02-02): add ETLRecipe, Pseudonymizer, exception hierarchy, public barrel`
- 40/40 plan-relevant tests pass; public barrel imports succeed.
- No-bypass invariant raises ValueError with literal `bypasses primitive layer`.
- Pseudonymizer fresh-fetch behavior verified (2 calls → 2 KV invocations).
