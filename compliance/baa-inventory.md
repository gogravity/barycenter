# BAA Inventory (COMP-06)

> Source of truth for HIPAA Business Associate Agreement coverage.
> Required by COMP-06. Reviewed annually.

**Last reviewed:** _pending — populated at phase 1 exit (plan 09)_
**Next review due:** _pending_

## Microsoft (Azure) BAA

- **Reference:** see `compliance/baa/microsoft-baa-reference.md`
- **Scope:** Azure SQL, Storage, Key Vault, Log Analytics, Entra ID, all services in the Online Services Terms HIPAA-eligible list
- **Status:** _pending verification — confirm via Microsoft Service Trust Portal_

## Anthropic BAA

- **Reference:** `compliance/baa/anthropic-baa.pdf` _(signed copy — not yet committed)_
- **Scope:** Anthropic API (Claude models — pinned versions only, see plan 03 model allowlist work)
- **Status:** _pending — must be signed before phase exit; blocks COMP-06_

## Anthropic Zero-Data-Retention (ZDR) Confirmation

- **Reference:** `compliance/baa/anthropic-zdr-confirmation.md`
- **Scope:** Written confirmation from Anthropic counsel that ZDR applies to the BAA-covered workspace
- **Status:** _pending — email from Anthropic counsel acceptable if signed BAA still in flight_

## Verification CI

`pytest tests/test_baa_inventory.py` (added in plan 09) asserts that all three reference files exist and that this inventory document references each.
