// Deployed at the target RG scope (the RG where eligibility is granted).
// Caller in main.bicep uses `scope: resourceGroup(subscription().subscriptionId, targetResourceGroup)`.
targetScope = 'resourceGroup'

@description('Object ID of the principal to make PIM-eligible')
param principalId string

@description('Built-in or custom role definition ID (full resource ID)')
param roleDefinitionId string

@description('Justification recorded with the eligibility schedule')
param justification string

@description('Maximum activation duration in hours')
@minValue(1)
@maxValue(8)
param maxActivationDurationHours int = 4

var scheduleName = guid(resourceGroup().id, principalId, roleDefinitionId, 'eligibility')

resource eligibility 'Microsoft.Authorization/roleEligibilityScheduleRequests@2020-10-01' = {
  name: scheduleName
  scope: resourceGroup()
  properties: {
    principalId: principalId
    roleDefinitionId: roleDefinitionId
    requestType: 'AdminAssign'
    justification: justification
    scheduleInfo: {
      startDateTime: null
      expiration: {
        type: 'NoExpiration'
      }
    }
  }
}

output eligibilityScheduleId string = eligibility.id
output activationMaxDurationHours int = maxActivationDurationHours
