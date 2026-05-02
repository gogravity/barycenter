// AUDIT-03: WORM blob container with locked 6-year (2190-day) retention.
// Once locked (via `az storage container immutability-policy lock` after deploy),
// retention CANNOT be shortened by anyone — including subscription Owner.
// The test container (worm-storage-test.bicep) MUST be validated first per Pitfall 7.

targetScope = 'resourceGroup'

@description('Azure region')
param location string

@description('Storage account name (3-24 lowercase alphanumeric)')
@minLength(3)
@maxLength(24)
param storageAccountName string = 'stbarywormdev'

@description('Container name for audit events')
param containerName string = 'audit'

@description('Immutability retention in days (2190 = 6 years for HIPAA audit retention)')
param retentionDays int = 2190

@description('Tags applied to all resources')
param tags object = {}

resource storageAccount 'Microsoft.Storage/storageAccounts@2024-01-01' = {
  name: storageAccountName
  location: location
  tags: tags
  sku: {
    name: 'Standard_GRS'
  }
  kind: 'StorageV2'
  properties: {
    accessTier: 'Cool'
    allowBlobPublicAccess: false
    minimumTlsVersion: 'TLS1_2'
    publicNetworkAccess: 'Disabled'
    networkAcls: {
      defaultAction: 'Deny'
      bypass: 'AzureServices'
    }
    // Force AAD-only auth — no shared-key access (T-1-06-03).
    allowSharedKeyAccess: false
    supportsHttpsTrafficOnly: true
    encryption: {
      services: {
        blob: {
          enabled: true
        }
      }
      keySource: 'Microsoft.Storage'
    }
  }
}

resource blobServices 'Microsoft.Storage/storageAccounts/blobServices@2024-01-01' = {
  parent: storageAccount
  name: 'default'
  properties: {
    deleteRetentionPolicy: {
      enabled: false
    }
    containerDeleteRetentionPolicy: {
      enabled: false
    }
  }
}

resource auditContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2024-01-01' = {
  parent: blobServices
  name: containerName
  properties: {
    publicAccess: 'None'
    immutableStorageWithVersioning: {
      enabled: true
    }
  }
}

// Immutability policy. NOTE: deployed in 'Unlocked' state by ARM/Bicep.
// Once locked (via `az storage container immutability-policy lock --account-name ... --container-name audit`,
// after deploy), retention cannot be shortened. Test container (worm-storage-test.bicep)
// MUST be validated first per Pitfall 7.
resource immutabilityPolicy 'Microsoft.Storage/storageAccounts/blobServices/containers/immutabilityPolicies@2024-01-01' = {
  parent: auditContainer
  name: 'default'
  properties: {
    immutabilityPeriodSinceCreationInDays: 2190
    allowProtectedAppendWrites: true
  }
}

output storageAccountId string = storageAccount.id
output storageAccountName string = storageAccount.name
output containerName string = auditContainer.name
output blobEndpoint string = storageAccount.properties.primaryEndpoints.blob
output retentionDaysApplied int = retentionDays
