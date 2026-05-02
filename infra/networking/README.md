# Barycenter — networking (FortiGate hub-and-spoke)

## Topology

Hub-and-spoke with FortiGate-VM02 as inline NVA. CIDRs:

- Hub VNet `10.10.0.0/22` — subnets: `untrust` (10.10.0.0/24), `trust` (10.10.1.0/24), `GatewaySubnet` (10.10.2.0/27).
- Spoke VNet `10.20.0.0/22` — subnets:
  - `etl-subnet`      `10.20.0.0/26`   — Phase 2+ ETL workers
  - `services-subnet` `10.20.0.64/26`  — Phase 3+ gateway/dispatcher
  - `data-subnet`     `10.20.0.128/27` — Azure SQL private endpoint NIC
  - `pe-subnet`       `10.20.0.160/27` — Key Vault + Storage private endpoints
  - `admin-subnet`    `10.20.1.0/27`   — PIM JIT bastion

FortiGate VM is `Standard_F2s_v2` running FortiGate-VM02 BYOL (FortiOS 7.4+). Trust NIC IP is statically assigned as `10.10.1.4` because spoke UDRs use it as the next hop.

## Recursion guard (CRITICAL)

`pe-subnet` and `data-subnet` get `routeTable: null`. Otherwise SQL/KV/Storage private link traffic would be forced through the FortiGate trust NIC, creating an infinite routing loop on private endpoint traffic — see project `ARCHITECTURE.md` §1.

The literal expression in `modules/spoke-vnet.bicep` is:

```bicep
routeTable: (contains(s.name, 'pe-') || contains(s.name, 'data-')) ? null : { id: udr.id }
```

`CODEOWNERS` protects this file. Any what-if diff that adds a route table to a `pe-` or `data-` subnet must be rejected (T-1-04-06 in the threat register).

## FortiGate license

BYOL license is stored in Key Vault as a secret named `fortigate-license`. The placeholder secret is created in plan 05; an admin populates it from the KV portal in plan 09. The plaintext `.lic` never enters git or GitHub Secrets.

The FortiGate VM's system-assigned identity is granted `Key Vault Secrets User` on the KV in plan 05. Post-deploy CI step (executed by `mi-bary-deploy` via OIDC):

```bash
LICENSE_B64=$(az keyvault secret show \
  --vault-name kv-bary-dev --name fortigate-license \
  --query value -o tsv)
echo "$LICENSE_B64" | base64 -d > /tmp/license.lic
az vm run-command invoke \
  --resource-group rg-barycenter-dev --name vm-fgt-bary-01 \
  --command-id RunShellScript \
  --scripts "fgt-cli execute restore license tftp:/tmp/license.lic"
shred -u /tmp/license.lic
```

## Config-as-code (NETW-01)

All FortiGate firewall rules live in `fortigate-config/policies.json`. The plan-08 drift detector (`scripts/ci/fortigate_drift.py`) reads this file and diffs it against the live FortiGate REST API output (`GET /api/v2/cmdb/firewall/policy` and `GET /api/v2/cmdb/firewall/address`). Manual edits via the FortiGate web UI are caught and revoked nightly. CODEOWNERS requires `@gravity/barycenter-infra` review on any `policies.json` change.

Initial rule set (this plan):

| Rule | src | dst | action | requirement |
|------|-----|-----|--------|-------------|
| `etl-to-anthropic-deny`        | etl-subnet      | anthropic-api    | deny   | EGRESS-01 |
| `services-to-source-tools-deny`| services-subnet | cw-manage        | deny   | EGRESS-01 |
| `services-to-anthropic-allow`  | services-subnet | anthropic-api    | accept | gateway IS allowed |
| `etl-to-source-tools-allow`    | etl-subnet      | cw-manage        | accept | ETL IS allowed |
| `spoke-to-azure-mgmt-allow`    | etl + services  | azure-arm/monitor| accept | telemetry/control plane |
| `default-deny-all`             | any             | any              | deny   | belt-and-braces |

Last entry must remain `default-deny-all`. Acceptance test in plan 09 asserts this.

## Syslog → Log Analytics (NETW-03)

`policies.json` contains a `syslog` block with target IP `REPLACED_BY_DEPLOY_PIPELINE`. Plan 06's deploy pipeline substitutes this with the LA workspace's syslog ingestion endpoint resource id before pushing the config to the FortiGate. The substitution is a CI step, not a free-form parameter, so an attacker cannot redirect logs to a different host (T-1-04-07).

Every policy sets `logtraffic: "all"`, so deny events are logged with full match metadata (T-1-04-08). Plan 09 verifies a deny event reaches LA after issuing a synthetic `etl → anthropic` request.

## Deploy

```bash
# What-if (always safe)
az deployment group what-if \
  --resource-group rg-barycenter-dev \
  --template-file infra/networking/main.bicep \
  --parameters infra/networking/main.dev.bicepparam

# Apply (run by mi-bary-deploy via GitHub Actions OIDC, plan 08)
az deployment group create \
  --resource-group rg-barycenter-dev \
  --template-file infra/networking/main.bicep \
  --parameters infra/networking/main.dev.bicepparam
```

Set `param deployFortigate = false` to deploy hub+spoke before the KV exists; re-run with `true` after plan 05 has deployed the KV and `keyVaultResourceId` has been updated.

## Cross-plan dependencies

- **Requires plan 05's KV** for the `fortigate-license` secret. Either deploy plan 05 first, or deploy this with `deployFortigate=false` and re-run after plan 05.
- **Provides** `spokeSubnetIds.{data-subnet,pe-subnet}` consumed by plan 05 for SQL / KV / Storage private endpoints.
- **Provides** `spokeSubnetIds.{etl-subnet,services-subnet}` consumed by Phase 2/3 Container Apps environments.
- **Provides** `fortigateTrustNicIp` (10.10.1.4) — referenced by plan 08's drift-detector container egress rules.
