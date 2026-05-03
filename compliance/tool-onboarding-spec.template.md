# Tool Onboarding Spec — {{tool_name}}

> Filled by the engineer onboarding the tool. Reviewed by Security + Architecture.
> Creates the contract this adapter must satisfy.

## Identification
- **Tool name:** {{tool_name}}
- **Category** (TOOL-04 enum): one of `productivity | rmm | security | backup | docs | distributors | cw`
- **Vendor BAA on file:** yes/no/n-a (link)
- **Adapter package path:** `packages/barycenter-etl/src/barycenter/etl/adapters/{{slug}}/`

## Field Map
| Source field | Type | Field class (RESTRICTED|SENSITIVE|INTERNAL|PUBLIC) | Primitive | Target column | Justification |
|---|---|---|---|---|---|

## Raw Schema
- Target schema: `raw_{{slug}}`
- DDL file: `sql/00-schemas/00X_create_raw_{{slug}}.sql`
- Required columns on every table: `synced_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()`, `source_etag NVARCHAR(128) NULL`
- Forbidden columns: any free-text body / description / resolution / internal-notes (architectural)

## ETL Recipe
- Recipes per table in `adapters/{{slug}}/recipes/*.py`
- Every column derivation uses one of the eight primitives (drop, hash, pseudonymize, aggregate, bucket, score, keyword_flags, as_is)
- `test_recipe_no_bypass.py` enforces this invariant in CI

## AI-Zone Contributions
| Canonical shape | Columns contributed | Aggregation grain | Field-class composition |
|---|---|---|---|
| customer_snapshot |  |  |  |
| customer_features_{{slug}} |  |  |  |
| timeseries_aggregate |  |  |  |
| customer_memory |  |  |  |

## CUI Surface
- `CUI_SENSITIVE_TABLES` (skipped entirely for CUI tenants):
- `CUI_CANARY_FIELDS` per table:
- Attachment handling: refused outright for CUI tenants (`refuse_attachment(tenant_cui_flag=True) -> True`)

## Retention
- Per-class TTLs follow `compliance/retention-policy.yaml`
- Customer-specific overrides:

## Erasure
- Erasure trigger: pseudonym map purge invalidates downstream pseudonyms
- Cascade list: tables this adapter writes to (raw_{{slug}}.*, ai_zone.* contributions)
- Manual steps (if any):

## Authentication
- Auth mode: OAuth client-credentials | HTTP Basic | API key | other
- KV secret names: `api-{{slug}}-*`
- Managed identity required: `mi-bary-etl`

## Sign-off
- Engineering: ____________   date: __________
- Security:    ____________   date: __________
- Architecture: ____________  date: __________
