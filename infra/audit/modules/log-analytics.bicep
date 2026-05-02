// Log Analytics workspace + AuditEvents_CL custom table.
// AUDIT-01: hot-tier 90-day retention; cold mirror handled by WORM (Pitfall 6).
// Schema mirrors the AuditEvent Pydantic model in
// packages/barycenter-audit/src/barycenter/audit/models.py and the DCR streamDeclarations.

targetScope = 'resourceGroup'

@description('Azure region')
param location string

@description('Log Analytics workspace name')
param workspaceName string = 'log-bary-dev'

@description('Tags applied to all resources')
param tags object = {}

resource workspace 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: workspaceName
  location: location
  tags: tags
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 90
    features: {
      // T-1-06-05: enforce RBAC on read; no fallthrough Reader at workspace scope.
      enableLogAccessUsingOnlyResourcePermissions: true
    }
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
  }
}

// Custom table — schema MUST match DCR streamDeclarations Custom-AuditEvents.
// Pitfall 9: metadata column type 'dynamic' allows forward-extension without schema change.
resource auditEventsTable 'Microsoft.OperationalInsights/workspaces/tables@2023-09-01' = {
  parent: workspace
  name: 'AuditEvents_CL'
  properties: {
    schema: {
      name: 'AuditEvents_CL'
      columns: [
        { name: 'TimeGenerated', type: 'datetime' }
        { name: 'event_id', type: 'string' }
        { name: 'occurred_at', type: 'datetime' }
        { name: 'actor_id', type: 'string' }
        { name: 'actor_type', type: 'string' }
        { name: 'verb', type: 'string' }
        { name: 'resource_type', type: 'string' }
        { name: 'resource_id', type: 'string' }
        { name: 'outcome', type: 'string' }
        { name: 'tenant_id', type: 'string' }
        { name: 'prior_digest', type: 'string' }
        { name: 'this_digest', type: 'string' }
        { name: 'metadata', type: 'dynamic' }
      ]
    }
    retentionInDays: 90
    totalRetentionInDays: 90
  }
}

output workspaceId string = workspace.id
output workspaceCustomerId string = workspace.properties.customerId
output workspaceResourceId string = workspace.id
output workspaceName string = workspace.name
