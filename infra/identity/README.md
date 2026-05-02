# infra/identity

Deploys the 4 canonical managed identities (IDENT-03) and the PIM eligibility schedule on `mi-bary-admin` (IDENT-02 + IDENT-05).

## Identities

| MI Name           | Purpose                                                        |
|-------------------|----------------------------------------------------------------|
| mi-bary-etl       | Sign HMAC keys (KV), CRUD on raw_* schemas, audit emit         |
| mi-bary-platform  | SELECT on ai_zone schema only (no raw_*)                       |
| mi-bary-audit     | LA ingest, WORM blob append, UPDATE on audit.chain_state       |
| mi-bary-admin     | PIM-eligible only, dual-approval, no standing grants           |

## Deploy

Via GitHub Actions OIDC (plan 08 wires this). Manual local what-if:

```bash
az deployment group what-if \
  --resource-group rg-barycenter-identity \
  --template-file infra/identity/main.bicep \
  --parameters infra/identity/main.dev.bicepparam
```

## Post-deploy: dual-approval policy on mi-bary-admin

The Bicep `roleEligibilityScheduleRequests` resource creates eligibility but does NOT
configure the role management *policy* (which sets `requireApproval=true` and `approverCount=2`).
That policy lives at the directory role management API and is configured via:

```bash
# IDENT-05: dual approval on activation
SCOPE="/subscriptions/$AZURE_SUBSCRIPTION_ID/resourceGroups/rg-barycenter-dev"
READER_ROLE_ID="acdd72a7-3385-48ef-bd42-f606fba81ae7"
POLICY_ID=$(az rest --method get \
  --uri "https://management.azure.com${SCOPE}/providers/Microsoft.Authorization/roleManagementPolicyAssignments?api-version=2020-10-01&\$filter=roleDefinitionId+eq+'${SCOPE}/providers/Microsoft.Authorization/roleDefinitions/${READER_ROLE_ID}'" \
  --query 'value[0].properties.policyId' -o tsv)

# PATCH the policy to require approval with 2 approvers (UPN list provided by admin)
az rest --method patch \
  --uri "https://management.azure.com${POLICY_ID}?api-version=2020-10-01" \
  --body '{ "properties": { "rules": [
    { "id": "Approval_EndUser_Assignment", "ruleType": "RoleManagementPolicyApprovalRule",
      "setting": { "isApprovalRequired": true,
                   "approvalStages": [ { "approvalStageTimeOutInDays": 1, "isApproverJustificationRequired": true,
                                          "escalationTimeInMinutes": 0, "primaryApprovers": [
                                            { "id": "<APPROVER_1_OBJECT_ID>", "userType": "User" },
                                            { "id": "<APPROVER_2_OBJECT_ID>", "userType": "User" } ],
                                          "isEscalationEnabled": false } ] } }
  ] } }'
```

Plan 09 (phase exit) verifies this policy is in effect by attempting an activation without approval and observing rejection.

## MI consumers (downstream plans)

| MI                | Plan 05 (data)        | Plan 06 (audit)         | Plan 07 (audit SDK) | Phase 3 (gateway)   |
|-------------------|-----------------------|-------------------------|---------------------|---------------------|
| mi-bary-etl       | KV sign + raw_* CRUD  | (audit emit only)       | as etl caller       | —                   |
| mi-bary-platform  | ai_zone SELECT        | (audit emit only)       | as platform caller  | as gateway runtime  |
| mi-bary-audit     | UPDATE chain_state    | LA ingest + WORM append | as audit identity   | —                   |
| mi-bary-admin     | (no standing)         | (no standing)           | —                   | —                   |

## Pitfall 1 enforcement

`mi-bary-admin` has ZERO standing role assignments. The PIM eligibility resource only makes the admin *able to request* activation. Plan 09 verifies via `az role assignment list --assignee <admin-principal-id>` returning empty.

## Notes

- The placeholder role for the PIM eligibility is the built-in Reader (`acdd72a7-3385-48ef-bd42-f606fba81ae7`). It will be promoted to a custom `raw_*` reader role in plan 05 once the SQL custom role definitions exist.
- The PIM scope here is `rg-barycenter-dev`. Plan 05 narrows the eligibility scope to the SQL DB resource ID.
- Managed identities have no client secret — there is no credential rotation API to call. Long-lived secret absence is verified architecturally (resource type is `userAssignedIdentities`, not `servicePrincipals` with passwords).
