# Phase 2: Tool Onboarding Framework + ConnectWise Manage — Pattern Map

**Mapped:** 2026-05-02
**Files analyzed:** ~45 new (Python framework + adapter + SQL DDL/grants + CI gates + workflows + compliance docs)
**Analogs found:** 38 / 45 (7 greenfield with no close analog — see "No Analog Found")

## File Classification

### Python package — framework + primitives + adapter

| New / Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `packages/barycenter-etl/pyproject.toml` | config | n/a | `packages/barycenter-audit/pyproject.toml` | exact |
| `packages/barycenter-etl/src/barycenter/etl/__init__.py` | package barrel | n/a | `packages/barycenter-audit/src/barycenter/audit/__init__.py` | exact |
| `packages/barycenter-etl/src/barycenter/etl/framework/adapter_base.py` | framework / orchestrator | request-response (loop over tables) | `packages/barycenter-audit/src/barycenter/audit/client.py` (AuditClient) | role-match |
| `packages/barycenter-etl/src/barycenter/etl/framework/recipe.py` | framework / model | transform | `packages/barycenter-audit/src/barycenter/audit/models.py` | role-match |
| `packages/barycenter-etl/src/barycenter/etl/framework/cui_gate.py` | middleware (decorator/gate) | request-response | `packages/barycenter-audit/src/barycenter/audit/client.py` (fail-closed wrapper pattern) | partial |
| `packages/barycenter-etl/src/barycenter/etl/framework/canary.py` | utility / scanner | transform (per-record) | `packages/barycenter-audit/src/barycenter/audit/_canonicalize.py` (pure-function module) | partial |
| `packages/barycenter-etl/src/barycenter/etl/framework/pseudonymizer.py` | service (HMAC) | transform | `packages/barycenter-audit/src/barycenter/audit/chain.py` (`compute_digest`) | role-match |
| `packages/barycenter-etl/src/barycenter/etl/framework/shape_builder.py` | service / writer | batch transform | `packages/barycenter-audit/src/barycenter/audit/sinks.py` (sink wrappers) | partial |
| `packages/barycenter-etl/src/barycenter/etl/framework/retention.py` | scheduled job | batch DELETE | (no analog — greenfield) | none |
| `packages/barycenter-etl/src/barycenter/etl/framework/salt_rotation.py` | runbook helper | event-driven | (no analog — greenfield) | none |
| `packages/barycenter-etl/src/barycenter/etl/framework/exceptions.py` | exception hierarchy | n/a | `packages/barycenter-audit/src/barycenter/audit/exceptions.py` | exact |
| `packages/barycenter-etl/src/barycenter/etl/primitives/{drop,hash,pseudonymize,aggregate,bucket,score,keyword_flags,as_is}.py` | utility / pure functions | transform | `packages/barycenter-audit/src/barycenter/audit/chain.py` (pure-fn module) | role-match |
| `packages/barycenter-etl/src/barycenter/etl/primitives/__init__.py` | barrel | n/a | `packages/barycenter-audit/src/barycenter/audit/__init__.py` | exact |
| `packages/barycenter-etl/src/barycenter/etl/adapters/connectwise/client.py` | service (HTTP client) | streaming (paginated) | (no analog — greenfield REST client) | none |
| `packages/barycenter-etl/src/barycenter/etl/adapters/connectwise/adapter.py` | controller / adapter | request-response | `packages/barycenter-audit/src/barycenter/audit/client.py` (orchestration shape) | partial |
| `packages/barycenter-etl/src/barycenter/etl/adapters/connectwise/models.py` | model (pydantic) | n/a | `packages/barycenter-audit/src/barycenter/audit/models.py` | exact |
| `packages/barycenter-etl/src/barycenter/etl/adapters/connectwise/recipes/*.py` | config / declarative | transform | (no analog — first declarative recipes) | none |
| `packages/barycenter-etl/src/barycenter/etl/run.py` | entry point | n/a | (no analog — greenfield) | none |

### Tests

| New / Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `packages/barycenter-etl/tests/conftest.py` | test fixture | n/a | `packages/barycenter-audit/tests/conftest.py` | exact |
| `packages/barycenter-etl/tests/test_primitives_*.py` | unit | n/a | `packages/barycenter-audit/tests/test_canonicalize.py` | exact |
| `packages/barycenter-etl/tests/test_recipe_no_bypass.py` | CI gate test (introspection) | n/a | `packages/barycenter-audit/tests/test_models.py` | role-match |
| `packages/barycenter-etl/tests/test_cui_gate.py` | unit | n/a | `packages/barycenter-audit/tests/test_fail_closed.py` | role-match |
| `packages/barycenter-etl/tests/test_canary.py` | unit | n/a | `packages/barycenter-audit/tests/test_canonicalize.py` | partial |
| `packages/barycenter-etl/tests/test_pseudonymizer.py` | unit | n/a | `packages/barycenter-audit/tests/test_chain_integrity.py` | role-match |
| `packages/barycenter-etl/tests/test_salt_rotation.py` | integration | n/a | `packages/barycenter-audit/tests/integration/test_emit_end_to_end.py` | role-match |
| `packages/barycenter-etl/tests/test_shape_builder.py` | unit | n/a | `packages/barycenter-audit/tests/test_sinks.py` | role-match |
| `packages/barycenter-etl/tests/test_no_body_column.py` | CI gate (DDL parse) | n/a | `scripts/ci/field_class_check.py` (DDL parser) | role-match |
| `packages/barycenter-etl/tests/test_no_novel_ai_zone.py` | CI gate (DDL parse) | n/a | `scripts/ci/field_class_check.py` | role-match |
| `packages/barycenter-etl/tests/test_retention.py` | unit | n/a | `packages/barycenter-audit/tests/test_fail_closed.py` | partial |
| `packages/barycenter-etl/tests/adapters/connectwise/test_client.py` | unit (respx-mocked) | n/a | (no analog — first httpx test) | none |
| `packages/barycenter-etl/tests/adapters/connectwise/test_adapter.py` | unit | n/a | `packages/barycenter-audit/tests/test_fail_closed.py` | role-match |
| `packages/barycenter-etl/tests/integration/test_e2e_synthetic.py` | integration | n/a | `packages/barycenter-audit/tests/integration/test_emit_end_to_end.py` | exact |

