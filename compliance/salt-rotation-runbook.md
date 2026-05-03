# Salt Rotation Runbook (ENC-02)

> How to rotate per-tenant HMAC salts using Key Vault secret versioning ("versioned pepper IDs").
> Re-run quarterly and on any suspected compromise. Fire drill (success criterion 5)
> = the first execution against a non-production tenant; outcome logged in
> `compliance/salt-rotation-state.yaml`.

## Pre-flight (T-7 days)
1. Confirm Key Vault diagnostic logs are healthy (`az monitor diagnostic-settings list ...`).
2. Confirm no in-flight ETL sync (`gh run list --workflow etl-cw-nightly.yml --limit 1`).
3. Confirm dual-write test fixture passes (`pytest packages/barycenter-etl/tests/test_salt_rotation.py -v`).

## Procedure

1. **Create new secret version** in Key Vault for the target tenant:
   ```bash
   az keyvault secret set --vault-name "$KV" --name "salt-${TENANT_ID}" --value "$(openssl rand -hex 32)"
   ```
   Record the new version ID (returned in JSON `id` field).

2. **Open dual-write window** by editing `compliance/salt-rotation-state.yaml`:
   set `tenants[<tenant_id>].mode = "dual-write"`, record `old_version`, `new_version`,
   `window_opened_at`, `expected_close_at` (= now + 24h).

3. **Run the ETL sync** (or wait for the next nightly cycle). Every pseudonymization
   writes BOTH (pid_old, ver_old) and (pid_new, ver_new) rows in `pseudo.person_map`.

4. **Verify dual-write coverage**: query
   `SELECT COUNT(DISTINCT person_pid) FROM pseudo.person_map WHERE tenant_id=? AND salt_version IN (?, ?)`
   — expect both versions present for every active email.

5. **Cut over**: set `tenants[<tenant_id>].mode = "new-only"` in the state YAML. Subsequent writes use only the new version.

6. **Backfill (asynchronous)** for adapters where the source data still contains the email
   (Pax8/Graph in Phase 4). For Phase 2 (CW-only, no emails in raw_cw), skip.

7. **Retire old version (T+30 days)**: disable the old KV secret version
   (`az keyvault secret set-attributes --enabled false --version "$OLD"`).
   Old pseudonyms in `pseudo.person_map` become unverifiable — intentional, also the erasure path.

8. **Audit**: every step emits `AuditEvent(verb='salt.rotate.<step>', resource='salt-<tenant>', ...)`.
   Append the operator identity, timestamp, and outcome to `compliance/salt-rotation-state.yaml` under `executions[]`.

## Pass criteria
- New secret version exists and is enabled.
- Dual-write window covered at least one nightly sync cycle.
- Cut-over recorded; subsequent sync writes only new-version rows.
- All step audit events visible in `audit.events` and WORM blob.

## Failure response
- If KV write fails: do not proceed; fix KV access policy on `mi-bary-etl`.
- If dual-write coverage incomplete: extend the window; investigate.
- If audit emit fails at any step: STOP. Per CLAUDE.md fail-closed mandate, the parent transaction must roll back.

## Automation
`scripts/ci/check_salt_runbook.py` (this plan) verifies the runbook + state YAML exist and the YAML is well-formed; `barycenter.etl.framework.salt_rotation.SaltRotation` (Plan 04) implements the dual-write logic.
