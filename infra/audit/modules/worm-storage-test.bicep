// Pitfall 7 validation. After successful lock + delete-attempt + observe-refusal,
// this entire account MUST be deleted before the prod 6-year lock applies.
// Plan 09 phase exit verifies the test account no longer exists.

targetScope = 'resourceGroup'

@description('Azure region')
param location string

@description('Test storage account name (must be unique; will be deleted post-validation)')
@minLength(3)
@maxLength(24)
param storageAccountName string = 'stbarywormtest1'

@description('Test container name')
param containerName string = 'audit-test'

@description('Tags applied to all resources')
param tags object = {}

resource storageAccount 'Microsoft.Storage/storageAccounts@2024-01-01' = {
  name: storageAccountName
  location: location
  tags: union(tags, { purpose: 'pitfall-7-lock-validation', lifetime: 'ephemeral' })
  sku: {
    name: 'Standard_LRS'
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
    allowSharedKeyAccess: false
    supportsHttpsTrafficOnly: true
  }
}

resource blobServices 'Microsoft.Storage/storageAccounts/blobServices@2024-01-01' = {
  parent: storageAccount
  name: 'default'
}

resource testContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2024-01-01' = {
  parent: blobServices
  name: containerName
  properties: {
    publicAccess: 'None'
    immutableStorageWithVersioning: {
      enabled: true
    }
  }
}

// Pitfall 7: 1-day retention so the test cycle (lock → attempt-delete → observe-refusal → wait → cleanup)
// completes within 24 hours and the test account can be torn down before prod is locked.
resource immutabilityPolicy 'Microsoft.Storage/storageAccounts/blobServices/containers/immutabilityPolicies@2024-01-01' = {
  parent: testContainer
  name: 'default'
  properties: {
    immutabilityPeriodSinceCreationInDays: 1
    allowProtectedAppendWrites: true
  }
}

output storageAccountId string = storageAccount.id
output storageAccountName string = storageAccount.name
output containerName string = testContainer.name
