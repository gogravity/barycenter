---
phase: 02-tool-onboarding-framework-connectwise-manage
reviewed: 2026-05-02T00:00:00Z
depth: standard
files_reviewed: 37
files_reviewed_list:
  - packages/barycenter-etl/src/barycenter/etl/framework/adapter_base.py
  - packages/barycenter-etl/src/barycenter/etl/framework/canary.py
  - packages/barycenter-etl/src/barycenter/etl/framework/cui_gate.py
  - packages/barycenter-etl/src/barycenter/etl/framework/exceptions.py
  - packages/barycenter-etl/src/barycenter/etl/framework/pseudonymizer.py
  - packages/barycenter-etl/src/barycenter/etl/framework/recipe.py
  - packages/barycenter-etl/src/barycenter/etl/framework/retention.py
  - packages/barycenter-etl/src/barycenter/etl/framework/salt_rotation.py
  - packages/barycenter-etl/src/barycenter/etl/framework/shape_builder.py
  - packages/barycenter-etl/src/barycenter/etl/framework/_audit_helpers.py
  - packages/barycenter-etl/src/barycenter/etl/primitives/_result.py
  - packages/barycenter-etl/src/barycenter/etl/primitives/drop.py
  - packages/barycenter-etl/src/barycenter/etl/primitives/hash.py
  - packages/barycenter-etl/src/barycenter/etl/primitives/pseudonymize.py
  - packages/barycenter-etl/src/barycenter/etl/primitives/aggregate.py
  - packages/barycenter-etl/src/barycenter/etl/primitives/bucket.py
  - packages/barycenter-etl/src/barycenter/etl/primitives/score.py
  - packages/barycenter-etl/src/barycenter/etl/primitives/keyword_flags.py
  - packages/barycenter-etl/src/barycenter/etl/primitives/as_is.py
  - packages/barycenter-etl/src/barycenter/etl/adapters/connectwise/client.py
  - packages/barycenter-etl/src/barycenter/etl/adapters/connectwise/auth.py
  - packages/barycenter-etl/src/barycenter/etl/adapters/connectwise/models.py
  - packages/barycenter-etl/src/barycenter/etl/adapters/connectwise/adapter.py
  - packages/barycenter-etl/src/barycenter/etl/adapters/connectwise/recipes/companies.py
  - packages/barycenter-etl/src/barycenter/etl/adapters/connectwise/recipes/agreements.py
  - packages/barycenter-etl/src/barycenter/etl/adapters/connectwise/recipes/tickets.py
  - packages/barycenter-etl/src/barycenter/etl/adapters/connectwise/recipes/configurations.py
  - packages/barycenter-etl/src/barycenter/etl/adapters/connectwise/recipes/time_entries.py
  - packages/barycenter-etl/src/barycenter/etl/run.py
  - .github/workflows/etl-cw-nightly.yml
  - .github/workflows/etl-retention-sweep.yml
  - .github/workflows/python-tests.yml
  - scripts/ci/check_salt_runbook.py
  - sql/00-schemas/005_create_raw_cw_remaining.sql
  - sql/00-schemas/006_create_pseudo_person_map.sql
  - sql/00-schemas/007_create_ai_zone_shapes.sql
  - sql/10-grants/001_etl_grants.sql
findings:
  critical: 3
  warning: 5
  info: 4
  total: 12
status: issues_found
---

# Phase 2: Code Review Report

**Reviewed:** 2026-05-02T00:00:00Z
**Depth:** standard
**Files Reviewed:** 37
**Status:** issues_found

## Summary

The ETL framework architecture is well-structured: fail-closed audit propagation, table-isolated rollbacks, CUI canary scanning, and OIDC-scoped GitHub Actions are all correctly implemented. The pseudonymizer salt handling (Pitfall 5) is sound, the `score` primitive's char-allowlist + empty-builtins `eval` is an acceptable mitigation, and pagination termination safety (Pitfall 4) is consistently enforced across all five CW tables.

Three critical runtime bugs were found that will cause the companies sync to fail at every run and prevent the `pseudonymize` primitive from being used in any future recipe without crashing. Two warnings cover a 4xx retry over-eagerness in the HTTP client and a `salt_material` local that is not explicitly cleared. Four info items cover test coverage gaps, an unclosed file handle, and a silenced CI gate.

---

## Critical Issues

### CR-01: `keyword_flags` output is a Python dict bound to a SQL `BIT` column — companies sync always fails at runtime

