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

@description('Resource ID of mi-bary-etl')
param etlIdentityResourceId string

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
