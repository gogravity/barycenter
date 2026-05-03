# BAA Inventory (COMP-06)

> Source of truth for HIPAA Business Associate Agreement coverage.
> Required by COMP-06. Reviewed annually.

**Last reviewed:** 2026-05-02
**Next review due:** 2027-05-02

## Microsoft (Azure) BAA

- **Reference:** see `compliance/baa/microsoft-baa-reference.md`
- **Scope:** Azure SQL, Storage, Key Vault, Log Analytics, Entra ID, all services in the Online Services Terms HIPAA-eligible list
- **Status:** _confirmed 2026-05-02 — auto-applied via OST on subscription debe8a68-e9df-4662-92b6-cebd05b776be_

## Anthropic BAA

- **Reference:** `compliance/baa/anthropic-baa.pdf` _(signed copy — pending legal review)_
- **Scope:** Anthropic API (Claude models — pinned versions only, see plan 03 model allowlist work)
- **Status:** _pending — BAA in legal review; documented exception per plan 09 exception path. ZDR written confirmation committed in lieu pending signed PDF._

## Anthropic Zero-Data-Retention (ZDR) Confirmation

- **Reference:** `compliance/baa/anthropic-zdr-confirmation.md`
- **Scope:** Written confirmation from Anthropic counsel that ZDR applies to the BAA-covered workspace
- **Status:** _pending — placeholder in place; must be replaced with real Anthropic written confirmation before COMP-06 is fully met_

## Verification CI

`pytest tests/test_baa_inventory.py` (added in plan 09) asserts that all three reference files exist and that this inventory document references each.