**File:** `packages/barycenter-etl/src/barycenter/etl/adapters/connectwise/recipes/companies.py:21`

**Issue:** The `companies_recipe` maps `cui_handling_required` (DDL: `BIT NOT NULL`) to the `keyword_flags` primitive. `keyword_flags` returns `PrimitiveResult(expr="?", params={f"{field}_flags": flags_dict})`, so the bound value is a Python `dict` of booleans (e.g. `{"defense": False, "federal": False}`). When `adapter_base.py` calls `cur.execute(sql, *list(params.values()))`, pyodbc receives a dict where a SQL `BIT` parameter is expected. This raises a pyodbc `ProgrammingError` at runtime, meaning the companies table sync fails on every run and `cui_handling_required` is never populated — which in turn makes CUI tenant detection (`CUIGate.should_skip`) permanently return `False`, silently bypassing the CUI fence for all downstream tables.

The correct primitive is `as_is` with a Python-side boolean derived from the types list, or a dedicated `any_keyword` helper. If `keyword_flags` is intentionally used, the recipe must post-process the flags dict into a scalar BIT value before binding.

**Fix:**
```python
# Option A: compute the flag Python-side in the adapter/recipe helper, then use as_is
"cui_handling_required": ("as_is", {
    "field": "_cui_flag",       # pre-computed bool added to record in fetch_table
    "field_class": "INTERNAL",
}),

# Option B: add a new primitive `any_keyword` that returns a single bool/int:
# any_keyword(field, value, kw_list) -> PrimitiveResult(expr="?", params={field: int(match)})
# Then in the recipe:
"cui_handling_required": ("any_keyword", {
    "field": "types[]",
    "keywords": ["defense", "federal"],
}),
```

---

### CR-02: `pseudonymize` primitive returns two params for one `?` placeholder — parameter count mismatch crashes any recipe that uses it

**File:** `packages/barycenter-etl/src/barycenter/etl/primitives/pseudonymize.py:32-35`

**Issue:** `pseudonymize` returns:
```python
PrimitiveResult(
    expr="?",
    params={field: pid, f"{field}_salt_version": ver},
    ...
)
```
This puts two entries in `params` for a single `?` expression. In `recipe.py:compile()`, all `params.values()` are collected and passed as `cur.execute(sql, *bound)`. The resulting call has one `?` placeholder but two positional arguments, which pyodbc rejects with `ProgrammingError: The SQL contains 1 parameter markers, but 2 parameters were supplied`. Any recipe column that uses `pseudonymize` will crash at runtime. The `salt_version` value is useful for audit but must not be bound as a SQL parameter for the primary column.

**Fix:** Either (a) bind only `pid` in the primary param and surface `salt_version` via a separate audit metadata path, or (b) require the recipe to declare an explicit second column for the salt version:

```python
# pseudonymize.py — return only the pid as the bound parameter:
return PrimitiveResult(
    expr="?",
    params={field: pid},
    field_class="SENSITIVE",
    # Pass version out-of-band via a new optional attribute, e.g.:
    # metadata={"salt_version": ver}
)
```

If the salt version must be stored in the same INSERT row (as a separate column), the recipe author must declare a second derivation column (e.g. `person_pid_salt_version`) using an `as_is` primitive whose value is pre-computed and injected into the record dict before recipe compilation.

---

### CR-03: `score` primitive params key is hardcoded to `"score"` regardless of target column — multiple score columns in one recipe collide and truncate bound values

**File:** `packages/barycenter-etl/src/barycenter/etl/primitives/score.py:34`

**Issue:**
```python
params={"score": result},
```
The key is always `"score"`, not `field`. If a recipe declares two columns via the `score` primitive (e.g. `health_score` and `risk_score`), the second call overwrites `params["score"]` set by the first call, leaving the params dict with one entry for two `?` placeholders. The INSERT then fails with a parameter count mismatch. The correct key is `field`, consistent with all other primitives.

**Fix:**
```python
# score.py line 34
return PrimitiveResult(
    expr="?",
    params={field: result},   # was {"score": result}
    field_class="INTERNAL",
)
```

Note: `score` accepts `fields: dict` as its first argument (not `field: str`), so the column name must be threaded in from `compile()`. The `compile()` call site already has `col` available; pass it:
```python
# recipe.py compile() score branch — add col as first arg:
elif primitive_name == "score":
    res = fn(
        col,                                          # add this
        kwargs.get("fields", {col: value or 0}),
        kwargs.get("formula", "0"),
    )
```
And update `score`'s signature accordingly:
```python
def score(field: str, fields: dict, formula: str) -> PrimitiveResult:
```

