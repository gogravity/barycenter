---
phase: 02
plan: 05
subsystem: etl-connectwise-adapter
tags: [int-01, tool-04, ret-01, comp-03, comp-07, oidc, httpx, tenacity, pydantic]
requires:
  - 02-04 (framework gates: AdapterBase, ETLRecipe, RetentionSweeper, CanaryScanner)
  - 02-03 (raw_cw schema; serial_number registry tag)
provides:
  - CWManageClient (httpx + tenacity + token-bucket + paginate w/ terminal_reason)
  - CWAuthStrategy + BasicAuthStrategy + OAuthClientCredsStrategy
  - Five ETL recipes (companies, agreements, tickets, configurations, time_entries)
  - CWManageAdapter(AdapterBase) -- INT-01 end-to-end wiring
  - python -m barycenter.etl.run --adapter connectwise CLI
  - Two scheduled GitHub Actions (etl-cw-nightly, etl-retention-sweep)
  - python-tests.yml extended with barycenter-etl + check_salt_runbook self-test
affects:
  - .github/workflows/python-tests.yml (extended, prior steps preserved)
  - compliance/field-class-registry.yaml (serial_number RESTRICTED -> INTERNAL, hashed via recipe)
tech-stack:
  added:
    - respx 0.23 (httpx mocking; dev dependency)
    - pytest-mock 3.15 (already declared, now installed)
  patterns:
    - Strategy interface for auth so tenant capability variance (Pitfall 2) is absorbed at the edge
    - terminal_reason on every paginate() exit + assert_clean_termination() guard (Pitfall 4)
    - Drift-tolerant pydantic with extra='ignore' + log_drift recorder (Pitfall 6)
    - OIDC env-scoped client IDs in workflows (Pitfall 11)
key-files:
  created:
    - packages/barycenter-etl/src/barycenter/etl/adapters/connectwise/auth.py
    - packages/barycenter-etl/src/barycenter/etl/adapters/connectwise/models.py
    - packages/barycenter-etl/src/barycenter/etl/adapters/connectwise/client.py
    - packages/barycenter-etl/src/barycenter/etl/adapters/connectwise/adapter.py
    - packages/barycenter-etl/src/barycenter/etl/adapters/connectwise/recipes/__init__.py
    - packages/barycenter-etl/src/barycenter/etl/adapters/connectwise/recipes/companies.py
    - packages/barycenter-etl/src/barycenter/etl/adapters/connectwise/recipes/agreements.py
    - packages/barycenter-etl/src/barycenter/etl/adapters/connectwise/recipes/tickets.py
    - packages/barycenter-etl/src/barycenter/etl/adapters/connectwise/recipes/configurations.py
    - packages/barycenter-etl/src/barycenter/etl/adapters/connectwise/recipes/time_entries.py
    - packages/barycenter-etl/src/barycenter/etl/run.py
    - .github/workflows/etl-cw-nightly.yml
    - .github/workflows/etl-retention-sweep.yml
  modified:
    - packages/barycenter-etl/tests/adapters/connectwise/test_client.py (importorskip stub -> 9 respx-driven cases)
    - packages/barycenter-etl/tests/adapters/connectwise/test_adapter.py (5 contract assertions)
    - packages/barycenter-etl/tests/adapters/connectwise/test_recipes.py (5 contract assertions incl. body-leak guard)
    - .github/workflows/python-tests.yml (extended; prior audit/VER-02/AUDIT-01 steps preserved verbatim)
    - compliance/field-class-registry.yaml (serial_number INTERNAL with hash comment)
decisions:
  - Hash serial_number at recipe time (Option 1) so the column stored is INTERNAL-class; registry updated to match.
  - Project billing_address_line1 with explicit only_classes=("RESTRICTED",) override so the as_is guardrail still demands an auditable opt-in for the only RESTRICTED column on raw_cw.companies.
  - Workflow run.py construction: invent sink builders inline using the Phase-1 LogsAnalyticsSink/WormBlobSink class signatures; no from_env helper exists yet (and the plan acknowledges this soft binding).
metrics:
  duration: ~45 minutes
  completed: 2026-05-02
  tasks_completed: 3
  files_created: 13
  files_modified: 5
  tests_added: 19 (9 client + 5 adapter + 5 recipes; plus existing tests still green)
---

# Phase 02 Plan 05: ConnectWise Manage adapter end-to-end (INT-01)

