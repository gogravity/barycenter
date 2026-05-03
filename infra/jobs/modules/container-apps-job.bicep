// Container Apps Environment (workload profiles, VNet-injected) + Manual-trigger Job
// for the nightly CW ETL. VNet injection gives the job full access to private endpoints
// (SQL, Key Vault, WORM storage) without punching holes in publicNetworkAccess.
//
// Trigger type: Manual — GitHub Actions (etl-cw-nightly.yml) starts the job via
// `az containerapp job start` after building and pushing the image. The CAJ schedule
// is driven by the GH Actions cron, not a CAJ schedule trigger, so the image is always
// fresh before each run.

targetScope = 'resourceGroup'

@description('Azure region')
param location string

@description('Container Apps Environment name')
param caeName string = 'cae-bary-dev'

@description('Container Apps Job name')
param cajName string = 'caj-bary-etl'

@description('Resource ID of the jobs-subnet (delegated to Microsoft.App/environments)')
param jobsSubnetId string

@description('Resource ID of mi-bary-etl (user-assigned identity on the job)')
param etlIdentityResourceId string

@description('ACR login server (e.g. acrbarydev.azurecr.io)')
param acrLoginServer string

@description('Key Vault URL (https://kv-bary-dev.vault.azure.net/)')
param keyVaultUrl string

@description('SQL connection string (no password — uses ActiveDirectoryMsi)')
param sqlConnectionString string

@description('DCE logs ingestion endpoint')
param dceEndpoint string

@description('DCR immutable ID')
param dcrImmutableId string

@description('WORM append blob URL (https://stbarywormdev.blob.core.windows.net/audit/audit.ndjson)')
param wormAppendBlobUrl string

@description('Tags applied to all resources')
param tags object = {}

// Workload profiles environment — minimum /27 subnet, supports VNet injection.
// Consumption workload profile: pay-per-execution, ~$0/mo for a nightly 5-min run.
resource cae 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: caeName
  location: location
  tags: tags
  properties: {
    vnetConfiguration: {
      infrastructureSubnetId: jobsSubnetId
      internal: true   // no public ingress — jobs only, no HTTP scale rules
    }
    workloadProfiles: [
      {
        name: 'Consumption'
        workloadProfileType: 'Consumption'
      }
    ]
  }
}

resource caj 'Microsoft.App/jobs@2024-03-01' = {
  name: cajName
  location: location
  tags: tags
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${etlIdentityResourceId}': {}
    }
  }
  properties: {
    environmentId: cae.id
    workloadProfileName: 'Consumption'
    configuration: {
      triggerType: 'Manual'
      manualTriggerConfig: {
        parallelism: 1
        replicaCompletionCount: 1
      }
      // Pull from ACR using the user-assigned managed identity (no stored credentials).
      registries: [
        {
          server: acrLoginServer
          identity: etlIdentityResourceId
        }
      ]
      // 15-minute timeout — CW API pages ~5 tables; 5 min is typical, 15 is safe.
      replicaTimeout: 900
      replicaRetryLimit: 1
    }
    template: {
      containers: [
        {
          name: 'etl'
          // etl-cw-nightly.yml tags the image with the commit SHA then updates this
          // job's image before starting it, so the job always runs the current build.
          image: '${acrLoginServer}/barycenter-etl:latest'
          env: [
            { name: 'KEY_VAULT_URL',             value: keyVaultUrl }
            { name: 'SQL_CONNECTION_STRING',      value: sqlConnectionString }
            { name: 'CW_AUTH_MODE',               value: 'basic' }
            { name: 'DCE_LOGS_INGESTION_ENDPOINT', value: dceEndpoint }
            { name: 'DCR_IMMUTABLE_ID',           value: dcrImmutableId }
            { name: 'WORM_APPEND_BLOB_URL',       value: wormAppendBlobUrl }
          ]
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
        }
      ]
    }
  }
}

output caeId string = cae.id
output cajId string = caj.id
output cajName string = caj.name
