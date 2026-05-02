// Default NSG for spoke subnets.
// Rule 100 (Deny): block any inbound from Internet — spoke must only be
// reachable via the FortiGate trust path.
// Rule 200 (Allow): permit intra-VNet traffic.

@description('Azure region for the NSG.')
param location string = resourceGroup().location

@description('NSG name.')
param nsgName string

@description('Tags propagated to the NSG.')
param tags object = {}

resource nsg 'Microsoft.Network/networkSecurityGroups@2024-01-01' = {
  name: nsgName
  location: location
  tags: tags
  properties: {
    securityRules: [
      {
        name: 'deny-inbound-from-internet'
        properties: {
          priority: 100
          direction: 'Inbound'
          access: 'Deny'
          protocol: '*'
          sourceAddressPrefix: 'Internet'
          sourcePortRange: '*'
          destinationAddressPrefix: '*'
          destinationPortRange: '*'
        }
      }
      {
        name: 'allow-vnet-inbound'
        properties: {
          priority: 200
          direction: 'Inbound'
          access: 'Allow'
          protocol: '*'
          sourceAddressPrefix: 'VirtualNetwork'
          sourcePortRange: '*'
          destinationAddressPrefix: 'VirtualNetwork'
          destinationPortRange: '*'
        }
      }
    ]
  }
}

output nsgId string = nsg.id
output nsgName string = nsg.name