CW Manage adapter built atop the Plan 04 framework: drift-tolerant pydantic models, strategy-pattern auth, a paginate iterator that refuses to hand back a sync without recording a clean ``terminal_reason``, five recipes that compose only from PRIMITIVE_REGISTRY, a CLI entry point, and the two scheduled workflows that drive it -- all with OIDC env-scoped credentials.

## What changed

INT-01 lands as configuration of the framework rather than a re-implementation of safety properties. Plan 04 already supplies CUI gating, canary scanning, audit emission, retention sweep, and salt rotation; Plan 05 adds:

- ``CWManageClient`` -- httpx + tenacity + 60 rpm token bucket + ``paginate()`` iterator that sets ``terminal_reason`` exactly once before returning. Persistent 429s exhaust through tenacity and surface as ``RateLimitExhausted`` (not a generic httpx error). ``assert_clean_termination()`` is the gate that adapter ``fetch_table`` calls before yielding records into the recipe stream.
- ``CWAuthStrategy`` + ``BasicAuthStrategy`` + ``OAuthClientCredsStrategy`` -- both supported because CW tenant capability varies (Pitfall 2). Plan 06 picks the strategy at first sync; the strategy interface absorbs whichever the tenant supports.
- Pydantic models with ``extra='ignore'`` and a ``log_drift`` recorder. ``CWTicket`` deliberately omits body fields; the docstring documents the absence so a future maintainer can't accidentally introduce them.
- Five recipes -- companies / agreements / tickets / configurations / time_entries. Tickets explicitly drops ``initialDescription``, ``resolution``, and ``initialInternalAnalysis`` via the ``drop`` primitive. Configurations hashes ``serialNumber`` via the ``hash`` primitive. Time entries projects an already-aggregated dict produced by the adapter; no per-entry rows reach raw_cw.
- ``CWManageAdapter(AdapterBase)`` with the canonical TABLES, CUI_SENSITIVE_TABLES, CUI_CANARY_FIELDS, ``fetch_table``, and ``recipe_for`` declarations. ``fetch_table('time_entries')`` aggregates client-side to ``(cw_company_id, entry_date)`` so the (already aggregated) dict matches the time_entries recipe shape.
- ``run.py`` -- ``python -m barycenter.etl.run --adapter connectwise [--dry-run]``. Dry-run emits the planned actions and exits 0 without importing Azure SDKs or pyodbc, so CI can exercise the entry point safely.
- Two GitHub Actions: ``etl-cw-nightly.yml`` (cron 0 6 * * *) and ``etl-retention-sweep.yml`` (cron 0 12 * * * -- 6h offset from sync per Pitfall 10). Both env-scoped to ``environment: prod`` so the federated credential subject claim is narrowed (Pitfall 11). No client secrets anywhere.
- ``python-tests.yml`` extended: barycenter-etl is now installed and tested in CI alongside barycenter-audit, and ``check_salt_runbook.py --check-static`` + ``--self-test`` run as additional gates. Existing audit/VER-02/AUDIT-01/grant-drift/fortigate steps are preserved verbatim.

## Self-Check: PASSED

