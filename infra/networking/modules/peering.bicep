// Bidirectional VNet peering between hub and spoke.
// AllowForwardedTraffic must be true so traffic transiting the FortiGate
// (which has different src IP than the originating subnet) is permitted.

@description('Hub VNet name (parent for hub-side peering).')
param hubVnetName string

@description('Spoke VNet name (parent for spoke-side peering).')
param spokeVnetName string

@description('Hub VNet resource id.')
param hubVnetId string

@description('Spoke VNet resource id.')
param spokeVnetId string

resource hubVnet 'Microsoft.Network/virtualNetworks@2024-01-01' existing = {
  name: hubVnetName
}

resource spokeVnet 'Microsoft.Network/virtualNetworks@2024-01-01' existing = {
  name: spokeVnetName
}

resource hubToSpoke 'Microsoft.Network/virtualNetworks/virtualNetworkPeerings@2024-01-01' = {
  parent: hubVnet
  name: 'peer-hub-to-spoke'
  properties: {
    allowForwardedTraffic: true
    allowVirtualNetworkAccess: true
    useRemoteGateways: false
    allowGatewayTransit: false
    remoteVirtualNetwork: {
      id: spokeVnetId
    }
  }
}

resource spokeToHub 'Microsoft.Network/virtualNetworks/virtualNetworkPeerings@2024-01-01' = {
  parent: spokeVnet
  name: 'peer-spoke-to-hub'
  properties: {
    allowForwardedTraffic: true
    allowVirtualNetworkAccess: true
    useRemoteGateways: false
    allowGatewayTransit: false
    remoteVirtualNetwork: {
      id: hubVnetId
    }
  }
}

output hubToSpokePeeringId string = hubToSpoke.id
output spokeToHubPeeringId string = spokeToHub.id
