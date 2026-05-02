// Generic private endpoint module. Used by main.bicep to land SQL and KV PEs onto the
// spoke subnets defined by plan 04 (data-subnet for SQL, pe-subnet for KV).

@description('Azure region')
param location string

@description('Private endpoint resource name')
param peName string

@description('Resource ID of the subnet to land the PE NIC into')
param subnetId string

@description('Resource ID of the target resource (SQL server, KV, etc.)')
param targetResourceId string

@description('Subresource group ID — sqlServer | vault | blob | etc.')
param groupId string

@description('Optional private DNS zone resource ID; leave empty to skip zone group registration')
param privateDnsZoneId string = ''

@description('Tags applied to all resources')
param tags object

resource pe 'Microsoft.Network/privateEndpoints@2024-01-01' = {
  name: peName
  location: location
  tags: tags
  properties: {
    subnet: {
      id: subnetId
    }
    privateLinkServiceConnections: [
      {
        name: '${peName}-conn'
        properties: {
          privateLinkServiceId: targetResourceId
          groupIds: [
            groupId
          ]
        }
      }
    ]
  }
}

resource peDnsZoneGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2024-01-01' = if (!empty(privateDnsZoneId)) {
  parent: pe
  name: 'default'
  properties: {
    privateDnsZoneConfigs: [
      {
        name: 'default'
        properties: {
          privateDnsZoneId: privateDnsZoneId
        }
      }
    ]
  }
}

output peId string = pe.id
output peName string = pe.name
output peNicIp string = length(pe.properties.networkInterfaces) > 0 ? pe.properties.networkInterfaces[0].id : ''
