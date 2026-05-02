---
phase: 01-network-data-foundations
plan: 04
subsystem: infra
tags: [bicep, azure, fortigate, vnet, hub-spoke, udr, nsg, network-perimeter, nva]

requires:
  - phase: 01-network-data-foundations
    provides: 01-RESEARCH §Code Example A (recursion-safe spoke UDR pattern); 01-CONTEXT (CIDR plan, FortiGate sizing)
provides:
  - Hub VNet 10.10.0.0/22 (untrust/trust/GatewaySubnet) Bicep module
  - Spoke VNet 10.20.0.0/22 with 5 subnets and recursion-safe UDR (PE/data subnets get routeTable null)
  - FortiGate-VM02 BYOL Bicep module (Standard_F2s_v2, dual-NIC, SystemAssigned MI for KV license retrieval)
  - FortiOS config-as-code (policies.json) with 6 rules including default-deny-all and syslog forwarder stub
  - Bidirectional hub-spoke peering with allowForwardedTraffic=true
  - Default NSG (deny-from-Internet 100, allow VNet-to-VNet 200)
  - Network orchestrator main.bicep + main.dev.bicepparam + README
  - Spoke subnet outputs (etl/services/data/pe/admin) for downstream plans
affects: [01-05-key-vault-storage, 01-06-log-analytics-audit, 01-08-deploy-pipeline-drift, 01-09-verification, 02-onboarding-framework, 03-agent-access-layer]

tech-stack:
  added: [Azure Bicep, FortiGate-VM02 BYOL, FortiOS REST API config-as-code, Azure routeTables, NSGs]
  patterns:
    - "Recursion guard expression in spoke-vnet.bicep: contains(s.name,'pe-')||contains(s.name,'data-')"
    - "Single-NVA hub-and-spoke with static trust NIC IP referenced by UDR next-hop"
    - "License-via-KV-secret pattern: Bicep declares KV resource id, post-deploy CI fetches and pushes via run-command"
    - "Config-as-code policies.json as drift-detector source-of-truth"
    - "Conditional module deployment via deployFortigate flag for plan ordering flexibility"

key-files:
  created:
    - infra/networking/main.bicep
    - infra/networking/main.dev.bicepparam
    - infra/networking/README.md
    - infra/networking/modules/hub-vnet.bicep
    - infra/networking/modules/spoke-vnet.bicep
    - infra/networking/modules/fortigate-vm.bicep
    - infra/networking/modules/nsg.bicep
    - infra/networking/modules/peering.bicep
    - infra/networking/modules/udr-policies.bicep
    - infra/networking/fortigate-config/policies.json
    - .gitignore
  modified: []

key-decisions:
  - "Recursion guard implemented via subnet-name substring match ('pe-'/'data-') rather than explicit subnet list — keeps spoke-vnet.bicep generic and forces naming discipline"
  - "FortiGate license install deferred to post-deploy CI step (az vm run-command) rather than customData — license blob too large and would require plaintext exposure"
  - "deployFortigate=true default but conditional module — allows plan 04 to deploy hub+spoke skeleton before plan 05's KV exists"
  - "Spoke NSG attached via spoke-vnet module's nsgId param (single NSG, deny-from-Internet) rather than per-subnet NSGs — keeps surface area small for v1"
  - "udr-policies.bicep is a stub today; reserved as the home for future overlay routes (admin bastion, ExpressRoute) so spoke-vnet stays generic"
  - "policies.json schema_version=1 + drift detector reads this file as source-of-truth — manual FortiGate UI edits are revoked nightly"

patterns-established:
  - "Recursion guard: routeTable: (contains(s.name,'pe-')||contains(s.name,'data-')) ? null : { id: udr.id }"
  - "Conditional module + non-null assertion: deployFortigate ? fortigate!.outputs.x : ''"
  - "FortiGate config-as-code in JSON, drift-checked nightly against live FortiOS REST API"
  - "All resource modules accept tags object propagated from parent (no hardcoded tags)"
  - ".gitignore excludes infra/**/*.json (Bicep build output) but allows fortigate-config/*.json (source)"

requirements-completed: [NETW-01, NETW-03, EGRESS-01]

duration: ~25min
completed: 2026-05-02
---

# Phase 01 Plan 04: FortiGate-anchored hub-and-spoke network perimeter — Summary

**Hub VNet (10.10.0.0/22), spoke VNet (10.20.0.0/22, 5 subnets, recursion-safe UDR), FortiGate-VM02 BYOL with KV-sourced license, NSGs, peering, and config-as-code FortiOS policies — all Bicep-validated and ready for plan 08 deploy.**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-05-02T (Wave 1 parallel executor)
- **Completed:** 2026-05-02
- **Tasks:** 2
- **Files created:** 11

## Accomplishments

