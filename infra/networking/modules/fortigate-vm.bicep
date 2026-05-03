// FortiGate-VM PAYG on Standard_F2s_v2 — single-NVA hub design.
// Using PAYG image (fortinet_fg-vm_payg_2023) while BYOL license is pending.
// Switch plan/sku back to fortinet_fg-vm once BYOL license is available.
//
// Auto-shutdown at 19:00 UTC daily via Microsoft.DevTestLab/schedules to
// avoid PAYG charges outside business hours. Re-enable manually or extend
// schedule when needed.
//
// Trust NIC IP is statically assigned because it is the next-hop in spoke UDRs.
// Both NICs have enableIPForwarding=true so the FortiGate can transit non-local
// destination traffic.

@description('Azure region for the VM and NICs.')
param location string = resourceGroup().location

@description('FortiGate VM name.')
param vmName string = 'vm-fgt-bary-01'

@description('VM SKU — Standard_F2s_v2 sized for FortiGate-VM.')
param vmSize string = 'Standard_F2s_v2'

@description('Auto-shutdown time in HHmm UTC (e.g. 1900 = 7 PM UTC). Empty string disables.')
param autoShutdownTime string = '1900'

@description('Notification email for auto-shutdown warning. Empty string skips notification.')
param autoShutdownNotificationEmail string = ''

@description('Untrust subnet resource id (Internet-facing NIC lands here).')
param untrustSubnetId string

@description('Trust subnet resource id (spoke-facing NIC lands here).')
param trustSubnetId string

@description('Trust NIC static IP — must match the next-hop in spoke UDRs.')
param trustNicIp string = '10.10.1.4'

@description('Key Vault resource id holding the FortiGate license. Empty string defers KV role assignment to a follow-up plan.')
param keyVaultResourceId string = ''

@description('KV secret name for the FortiGate license.')
param licenseSecretName string = 'fortigate-license'

@description('SSH public key for FortiGate admin access.')
@secure()
param adminSshPublicKey string

@description('FortiGate admin username (Linux osProfile required for ssh key injection).')
param adminUsername string = 'fgtadmin'

@description('Tags propagated to all created resources.')
param tags object = {}

var customDataScript = '#!/bin/sh\nhostname ${vmName}\n'

resource untrustNic 'Microsoft.Network/networkInterfaces@2024-01-01' = {
  name: '${vmName}-nic-untrust'
  location: location
  tags: tags
  properties: {
    enableIPForwarding: true
    enableAcceleratedNetworking: false
    ipConfigurations: [
      {
        name: 'ipcfg-untrust'
        properties: {
          subnet: {
            id: untrustSubnetId
          }
          privateIPAllocationMethod: 'Dynamic'
        }
      }
    ]
  }
}

resource trustNic 'Microsoft.Network/networkInterfaces@2024-01-01' = {
  name: '${vmName}-nic-trust'
  location: location
  tags: tags
  properties: {
    enableIPForwarding: true
    enableAcceleratedNetworking: false
    ipConfigurations: [
      {
        name: 'ipcfg-trust'
        properties: {
          subnet: {
            id: trustSubnetId
          }
          privateIPAllocationMethod: 'Static'
          privateIPAddress: trustNicIp
        }
      }
    ]
  }
}

resource fortigateVm 'Microsoft.Compute/virtualMachines@2024-07-01' = {
  name: vmName
  location: location
  tags: tags
  identity: {
    type: 'SystemAssigned'
  }
  plan: {
    name: 'fortinet_fg-vm_payg_2023'
    product: 'fortinet_fortigate-vm_v5'
    publisher: 'fortinet'
  }
  properties: {
    hardwareProfile: {
      vmSize: vmSize
    }
    storageProfile: {
      imageReference: {
        publisher: 'fortinet'
        offer: 'fortinet_fortigate-vm_v5'
        sku: 'fortinet_fg-vm_payg_2023'
        version: 'latest'
      }
      osDisk: {
        name: '${vmName}-osdisk'
        createOption: 'FromImage'
        managedDisk: {
          storageAccountType: 'StandardSSD_LRS'
        }
      }
    }
    osProfile: {
      computerName: vmName
      adminUsername: adminUsername
      customData: base64(customDataScript)
      linuxConfiguration: {
        disablePasswordAuthentication: true
        ssh: {
          publicKeys: [
            {
              path: '/home/${adminUsername}/.ssh/authorized_keys'
              keyData: adminSshPublicKey
            }
          ]
        }
      }
    }
    networkProfile: {
      networkInterfaces: [
        {
          id: untrustNic.id
          properties: {
            primary: true
          }
        }
        {
          id: trustNic.id
          properties: {
            primary: false
          }
        }
      ]
    }
  }
}

resource autoShutdown 'Microsoft.DevTestLab/schedules@2018-09-15' = if (!empty(autoShutdownTime)) {
  name: 'shutdown-computevm-${vmName}'
  location: location
  tags: tags
  properties: {
    status: 'Enabled'
    taskType: 'ComputeVmShutdownTask'
    dailyRecurrence: {
      time: autoShutdownTime
    }
    timeZoneId: 'UTC'
    targetResourceId: fortigateVm.id
    notificationSettings: {
      status: empty(autoShutdownNotificationEmail) ? 'Disabled' : 'Enabled'
      timeInMinutes: 30
      emailRecipient: autoShutdownNotificationEmail
    }
  }
}

output vmId string = fortigateVm.id
output vmName string = fortigateVm.name
output trustNicId string = trustNic.id
output untrustNicId string = untrustNic.id
output trustNicIp string = trustNicIp
output systemAssignedPrincipalId string = fortigateVm.identity.principalId
output keyVaultResourceIdEcho string = keyVaultResourceId
output licenseSecretNameEcho string = licenseSecretName
