// Phase 03 — jobs plane orchestrator.
// Provisions ACR (ETL image store) + Container Apps Job (VNet-injected ETL runner).
//
// Depends on:
// - Plan 03 (identity): etlPrincipalId, deployPrincipalId, etlIdentityResourceId
// - Plan 04 (networking): jobsSubnetId
// - Plan 05 (data): keyVaultUrl, sqlConnectionString, dceEndpoint, dcrImmutableId
// - Plan 09 (audit): wormAppendBlobUrl

targetScope = 'resourceGroup'

@description('Azure region')
param location string

@description('ACR name (5-50 lowercase alphanumeric, globally unique)')
param acrName string = 'acrbarydev'

@description('Container Apps Environment name')
param caeName string = 'cae-bary-dev'

@description('Container Apps Job name')
param cajName string = 'caj-bary-etl'

@description('Resource ID of the jobs-subnet (delegated to Microsoft.App/environments)')
param jobsSubnetId string

@description('Principal ID of mi-bary-etl')
param etlPrincipalId string

@description('Client ID of mi-bary-etl (injected as AZURE_CLIENT_ID in the CAJ container)')
param etlClientId string

@description('Resource ID of mi-bary-etl')
param etlIdentityResourceId string

@description('Principal ID of mi-bary-audit (audit.chain_state access)')
param auditPrincipalId string

@description('Client ID of mi-bary-audit (injected as AUDIT_CLIENT_ID in the CAJ container)')
param auditClientId string

@description('Resource ID of mi-bary-audit (second user-assigned identity on the CAJ)')
param auditIdentityResourceId string

@description('Principal ID of mi-bary-deploy (AcrPush for CI builds)')
param deployPrincipalId string

@description('Key Vault URL')
param keyVaultUrl string

@description('SQL connection string (ActiveDirectoryMsi — no password)')
param sqlConnectionString string

@description('DCE logs ingestion endpoint')
param dceEndpoint string

@description('DCR immutable ID')
param dcrImmutableId string

@description('WORM append blob URL')
param wormAppendBlobUrl string

@description('Tags applied to all resources')
param tags object

// Built-in Contributor role
// https://learn.microsoft.com/azure/role-based-access-control/built-in-roles
var contributorRoleId = 'b24988ac-6180-42a0-ab88-20f7382dd24c'

// mi-bary-etl needs Contributor at RG scope to manage the CAJ (update image, start
// executions, poll status). Microsoft.App/jobs does not support resource-level RBAC
// — az role assignment create at the job or CAE resource scope returns 400 Bad Request.
// AcrPull/AcrPush on ACR + data-plane KV/SQL roles are unaffected by this RG grant.
resource etlRgContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(resourceGroup().id, etlPrincipalId, contributorRoleId)
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', contributorRoleId)
    principalId: etlPrincipalId
    principalType: 'ServicePrincipal'
  }
}

module acr 'modules/container-registry.bicep' = {
  name: 'container-registry'
  params: {
    location: location
    acrName: acrName
    etlPrincipalId: etlPrincipalId
    deployPrincipalId: deployPrincipalId
    tags: tags
  }
}

module caj 'modules/container-apps-job.bicep' = {
  name: 'container-apps-job'
  params: {
    location: location
    caeName: caeName
    cajName: cajName
    jobsSubnetId: jobsSubnetId
    etlIdentityResourceId: etlIdentityResourceId
    etlClientId: etlClientId
    auditIdentityResourceId: auditIdentityResourceId
    auditClientId: auditClientId
    acrLoginServer: acr.outputs.acrLoginServer
    keyVaultUrl: keyVaultUrl
    sqlConnectionString: sqlConnectionString
    dceEndpoint: dceEndpoint
    dcrImmutableId: dcrImmutableId
    wormAppendBlobUrl: wormAppendBlobUrl
    tags: tags
  }
}

output acrName string = acr.outputs.acrName
output acrLoginServer string = acr.outputs.acrLoginServer
output cajName string = caj.outputs.cajName
