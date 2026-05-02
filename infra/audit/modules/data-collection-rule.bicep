// Data Collection Endpoint + Data Collection Rule for the Logs Ingestion API.
// The audit SDK (plan 07 — packages/barycenter-audit) posts AuditEvent JSON to
// the DCE's `dataCollectionEndpoints/{name}/dataCollectionRules/{immutableId}/streams/Custom-AuditEvents`
// endpoint with an AAD token; DCR routes to AuditEvents_CL in the LA workspace.
//
// CLAUDE.md tradeoff: DCE is `publicNetworkAccess: 'Enabled'` (the standard pattern for
// Logs Ingestion API). The actual control is AAD token + DCR scope (mi-bary-audit
// has Monitoring Metrics Publisher ONLY on this DCR). Future enhancement: PE-on-DCE
// once Network Security Perimeter Phase 2 reaches GA. Documented in README.

targetScope = 'resourceGroup'

@description('Azure region')
param location string

@description('Data Collection Rule name')
param dcrName string = 'dcr-bary-audit-dev'

@description('Data Collection Endpoint name')
param dceName string = 'dce-bary-audit-dev'

@description('Resource ID of the target Log Analytics workspace')
param workspaceResourceId string

@description('Principal ID of mi-bary-audit (granted Monitoring Metrics Publisher on DCR)')
param auditPrincipalId string

@description('Tags applied to all resources')
param tags object = {}

// Built-in role: Monitoring Metrics Publisher
// https://learn.microsoft.com/azure/role-based-access-control/built-in-roles#monitoring-metrics-publisher
var monitoringMetricsPublisherRoleId = '3913510d-42f4-4e42-8a64-420c390055eb'

resource dce 'Microsoft.Insights/dataCollectionEndpoints@2023-03-11' = {
  name: dceName
  location: location
  tags: tags
  properties: {
    networkAcls: {
      // Public ingestion required for current Logs Ingestion API; AAD token + DCR scope is
      // the boundary. See README for tradeoff and roadmap to PE-on-DCE.
      publicNetworkAccess: 'Enabled'
    }
  }
}

resource dcr 'Microsoft.Insights/dataCollectionRules@2023-03-11' = {
  name: dcrName
  location: location
  tags: tags
  properties: {
    dataCollectionEndpointId: dce.id
    streamDeclarations: {
      'Custom-AuditEvents': {
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
          // Pitfall 9: metadata is `dynamic` so adding top-level AuditEvent fields
          // does NOT require DCR + table schema migration.
          { name: 'metadata', type: 'dynamic' }
        ]
      }
    }
    destinations: {
      logAnalytics: [
        {
          workspaceResourceId: workspaceResourceId
          name: 'la-dest'
        }
      ]
    }
    dataFlows: [
      {
        streams: [
          'Custom-AuditEvents'
        ]
        destinations: [
          'la-dest'
        ]
        outputStream: 'Custom-AuditEvents_CL'
        transformKql: 'source'
      }
    ]
  }
}

// Grant mi-bary-audit Monitoring Metrics Publisher on this DCR (and only this DCR).
// T-1-06-09: scoped to DCR, not workspace-wide.
resource auditDcrRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: dcr
  name: guid(dcr.id, auditPrincipalId, monitoringMetricsPublisherRoleId)
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', monitoringMetricsPublisherRoleId)
    principalId: auditPrincipalId
    principalType: 'ServicePrincipal'
  }
}

output dcrId string = dcr.id
output dcrImmutableId string = dcr.properties.immutableId
output dceId string = dce.id
output dceLogsIngestionEndpoint string = dce.properties.logsIngestion.endpoint
output streamName string = 'Custom-AuditEvents'