### SQL

| New / Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `sql/00-schemas/005_create_raw_cw_remaining.sql` | DDL | n/a | `sql/00-schemas/001_create_raw_cw.sql` | exact |
| `sql/00-schemas/006_create_pseudo_person_map.sql` | DDL | n/a | `sql/00-schemas/001_create_raw_cw.sql` | exact |
| `sql/00-schemas/007_create_ai_zone_shapes.sql` | DDL | n/a | `sql/00-schemas/001_create_raw_cw.sql` | exact |
| `sql/10-grants/001_etl_grants.sql` (modify) | grants | n/a | `sql/10-grants/001_etl_grants.sql` (existing) | exact (extension) |

### CI scripts + workflows

| New / Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `scripts/ci/check_salt_runbook.py` | CI gate (file presence) | n/a | `scripts/ci/field_class_check.py` | role-match |
| `.github/workflows/etl-cw-nightly.yml` | scheduled workflow (cron + OIDC) | event-driven | `.github/workflows/audit-chain-validate.yml` (live-validate job) | exact |
| `.github/workflows/etl-retention-sweep.yml` | scheduled workflow (cron + OIDC) | event-driven | `.github/workflows/infra-drift.yml` | exact |
| `.github/workflows/etl-tests.yml` (or extend `python-tests.yml`) | CI test workflow | n/a | `.github/workflows/python-tests.yml` | exact |

### Compliance / config

| New / Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `compliance/field-class-registry.yaml` (extend) | config | n/a | existing file | exact (extension) |
| `compliance/cui-canary-phrases.yaml` | config | n/a | `compliance/field-class-registry.yaml` (versioned YAML) | role-match |
| `compliance/retention-policy.yaml` | config | n/a | `compliance/field-class-registry.yaml` | role-match |
| `compliance/tool-onboarding-spec.template.md` | doc template | n/a | `compliance/runbooks/chain-validate.md` | partial |
| `compliance/salt-rotation-runbook.md` | doc / runbook | n/a | `compliance/runbooks/chain-validate.md` | exact |
| `compliance/salt-rotation-state.yaml` | runtime state file (in-git) | n/a | (no analog — greenfield) | none |

## Pattern Assignments

### `packages/barycenter-etl/pyproject.toml` (config)

**Analog:** `packages/barycenter-audit/pyproject.toml`

**Full file** (lines 1-23):
```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "barycenter-audit"
version = "0.1.0"
requires-python = ">=3.12"
description = "Fail-closed audit SDK with SHA-256 chain integrity (D-04, D-05, D-06)"
dependencies = [
  "azure-identity>=1.19",
  ...
]

[project.optional-dependencies]
dev = ["pytest>=8.3", "pytest-mock>=3.14"]

[tool.hatch.build.targets.wheel]
packages = ["src/barycenter"]
```

Copy verbatim — change `name`, `description`, `dependencies` per RESEARCH.md §Standard Stack. Keep `requires-python = ">=3.12"`, hatchling build backend, and `packages = ["src/barycenter"]` so both packages share the `barycenter.*` namespace.

---

### `packages/barycenter-etl/src/barycenter/etl/__init__.py` (package barrel)

**Analog:** `packages/barycenter-audit/src/barycenter/audit/__init__.py` (lines 1-11)

**Pattern to copy:**
```python
"""Barycenter fail-closed audit SDK (D-04). Single canonical import path."""
from barycenter.audit.client import AuditClient
from barycenter.audit.models import AuditEvent, AuditOutcome, ActorType
from barycenter.audit.exceptions import AuditEmitError, ChainIntegrityError, FailClosedAbort
from barycenter.audit.chain import GENESIS_HASH, canonicalize_json, compute_digest, validate_chain

__all__ = [
    "AuditClient", "AuditEvent", "AuditOutcome", "ActorType",
    ...
]
```

Re-export top-level public surface (`AdapterBase`, `ETLRecipe`, `Pseudonymizer`, `CanaryScanner`, `ShapeBuilder`, primitive functions, exception types). Single canonical import path is a project convention.

---

### `packages/barycenter-etl/src/barycenter/etl/framework/adapter_base.py` (framework orchestrator)

