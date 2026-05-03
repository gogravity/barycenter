---
phase: 02
plan: 01
subsystem: tool-onboarding-framework
tags: [scaffold, wave-0, etl, compliance, ci-gate]
requires:
  - barycenter-audit (existing Phase 1 package)
  - python>=3.12
provides:
  - barycenter-etl package skeleton (installable, importable)
  - 14 Wave-0 test stubs (importorskip until implementations land in plans 02/04/05)
  - Phase 2 compliance configs (canary phrases, retention policy, onboarding template)
  - ENC-02 salt rotation runbook + state tracker + CI gate
affects:
  - packages/barycenter-audit/src/barycenter/__init__.py (removed empty file to enable PEP 420 namespace packages)
tech-stack:
  added:
    - httpx>=0.28
    - tenacity>=9.1
    - pyodbc>=5.2
    - pydantic>=2.10
    - azure-identity>=1.19
    - azure-keyvault-secrets>=4.9
    - azure-keyvault-keys>=4.10
    - pyyaml>=6.0
    - respx>=0.22 (dev)
    - freezegun>=1.5 (dev)
  patterns:
    - PEP 420 namespace packages for shared barycenter.* root
    - pytest.importorskip for not-yet-implemented module stubs
    - CI gate self-test pattern (--self-test) per scripts/ci/field_class_check.py analog
key-files:
  created:
    - packages/barycenter-etl/pyproject.toml
    - packages/barycenter-etl/README.md
    - packages/barycenter-etl/src/barycenter/etl/__init__.py
    - packages/barycenter-etl/src/barycenter/etl/primitives/__init__.py
    - packages/barycenter-etl/src/barycenter/etl/framework/__init__.py
    - packages/barycenter-etl/src/barycenter/etl/adapters/__init__.py
    - packages/barycenter-etl/src/barycenter/etl/adapters/connectwise/__init__.py
    - packages/barycenter-etl/tests/conftest.py
    - packages/barycenter-etl/tests/test_primitives_drop.py
    - packages/barycenter-etl/tests/test_primitives_hash.py
    - packages/barycenter-etl/tests/test_primitives_pseudonymize.py
    - packages/barycenter-etl/tests/test_primitives_aggregate.py
    - packages/barycenter-etl/tests/test_primitives_bucket.py
    - packages/barycenter-etl/tests/test_primitives_score.py
    - packages/barycenter-etl/tests/test_primitives_keyword_flags.py
    - packages/barycenter-etl/tests/test_primitives_as_is.py
    - packages/barycenter-etl/tests/test_recipe_no_bypass.py
    - packages/barycenter-etl/tests/test_no_body_column.py
    - packages/barycenter-etl/tests/test_no_novel_ai_zone.py
    - packages/barycenter-etl/tests/test_cui_gate.py
    - packages/barycenter-etl/tests/test_canary.py
    - packages/barycenter-etl/tests/test_pseudonymizer.py
    - packages/barycenter-etl/tests/test_shape_builder.py
    - packages/barycenter-etl/tests/test_salt_rotation.py
    - packages/barycenter-etl/tests/test_retention.py
    - packages/barycenter-etl/tests/test_category.py
    - packages/barycenter-etl/tests/test_onboarding_spec.py
    - packages/barycenter-etl/tests/adapters/connectwise/test_client.py
    - packages/barycenter-etl/tests/adapters/connectwise/test_adapter.py
    - packages/barycenter-etl/tests/adapters/connectwise/test_recipes.py
    - packages/barycenter-etl/tests/integration/test_e2e_synthetic.py
    - compliance/cui-canary-phrases.yaml
    - compliance/retention-policy.yaml
    - compliance/tool-onboarding-spec.template.md
    - compliance/salt-rotation-runbook.md
    - compliance/salt-rotation-state.yaml
    - scripts/ci/check_salt_runbook.py
  modified:
    - packages/barycenter-audit/src/barycenter/__init__.py (deleted; was empty)
decisions:
  - PEP 420 namespace packages adopted for barycenter.* root so both barycenter-audit and barycenter-etl share the namespace cleanly. Required deleting the empty packages/barycenter-audit/src/barycenter/__init__.py.
  - Test stubs use pytest.importorskip rather than xfail/skip so the test files run without producing failures until the implementing plan lands the module.
  - check_salt_runbook.py mirrors scripts/ci/field_class_check.py: argparse + --self-test meta-test that injects a missing runbook and asserts the gate fires.
metrics:
  duration: ~25 minutes
  completed: 2026-05-02
  tasks: 3
  files_created: 36
  commits: 3
---

# Phase 2 Plan 1: Wave-0 Scaffold Summary

Wave-0 scaffolding for the barycenter-etl package: installable empty Python package with namespace barrels, 14 Wave-0 test stubs (importorskip-guarded until implementations arrive), Phase 2 compliance YAMLs (CUI canaries, retention policy, onboarding template), salt rotation runbook + state tracker, and the ENC-02 CI gate that verifies them.

## What Was Built

### Task 1: barycenter-etl package skeleton (commit fd89063)

- pyproject.toml with the full Phase 2 dependency set: httpx, tenacity, pyodbc, pydantic, azure-identity, azure-keyvault-secrets, azure-keyvault-keys, pyyaml, barycenter-audit (local path dep). Dev extras: pytest, pytest-mock, respx, freezegun.
- Namespace barrels at barycenter.etl, barycenter.etl.primitives, barycenter.etl.framework, barycenter.etl.adapters, barycenter.etl.adapters.connectwise.
- tests/conftest.py with seven fixtures: mock_sql, mock_kv_client, mock_audit, mock_cw_client, synthetic_cw_company, synthetic_cui_company, synthetic_cui_ticket_with_canary.
- README.md pointing to 02-RESEARCH.md.