---

## Warnings

### WR-01: HTTP client retries all 4xx status codes, including permanent errors like 404

**File:** `packages/barycenter-etl/src/barycenter/etl/adapters/connectwise/client.py:88-93`

**Issue:** The tenacity decorator retries on `httpx.HTTPStatusError`, which is raised by `r.raise_for_status()` for any non-2xx response including 404, 401, 403. A misconfigured path or revoked credential will silently retry 5 times with exponential back-off (up to 60s delays), wasting several minutes and potentially masking the root cause in logs before eventually raising `RateLimitExhausted` or re-raising the status error.

**Fix:** Restrict retries to transient conditions only:
```python
from tenacity import retry_if_exception

def _is_transient(exc: BaseException) -> bool:
    if isinstance(exc, httpx.TransportError):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in (429, 500, 502, 503, 504)
    return False

@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=60),
    retry=retry_if_exception(_is_transient),
    reraise=True,
)
def _get(self, path: str, params: dict) -> httpx.Response:
    ...
```

---

### WR-02: `salt_material` local variable not cleared in `Pseudonymizer.derive` finally block

**File:** `packages/barycenter-etl/src/barycenter/etl/framework/pseudonymizer.py:51-67`

**Issue:** The `finally` block deletes `salt_bytes` and `secret`, but `salt_material` (the raw decoded string from `secret.value`, line 51) is never deleted. It remains in the local frame until the function returns and CPython's reference count reaches zero. Under CPython this is typically immediate, but under PyPy or when exceptions extend the frame lifetime, the plaintext salt string persists longer than intended. The Pitfall 5 mitigation comment explicitly calls out that salt material must be dereferenced; the current code leaves one reference alive.

**Fix:**
```python
finally:
    if salt_bytes is not None:
        del salt_bytes
    try:
        del salt_material   # add this line
    except NameError:
        pass
    del secret
```

---

### WR-03: `RetentionSweeper.sweep_table` does not validate `qualified_table` before string-interpolating it into SQL

**File:** `packages/barycenter-etl/src/barycenter/etl/framework/retention.py:62`

**Issue:**
```python
sql = f"DELETE FROM {qualified_table} WHERE synced_at < ?"
```
The `qualified_table` argument is caller-supplied. In the current CI harness the values come from a repo-committed YAML file (`compliance/field-class-registry.yaml`), so injection is not an immediate risk. However, `sweep_table` is a public method with no guardrail against a future caller passing an unsanitized string. A pattern like `schema.table; DROP TABLE raw_cw.companies --` would be executed. The cutoff date is correctly parameterized, but the table name is not. SQL Server does not support parameterized table names via `?`.

**Fix:** Add an allowlist check against a known-safe set before interpolation:
```python
_SAFE_TABLE_RE = re.compile(r'^[a-z_][a-z0-9_]*\.[a-z_][a-z0-9_]*$')

def sweep_table(self, qualified_table: str, field_class: str, *, tenant_id=None) -> int:
    if not _SAFE_TABLE_RE.match(qualified_table):
        raise ValueError(f"sweep_table: unsafe table name {qualified_table!r}")
    ...
```

---

### WR-04: Pydantic CW response models are never applied — schema drift detection is dead code

**File:** `packages/barycenter-etl/src/barycenter/etl/adapters/connectwise/models.py:1-106`

**Issue:** `CWManageAdapter.fetch_table` calls `self._cw.paginate(path)` which yields raw `dict` objects. None of the Pydantic models (`CWCompany`, `CWAgreement`, `CWTicket`, `CWConfiguration`, `CWTimeEntry`) are ever instantiated with `model_validate()`. The schema drift logging mechanism (the `log_drift` function and `_seen_drift` set in `models.py`) is therefore never invoked. Unknown API response fields pass silently into the recipe layer without triggering the drift warning that Pitfall 6 requires.

**Fix:** In `adapter.py`, validate raw records through their models before yielding to the recipe:
```python
from barycenter.etl.adapters.connectwise.models import (
    CWCompany, CWAgreement, CWTicket, CWConfiguration, CWTimeEntry,
)

_MODELS = {
    "companies": CWCompany,
    "agreements": CWAgreement,
    "tickets": CWTicket,
    "configurations": CWConfiguration,
    # time_entries uses pre-aggregated dicts — no CW model applies
}

def fetch_table(self, table: str) -> Iterator[dict]:
    path = self._PATHS[table]
    model = _MODELS.get(table)
    if table == "time_entries":
        yield from self._fetch_time_entries_aggregated(path)
    else:
        for raw in self._cw.paginate(path):
            if model is not None:
                validated = model.model_validate(raw)
                unknown = set(raw) - set(validated.model_fields)
                if unknown:
                    log_drift(model.__name__, unknown)
            yield raw
        self._cw.assert_clean_termination(path)
```

