// FOUND-01 + ENC-01: Azure SQL Serverless GP_S_Gen5_2 with private endpoint, AAD-only
// auth, TDE explicitly enabled. publicNetworkAccess Disabled from first commit
// (CLAUDE.md global rule). Consumed by infra/data/main.bicep.

@description('Azure region')
param location string

@description('SQL logical server name (e.g. sql-bary-dev)')
param sqlServerName string

@description('Entra security group display name granted SQL admin (PIM-eligible)')
param adminLoginName string

@description('Entra security group object ID for the SQL admin group')
param adminLoginObjectId string

@description('Tags applied to all resources')
param tags object

resource sqlServer 'Microsoft.Sql/servers@2024-05-01-preview' = {
  name: sqlServerName
  location: location
  tags: tags
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    publicNetworkAccess: 'Disabled'
    minimalTlsVersion: '1.2'
    administrators: {
      administratorType: 'ActiveDirectory'
      principalType: 'Group'
      login: adminLoginName
      sid: adminLoginObjectId
      tenantId: subscription().tenantId
      azureADOnlyAuthentication: true
    }
  }
}

resource sqlDatabase 'Microsoft.Sql/servers/databases@2024-05-01-preview' = {
  parent: sqlServer
  name: 'barycenter'
  location: location
  tags: tags
  sku: {
    name: 'GP_S_Gen5_2'
    tier: 'GeneralPurpose'
    family: 'Gen5'
    capacity: 2
  }
  properties: {
    autoPauseDelay: 60
    minCapacity: json('0.5')
    maxSizeBytes: 34359738368
    zoneRedundant: false
  }
}

// ENC-01: explicitly enable TDE. On by default since 2017 — declaring explicitly so
// the requirement is grep-verifiable in source and drift detector flags any change.
resource tde 'Microsoft.Sql/servers/databases/transparentDataEncryption@2024-05-01-preview' = {
  parent: sqlDatabase
  name: 'current'
  properties: {
    state: 'Enabled'
  }
}

output serverId string = sqlServer.id
output serverFqdn string = sqlServer.properties.fullyQualifiedDomainName
output databaseId string = sqlDatabase.id
output databaseName string = sqlDatabase.name