**Analog:** `packages/barycenter-audit/src/barycenter/audit/client.py` (`AuditClient.emit`)

**Imports pattern** (client.py lines 15-31):
```python
from __future__ import annotations
import logging
from contextlib import contextmanager
from typing import Iterator, Optional

from barycenter.audit.chain import ...
from barycenter.audit.exceptions import AuditEmitError, FailClosedAbort
from barycenter.audit.models import AuditEvent

log = logging.getLogger(__name__)
```

**Constructor pattern** (client.py lines 44-52) — dependency-injected sinks/clients:
```python
def __init__(self, sql_conn, la_sink: LogsAnalyticsSink, worm_sink: WormBlobSink):
    self._sql = sql_conn
    self._la = la_sink
    self._worm = worm_sink
```

`AdapterBase.__init__` should take `audit: AuditClient`, `sql_conn`, `kv_client`, `cw_client` as injected dependencies — never construct them internally. Mirrors AuditClient testability.

**Fail-closed try/except pattern** (client.py lines 71-104) — adapt for D-02 (table-isolated):
```python
try:
    cur = self._sql.cursor()
    prior = read_head_locked(cur)
    ...
    self._sql.commit()
    return event
except Exception as exc:
    try:
        self._sql.rollback()
    except Exception as rollback_exc:
        log.error("rollback failed during fail-closed abort: %r", rollback_exc)
    if isinstance(exc, AuditEmitError):
        raise
    raise FailClosedAbort(f"audit emit failed: {exc!r}") from exc
```

**Per RESEARCH Pitfall 9** — adapter `run()` differs in one critical way: catch `Exception` per-table, emit failure audit, alert, and `continue` to next table (D-02). But re-raise `AuditEmitError` (CLAUDE.md mandate — audit failure is unrecoverable).

---

### `packages/barycenter-etl/src/barycenter/etl/framework/recipe.py` (framework model)

**Analog:** `packages/barycenter-audit/src/barycenter/audit/models.py` (lines 1-26)

**Pydantic model pattern**:
```python
from pydantic import BaseModel, ConfigDict, Field

class AuditEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=False)
    event_id: UUID
    occurred_at: datetime
    ...
    metadata: Dict[str, Any] = Field(default_factory=dict)
```

`ETLRecipe` should also use `model_config = ConfigDict(extra="forbid")` so a typo in a recipe declaration fails loudly. For CW response models (`adapters/connectwise/models.py`), use `extra="ignore"` per RESEARCH Pitfall 6 (drift log) — opposite default, intentionally.

---

### `packages/barycenter-etl/src/barycenter/etl/framework/exceptions.py`

**Analog:** `packages/barycenter-audit/src/barycenter/audit/exceptions.py` (lines 1-13)

**Pattern to copy verbatim shape:**
```python
"""Audit SDK exception hierarchy (per D-06 fail-closed discipline)."""

class AuditEmitError(Exception):
    """Raised when audit emission fails. Parent transaction MUST roll back."""

class FailClosedAbort(AuditEmitError):
    """Specific subclass for sink failures (LA, WORM, chain_state lock)."""

class ChainIntegrityError(Exception):
    """Raised when audit chain validation detects tampering or break."""
```

Phase 2 hierarchy: `ETLError` (base) → `CUIBoundaryViolation`, `SchemaDriftError`, `RateLimitExhausted`, `PaginationTruncated` (Pitfall 4 `terminal_reason` enforcement). Each subclass docstring states its post-condition (e.g., "table sync rolls back; D-02 isolation: other tables continue").

---

### `packages/barycenter-etl/src/barycenter/etl/framework/pseudonymizer.py`

**Analog:** `packages/barycenter-audit/src/barycenter/audit/chain.py` (`compute_digest`, lines 28-39)

**Pure-function HMAC pattern** (chain.py lines 28-39):
```python
def compute_digest(prior_hex: str, canonical: str) -> str:
    if not isinstance(prior_hex, str) or len(prior_hex) != 64:
        raise ValueError(f"prior_hex must be a 64-char hex string, got {prior_hex!r}")
    h = hashlib.sha256()
    h.update(prior_hex.encode("utf-8"))
    h.update(canonical.encode("utf-8"))
    return h.hexdigest()
```

For Pseudonymizer, use `hmac.new(salt, email.lower().encode(), hashlib.sha256)` — Pitfall 5: salt fetched fresh per call from KV, dereferenced via `del secret` in a `finally` block (RESEARCH Example 2). Strict input validation pattern (lines 34-35) — validate email format and tenant_id before HMAC.

---

### `packages/barycenter-etl/src/barycenter/etl/primitives/*.py`

**Analog:** `packages/barycenter-audit/src/barycenter/audit/chain.py` (pure-function module style; `_canonicalize.py` for one-trick utility modules)

**Pattern:** Each primitive is a top-level function in its own module, returning a `PrimitiveResult` dataclass (RESEARCH Pattern 2). Module docstring states the contract; function docstring states the SQL fragment shape and field-class. Mirrors how `chain.py` exposes `canonicalize_json`, `compute_digest`, `read_head_locked`, `update_head` as flat module-level pure functions.

