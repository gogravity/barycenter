# Audit Chain Validation Runbook (AUDIT-01)

> How to verify end-to-end that the audit chain is unbroken from genesis to head.
> Re-run on demand and as part of the `audit-chain-validate` CI workflow (plan 08).

## Procedure

1. Connect with the audit identity (PIM-activated):
   ```bash
   az login --identity --client-id "$AUDIT_MI_CLIENT_ID"
   ```
2. Fetch all WORM blob entries for the audit container, in append order:
   ```bash
   az storage blob list --account-name "$STORAGE_ACCT" --container-name audit \
     --auth-mode login --query "[].name" -o tsv | sort
   ```
3. For each entry, parse the JSON payload, extract `prior_digest`, `this_digest`, and the canonical payload.
4. Recompute `compute_digest(prior_digest, canonicalize_json(payload))` (using `barycenter.audit.chain`) and assert equality with `this_digest`.
5. Assert the first entry's `prior_digest == GENESIS_HASH` (`"0" * 64`).
6. Query `audit.chain_state.head_digest` from SQL and assert equality with the last entry's `this_digest`.

## Pass criteria
- Every recomputed digest matches the stored `this_digest`.
- First entry chains from `GENESIS_HASH`.
- SQL `chain_state.head_digest` equals the final WORM entry digest.

## Failure response
Any mismatch → page on-call (alert wired in Phase 4 OPS-02) → freeze write traffic → forensic export of WORM container (immutable; cannot be altered) → root cause investigation. Do NOT attempt to re-chain in place.

## Automation
`scripts/ci/chain_validate.py` (plan 08) implements steps 2–6. CI runs it nightly and on every PR touching the audit SDK.