Verification: pip install -e packages/barycenter-etl[dev] succeeds; all imports resolve.

### Task 2: 14 Wave-0 test stubs (commit dbf9143)

Each stub uses pytest.importorskip on the not-yet-existing module so the file passes-as-skipped today and becomes a real test as the implementation arrives:

- 8 primitive tests (drop, hash, pseudonymize, aggregate, bucket, score, keyword_flags, as_is) — each asserts PrimitiveResult shape + valid field_class
- test_recipe_no_bypass — CI gate primitives-only enforcement
- test_no_body_column — DDL parse asserts raw_cw.tickets has no body fields (skips when SQL DDL not yet present)
- test_no_novel_ai_zone — DDL parse limits ai_zone tables to 4 canonical shapes
- test_cui_gate, test_canary, test_pseudonymizer, test_shape_builder, test_salt_rotation, test_retention, test_category — framework component contracts
- test_onboarding_spec — template existence + section coverage
- adapters/connectwise: test_client, test_adapter, test_recipes
- integration: test_e2e_synthetic

Verification: `pytest packages/barycenter-etl/tests/` collects all test files, 3 active pass, 20 skip cleanly via importorskip.

### Task 3: Compliance configs + salt runbook CI gate (commit d41dea0)

- compliance/cui-canary-phrases.yaml — COMP-07 phrase dictionary (CUI, FOUO, FEDCON, ITAR, EAR99, SECRET//NOFORN + test canaries)
- compliance/retention-policy.yaml — RET-01 per-class TTL config (RESTRICTED 13mo; SENSITIVE/INTERNAL/PUBLIC 60mo) with sweep cron + offset
- compliance/tool-onboarding-spec.template.md — TOOL-01 template with required sections (Field Map, Raw Schema, ETL Recipe, AI-Zone Contributions, CUI Surface, Retention, Erasure, Authentication, Sign-off)
- compliance/salt-rotation-runbook.md — ENC-02 8-step procedure
- compliance/salt-rotation-state.yaml — rotation state tracker (version, tenants, executions, fire_drill)
- scripts/ci/check_salt_runbook.py — CI gate (file presence, YAML well-formedness, runbook section coverage) + --self-test meta-test mode

Verification: `python scripts/ci/check_salt_runbook.py` exits 0; `--self-test` exits 0; all three new YAMLs parse via yaml.safe_load; `pytest packages/barycenter-etl/tests/test_onboarding_spec.py` passes when run from repo root.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocker] Removed empty packages/barycenter-audit/src/barycenter/__init__.py**

- Found during: Task 1 verification (`python -c "import barycenter.etl"` failed)
- Issue: The barycenter-audit package shipped with an empty `src/barycenter/__init__.py`, which made `barycenter` a regular package rooted exclusively in barycenter-audit's source directory. As soon as barycenter-etl was installed, `import barycenter.etl` failed because Python looked only inside the audit package's namespace.
- Fix: Deleted the empty `packages/barycenter-audit/src/barycenter/__init__.py` so both packages cooperate as PEP 420 namespace packages under the shared `barycenter.*` root. No content was lost (file was 0 bytes). PATTERNS.md S2 (Single canonical import path) implies a shared namespace, so this aligns with the documented pattern.
- Files modified: packages/barycenter-audit/src/barycenter/__init__.py (deleted)
- Commit: fd89063

No other deviations.

## Authentication Gates

None — Wave-0 scaffold is local code only; no Azure or CW credentials touched.

## Verification Results

- `pip install -e 'packages/barycenter-etl[dev]'` → success (uv-managed venv)
- `python -c "import barycenter.etl; import barycenter.etl.primitives; import barycenter.etl.framework; import barycenter.etl.adapters.connectwise; import barycenter.audit"` → success
- `python -m pytest packages/barycenter-etl/tests/` → 3 passed, 20 skipped (importorskip stubs)
- `python scripts/ci/check_salt_runbook.py` → exit 0, "ENC-02 OK"
- `python scripts/ci/check_salt_runbook.py --self-test` → exit 0, "salt-runbook meta-test PASS"
- `python -c "import yaml; yaml.safe_load(...)"` for all three YAMLs → success

## Known Stubs

The 14 test files use `pytest.importorskip` to skip until later plans land their modules. This is intentional and documented per the plan's `<objective>`. They are not stubs in the production code path — production code does not yet exist for these modules and will be added by:

- Plan 02 (primitives, recipe, pseudonymizer)
- Plan 04 (framework: cui_gate, canary, shape_builder, salt_rotation, retention, adapter_base)
- Plan 05 (CW adapter: client, adapter, recipes)

No production stubs/placeholders exist that would cause user-facing "no data" issues.

## Self-Check: PASSED

Created files verified present:

- packages/barycenter-etl/pyproject.toml — FOUND
- packages/barycenter-etl/tests/conftest.py — FOUND (7 fixtures)
- compliance/cui-canary-phrases.yaml — FOUND
- compliance/retention-policy.yaml — FOUND
- compliance/tool-onboarding-spec.template.md — FOUND
- compliance/salt-rotation-runbook.md — FOUND
- compliance/salt-rotation-state.yaml — FOUND
- scripts/ci/check_salt_runbook.py — FOUND, executable

Commits verified:

- fd89063: feat(02-01): scaffold barycenter-etl package skeleton — FOUND
- dbf9143: test(02-01): add 14 Wave-0 test stubs for Phase 2 framework — FOUND
- d41dea0: feat(02-01): add Phase 2 compliance configs + salt runbook CI gate — FOUND
