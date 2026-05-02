// FortiGate-VM02 BYOL on Standard_F2s_v2 — single-NVA hub design.
//
// License install (`execute restore license`) is performed post-deploy by a CI
// step that fetches KV secret 'fortigate-license' and pushes via az vm run-command
// invoke. Bicep customData only handles hostname bootstrap; license install is too
// long to fit in customData and would require plaintext exposure. The FortiGate
// VM's system-assigned identity gets KV Secrets User on the KV in plan 05.
//
// Trust NIC IP is statically assigned because it is the next-hop in spoke UDRs.
// Both NICs have enableIPForwarding=true so the FortiGate can transit non-local
// destination traffic.

@description('Azure region for the VM and NICs.')
param location string = resourceGroup().location

@description('FortiGate VM name.')
param vmName string = 'vm-fgt-bary-01'

@description('VM SKU — Standard_F2s_v2 sized for FortiGate-VM02 BYOL.')
param vmSize string = 'Standard_F2s_v2'

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
    name: 'fortinet_fg-vm'
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
        sku: 'fortinet_fg-vm'
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

output vmId string = fortigateVm.id
output vmName string = fortigateVm.name
output trustNicId string = trustNic.id
output untrustNicId string = untrustNic.id
output trustNicIp string = trustNicIp
output systemAssignedPrincipalId string = fortigateVm.identity.principalId
output keyVaultResourceIdEcho string = keyVaultResourceId
output licenseSecretNameEcho string = licenseSecretName
