// Azure Container Registry (Basic SKU) for the ETL container image.
// Images do not contain PHI — Basic SKU with public pull is acceptable.
// Admin user disabled; mi-bary-etl authenticates via AcrPull managed identity role.
// mi-bary-deploy (CI build) authenticates via AcrPush managed identity role.

targetScope = 'resourceGroup'

@description('Azure region')
param location string

@description('ACR name (5-50 lowercase alphanumeric)')
@minLength(5)
@maxLength(50)
param acrName string = 'acrbarydev'

@description('Principal ID of mi-bary-etl (granted AcrPull — image pull inside CAJ)')
param etlPrincipalId string

@description('Principal ID of mi-bary-deploy (granted AcrPush — image build/push from CI)')
param deployPrincipalId string

@description('Tags applied to all resources')
param tags object = {}

// Built-in roles
// https://learn.microsoft.com/azure/role-based-access-control/built-in-roles
var acrPullRoleId  = '7f951dda-4ed3-4680-a7ca-43fe172d538d'
var acrPushRoleId  = '8311e382-0749-4cb8-b61a-304f252e45ec'

resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: acrName
  location: location
  tags: tags
  sku: { name: 'Basic' }
  properties: {
    adminUserEnabled: false          // managed identity auth only
    anonymousPullEnabled: false
    publicNetworkAccess: 'Enabled'   // Basic SKU — no private endpoint support; images only, no PHI
  }
}

// mi-bary-etl: pull images inside the Container Apps Job
resource etlAcrPull 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: acr
  name: guid(acr.id, etlPrincipalId, acrPullRoleId)
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', acrPullRoleId)
    principalId: etlPrincipalId
    principalType: 'ServicePrincipal'
  }
}

// mi-bary-deploy: push images from CI (az acr build)
resource deployAcrPush 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: acr
  name: guid(acr.id, deployPrincipalId, acrPushRoleId)
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', acrPushRoleId)
    principalId: deployPrincipalId
    principalType: 'ServicePrincipal'
  }
}

output acrId string = acr.id
output acrName string = acr.name
output acrLoginServer string = acr.properties.loginServer
