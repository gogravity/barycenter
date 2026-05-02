using 'main.bicep'

param location = 'eastus2'
param targetResourceGroup = 'rg-barycenter-dev'
param tags = {
  project: 'barycenter'
  env: 'dev'
  'managed-by': 'bicep'
  phase: '01-network-data-foundations'
}