**Barrel pattern** for `primitives/__init__.py`:
```python
from barycenter.etl.primitives.drop import drop
from barycenter.etl.primitives.hash import hash_
from barycenter.etl.primitives.pseudonymize import pseudonymize
# ... eight total
PRIMITIVE_REGISTRY = {"drop": drop, "hash": hash_, ...}  # used by test_recipe_no_bypass
__all__ = [...]
```

---

### `packages/barycenter-etl/src/barycenter/etl/framework/canary.py`

**Analog:** `packages/barycenter-audit/src/barycenter/audit/_canonicalize.py` (single-purpose pure utility module)

**Pattern:** Self-contained module with a class encapsulating the regex compiled once at construction (RESEARCH Pattern 4 example, lines 423-444). Lazy YAML load in `__init__`, no module-level state, separate methods per scan target (`scan_text`, `scan_subject`, `scan_filename`, `refuse_attachment`).

---

### `packages/barycenter-etl/src/barycenter/etl/framework/shape_builder.py`

**Analog:** `packages/barycenter-audit/src/barycenter/audit/sinks.py` (thin SDK wrapper pattern)

**Wrapper pattern** (sinks.py lines 14-34):
```python
class LogsAnalyticsSink:
    def __init__(self, ingestion_client, dcr_immutable_id: str, stream_name: str):
        self._client = ingestion_client
        self._dcr_id = dcr_immutable_id
        self._stream = stream_name

    def upload(self, event: AuditEvent) -> None:
        payload = event.model_dump(mode="json")
        self._client.upload(rule_id=self._dcr_id, ...)
```

ShapeBuilder takes `sql_conn` injected; `populate(shape: str)` validates `shape ∈ CANONICAL` (RESEARCH Pattern 3) before issuing TRUNCATE+INSERT. No swallowing — every exception propagates verbatim per CLAUDE.md.

---

### `packages/barycenter-etl/src/barycenter/etl/adapters/connectwise/adapter.py`

**Analog:** `packages/barycenter-audit/src/barycenter/audit/client.py` (orchestration shape) + RESEARCH Pattern 1 example (`AdapterBase.run()`)

**Class declaration pattern** (RESEARCH lines 290-325):
```python
class AdapterBase(ABC):
    CATEGORY: str
    TABLES: list[str]
    CUI_SENSITIVE_TABLES: list[str]
    CUI_CANARY_FIELDS: dict[str, list[str]]

    @abstractmethod
    def fetch_table(self, table: str) -> Iterator[dict]: ...
    @abstractmethod
    def recipe_for(self, table: str) -> ETLRecipe: ...
```

CW adapter declares class-level constants for the 5 tables (`companies`, `agreements`, `tickets`, `configurations`, `time_entries`) and supplies `fetch_table` (delegating to `CWManageClient.paginate`) + `recipe_for` (returning the recipe from `recipes/`).

---

### `packages/barycenter-etl/src/barycenter/etl/adapters/connectwise/models.py`

**Analog:** `packages/barycenter-audit/src/barycenter/audit/models.py`

**Inverted ConfigDict for inbound API drift handling:**
```python
# audit (strict, internal):
model_config = ConfigDict(extra="forbid", frozen=False)

# CW models (drift-tolerant, external API):
model_config = ConfigDict(extra="ignore")  # + drift logger captures unknown fields
```

Per RESEARCH Pitfall 6 — every "ignored" field is logged.

---

### `packages/barycenter-etl/src/barycenter/etl/adapters/connectwise/client.py`

**No analog in repo** — first HTTP client in the codebase. Use RESEARCH Example 1 (lines 653-711) verbatim as starting point: `httpx.Client` + `tenacity` decorators + token-bucket throttle + `paginate()` iterator with `terminal_reason` enforcement (Pitfall 4).

---

### `packages/barycenter-etl/tests/conftest.py`

**Analog:** `packages/barycenter-audit/tests/conftest.py` (full file, lines 1-21)

**Pattern to copy:**
```python
"""Shared pytest fixtures for audit SDK tests."""
from unittest.mock import MagicMock
import pytest

@pytest.fixture
def mock_sql():
    conn = MagicMock(name="sql_conn")
    cur = MagicMock(name="cursor")
    conn.cursor.return_value = cur
    return conn

@pytest.fixture
def mock_la_sink():
    return MagicMock(name="la_sink")
```

Add: `mock_audit_client`, `mock_kv_client` (returns MagicMock with `.get_secret(...)` stubbable), `mock_cw_server` (respx-based fixture mounting CW REST endpoints), `synthetic_cui_record` (canary-fixture record).

---

### `packages/barycenter-etl/tests/test_primitives_*.py`

**Analog:** `packages/barycenter-audit/tests/test_canonicalize.py` (one-test-per-pure-function pattern). Confirmed style elsewhere in `tests/test_chain_integrity.py`.

One test file per primitive, asserting (1) SQL projection emitted, (2) parameter dict shape, (3) field-class returned, (4) refuses RESTRICTED for `as_is`.

---

### `packages/barycenter-etl/tests/test_cui_gate.py` & `test_pseudonymizer.py`

**Analog:** `packages/barycenter-audit/tests/test_fail_closed.py` (lines 1-80)

