// Audit substrate orchestrator.
// Deploys: LA workspace + AuditEvents_CL custom table, WORM container (locked 2190-day),
// optional test WORM container (deploy first; manually validated then deleted before
// prod lock per Pitfall 7), DCE + DCR, and diagnostic settings on SQL/KV/Storage.
//
// Wave-2 dependency: depends on plans 01 (RG), 02 (OIDC for deploy), 03 (networking),
// 04 (FortiGate — its policies.json gets the LA endpoint substituted in by the deploy
// pipeline post-deploy), 05 (SQL DB + KV — diagnostic targets).

targetScope = 'resourceGroup'

@description('Azure region')
param location string

@description('Log Analytics workspace name')
param workspaceName string = 'log-bary-dev'

@description('Data Collection Rule name')
param dcrName string = 'dcr-bary-audit-dev'

@description('Data Collection Endpoint name')
param dceName string = 'dce-bary-audit-dev'

@description('Production WORM storage account name')
param wormStorageAccountName string = 'stbarywormdev'

@description('Test WORM storage account name (Pitfall 7). Empty disables.')
param wormStorageTestAccountName string = ''

@description('SQL Server resource ID for diagnostic settings. Empty skips.')
param sqlServerId string = ''

@description('SQL Database resource ID for diagnostic settings. Empty skips.')
param sqlDatabaseId string = ''

@description('Key Vault resource ID for diagnostic settings. Empty skips.')
param keyVaultId string = ''

@description('Principal ID of mi-bary-audit (DCR + WORM access)')
param auditPrincipalId string

@description('Tags applied to all resources')
param tags object = {}

module la 'modules/log-analytics.bicep' = {
  name: 'audit-la-deploy'
  params: {
    location: location
    workspaceName: workspaceName
    tags: tags
  }
}

// Pitfall 7: deploy first, validate lock, observe shorten refusal, delete account,
// THEN deploy wormProd. Toggle by setting wormStorageTestAccountName empty after validation.
module wormTest 'modules/worm-storage-test.bicep' = if (!empty(wormStorageTestAccountName)) {
  name: 'audit-worm-test-deploy'
  params: {
    location: location
    storageAccountName: wormStorageTestAccountName
    tags: tags
  }
}

module wormProd 'modules/worm-storage.bicep' = {
  name: 'audit-worm-prod-deploy'
  params: {
    location: location
    storageAccountName: wormStorageAccountName
    tags: tags
  }
  dependsOn: [
    la
  ]
}

module dcr 'modules/data-collection-rule.bicep' = {
  name: 'audit-dcr-deploy'
  params: {
    location: location
    dcrName: dcrName
    dceName: dceName
    workspaceResourceId: la.outputs.workspaceResourceId
    auditPrincipalId: auditPrincipalId
    tags: tags
  }
}

module diag 'modules/diagnostic-settings.bicep' = {
  name: 'audit-diag-deploy'
  params: {
    workspaceResourceId: la.outputs.workspaceResourceId
    sqlServerId: sqlServerId
    sqlDatabaseId: sqlDatabaseId
    keyVaultId: keyVaultId
    wormStorageAccountId: wormProd.outputs.storageAccountId
    auditPrincipalId: auditPrincipalId
  }
  dependsOn: [
    la
    wormProd
  ]
}

output workspaceId string = la.outputs.workspaceId
output workspaceCustomerId string = la.outputs.workspaceCustomerId
output dcrId string = dcr.outputs.dcrId
output dcrImmutableId string = dcr.outputs.dcrImmutableId
output dceLogsIngestionEndpoint string = dcr.outputs.dceLogsIngestionEndpoint
output dcrStreamName string = dcr.outputs.streamName
output wormStorageAccountId string = wormProd.outputs.storageAccountId
output wormContainerName string = wormProd.outputs.containerName
// FortiGate syslog target IP/endpoint substituted into infra/networking/fortigate-config/policies.json
// at deploy-time (REPLACED_BY_DEPLOY_PIPELINE marker → this output).
output fortigateSyslogTargetEndpoint string = dcr.outputs.dceLogsIngestionEndpoint