- 5 Bicep network sub-modules (hub-vnet, spoke-vnet, nsg, peering, udr-policies) with the recursion-safe UDR expression copied verbatim from RESEARCH §Code Example A
- FortiGate-VM02 BYOL module on Standard_F2s_v2 with dual-NIC (untrust dynamic, trust static at 10.10.1.4), enableIPForwarding on both NICs, and SystemAssigned managed identity for post-deploy KV license retrieval
- `policies.json` (FortiOS config-as-code) with the four required deny/allow rules, the spoke-to-azure-mgmt allow, and `default-deny-all` as the final entry — every rule has `logtraffic: "all"` (T-1-04-08 mitigation)
- `main.bicep` orchestrator wiring hub → nsg → fortigate → spoke → peering → udr-overlay in the correct order, with `deployFortigate` flag for cross-plan flexibility
- `main.dev.bicepparam` with KV placeholder (substituted after plan 05) and SSH key sourced from `FGT_ADMIN_SSH_PUBLIC_KEY` env var
- README documents license-via-KV procedure, recursion guard rationale, drift-detector contract, and cross-plan dependencies
- All 6 Bicep files build cleanly with `az bicep build` (zero errors, zero warnings after BCP318 fix)

## Task Commits

1. **Task 1: Five network sub-modules with recursion-safe UDR** — `4b60cab` (feat)
2. **Task 2: FortiGate VM module + FortiOS config-as-code + main orchestrator + bicepparam + README** — `5f7dc73` (feat)
3. **Build artifact / secret gitignore** — `23f367c` (chore)

## Files Created/Modified

- `infra/networking/main.bicep` — Network orchestrator wiring hub + FortiGate + spoke + peering + NSGs + UDR overlay
- `infra/networking/main.dev.bicepparam` — Dev environment parameter file with KV placeholder
- `infra/networking/README.md` — Topology, recursion guard, license-via-KV, drift detector, cross-plan deps
- `infra/networking/modules/hub-vnet.bicep` — Hub VNet 10.10.0.0/22 with untrust/trust/GatewaySubnet
- `infra/networking/modules/spoke-vnet.bicep` — Spoke VNet with recursion-safe UDR (the load-bearing pattern)
- `infra/networking/modules/fortigate-vm.bicep` — FortiGate-VM02 BYOL VM, dual-NIC, SystemAssigned MI
- `infra/networking/modules/nsg.bicep` — Default NSG (deny Internet inbound 100, allow VNet inbound 200)
- `infra/networking/modules/peering.bicep` — Bidirectional peering with allowForwardedTraffic=true
- `infra/networking/modules/udr-policies.bicep` — Stub for future overlay routes
- `infra/networking/fortigate-config/policies.json` — FortiOS config-as-code (FQDN objects, 6 policies, syslog stub)
- `.gitignore` — Exclude bicep ARM JSON output and license/key files

## Decisions Made

- **Recursion guard via substring match.** The literal `contains(s.name, 'pe-') || contains(s.name, 'data-')` expression was preserved verbatim from RESEARCH §Code Example A. Named subnet enumeration would have been more explicit but couples module to specific subnet names; substring match forces naming discipline (caught in plan 09 acceptance test).
- **License install deferred to post-deploy CI.** Bicep `customData` only handles hostname bootstrap. The license blob is too long for customData and base64-embedding it in any Bicep file is a Rule 4 violation (information disclosure threat T-1-04-03). Post-deploy `az vm run-command` invokes `execute restore license` after fetching the secret from KV.
- **`deployFortigate` flag.** Allows hub+spoke skeleton to deploy before plan 05's KV exists. Without this, plan 04 → plan 05 would need a circular dependency (KV needs the data-subnet from spoke; FortiGate needs the KV).
- **Single spoke NSG, attached via spoke-vnet module.** v1 keeps the NSG count to 1 to minimize surface area. Per-subnet NSGs are deferred until a documented use case (e.g., admin bastion needs different inbound rules than etl-subnet).
- **`udr-policies.bicep` stub today.** Reserves a clean home for future overlay routes (admin bastion bypass, ExpressRoute) without churning `spoke-vnet.bicep`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] BCP318 warning on conditional module output access**
- **Found during:** Task 2 (`az bicep build --file main.bicep`)
- **Issue:** `output fortigateVmId string = deployFortigate ? fortigate.outputs.vmId : ''` produced `BCP318: The value of type "module | null" may be null at the start of the deployment, which would cause this access expression (and the overall deployment with it) to fail.` because Bicep types conditional modules as `module | null` and the runtime can't statically prove the guard.
- **Fix:** Used the non-null assertion operator: `deployFortigate ? fortigate!.outputs.vmId : ''`. Safe because the only path that reads `fortigate.outputs` is gated by the same `deployFortigate` flag that gates module deployment.
- **Files modified:** infra/networking/main.bicep
- **Verification:** `az bicep build --file infra/networking/main.bicep` exits clean with zero warnings.
- **Committed in:** 5f7dc73 (Task 2 commit)