**Fixture-prime + raise-then-assert pattern** (test_fail_closed.py lines 28-37):
```python
def test_fail_closed_on_la_outage(mock_sql, mock_la_sink, mock_worm_sink):
    _prime_chain_head(mock_sql)
    mock_la_sink.upload.side_effect = RuntimeError("LA unreachable")
    client = AuditClient(mock_sql, mock_la_sink, mock_worm_sink)
    with pytest.raises(AuditEmitError):
        client.emit(_make_event())
    mock_sql.commit.assert_not_called()
    mock_sql.rollback.assert_called()
```

For `test_cui_gate.py`: prime mock_sql to return `cui_handling_required=1`, fetch a synthetic record, assert `CUIBoundaryViolation` raises and table sync aborted (no commit). For `test_pseudonymizer.py`: prime mock_kv with versioned secret, derive pid, assert `del` happened (mock_kv.get_secret call count + no module attribute).

---

### `packages/barycenter-etl/tests/test_no_body_column.py` & `test_no_novel_ai_zone.py`

**Analog:** `scripts/ci/field_class_check.py` (DDL parse pattern, lines 28-92)

**SQL DDL parse pattern** (field_class_check.py `_strip_line_comments` + `parse_create_table`):
```python
pattern = re.compile(
    r"CREATE\s+TABLE\s+\[?(\w+)\]?\.\[?(\w+)\]?\s*\((.*?)\)\s*;",
    re.IGNORECASE | re.DOTALL,
)
for m in pattern.finditer(sql_text):
    schema, table, body = m.group(1), m.group(2), m.group(3)
    # paren-aware comma split (lines 64-79)
```

`test_no_body_column.py`: parse `sql/00-schemas/*.sql`, locate `raw_cw.tickets` columns, assert none of `{body, internalAnalysis, resolution, notes}` present. `test_no_novel_ai_zone.py`: scan all `CREATE TABLE ai_zone.*` and assert table name ∈ canonical four. Reuse `parse_create_table` import directly.

---

### `packages/barycenter-etl/tests/integration/test_e2e_synthetic.py`

**Analog:** `packages/barycenter-audit/tests/integration/test_emit_end_to_end.py`

End-to-end with mocked CW (respx) + real-ish SQL (sqlite or pyodbc-against-localdb if available; otherwise heavy mock) + mocked KV. Confirms full path: CW response → primitives → recipe → MERGE INTO raw_cw → ShapeBuilder → ai_zone. AuditClient.emit must be called with `verb='etl.write'` per table.

---

### `sql/00-schemas/005_create_raw_cw_remaining.sql`, `006_create_pseudo_person_map.sql`, `007_create_ai_zone_shapes.sql`

**Analog:** `sql/00-schemas/001_create_raw_cw.sql` (full file, lines 1-20)

**DDL pattern to copy:**
```sql
-- FOUND-01: raw zone for ConnectWise mirror. Populated by ETL in Phase 2.
-- All columns must appear in compliance/field-class-registry.yaml (VER-02).
IF SCHEMA_ID('raw_cw') IS NULL EXEC('CREATE SCHEMA raw_cw');
GO

IF OBJECT_ID('raw_cw.companies') IS NULL
CREATE TABLE raw_cw.companies (
    cw_company_id           BIGINT          NOT NULL PRIMARY KEY,
    company_name            NVARCHAR(256)   NOT NULL,
    ...
    cui_handling_required   BIT             NOT NULL DEFAULT 0,
    ai_opt_out              BIT             NOT NULL DEFAULT 0,
    synced_at               DATETIME2       NOT NULL DEFAULT SYSUTCDATETIME(),
    source_etag             NVARCHAR(128)   NULL
);
GO
```

Copy idiomatic pieces verbatim:
- Header comment cites the requirement ID + VER-02 reminder
- `IF SCHEMA_ID(...) IS NULL EXEC('CREATE SCHEMA ...')` then `GO`
- `IF OBJECT_ID(...) IS NULL CREATE TABLE` (idempotent)
- `synced_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()` on every table (Phase 2 framework requires it for retention sweep + AI-zone audit)
- `source_etag NVARCHAR(128) NULL` on every raw_cw table (D-01 future-proofing)
- **NO `body`, `initialDescription`, `resolution`, `internalAnalysis` columns on `raw_cw.tickets`** — architectural enforcement per Pitfall 1

---

### `sql/10-grants/001_etl_grants.sql` (extend)

**Analog:** existing `sql/10-grants/001_etl_grants.sql` (full file, lines 1-15)

**Pattern to extend:**
```sql
DECLARE @etl_principal NVARCHAR(256) = 'mi-bary-etl';

IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = @etl_principal)
    EXEC('CREATE USER [mi-bary-etl] FROM EXTERNAL PROVIDER');

GRANT SELECT, INSERT, UPDATE, DELETE ON SCHEMA::raw_cw TO [mi-bary-etl];
DENY  SELECT, INSERT, UPDATE, DELETE ON SCHEMA::ai_zone TO [mi-bary-etl];
DENY  SELECT, INSERT, UPDATE, DELETE ON SCHEMA::audit  TO [mi-bary-etl];
DENY  SELECT, INSERT, UPDATE, DELETE ON SCHEMA::pseudo TO [mi-bary-etl];
```