---

### WR-05: Post-sync chain integrity check is silenced — a broken WORM chain does not fail the nightly job

**File:** `.github/workflows/etl-cw-nightly.yml:48`

**Issue:**
```yaml
run: python scripts/ci/chain_validate.py --live || echo "chain validate not yet wired in this env"
```
The `|| echo` makes chain validation advisory rather than blocking. If `chain_validate.py --live` exits non-zero (chain tampered, WORM blob missing, etc.), the job succeeds and no alert fires. The comment suggests this is a temporary placeholder, but as-is it means the WORM integrity guarantee is unverified after every sync.

**Fix:** Once `chain_validate.py --live` is wired to the production environment, remove the `|| echo` fallback:
```yaml
- name: post-sync chain integrity check
  run: python scripts/ci/chain_validate.py --live
```
Until then, at a minimum add a `continue-on-error: false` annotation and a TODO comment dated with the expected wiring sprint so it does not go stale.

---

## Info

### IN-01: `BasicAuthStrategy` has no `__repr__` guard — Base64-encoded credentials could appear in logs

**File:** `packages/barycenter-etl/src/barycenter/etl/adapters/connectwise/auth.py:26-46`

**Issue:** `self._headers` stores the full `Authorization: Basic <b64>` header. Python's default `__repr__` on the instance would expose this dict if the object is logged or inspected. While `BasicAuthStrategy` is not logged in current code, the absence of a guard is a latent risk given the sensitive value stored.

**Fix:**
```python
def __repr__(self) -> str:
    return "<BasicAuthStrategy company=REDACTED>"
```

---

### IN-02: Unclosed file handle in retention sweep inline script

**File:** `.github/workflows/etl-retention-sweep.yml:64`

**Issue:**
```python
reg = yaml.safe_load(open("compliance/field-class-registry.yaml"))
```
`open()` without `with` leaves the file handle open until GC collects it. In a short-lived CI script this is harmless but is a Python quality violation.

**Fix:**
```python
with open("compliance/field-class-registry.yaml") as fh:
    reg = yaml.safe_load(fh)
```

---

### IN-03: `iter_all_recipes()` silently returns empty list on `ImportError` — the no-bypass CI gate may pass vacuously

**File:** `packages/barycenter-etl/src/barycenter/etl/framework/recipe.py:165-179`

**Issue:** The broad `except ImportError: pass` means that a broken import in any recipe module (e.g. a syntax error in `tickets.py`) causes `iter_all_recipes` to return `[]` rather than raising. The CI gate that calls this function would then report zero recipes checked and pass vacuously, providing false assurance that all recipes are validated.

**Fix:** Log the import error at minimum, or re-raise if running in CI context:
```python
except ImportError as exc:
    import logging
    logging.getLogger(__name__).warning(
        "iter_all_recipes: import error — recipe validation may be incomplete: %s", exc
    )
    # Re-raise in strict mode so CI fails loudly:
    # raise
```

---

### IN-04: `aggregate` primitive's `MAX` and `MIN` fail with a `TypeError` on non-numeric inputs, not an `ETLError`

**File:** `packages/barycenter-etl/src/barycenter/etl/primitives/aggregate.py:32-35`

**Issue:** If `values` contains non-numeric items (e.g. strings from a malformed API response), `max(values)` or `min(values)` raises a bare `TypeError`. In `adapter_base.run()`, this is caught by the broad `except Exception` branch (not the `ETLError` branch), which still rolls back and continues, but the error message in the audit log reads `repr(exc)[:200]` rather than a structured `ETLError`. The table-isolation behaviour is correct; the classification is slightly imprecise.

**Fix:**
```python
if values:
    try:
        result = _FNS[fn](values)
    except (TypeError, ValueError) as exc:
        raise ETLError(
            f"aggregate {fn} failed on values {values!r}: {exc}"
        ) from exc
else:
    result = 0
```
This requires importing `ETLError`:
```python
from barycenter.etl.framework.exceptions import ETLError
```

---

_Reviewed: 2026-05-02T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
