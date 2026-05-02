targetScope = 'resourceGroup'

@description('Azure region')
param location string

@description('Tags applied to all identities')
param tags object = {}

@description('Resource group name where downstream resources live (used for PIM scope)')
param targetResourceGroup string

@description('Built-in Reader role definition ID (placeholder for raw_* reader; promoted in plan 05)')
param readerRoleDefinitionId string = '/subscriptions/${subscription().subscriptionId}/providers/Microsoft.Authorization/roleDefinitions/acdd72a7-3385-48ef-bd42-f606fba81ae7'

var identityNames = {
  etl:      'mi-bary-etl'
  platform: 'mi-bary-platform'
  audit:    'mi-bary-audit'
  admin:    'mi-bary-admin'
}

module miEtl 'modules/managed-identity.bicep' = {
  name: 'mi-${identityNames.etl}-deploy'
  params: {
    identityName: identityNames.etl
    location: location
    tags: union(tags, { role: 'etl' })
  }
}

module miPlatform 'modules/managed-identity.bicep' = {
  name: 'mi-${identityNames.platform}-deploy'
  params: {
    identityName: identityNames.platform
    location: location
    tags: union(tags, { role: 'platform' })
  }
}

module miAudit 'modules/managed-identity.bicep' = {
  name: 'mi-${identityNames.audit}-deploy'
  params: {
    identityName: identityNames.audit
    location: location
    tags: union(tags, { role: 'audit' })
  }
}

module miAdmin 'modules/managed-identity.bicep' = {
  name: 'mi-${identityNames.admin}-deploy'
  params: {
    identityName: identityNames.admin
    location: location
    tags: union(tags, { role: 'admin' })
  }
}

// PIM eligibility on mi-bary-admin only (Pitfall 1: no standing grants).
// Module is deployed against the target RG (rg-barycenter-dev), which is a different
// RG than the one this template deploys to (rg-barycenter-identity).
module pimAdmin 'modules/pim-eligibility.bicep' = {
  name: 'pim-${identityNames.admin}-eligible'
  scope: resourceGroup(targetResourceGroup)
  params: {
    principalId: miAdmin.outputs.principalId
    roleDefinitionId: readerRoleDefinitionId
    justification: 'IDENT-02 + IDENT-05: admin MI is PIM-eligible only; activation requires dual approval (configured via role management policy — see infra/identity/README.md)'
    maxActivationDurationHours: 4
  }
}

output etlIdentityId string = miEtl.outputs.identityId
output etlPrincipalId string = miEtl.outputs.principalId
output platformIdentityId string = miPlatform.outputs.identityId
output platformPrincipalId string = miPlatform.outputs.principalId
output auditIdentityId string = miAudit.outputs.identityId
output auditPrincipalId string = miAudit.outputs.principalId
output adminIdentityId string = miAdmin.outputs.identityId
output adminPrincipalId string = miAdmin.outputs.principalId
