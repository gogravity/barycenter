using 'main.bicep'

param location = 'eastus2'
param acrName = 'acrbarydev'
param caeName = 'cae-bary-dev'
param cajName = 'caj-bary-etl'

// Networking (plan 04) — jobs-subnet resource ID
param jobsSubnetId = readEnvironmentVariable('JOBS_SUBNET_ID', '')

// Identity (plan 03)
param etlPrincipalId    = readEnvironmentVariable('ETL_PRINCIPAL_ID', '')
param etlClientId       = readEnvironmentVariable('AZURE_ETL_CLIENT_ID', '')
param etlIdentityResourceId = readEnvironmentVariable('ETL_IDENTITY_RESOURCE_ID', '')
param deployPrincipalId = readEnvironmentVariable('DEPLOY_PRINCIPAL_ID', '')

// Data + audit plane endpoints (plans 05, 09)
param keyVaultUrl        = readEnvironmentVariable('KEY_VAULT_URL', '')
param sqlConnectionString = readEnvironmentVariable('SQL_CONNECTION_STRING', '')
param dceEndpoint        = readEnvironmentVariable('DCE_LOGS_INGESTION_ENDPOINT', '')
param dcrImmutableId     = readEnvironmentVariable('DCR_IMMUTABLE_ID', '')
param wormAppendBlobUrl  = readEnvironmentVariable('WORM_APPEND_BLOB_URL', '')

param tags = {
  project: 'barycenter'
  env: 'dev'
  'managed-by': 'bicep'
  phase: '03-etl-container-jobs'
}
