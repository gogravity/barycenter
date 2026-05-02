# Branch Protection — How to Apply (IDENT-04)

`branch-protection.json` in this directory is the declarative source of truth for the
`main` branch protection ruleset. It is applied by a human admin during the Phase 1
exit (plan 01-09 task 2).

## Apply

```bash
gh api -X PUT repos/gravity/barycenter/branches/main/protection \
  --input .github/branch-protection.json
```

## Verify

```bash
gh api repos/gravity/barycenter/branches/main/protection > /tmp/protection.json
jq '{enforce_admins: .enforce_admins.enabled, signatures: .required_signatures.enabled, contexts: .required_status_checks.contexts}' /tmp/protection.json
```

Expected:

```json
{"enforce_admins": true, "signatures": true, "contexts": ["what-if","ver-02-static","self-test","unit-tests"]}
```

## Pitfall 12 — Admin bypass MUST be disabled

`enforce_admins: true` is load-bearing. Without it, an admin can push directly to
`main` and silently bypass every CI gate. Verify by attempting a direct push as
admin AFTER applying the protection — the push MUST be rejected with
`Changes must be made through a pull request`. Capture the rejection
message + timestamp in `phase-exit-evidence.md`.

## Required status checks → Workflow job mapping

| Context name      | Workflow file              | Job name        |
| ----------------- | -------------------------- | --------------- |
| `what-if`         | `infra-deploy.yml`         | `what-if`       |
| `ver-02-static`   | `field-class-check.yml`    | `ver-02-static` |
| `self-test`       | `audit-chain-validate.yml` | `self-test`     |
| `unit-tests`      | `python-tests.yml`         | `unit-tests`    |

If any workflow's job name changes, update both the workflow YAML AND this JSON,
then re-apply via `gh api -X PUT`.
