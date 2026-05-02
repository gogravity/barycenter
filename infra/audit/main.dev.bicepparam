using 'main.bicep'

param location = 'eastus2'
param workspaceName = 'log-bary-dev'
param dcrName = 'dcr-bary-audit-dev'
param dceName = 'dce-bary-audit-dev'
param wormStorageAccountName = 'stbarywormdev'
param wormStorageTestAccountName = readEnvironmentVariable('WORM_TEST_STORAGE_NAME', 'stbarywormtest1')
param sqlServerId = readEnvironmentVariable('SQL_SERVER_ID', '')
param sqlDatabaseId = readEnvironmentVariable('SQL_DATABASE_ID', '')
param keyVaultId = readEnvironmentVariable('KEY_VAULT_ID', '')
param auditPrincipalId = readEnvironmentVariable('AUDIT_PRINCIPAL_ID', '')
param tags = {
  project: 'barycenter'
  env: 'dev'
  'managed-by': 'bicep'
  phase: '01-network-data-foundations'
}
