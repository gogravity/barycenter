// Hub VNet for FortiGate-anchored hub-and-spoke topology.
// CIDRs locked by 01-RESEARCH.md §System Architecture Diagram.

@description('Azure region for the hub VNet.')
param location string = resourceGroup().location

@description('Hub VNet name.')
param vnetName string = 'vnet-bary-hub'

@description('Hub VNet CIDR (default 10.10.0.0/22).')
param vnetCidr string = '10.10.0.0/22'

@description('Untrust subnet CIDR (default 10.10.0.0/24) — FortiGate untrust NIC lands here.')
param untrustSubnetCidr string = '10.10.0.0/24'

@description('Trust subnet CIDR (default 10.10.1.0/24) — FortiGate trust NIC lands here.')
param trustSubnetCidr string = '10.10.1.0/24'

@description('GatewaySubnet CIDR (default 10.10.2.0/27) — reserved for future ExpressRoute / VPN gateway.')
param gatewaySubnetCidr string = '10.10.2.0/27'

@description('Tags propagated to the VNet from the parent template.')
param tags object = {}

resource hubVnet 'Microsoft.Network/virtualNetworks@2024-01-01' = {
  name: vnetName
  location: location
  tags: tags
  properties: {
    addressSpace: {
      addressPrefixes: [ vnetCidr ]
    }
    subnets: [
      {
        name: 'untrust'
        properties: {
          addressPrefix: untrustSubnetCidr
        }
      }
      {
        name: 'trust'
        properties: {
          addressPrefix: trustSubnetCidr
        }
      }
      {
        name: 'GatewaySubnet'
        properties: {
          addressPrefix: gatewaySubnetCidr
        }
      }
    ]
  }
}

output vnetId string = hubVnet.id
output vnetName string = hubVnet.name
output untrustSubnetId string = '${hubVnet.id}/subnets/untrust'
output trustSubnetId string = '${hubVnet.id}/subnets/trust'
output gatewaySubnetId string = '${hubVnet.id}/subnets/GatewaySubnet'