Phase 2 must REVOKE the DENY on `pseudo` and `ai_zone` for `mi-bary-etl` and replace with:
- `GRANT SELECT, INSERT, UPDATE ON SCHEMA::pseudo TO [mi-bary-etl]` (pseudo.person_map writes)
- `GRANT SELECT, INSERT, DELETE ON SCHEMA::ai_zone TO [mi-bary-etl]` (TRUNCATE+INSERT for shape_builder; explicitly NOT UPDATE per principle of minimal grant)

Per Phase 1 grant_drift_check, every change MUST update the `EXPECTED_PRINCIPALS` registry (`scripts/ci/grant_drift_check.py` line 18) — verify still complete.

---

### `scripts/ci/check_salt_runbook.py`

**Analog:** `scripts/ci/field_class_check.py` (CLI argparse + sys.exit pattern, lines 126-159)

**CLI gate pattern:**
```python
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check-static", action="store_true", default=True)
    ap.add_argument("--simulate-untagged", action="store_true", help="Meta-test ...")
    args = ap.parse_args()

    errors = check(...)
    if errors:
        for e in errors: print(e, file=sys.stderr)
        sys.exit(1)
    print(f"VER-02 OK: {cols_total} columns checked across {tables_total} tables")
    sys.exit(0)
```

`check_salt_runbook.py`: assert `compliance/salt-rotation-runbook.md` exists AND `compliance/salt-rotation-state.yaml` has at least one entry with `fire_drill_completed: true` (Phase 2 success criterion 5). Include `--self-test` mode that primes a fake state and asserts the gate fires when missing — same meta-test pattern as `--simulate-untagged`.

---

### `.github/workflows/etl-cw-nightly.yml`

**Analog:** `.github/workflows/audit-chain-validate.yml` (live-validate job, lines 28-56)

**OIDC + cron + azure/login pattern:**
```yaml
on:
  schedule:
    - cron: '15 6 * * *'    # 06:15 UTC nightly (after infra-drift)
  workflow_dispatch:

permissions:
  id-token: write
  contents: read

jobs:
  live-validate:
    if: github.event_name == 'schedule' || github.event_name == 'workflow_dispatch'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: azure/login@v2
        with:
          client-id: ${{ vars.AZURE_WHATIF_CLIENT_ID }}
          tenant-id: ${{ vars.AZURE_TENANT_ID }}
          subscription-id: ${{ vars.AZURE_SUBSCRIPTION_ID }}
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: |
          pip install -r scripts/ci/requirements.txt
          pip install -e packages/barycenter-audit
```

For `etl-cw-nightly.yml`:
- Cron `0 6 * * *` (RESEARCH spec)
- Use `vars.AZURE_ETL_CLIENT_ID` (mi-bary-etl) — NOT the what-if MI
- `pip install -e packages/barycenter-audit packages/barycenter-etl`
- Run `python -m barycenter.etl.run --adapter connectwise`
- Per CLAUDE.md D-08 / Pitfall 11: OIDC subject claim MUST be env-scoped (no wildcards) — verify `vars.AZURE_ETL_CLIENT_ID` is bound to a federated credential with subject `repo:gravity/barycenter:ref:refs/heads/main` or `repo:...:environment:prod`.

---

### `.github/workflows/etl-retention-sweep.yml`

**Analog:** `.github/workflows/infra-drift.yml` (cron-driven Azure-authenticated job, lines 1-56)

Same template; cron `0 12 * * *` (RESEARCH Pitfall 10 — different time of day from sync). Reads `compliance/retention-policy.yaml` and emits per-table audit events.

---

### `.github/workflows/etl-tests.yml` or extension of `python-tests.yml`

**Analog:** `.github/workflows/python-tests.yml` (full file, lines 1-35)

**Pattern to copy/extend:**
```yaml
- name: install
  run: |
    pip install -r scripts/ci/requirements.txt
    pip install -e 'packages/barycenter-audit[dev]'
- name: pytest audit SDK
  run: pytest packages/barycenter-audit/tests -q --ignore=packages/barycenter-audit/tests/integration
- name: VER-02 + AUDIT-01 self-tests
  run: |
    python scripts/ci/field_class_check.py --check-static
    python scripts/ci/field_class_check.py --simulate-untagged
    ...
```

Add steps:
- `pip install -e 'packages/barycenter-etl[dev]'`
- `pytest packages/barycenter-etl/tests -q --ignore=packages/barycenter-etl/tests/integration`
- `python scripts/ci/check_salt_runbook.py --check-static`
- `python scripts/ci/check_salt_runbook.py --self-test`

---

### `compliance/cui-canary-phrases.yaml`, `compliance/retention-policy.yaml`

**Analog:** `compliance/field-class-registry.yaml` (full file, lines 1-19)

**Versioned-config YAML pattern:**
```yaml
# VER-02 source of truth. ... CI gate fails any PR that adds a column without a tag ...
version: 1
schemas:
  raw_cw:
    companies:
      cw_company_id: INTERNAL
```

Header comment naming the gate that consumes it; `version: 1` top-level; nested YAML map. Use the same shape: `version: 1`, list of `phrases:` for canary; `default:` + `overrides:` map for retention (RESEARCH Pattern 7 example).

---

### `compliance/salt-rotation-runbook.md`, `compliance/tool-onboarding-spec.template.md`

