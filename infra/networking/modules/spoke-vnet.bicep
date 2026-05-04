// Spoke VNet with FortiGate-default UDR and recursion guard.
// Pattern verbatim from 01-RESEARCH.md §Code Example A.
//
// CRITICAL: subnets named with substring 'pe-' or 'data-' get routeTable: null.
// Forcing PE subnet traffic through the FortiGate creates an infinite routing
// loop on private link — see project ARCHITECTURE.md §1.

@description('Azure region for the spoke VNet.')
param location string = resourceGroup().location

@description('Spoke VNet name.')
param vnetName string

@description('Spoke VNet CIDR (default 10.20.0.0/22).')
param vnetCidr string = '10.20.0.0/22'

@description('Subnets to create (array of {name, cidr} or {name, cidr, delegation}).')
param subnets array

@description('FortiGate trust NIC IP — UDR next hop.')
param fortigateTrustNicIp string = '10.10.1.4'

@description('NSG resource id to attach to non-PE/data subnets (optional, defaults to empty).')
param nsgId string = ''

@description('Tags propagated to created resources.')
param tags object = {}

resource udr 'Microsoft.Network/routeTables@2024-01-01' = {
  name: 'rt-${vnetName}-fgt'
  location: location
  tags: tags
  properties: {
    routes: [
      {
        name: 'default-via-fortigate'
        properties: {
          addressPrefix: '0.0.0.0/0'
          nextHopType: 'VirtualAppliance'
          nextHopIpAddress: fortigateTrustNicIp
        }
      }
    ]
  }
}

resource vnet 'Microsoft.Network/virtualNetworks@2024-01-01' = {
  name: vnetName
  location: location
  tags: tags
  properties: {
    addressSpace: {
      addressPrefixes: [ vnetCidr ]
    }
    subnets: [for s in subnets: {
      name: s.name
      properties: {
        addressPrefix: s.cidr
        // Recursion guard: PE, data, and delegated subnets must NOT route 0/0
        // through the FortiGate. Delegated subnets (e.g. Container Apps) need
        // direct egress for Azure control-plane management traffic.
        routeTable: (contains(s.name, 'pe-') || contains(s.name, 'data-') || contains(s, 'delegation')) ? null : {
          id: udr.id
        }
        networkSecurityGroup: empty(nsgId) ? null : {
          id: nsgId
        }
        privateEndpointNetworkPolicies: (contains(s.name, 'pe-') || contains(s.name, 'data-')) ? 'Disabled' : 'Enabled'
        delegations: contains(s, 'delegation') ? [
          {
            name: 'delegation'
            properties: { serviceName: s.delegation }
          }
        ] : []
        // Optional service endpoints (e.g. Microsoft.Storage for deploy-script-subnet)
        serviceEndpoints: contains(s, 'serviceEndpoints') ? map(s.serviceEndpoints, svc => {
          service: svc
        }) : []
      }
    }]
  }
}

output vnetId string = vnet.id
output vnetName string = vnet.name
output udrId string = udr.id
output subnetIds object = toObject(subnets, s => s.name, s => '${vnet.id}/subnets/${s.name}')
