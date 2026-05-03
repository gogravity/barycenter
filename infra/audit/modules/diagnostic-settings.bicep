// Diagnostic settings forwarding SQL DB, Key Vault, and Storage logs to the LA workspace.
// AUDIT-01 source-of-truth coverage for KV sign ops, SQL audit, and audit-of-audit (AUDIT-02)
// when queries against the WORM storage account are themselves logged.
//
// Targets are referenced by resource ID rather than constructed here, so this module
// is reusable across environments and dependent resources can come from sibling templates
// (data plane, identity plane).

targetScope = 'resourceGroup'

@description('Resource ID of the Log Analytics workspace receiving diagnostics')
param workspaceResourceId string

@description('Resource ID of the SQL Server (parent of the audit DB). Empty string skips.')
param sqlServerId string = ''

@description('Resource ID of the SQL Database. Empty string skips.')
param sqlDatabaseId string = ''

@description('Resource ID of the Key Vault. Empty string skips.')
param keyVaultId string = ''

@description('Resource ID of the WORM storage account. Empty string skips.')
param wormStorageAccountId string = ''

@description('Principal ID of mi-bary-audit (granted Storage Blob Data Contributor on WORM)')
param auditPrincipalId string

// Built-in role: Storage Blob Data Contributor
// https://learn.microsoft.com/azure/role-based-access-control/built-in-roles#storage-blob-data-contributor
var storageBlobDataContributorRoleId = 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'

// ---- SQL Database diagnostic settings ----
// SQLSecurityAuditEvents: HIPAA §164.312(b) source-of-truth for DB access.
resource sqlDbExisting 'Microsoft.Sql/servers/databases@2023-08-01-preview' existing = if (!empty(sqlServerId) && !empty(sqlDatabaseId)) {
  name: '${last(split(sqlServerId, '/'))}/${last(split(sqlDatabaseId, '/'))}'
}

resource sqlDiag 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = if (!empty(sqlServerId) && !empty(sqlDatabaseId)) {
  scope: sqlDbExisting
  name: 'sql-to-la'
  properties: {
    workspaceId: workspaceResourceId
    logs: [
      // categoryGroup and category cannot be mixed in the same diagnostic setting.
      // Individual categories used here; SQLSecurityAuditEvents covers HIPAA §164.312(b).
      { category: 'SQLSecurityAuditEvents', enabled: true }
      { category: 'SQLInsights', enabled: true }
      { category: 'AutomaticTuning', enabled: true }
    ]
    metrics: [
      { category: 'AllMetrics', enabled: true }
    ]
  }
}

// ---- Key Vault diagnostic settings ----
// AuditEvent: every secret access + sign() call (FOUND-03 verification).
resource kvExisting 'Microsoft.KeyVault/vaults@2023-07-01' existing = if (!empty(keyVaultId)) {
  name: last(split(keyVaultId, '/'))
}

resource kvDiag 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = if (!empty(keyVaultId)) {
  scope: kvExisting
  name: 'kv-to-la'
  properties: {
    workspaceId: workspaceResourceId
    logs: [
      { category: 'AuditEvent', enabled: true }
      { category: 'AzurePolicyEvaluationDetails', enabled: true }
    ]
    metrics: [
      { category: 'AllMetrics', enabled: true }
    ]
  }
}

// ---- Storage account (WORM) diagnostic settings ----
// AUDIT-02: queries against WORM (audit log) are themselves logged.
resource wormStorageExisting 'Microsoft.Storage/storageAccounts@2024-01-01' existing = if (!empty(wormStorageAccountId)) {
  name: last(split(wormStorageAccountId, '/'))
}

resource wormStorageDiag 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = if (!empty(wormStorageAccountId)) {
  scope: wormStorageExisting
  name: 'worm-storage-to-la'
  properties: {
    workspaceId: workspaceResourceId
    metrics: [
      { category: 'Transaction', enabled: true }
    ]
  }
}

// Diagnostic settings on the blob services child for read/write/delete plane.
resource wormBlobDiag 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = if (!empty(wormStorageAccountId)) {
  scope: wormStorageBlobServices
  name: 'worm-blob-to-la'
  properties: {
    workspaceId: workspaceResourceId
    logs: [
      { category: 'StorageRead', enabled: true }
      { category: 'StorageWrite', enabled: true }
      { category: 'StorageDelete', enabled: true }
    ]
    metrics: [
      { category: 'Transaction', enabled: true }
    ]
  }
}

resource wormStorageBlobServices 'Microsoft.Storage/storageAccounts/blobServices@2024-01-01' existing = if (!empty(wormStorageAccountId)) {
  parent: wormStorageExisting
  name: 'default'
}

// ---- mi-bary-audit role assignment on WORM storage account ----
// T-1-06-03: scoped to specific account; allows append-block writes only via AAD.
resource auditWormRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(wormStorageAccountId)) {
  scope: wormStorageExisting
  name: guid(wormStorageAccountId, auditPrincipalId, storageBlobDataContributorRoleId)
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', storageBlobDataContributorRoleId)
    principalId: auditPrincipalId
    principalType: 'ServicePrincipal'
  }
}

output sqlDiagnosticId string = (!empty(sqlServerId) && !empty(sqlDatabaseId)) ? sqlDiag.id : ''
output kvDiagnosticId string = !empty(keyVaultId) ? kvDiag.id : ''
output storageDiagnosticId string = !empty(wormStorageAccountId) ? wormBlobDiag.id : ''