**Analog:** `compliance/runbooks/chain-validate.md` (full file, lines 1-32)

**Runbook pattern to copy:**
```markdown
# Audit Chain Validation Runbook (AUDIT-01)

> How to verify ... Re-run on demand and as part of the `audit-chain-validate` CI workflow.

## Procedure
1. Connect with the audit identity (PIM-activated):
   ```bash
   az login --identity --client-id "$AUDIT_MI_CLIENT_ID"
   ```
...
## Pass criteria
...
## Failure response
...
## Automation
`scripts/ci/chain_validate.py` (plan 08) implements steps 2–6.
```

Sections: title with req ID, blockquote summary, `## Procedure` (numbered with code blocks), `## Pass criteria`, `## Failure response`, `## Automation` referencing the CI gate. Salt-rotation runbook follows the 8-step procedure in RESEARCH Pattern 6.

---

## Shared Patterns

### Pattern S1: Fail-closed audit emission per ETL operation

**Source:** `packages/barycenter-audit/src/barycenter/audit/client.py` (lines 71-104)
**Apply to:** `adapter_base.py`, `shape_builder.py`, `retention.py`, `salt_rotation.py`, every entry point in `framework/`

Every ETL operation that mutates data MUST be flanked by `AuditClient.emit(AuditEvent(verb='etl.write'|'retention.sweep'|'salt.rotate.*'|'cui.boundary_violation', ...))`. Per CLAUDE.md: NO `try/except/pass`, NO fire-and-forget. Audit failure = parent transaction rollback. The `AuditEmitError` re-raise in `client.py` line 102-104 is the model.

### Pattern S2: Single canonical import path

**Source:** `packages/barycenter-audit/src/barycenter/audit/__init__.py` (lines 1-11)
**Apply to:** `barycenter/etl/__init__.py`, `barycenter/etl/primitives/__init__.py`, `barycenter/etl/framework/__init__.py`, `barycenter/etl/adapters/__init__.py`

Each barrel re-exports the public names; consumers import from the package root, not deep paths. Mirrors CLAUDE.md mandate `from barycenter.audit import AuditClient`.

### Pattern S3: SQL DDL — idempotent, registry-tagged, comment-cited

**Source:** `sql/00-schemas/001_create_raw_cw.sql` (full file)
**Apply to:** all new `sql/00-schemas/*.sql` files

- `IF SCHEMA_ID(...) IS NULL EXEC('CREATE SCHEMA ...')` + `GO`
- `IF OBJECT_ID(...) IS NULL CREATE TABLE ...` + `GO`
- Top-of-file comment cites the requirement ID + the CI gate that enforces compliance
- Every column gets an entry in `compliance/field-class-registry.yaml` BEFORE the PR merges (VER-02 enforcement)
- Every table has `synced_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()` for retention sweep
- Raw-zone tables include `source_etag NVARCHAR(128) NULL` for forward-compat with incremental sync

### Pattern S4: SQL grants — explicit GRANT + DENY for defense-in-depth

**Source:** `sql/10-grants/001_etl_grants.sql` (lines 9-14)
**Apply to:** `sql/10-grants/001_etl_grants.sql` extension

Every principal gets explicit GRANT on its allowed schemas AND explicit DENY on every other schema. `grant_drift_check.py` (line 18) maintains `EXPECTED_PRINCIPALS = {"mi-bary-etl", "mi-bary-platform", "mi-bary-audit", "mi-bary-admin"}` — must be updated alongside any new grant.

### Pattern S5: GitHub Actions OIDC workflow

**Source:** `.github/workflows/audit-chain-validate.yml` (lines 28-56) and `infra-drift.yml`
**Apply to:** `etl-cw-nightly.yml`, `etl-retention-sweep.yml`

```yaml
permissions:
  id-token: write
  contents: read

steps:
  - uses: actions/checkout@v4
  - uses: azure/login@v2
    with:
      client-id: ${{ vars.AZURE_*_CLIENT_ID }}   # env-scoped (Pitfall 11)
      tenant-id: ${{ vars.AZURE_TENANT_ID }}
      subscription-id: ${{ vars.AZURE_SUBSCRIPTION_ID }}
```

No client secrets. All workflows declare `permissions:` explicitly (least-privilege).

### Pattern S6: CI gate self-test (`--simulate-*` / `--self-test --drifted`)

**Source:** `scripts/ci/field_class_check.py` (lines 109-149) and `scripts/ci/grant_drift_check.py`
**Apply to:** `scripts/ci/check_salt_runbook.py`, plus inline pytest gates `test_no_body_column.py`, `test_no_novel_ai_zone.py`, `test_recipe_no_bypass.py`

Every CI gate ships with a meta-test that injects a known-bad input and asserts the gate fires. From `field_class_check.py`:
```python
if args.simulate_untagged:
    if not errors:
        print("VER-02 meta-test FAIL: gate did not fire on injected untagged column", file=sys.stderr)
        sys.exit(1)
    print("VER-02 meta-test PASS (gate correctly fires on untagged column)")
    sys.exit(0)
```

The CI workflow runs both the real check AND the meta-test (`python-tests.yml` lines 27-34).

### Pattern S7: pytest fixture pattern — MagicMock over external resources

