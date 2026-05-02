# Conditional Access — MFA Enforcement (IDENT-01)

Conditional Access (CA) policies cannot be fully expressed as Bicep at time of
Phase 1 (Microsoft.Conditional access policies require Microsoft Graph API for
automation). This runbook documents the manual configuration applied during phase
exit.

## Policy 1: Tenant-wide MFA on all sign-ins

- **Name:** `bary-ca-mfa-all-users`
- **Assignments → Users:** All users (exclude break-glass account)
- **Assignments → Cloud apps:** All cloud apps
- **Assignments → Conditions:** None (apply always)
- **Access controls → Grant:** Require MFA
- **Session:** Sign-in frequency 12 hours, persistent browser disabled
- **State:** On (NOT Report-only — see T-1-09-02)

## Policy 2: Phishing-resistant MFA on privileged operations

- **Name:** `bary-ca-fido2-privileged`
- **Assignments → Users:** PIM-eligible users + Owner role members
- **Assignments → Cloud apps:** Microsoft Azure Management, Microsoft Graph
- **Assignments → Conditions:** Sign-in risk: medium or high; OR User risk: medium or high
- **Access controls → Grant:** Require authentication strength → "Phishing-resistant MFA"
  (built-in strength: FIDO2 security key, Windows Hello for Business,
  certificate-based authentication — `PhishingResistantMfa`)
- **State:** On

## Policy 3: 15-minute idle session for admin operations

- **Name:** `bary-ca-admin-idle-15min`
- **Status:** Deferred to Phase 4 (COMP-01). Placeholder noted here so the policy
  family is discoverable in one runbook when Phase 4 begins. Do NOT create in
  Phase 1.

## Verification (run during phase exit task 2)

```bash
# List policies
az rest --method get \
  --uri "https://graph.microsoft.com/v1.0/identity/conditionalAccess/policies?\$filter=startswith(displayName,'bary-ca-')" \
  --query "value[].{name:displayName,state:state}" -o table

# Expected:
#   Name                       State
#   -------------------------  -------
#   bary-ca-mfa-all-users       enabled
#   bary-ca-fido2-privileged    enabled
```

A `state` of `enabledForReportingButNotEnforced` is NOT acceptable — that is
Report-only mode. The state field MUST equal `enabled` exactly.

```bash
# Attempt admin sign-in without MFA → must prompt for MFA
# Attempt PIM activation without FIDO2 → must require FIDO2
```

Capture the rejection screenshots / Sign-In log entries and reference them in
`phase-exit-evidence.md`.

## Break-glass account

Per Microsoft guidance: maintain ONE break-glass account excluded from all CA
policies, secured with a long random password stored in a physical safe,
monitored by a Sign-In log alert (Phase 4 OPS-02). Document the account UPN in
`compliance/break-glass.md` (NOT this file — separate restricted-readership doc
created during Phase 4 OPS-02 work).

The break-glass account is the ONE permitted exclusion from `bary-ca-mfa-all-users`.
Every other exclusion requires CODEOWNERS approval and a dated entry in this
runbook.
