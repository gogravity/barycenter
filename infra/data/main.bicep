// Phase 01 / Plan 05 — data plane orchestrator. Wires Azure SQL Serverless + Key Vault
// behind private endpoints, then runs the SQL DDL + grants + chain genesis seed via a
// deployment script.
//
// Inputs from upstream plans:
// - Plan 03 outputs: principalIds for the 4 canonical MIs + deploy MI
// - Plan 04 outputs: spokeSubnetIds.{data, pe}
// - OIDC bootstrap evidence (plan 02): deploy MI resource ID

targetScope = 'resourceGroup'

@description('Azure region')
param location string

@description('SQL logical server name')
param sqlServerName string = 'sql-bary-dev'

@description('Key Vault name')
param keyVaultName string = 'kv-bary-dev'

@description('Resource ID of the spoke data subnet (SQL PE target)')
param dataSubnetId string

@description('Resource ID of the spoke pe subnet (KV PE target)')
param peSubnetId string

@description('Optional private DNS zone resource ID for privatelink.database.windows.net')
param sqlPrivateDnsZoneId string = ''

@description('Optional private DNS zone resource ID for privatelink.vaultcore.azure.net')
param kvPrivateDnsZoneId string = ''

@description('PrincipalId of mi-bary-etl')
param etlPrincipalId string

@description('PrincipalId of mi-bary-platform')
param platformPrincipalId string

@description('PrincipalId of mi-bary-audit')
param auditPrincipalId string

@description('PrincipalId of mi-bary-admin')
param adminPrincipalId string

@description('PrincipalId of mi-bary-deploy (KV Administrator + deploy script identity)')
param deployPrincipalId string

@description('System-assigned principalId of the FortiGate VM (Secrets User on license secret); leave empty until plan 04 wires the FGT VM')
param fortigateVmPrincipalId string = ''

@description('SQL admin Entra group display name (e.g. sg-bary-sql-admins)')
param adminLoginName string

@description('SQL admin Entra group object ID')
param adminLoginObjectId string

@description('Resource ID of mi-bary-deploy (used as user-assigned identity on the deployment script)')
param deployIdentityResourceId string

@description('Storage account name for the deploy-script transient container (created by CI workflow before deploy)')
param scriptStorageAccountName string

@description('SAS URI to the deploy-script transient blob container (issued by CI workflow at deploy time)')
@secure()
param scriptContainerSasUri string

@description('Tags applied to all resources')
param tags object

module sql 'modules/sql-serverless.bicep' = {
  name: 'sql-serverless'
  params: {
    location: location
    sqlServerName: sqlServerName
    adminLoginName: adminLoginName
    adminLoginObjectId: adminLoginObjectId
    tags: tags
  }
}

module kv 'modules/key-vault.bicep' = {
  name: 'key-vault'
  params: {
    location: location
    vaultName: keyVaultName
    etlPrincipalId: etlPrincipalId
    fortigateVmPrincipalId: fortigateVmPrincipalId
    deployPrincipalId: deployPrincipalId
    tags: tags
  }
}

module sqlPe 'modules/private-endpoint.bicep' = {
  name: 'sql-pe'
  params: {
    location: location
    peName: 'pe-${sqlServerName}'
    subnetId: dataSubnetId
    targetResourceId: sql.outputs.serverId
    groupId: 'sqlServer'
    privateDnsZoneId: sqlPrivateDnsZoneId
    tags: tags
  }
}

module kvPe 'modules/private-endpoint.bicep' = {
  name: 'kv-pe'
  params: {
    location: location
    peName: 'pe-${keyVaultName}'
    subnetId: peSubnetId
    targetResourceId: kv.outputs.vaultId
    groupId: 'vault'
    privateDnsZoneId: kvPrivateDnsZoneId
    tags: tags
  }
}

// Grants script depends on SQL + KV + both PEs because it must connect to SQL via the
// private endpoint to apply DDL + grants.
module grants 'modules/sql-grants-deploy-script.bicep' = {
  name: 'sql-grants'
  params: {
    location: location
    deployIdentityId: deployIdentityResourceId
    sqlServerFqdn: sql.outputs.serverFqdn
    etlPrincipalId: etlPrincipalId
    platformPrincipalId: platformPrincipalId
    auditPrincipalId: auditPrincipalId
    adminPrincipalId: adminPrincipalId
    scriptStorageAccountName: scriptStorageAccountName
    scriptContainerSasUri: scriptContainerSasUri
    tags: tags
  }
  dependsOn: [
    sqlPe
    kvPe
  ]
}

output sqlServerId string = sql.outputs.serverId
output sqlServerFqdn string = sql.outputs.serverFqdn
output keyVaultId string = kv.outputs.vaultId
output keyVaultUri string = kv.outputs.vaultUri
output saltKeyId string = kv.outputs.saltKeyId
output fortigateLicenseSecretUri string = kv.outputs.fortigateLicenseSecretUri