**Source:** `packages/barycenter-audit/tests/conftest.py` (lines 1-21)
**Apply to:** `packages/barycenter-etl/tests/conftest.py`

`MagicMock(name="...")` for `sql_conn`, `cursor`, `kv_client`, `cw_client`. Side-effects primed per-test via `mock.side_effect = ...`. Pattern shown in `test_fail_closed.py` lines 28-37.

### Pattern S8: Pure-function modules + class wrappers

**Source:** `packages/barycenter-audit/src/barycenter/audit/chain.py` (pure fns) + `sinks.py` (thin classes)
**Apply to:** `primitives/*.py` (pure fns), `framework/{canary,pseudonymizer,shape_builder}.py` (thin classes wrapping injected clients)

Stateless transforms = top-level functions. Anything holding a client/connection = class with `__init__(injected_client)` and no module-level state (Pitfall 5: salt never module-level).

## No Analog Found

These files break new ground in the codebase. Planner should rely on RESEARCH.md Code Examples + Architecture Patterns instead of an in-repo analog.

| File | Role | Data Flow | RESEARCH section to use |
|---|---|---|---|
| `packages/barycenter-etl/src/barycenter/etl/adapters/connectwise/client.py` | HTTP client (httpx + tenacity + token-bucket) | streaming pagination | RESEARCH Code Example 1 (lines 653-711) |
| `packages/barycenter-etl/src/barycenter/etl/adapters/connectwise/recipes/*.py` | declarative ETL recipe | transform composition | RESEARCH Code Examples 3 & 4 (lines 740-790) |
| `packages/barycenter-etl/src/barycenter/etl/run.py` | CLI entry point | n/a | RESEARCH §System Architecture Diagram (line 152) — `python -m barycenter.etl.run --adapter connectwise` |
| `packages/barycenter-etl/src/barycenter/etl/framework/retention.py` | scheduled DELETE sweeper | batch | RESEARCH Pattern 7 (lines 491-508) |
| `packages/barycenter-etl/src/barycenter/etl/framework/salt_rotation.py` | runbook automation helper | event-driven | RESEARCH Pattern 6 (lines 472-489) |
| `packages/barycenter-etl/tests/adapters/connectwise/test_client.py` | respx-mocked unit | n/a | respx docs cited in RESEARCH §Standard Stack Supporting table |
| `compliance/salt-rotation-state.yaml` | rotation state tracker (in-git) | n/a | RESEARCH §Runtime State Inventory (line 551) |

## Metadata

**Analog search scope:**
- `/packages/barycenter-audit/src/**` — primary structural analog (Python package, audit SDK)
- `/packages/barycenter-audit/tests/**` — pytest conventions, fixtures
- `/sql/00-schemas/**` — DDL conventions
- `/sql/10-grants/**` — grant model
- `/scripts/ci/**` — CI gate conventions, argparse + meta-test pattern
- `/.github/workflows/**` — OIDC + cron + Azure auth pattern
- `/compliance/**` — versioned-config YAML, runbook markdown structure

**Files scanned:** ~30 source files across 7 directories
**Pattern extraction date:** 2026-05-02

---

## PATTERN MAPPING COMPLETE

**Phase:** 02 - Tool Onboarding Framework + ConnectWise Manage
**Files classified:** 45
**Analogs found:** 38 / 45

### Coverage
- Files with exact analog: 18 (DDL, grants, pyproject, package barrels, runbook, CI workflow, conftest)
- Files with role-match analog: 17 (framework classes, primitives, exceptions, gates)
- Files with partial analog: 3 (canary scanner, shape builder, CUI gate — analogs in spirit only)
- Files with no analog: 7 (httpx client, recipes, run.py, retention, salt rotation, respx tests, salt-state YAML)

### Key Patterns Identified
1. **Fail-closed audit envelope** (S1) — `AuditClient.emit()` mandatory around every mutation; `try/except` rolls back parent transaction; `AuditEmitError` re-raised never swallowed (CLAUDE.md D-04/D-06).
2. **Pure functions for transforms; injected-client classes for stateful work** (S8) — primitives are flat module functions (mirrors `chain.py`); CanaryScanner/Pseudonymizer/ShapeBuilder are thin classes wrapping injected dependencies (mirrors `sinks.py`).
3. **CI gate + meta-test self-check** (S6) — every gate ships with a `--simulate-*` mode that injects bad input and asserts the gate fires; both modes run in CI (`field_class_check.py`, `grant_drift_check.py` exemplars).
4. **Idempotent, requirement-cited SQL DDL** (S3) — `IF OBJECT_ID IS NULL CREATE TABLE`, mandatory `synced_at` and `source_etag`, header comment naming the requirement ID and VER-02.
5. **OIDC-only GitHub Actions** (S5) — env-scoped client IDs (Pitfall 11), explicit `permissions:`, no client secrets; cron jobs use the audit-chain-validate / infra-drift template.

### File Created
`/Users/craig/projects/repository/.claude/worktrees/elastic-robinson-3d5ab0/.planning/phases/02-tool-onboarding-framework-connectwise-manage/02-PATTERNS.md`

### Ready for Planning
Pattern mapping complete. Planner can now reference analog patterns + line numbers in PLAN.md task actions.
