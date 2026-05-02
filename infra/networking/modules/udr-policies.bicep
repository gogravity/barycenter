// Reserved stub for overlay UDRs (admin bastion path, future ExpressRoute).
// The primary spoke-default UDR (0.0.0.0/0 → FortiGate trust NIC) is bound to
// subnets in spoke-vnet.bicep because Azure couples route-table assignment to
// subnet creation. This module exists so future overlay routes (e.g., admin
// bastion bypassing FortiGate, ExpressRoute peering routes) have a dedicated
// home without churning spoke-vnet.bicep.

@description('Azure region (currently unused — reserved for future routes).')
param location string = resourceGroup().location

@description('Tags propagated to future resources.')
param tags object = {}

// Intentionally no resources — this module is reserved.
// Suppress unused-parameter linter warnings via the outputs below.

output reserved string = 'reserved-for-future-udrs'
output reservedLocation string = location
output reservedTags object = tags
