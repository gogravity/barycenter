// Dev parameter file for the network orchestrator.
// keyVaultResourceId placeholder is replaced after plan 05 deploys the KV.
// Bicep what-if can run before that with placeholder; az deployment group create
// must wait for plan 05.

using 'main.bicep'

param location = 'eastus2'
param hubVnetName = 'vnet-bary-hub'
param spokeVnetName = 'vnet-bary-spoke'
param keyVaultResourceId = '/subscriptions/PLACEHOLDER/resourceGroups/rg-barycenter-data/providers/Microsoft.KeyVault/vaults/kv-bary-dev'
param deployFortigate = true
param fortigateTrustNicIp = '10.10.1.4'
param fortigateVmSize = 'Standard_F4s_v2'
param adminSshPublicKey = readEnvironmentVariable('FGT_ADMIN_SSH_PUBLIC_KEY', 'ssh-rsa PLACEHOLDER')
param spokeSubnets = [
  { name: 'etl-subnet',      cidr: '10.20.0.0/26' }
  { name: 'services-subnet', cidr: '10.20.0.64/26' }
  { name: 'data-subnet',     cidr: '10.20.0.128/27' }
  { name: 'pe-subnet',       cidr: '10.20.0.160/27' }
  { name: 'admin-subnet',    cidr: '10.20.1.0/27' }
]
param tags = {
  project: 'barycenter'
  env: 'dev'
  'managed-by': 'bicep'
  phase: '01-network-data-foundations'
}
