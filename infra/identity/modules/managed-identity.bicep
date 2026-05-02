@description('Name of the user-assigned managed identity')
param identityName string

@description('Azure region')
param location string

@description('Tags applied to the identity')
param tags object = {}

resource identity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: identityName
  location: location
  tags: tags
}

output identityId string = identity.id
output principalId string = identity.properties.principalId
output clientId string = identity.properties.clientId
output name string = identity.name