- All 89 unit tests green (`pytest tests/ --ignore=tests/integration`).
- 9 respx-driven test_client.py cases assert pagination terminal_reason states, 429 retry+exhaustion, RateLimitExhausted, and BasicAuthStrategy header shape.
- ``python -m barycenter.etl.run --adapter connectwise --dry-run`` exits 0.
- ``scripts/ci/field_class_check.py --check-static`` exits 0 (48 columns; serial_number now INTERNAL).
- ``scripts/ci/check_salt_runbook.py --check-static`` exits 0.
- All three workflow files parse via ``yaml.safe_load``; all reference ``id-token: write``; no wildcard OIDC subjects (``grep -E 'subject.*\*' .github/workflows/etl-*.yml`` -> empty).
- ``grep -i body packages/barycenter-etl/src/barycenter/etl/adapters/connectwise/recipes/tickets.py | grep -v drop`` returns only docstring/comment lines (no projection lines).
- File presence (created):
  - packages/barycenter-etl/src/barycenter/etl/adapters/connectwise/{auth,models,client,adapter}.py FOUND
  - packages/barycenter-etl/src/barycenter/etl/adapters/connectwise/recipes/*.py (6 files) FOUND
  - packages/barycenter-etl/src/barycenter/etl/run.py FOUND
  - .github/workflows/etl-cw-nightly.yml FOUND
  - .github/workflows/etl-retention-sweep.yml FOUND
- Commits exist on this branch:
  - 76e4d10 feat(02-05): CW HTTP client + auth strategies + drift-tolerant pydantic models
  - 9f0e985 feat(02-05): five CW recipes + CWManageAdapter + CLI entry point (INT-01)
  - 5cc4c84 feat(02-05): GitHub Actions for nightly CW sync + retention sweep + tests

## Deviations from Plan

### Auto-fixed issues

**1. [Rule 1 - Bug] ``billing_address_line1`` field-class conflict**
- **Found during:** Task 2 recipe construction
- **Issue:** plan declares ``("as_is", {"field": "addressLine1", "field_class": "PUBLIC"})`` but the field-class registry has ``billing_address_line1: RESTRICTED``. The default ``as_is`` guardrail (``only_classes=("PUBLIC","INTERNAL")``) would refuse the projection at runtime.
- **Fix:** Project with explicit ``only_classes=("RESTRICTED",), field_class="RESTRICTED"`` -- still inside the primitive layer (no bypass), still required to opt in explicitly, and consistent with the registry.
- **Files modified:** packages/barycenter-etl/src/barycenter/etl/adapters/connectwise/recipes/companies.py
- **Commit:** 9f0e985

**2. [Rule 1 - Bug] ``MagicMock`` cannot expose attributes that start with ``assert_``**
- **Found during:** Task 2 test execution (`test_fetch_table_aggregates_time_entries_per_company_per_day`)
- **Issue:** ``cw.assert_clean_termination.return_value = None`` raised ``AttributeError`` because Python's mock library treats ``assert_*`` as a typo guard.
- **Fix:** Construct the cw mock with ``MagicMock(unsafe=True)`` so the real method name (``assert_clean_termination``, defined on ``CWManageClient``) is permitted.
- **Files modified:** packages/barycenter-etl/tests/adapters/connectwise/test_adapter.py
- **Commit:** 9f0e985

### Plan-acknowledged soft bindings

- ``run.py`` constructs ``LogsAnalyticsSink`` and ``WormBlobSink`` directly from ``LogsIngestionClient`` / ``AppendBlobClient`` (their actual ``__init__`` signatures in ``barycenter-audit``); the plan suggested ``LogsAnalyticsSink.from_env(cred)`` as a possible helper but acknowledged it may not exist. Verified that no ``from_env`` exists on either class in barycenter-audit/sinks.py.
- The same construction is mirrored in ``etl-retention-sweep.yml``'s inline Python so the workflow does not assume a helper that doesn't exist.

## Threat Flags

None. Every file in this plan corresponds to a surface already enumerated in the plan's ``<threat_model>`` (T-02-25 through T-02-33). No new network endpoints, auth paths, or trust boundaries introduced beyond what the plan registered.

## Known Stubs

None. All recipes wire to live data sources; the CLI dry-run mode is intentional and documented (workflow runs the real path with KV+SQL).

## TDD Gate Compliance

This plan's tasks declared `tdd="true"` on Tasks 1 and 2 but the plan itself is type=execute, not type=tdd, so the strict RED/GREEN/REFACTOR commit-sequence gate does not apply. Tests were written alongside implementation (test files already existed as importorskip stubs from Plan 02; this plan replaced them with concrete assertions). The 89-test suite remains green.

## Verification commands run

```bash
cd packages/barycenter-etl && .venv/bin/python -m pytest tests/ --ignore=tests/integration -q
# 89 passed

python -m barycenter.etl.run --adapter connectwise --dry-run
# DRY RUN: would invoke connectwise adapter ...

scripts/ci/field_class_check.py --check-static
# VER-02 OK: 48 columns checked across 5 tables

scripts/ci/check_salt_runbook.py --check-static
# ENC-02 OK: runbook + state YAML present and well-formed

python3 -c "import yaml; yaml.safe_load(open('.github/workflows/etl-cw-nightly.yml')); ..."
# workflows OK
```

## Next plan

Plan 02-06 (Wave 4): Operator gates -- CW auth-mode confirmation with Gravity admin, KV secret provisioning (api-cw-*), salt-rotation fire drill execution, and ai_zone shape backfill against synthetic + early-prod data.
