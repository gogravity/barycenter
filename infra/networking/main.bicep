// Network orchestrator: hub VNet + FortiGate + spoke VNet + peering + NSGs + UDR overlay stub.
//
// Module wiring order (must hold):
//   1. hub-vnet            (provides untrust/trust subnet ids)
//   2. nsg                 (one default NSG attached to spoke subnets via spoke-vnet)
//   3. fortigate-vm        (depends on hub subnets)
//   4. spoke-vnet          (depends on FortiGate trust NIC IP for UDR next-hop)
//   5. peering hub<->spoke (depends on both vnets existing)
//   6. udr-policies        (stub — reserved for future overlay routes)
//
// Cross-plan dependencies:
// - keyVaultResourceId is populated by plan 05 (KV creation); set deployFortigate=false
//   if running this template before plan 05 has deployed the KV.
// - The 'fortigate-license' secret is populated by an admin in plan 09 from the KV portal;
//   it never enters this repo or GitHub Secrets.

targetScope = 'resourceGroup'

@description('Azure region for all resources.')
param location string = resourceGroup().location

@description('Hub VNet name.')
param hubVnetName string = 'vnet-bary-hub'

@description('Spoke VNet name.')
param spokeVnetName string = 'vnet-bary-spoke'

@description('Resource id of the Key Vault holding the fortigate-license secret. Placeholder until plan 05 deploys KV.')
param keyVaultResourceId string = ''

@description('Whether to deploy the FortiGate VM. Set false to deploy hub+spoke skeleton before KV exists.')
param deployFortigate bool = true

@description('SSH public key for FortiGate admin access.')
@secure()
param adminSshPublicKey string

@description('Spoke subnet definitions (array of {name, cidr}).')
param spokeSubnets array = [
  { name: 'etl-subnet',      cidr: '10.20.0.0/26' }
  { name: 'services-subnet', cidr: '10.20.0.64/26' }
  { name: 'data-subnet',     cidr: '10.20.0.128/27' }
  { name: 'pe-subnet',       cidr: '10.20.0.160/27' }
  { name: 'admin-subnet',    cidr: '10.20.1.0/27' }
]

@description('FortiGate trust NIC IP — also the next-hop for spoke UDRs.')
param fortigateTrustNicIp string = '10.10.1.4'

@description('Tags propagated to all created resources.')
param tags object = {}

module hub 'modules/hub-vnet.bicep' = {
  name: 'hub-vnet-deploy'
  params: {
    location: location
    vnetName: hubVnetName
    tags: tags
  }
}

module spokeNsg 'modules/nsg.bicep' = {
  name: 'spoke-nsg-deploy'
  params: {
    location: location
    nsgName: 'nsg-${spokeVnetName}'
    tags: tags
  }
}

module fortigate 'modules/fortigate-vm.bicep' = if (deployFortigate) {
  name: 'fortigate-vm-deploy'
  params: {
    location: location
    untrustSubnetId: hub.outputs.untrustSubnetId
    trustSubnetId: hub.outputs.trustSubnetId
    trustNicIp: fortigateTrustNicIp
    keyVaultResourceId: keyVaultResourceId
    adminSshPublicKey: adminSshPublicKey
    tags: tags
  }
}

module spoke 'modules/spoke-vnet.bicep' = {
  name: 'spoke-vnet-deploy'
  params: {
    location: location
    vnetName: spokeVnetName
    subnets: spokeSubnets
    fortigateTrustNicIp: fortigateTrustNicIp
    nsgId: spokeNsg.outputs.nsgId
    tags: tags
  }
  // Spoke depends on FortiGate so the trust NIC exists at the static IP referenced
  // by the UDR. When deployFortigate=false, the operator must ensure something
  // else owns 10.10.1.4 before peering completes.
  dependsOn: deployFortigate ? [
    fortigate
  ] : []
}

module peering 'modules/peering.bicep' = {
  name: 'hub-spoke-peering-deploy'
  params: {
    hubVnetName: hub.outputs.vnetName
    spokeVnetName: spoke.outputs.vnetName
    hubVnetId: hub.outputs.vnetId
    spokeVnetId: spoke.outputs.vnetId
  }
}

module udrOverlay 'modules/udr-policies.bicep' = {
  name: 'udr-overlay-deploy'
  params: {
    location: location
    tags: tags
  }
}

output hubVnetId string = hub.outputs.vnetId
output spokeVnetId string = spoke.outputs.vnetId
output fortigateVmId string = deployFortigate ? fortigate!.outputs.vmId : ''
output fortigateTrustNicIp string = fortigateTrustNicIp
output spokeSubnetIds object = spoke.outputs.subnetIds
