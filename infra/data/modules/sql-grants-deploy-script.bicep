// Deployment script that runs the SQL DDL + grants + chain genesis seed against the
// freshly-deployed SQL server via private endpoint. Uses sqlcmd authenticated with an
// AAD access token from the deploy MI. Idempotent: every .sql file uses IF NOT EXISTS
// guards.
//
// SQL files are uploaded to a transient storage container by the GitHub Actions
// workflow (plan 08) and passed as a SAS URI. After cleanupPreference: OnSuccess the
// script container is auto-deleted.
//
// Cloud-environment URLs (Azure SQL audience, storage suffix) are sourced from the
// Bicep `environment()` function and passed in as env vars so this module is portable
// across AzureCloud / AzureUSGovernment / AzureChinaCloud.

@description('Azure region')
param location string

@description('Resource ID of mi-bary-deploy (the user-assigned MI executing the script)')
param deployIdentityId string

@description('FQDN of the SQL server (e.g. sql-bary-dev.database.windows.net)')
param sqlServerFqdn string

@description('PrincipalId of mi-bary-etl (passed to grant SQL files)')
param etlPrincipalId string

@description('PrincipalId of mi-bary-platform')
param platformPrincipalId string

@description('PrincipalId of mi-bary-audit')
param auditPrincipalId string

@description('PrincipalId of mi-bary-admin (revoke target)')
param adminPrincipalId string

@description('Storage account name hosting the SQL file blob container')
param scriptStorageAccountName string

@description('SAS URI to the container holding 00-schemas/, 10-grants/, 20-seed/ blobs')
@secure()
param scriptContainerSasUri string

@description('Force-update tag — bump to re-run the script with new SQL content')
param forceUpdateTag string = utcNow()

@description('Tags applied to all resources')
param tags object

// AAD audience for Azure SQL — sourced from environment().authentication.audiences so
// AzureUSGovernment / AzureChinaCloud resolve correctly. The first audience is the SQL
// management URL in all current Azure clouds.
var sqlAadResource = environment().authentication.audiences[0]

resource grantsScript 'Microsoft.Resources/deploymentScripts@2023-08-01' = {
  name: 'ds-bary-sql-grants'
  location: location
  tags: tags
  kind: 'AzureCLI'
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${deployIdentityId}': {}
    }
  }
  properties: {
    azCliVersion: '2.67.0'
    forceUpdateTag: forceUpdateTag
    timeout: 'PT30M'
    retentionInterval: 'P1D'
    cleanupPreference: 'OnSuccess'
    environmentVariables: [
      {
        name: 'SQL_FQDN'
        value: sqlServerFqdn
      }
      {
        name: 'SQL_AAD_RESOURCE'
        value: sqlAadResource
      }
      {
        name: 'ETL_PRINCIPAL_ID'
        value: etlPrincipalId
      }
      {
        name: 'PLATFORM_PRINCIPAL_ID'
        value: platformPrincipalId
      }
      {
        name: 'AUDIT_PRINCIPAL_ID'
        value: auditPrincipalId
      }
      {
        name: 'ADMIN_PRINCIPAL_ID'
        value: adminPrincipalId
      }
      {
        name: 'SCRIPT_STORAGE'
        value: scriptStorageAccountName
      }
      {
        name: 'SCRIPT_CONTAINER_SAS'
        secureValue: scriptContainerSasUri
      }
    ]
    scriptContent: '''
      #!/bin/bash
      set -euo pipefail

      # Install sqlcmd (mssql-tools) — Microsoft Linux package signed and trusted.
      curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | tee /etc/apt/trusted.gpg.d/microsoft.asc >/dev/null
      curl -fsSL https://packages.microsoft.com/config/ubuntu/22.04/prod.list | tee /etc/apt/sources.list.d/mssql-release.list >/dev/null
      ACCEPT_EULA=Y apt-get update -qq
      ACCEPT_EULA=Y apt-get install -y mssql-tools18 unixodbc-dev >/dev/null
      export PATH="$PATH:/opt/mssql-tools18/bin"

      # Acquire AAD token for SQL via the deploy MI. Audience comes from environment().
      TOKEN=$(az account get-access-token --resource "$SQL_AAD_RESOURCE" --query accessToken -o tsv)

      # Pull SQL files from the transient blob container provisioned by the CI workflow.
      # Container SAS URI form: https://<acct>.<storage-suffix>/<container>?sv=...
      mkdir -p /tmp/sql/00-schemas /tmp/sql/10-grants /tmp/sql/20-seed
      for SUBDIR in 00-schemas 10-grants 20-seed; do
        BASE=$(echo "$SCRIPT_CONTAINER_SAS" | sed 's/?.*//')
        QUERY=$(echo "$SCRIPT_CONTAINER_SAS" | sed 's/^[^?]*//')
        # azcopy is preinstalled in deploymentScripts AzureCLI image as of 2.67.0
        azcopy copy "${BASE}/${SUBDIR}/*${QUERY}" "/tmp/sql/${SUBDIR}/" --recursive=false
      done

      run_sql() {
        local FILE="$1"
        echo ">> Applying $FILE"
        sqlcmd -S "$SQL_FQDN" -d barycenter -G --access-token "$TOKEN" -i "$FILE" -b
      }

      # Order matters: schemas first, then grants, then seed.
      run_sql /tmp/sql/00-schemas/001_create_raw_cw.sql
      run_sql /tmp/sql/00-schemas/002_create_ai_zone.sql
      run_sql /tmp/sql/00-schemas/003_create_audit.sql
      run_sql /tmp/sql/00-schemas/004_create_pseudo.sql
      run_sql /tmp/sql/10-grants/001_etl_grants.sql
      run_sql /tmp/sql/10-grants/002_audit_grants.sql
      run_sql /tmp/sql/10-grants/003_admin_revoke.sql
      run_sql /tmp/sql/10-grants/004_platform_grants.sql
      run_sql /tmp/sql/20-seed/001_chain_genesis.sql

      echo "All SQL files applied successfully."
    '''
  }
}

output deploymentScriptId string = grantsScript.id
