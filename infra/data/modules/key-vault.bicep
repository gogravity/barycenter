// FOUND-03 + plan 04 dependency: Key Vault in RBAC mode behind a private endpoint.
// Holds the bootstrap salt key (oct sign/verify) and placeholder secrets for FortiGate
// license + Anthropic API key. publicNetworkAccess Disabled (CLAUDE.md global rule).

@description('Azure region')
param location string

@description('Key Vault name (e.g. kv-bary-dev)')
param vaultName string

@description('Object ID of mi-bary-etl (Key Vault Crypto User on the salt key only)')
param etlPrincipalId string

@description('System-assigned principalId of the FortiGate VM (Secrets User on license secret only); empty until plan 04 wires it')
param fortigateVmPrincipalId string = ''

@description('PrincipalId of mi-bary-deploy (Key Vault Administrator vault-wide; revoke after Wave 0 stabilizes — see README)')
param deployPrincipalId string

@description('Tags applied to all resources')
param tags object

resource kv 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: vaultName
  location: location
  tags: tags
  properties: {
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 90
    enablePurgeProtection: true
    publicNetworkAccess: 'Disabled'
    networkAcls: {
      defaultAction: 'Deny'
      bypass: 'AzureServices'
    }
    tenantId: subscription().tenantId
    sku: {
      family: 'A'
      name: 'standard'
    }
  }
}

// FOUND-03: bootstrap salt key as RSA-2048 (standard KV only supports RSA and EC;
// oct requires Managed HSM). Salt material for HMAC is stored as a KV secret and
// fetched by Pseudonymizer.derive() — this key serves as the bootstrap anchor.
// Upgrade to Managed HSM + oct-HSM for FIPS 140-2 Level 3 when required.
resource saltKey 'Microsoft.KeyVault/vaults/keys@2023-07-01' = {
  parent: kv
  name: 'salt-tenant-bootstrap'
  properties: {
    kty: 'RSA'
    keySize: 2048
    keyOps: [
      'sign'
      'verify'
    ]
  }
}

// Placeholder; admin populates with real .lic content via `az keyvault secret set` in
// plan 09 phase exit. attributes.enabled stays false until then so a typo or premature
// consume cannot hand back the literal placeholder string.
resource fortigateLicenseSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: kv
  name: 'fortigate-license'
  properties: {
    value: 'PLACEHOLDER_REPLACE_VIA_AZ_CLI'
    attributes: {
      enabled: false
    }
  }
}

resource anthropicApiKeySecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: kv
  name: 'anthropic-api-key'
  properties: {
    value: 'PLACEHOLDER_PHASE3'
    attributes: {
      enabled: false
    }
  }
}

// Key Vault Crypto User (12338af0-0e69-4776-bea7-57ae8d297424) → mi-bary-etl, scoped
// to the salt key resource only. Sign permission only — cannot retrieve plaintext key.
resource etlSaltKeyCryptoUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: saltKey
  name: guid(saltKey.id, etlPrincipalId, '12338af0-0e69-4776-bea7-57ae8d297424')
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '12338af0-0e69-4776-bea7-57ae8d297424')
    principalId: etlPrincipalId
    principalType: 'ServicePrincipal'
  }
}

// Key Vault Secrets User (4633458b-17de-408a-b874-0445c86b69e6) → FortiGate VM
// system-assigned identity, scoped to the fortigate-license secret only. Conditional
// because the FGT VM identity may not exist until plan 04 deploys the FortiGate.
resource fortigateLicenseSecretsUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(fortigateVmPrincipalId)) {
  scope: fortigateLicenseSecret
  name: guid(fortigateLicenseSecret.id, fortigateVmPrincipalId, '4633458b-17de-408a-b874-0445c86b69e6')
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '4633458b-17de-408a-b874-0445c86b69e6')
    principalId: fortigateVmPrincipalId
    principalType: 'ServicePrincipal'
  }
}

// Key Vault Administrator (00482a5a-887f-4fb3-b363-3b7fe8e74483) → mi-bary-deploy,
// vault-wide. Required for the deploy script to populate keys/secrets during initial
// deploy. TODO (plan 09 phase exit): remove this assignment once Wave 0 stabilizes.
// Acceptable risk window because mi-bary-deploy is OIDC-only (federated to refs/heads/main)
// with no human-interactive path (Pitfall 11).
resource deployKvAdmin 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: kv
  name: guid(kv.id, deployPrincipalId, '00482a5a-887f-4fb3-b363-3b7fe8e74483')
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '00482a5a-887f-4fb3-b363-3b7fe8e74483')
    principalId: deployPrincipalId
    principalType: 'ServicePrincipal'
  }
}

output vaultId string = kv.id
output vaultUri string = kv.properties.vaultUri
output saltKeyId string = saltKey.id
output fortigateLicenseSecretUri string = fortigateLicenseSecret.properties.secretUri
