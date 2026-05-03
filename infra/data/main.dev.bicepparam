using 'main.bicep'

param location = 'eastus2'
param sqlLocation = 'centralus'
param sqlServerName = 'sql-bary-dev'
param keyVaultName = 'kv-bary-dev'
param dataSubnetId = readEnvironmentVariable('DATA_SUBNET_ID', '')
param peSubnetId = readEnvironmentVariable('PE_SUBNET_ID', '')
param sqlPrivateDnsZoneId = readEnvironmentVariable('SQL_PRIVATE_DNS_ZONE_ID', '')
param kvPrivateDnsZoneId = readEnvironmentVariable('KV_PRIVATE_DNS_ZONE_ID', '')
param etlPrincipalId = readEnvironmentVariable('ETL_PRINCIPAL_ID', '')
param platformPrincipalId = readEnvironmentVariable('PLATFORM_PRINCIPAL_ID', '')
param auditPrincipalId = readEnvironmentVariable('AUDIT_PRINCIPAL_ID', '')
param adminPrincipalId = readEnvironmentVariable('ADMIN_PRINCIPAL_ID', '')
param deployPrincipalId = readEnvironmentVariable('DEPLOY_PRINCIPAL_ID', '')
param fortigateVmPrincipalId = readEnvironmentVariable('FGT_VM_PRINCIPAL_ID', '')
param adminLoginName = 'sg-bary-sql-admins'
param adminLoginObjectId = readEnvironmentVariable('SQL_ADMIN_GROUP_OBJECT_ID', '')
param deployIdentityResourceId = readEnvironmentVariable('DEPLOY_IDENTITY_RESOURCE_ID', '')
param scriptStorageAccountName = readEnvironmentVariable('SCRIPT_STORAGE_ACCOUNT', '')
param scriptContainerSasUri = readEnvironmentVariable('SCRIPT_CONTAINER_SAS', '')
param tags = {
  project: 'barycenter'
  env: 'dev'
  'managed-by': 'bicep'
  phase: '01-network-data-foundations'
}