**2. [Rule 2 - Missing Critical] .gitignore for bicep build artifacts and secret files**
- **Found during:** Post-task-2 `git status`
- **Issue:** `az bicep build` emits ARM JSON next to each `.bicep` file (e.g., `main.json`). Without a gitignore, these would be committed and create permanent merge conflicts. Additionally, `.lic`, `.pem`, `.key`, `.env` files were not blocked from accidental commit — relevant because the license-handling procedure produces a transient `/tmp/license.lic` and the SSH key path is documented in README.
- **Fix:** Added `.gitignore` excluding `infra/**/*.json` (with explicit allowlist for `fortigate-config/*.json` so policies.json stays tracked) plus `*.lic`, `*.pem`, `*.key`, `.env*`.
- **Files modified:** .gitignore
- **Verification:** `git status --short` shows no stray build artifacts.
- **Committed in:** 23f367c

---

**Total deviations:** 2 auto-fixed (1 bicep type bug, 1 missing critical hygiene)
**Impact on plan:** Both essential. The BCP318 fix makes builds clean; the .gitignore prevents both ARM-output noise and accidental secret commits (T-1-04-03 mitigation).

## Issues Encountered

None. The recursion guard pattern from RESEARCH was used verbatim; the conditional module non-null operator was the only Bicep-version-specific tweak.

## Threat Model Compliance

All `mitigate` dispositions in the plan's threat register are satisfied or explicitly deferred to a downstream plan:

| Threat | Mitigation present | Deferred to |
|--------|--------------------|-------------|
| T-1-04-01 (spoofing across spoke subnets) | UDR forces 0/0 through FortiGate; src_addr objects bound to subnet names in policies.json | — |
| T-1-04-02 (UI bypass of config-as-code) | policies.json checked-in as source-of-truth; drift-detector contract documented in README | plan 08 (drift detector implementation) |
| T-1-04-03 (license leak) | License-via-KV pattern; `.gitignore` blocks `*.lic`; no plaintext blob in any module file | plan 09 (admin populates secret) |
| T-1-04-04 (single-NVA DoS) | Acknowledged risk per STACK.md; HA-pair upgrade path preserved | accepted at v1.0 |
| T-1-04-05 (default-allow before default-deny) | policies.json final entry IS `default-deny-all`; verified by python json acceptance test | — |
| T-1-04-06 (recursion guard removal) | Literal expression in spoke-vnet.bicep; documented in README | plan 08 (CODEOWNERS) |
| T-1-04-07 (syslog redirected to attacker) | `server` field is the literal `REPLACED_BY_DEPLOY_PIPELINE` placeholder; substituted from LA workspace resource id | plan 06 (LA workspace) + plan 08 (substitution CI step) |
| T-1-04-08 (deny events not logged) | Every policy has `logtraffic: "all"` | — |

## Threat Flags

None. No new security-relevant surface introduced beyond what the threat register already covers.

## User Setup Required

None at this plan boundary. Plan 09 will require a Gravity admin to populate the `fortigate-license` KV secret from the FortiCloud portal — that step is owned by plan 09's USER-SETUP, not this one.

## Self-Check: PASSED

Created files (verified to exist on disk):
- FOUND: infra/networking/main.bicep
- FOUND: infra/networking/main.dev.bicepparam
- FOUND: infra/networking/README.md
- FOUND: infra/networking/modules/hub-vnet.bicep
- FOUND: infra/networking/modules/spoke-vnet.bicep
- FOUND: infra/networking/modules/fortigate-vm.bicep
- FOUND: infra/networking/modules/nsg.bicep
- FOUND: infra/networking/modules/peering.bicep
- FOUND: infra/networking/modules/udr-policies.bicep
- FOUND: infra/networking/fortigate-config/policies.json
- FOUND: .gitignore

Commits (verified in git log):
- FOUND: 4b60cab (feat: bicep network sub-modules)
- FOUND: 5f7dc73 (feat: fortigate VM + config + orchestrator)
- FOUND: 23f367c (chore: gitignore)

## Next Plan Readiness

- Plan 05 (Key Vault + Storage) can consume `spokeSubnetIds.{data-subnet,pe-subnet}` from this plan's `main.bicep` outputs for SQL/KV/Storage private endpoints.
- Plan 06 (Log Analytics) can substitute the `REPLACED_BY_DEPLOY_PIPELINE` placeholder in `policies.json` once the LA workspace ingestion endpoint is known.
- Plan 08 (deploy pipeline + drift detector) consumes `policies.json` as the drift baseline and `fortigateTrustNicIp` (10.10.1.4) for egress rules.
- Plan 09 (verification) can issue synthetic `etl → anthropic` traffic and assert a deny event reaches LA.

**No blockers** — artifacts validate cleanly and are ready for downstream plans.

---
*Phase: 01-network-data-foundations*
*Plan: 04*
*Completed: 2026-05-02*
