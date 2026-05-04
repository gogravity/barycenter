// Deployment script that runs the SQL DDL + grants + chain genesis seed against the
// freshly-deployed SQL server via private endpoint. Uses sqlcmd authenticated with an
// AAD access token from the deploy MI.
//
// SQL content is embedded inline (no storage SAS URI required). The ACI container is
// VNet-injected into deploy-script-subnet so it can reach the SQL private endpoint.
// The subnet must be delegated to Microsoft.ContainerInstance/containerGroups.
//
// Idempotent: every .sql block uses IF NOT EXISTS / IF SCHEMA_ID IS NULL guards.

@description('Azure region')
param location string

@description('Resource ID of mi-bary-deploy (the user-assigned MI executing the script)')
param deployIdentityId string

@description('FQDN of the SQL server (e.g. sql-bary-dev.database.windows.net)')
param sqlServerFqdn string

@description('Resource ID of the deploy-script-subnet (delegated to Microsoft.ContainerInstance/containerGroups)')
param deployScriptSubnetId string

@description('Name of the pre-existing storage account the deployment script uses for its working files (required when VNet-injected)')
param scriptStorageAccountName string

@description('Resource group of the script storage account (defaults to current RG)')
param scriptStorageAccountResourceGroupName string = resourceGroup().name

@description('Force-update tag — bump to re-run the script with new SQL content')
param forceUpdateTag string = utcNow()

@description('Tags applied to all resources')
param tags object

// AAD audience for Azure SQL — sourced from environment().authentication.audiences so
// AzureUSGovernment / AzureChinaCloud resolve correctly.
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
    // Storage account for deployment script working files. Required when VNet-injected.
    // The account is created in main.bicep with a VNet rule allowing deploy-script-subnet.
    storageAccountSettings: {
      storageAccountName: scriptStorageAccountName
      storageAccountResourceGroupName: scriptStorageAccountResourceGroupName
    }
    // VNet-inject the ACI container so it can reach the private SQL endpoint.
    // The deploy-script-subnet is delegated to Microsoft.ContainerInstance/containerGroups
    // and has no FortiGate UDR (delegation skips it) so it has direct internet egress
    // for installing sqlcmd.
    containerSettings: {
      containerGroupName: 'acg-bary-sql-migrate'
      subnetIds: [
        {
          id: deployScriptSubnetId
        }
      ]
    }
    environmentVariables: [
      {
        name: 'SQL_FQDN'
        value: sqlServerFqdn
      }
      {
        name: 'SQL_AAD_RESOURCE'
        value: sqlAadResource
      }
    ]
    scriptContent: '''
      #!/bin/bash
      set -euo pipefail

      # Install sqlcmd (mssql-tools18) — Microsoft Linux package signed and trusted.
      curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | tee /etc/apt/trusted.gpg.d/microsoft.asc >/dev/null
      curl -fsSL https://packages.microsoft.com/config/ubuntu/22.04/prod.list | tee /etc/apt/sources.list.d/mssql-release.list >/dev/null
      ACCEPT_EULA=Y apt-get update -qq
      ACCEPT_EULA=Y apt-get install -y mssql-tools18 unixodbc-dev >/dev/null
      export PATH="$PATH:/opt/mssql-tools18/bin"

      # Acquire AAD token for SQL via the deploy MI. Audience comes from environment().
      TOKEN=$(az account get-access-token --resource "$SQL_AAD_RESOURCE" --query accessToken -o tsv)

      mkdir -p /tmp/sql

      # ── 001_create_raw_cw.sql ─────────────────────────────────────────────────
      cat > /tmp/sql/001_create_raw_cw.sql << 'SQLEOF'
IF SCHEMA_ID('raw_cw') IS NULL EXEC('CREATE SCHEMA raw_cw');
GO

IF OBJECT_ID('raw_cw.companies') IS NULL
CREATE TABLE raw_cw.companies (
    cw_company_id           BIGINT          NOT NULL PRIMARY KEY,
    company_name            NVARCHAR(256)   NOT NULL,
    billing_address_line1   NVARCHAR(256)   NULL,
    billing_address_city    NVARCHAR(128)   NULL,
    billing_address_region  NVARCHAR(64)    NULL,
    cui_handling_required   BIT             NOT NULL DEFAULT 0,
    ai_opt_out              BIT             NOT NULL DEFAULT 0,
    ai_opt_out_classes      NVARCHAR(MAX)   NULL,
    synced_at               DATETIME2       NOT NULL DEFAULT SYSUTCDATETIME(),
    source_etag             NVARCHAR(128)   NULL
);
GO
SQLEOF

      # ── 002_create_ai_zone.sql ────────────────────────────────────────────────
      cat > /tmp/sql/002_create_ai_zone.sql << 'SQLEOF'
IF SCHEMA_ID('ai_zone') IS NULL EXEC('CREATE SCHEMA ai_zone');
GO
SQLEOF

      # ── 003_create_audit.sql ──────────────────────────────────────────────────
      cat > /tmp/sql/003_create_audit.sql << 'SQLEOF'
IF SCHEMA_ID('audit') IS NULL EXEC('CREATE SCHEMA audit');
GO

IF OBJECT_ID('audit.chain_state') IS NULL
CREATE TABLE audit.chain_state (
    id              INT             NOT NULL PRIMARY KEY,
    head_digest     CHAR(64)        NOT NULL,
    updated_at      DATETIME2       NOT NULL DEFAULT SYSUTCDATETIME(),
    updated_by      NVARCHAR(256)   NULL,
    CONSTRAINT CK_chain_state_singleton CHECK (id = 1)
);
GO
SQLEOF

      # ── 004_create_pseudo.sql ─────────────────────────────────────────────────
      cat > /tmp/sql/004_create_pseudo.sql << 'SQLEOF'
IF SCHEMA_ID('pseudo') IS NULL EXEC('CREATE SCHEMA pseudo');
GO
SQLEOF

      # ── 005_create_raw_cw_remaining.sql ───────────────────────────────────────
      cat > /tmp/sql/005_create_raw_cw_remaining.sql << 'SQLEOF'
IF SCHEMA_ID('raw_cw') IS NULL EXEC('CREATE SCHEMA raw_cw');
GO

IF OBJECT_ID('raw_cw.agreements') IS NULL
CREATE TABLE raw_cw.agreements (
    agreement_id            BIGINT          NOT NULL PRIMARY KEY,
    cw_company_id           BIGINT          NOT NULL,
    agreement_name          NVARCHAR(256)   NOT NULL,
    agreement_type_name     NVARCHAR(128)   NULL,
    start_date              DATETIME2       NULL,
    end_date                DATETIME2       NULL,
    billing_cycle           NVARCHAR(64)    NULL,
    monthly_value_cents     BIGINT          NULL,
    synced_at               DATETIME2       NOT NULL DEFAULT SYSUTCDATETIME(),
    source_etag             NVARCHAR(128)   NULL
);
GO

IF OBJECT_ID('raw_cw.tickets') IS NULL
CREATE TABLE raw_cw.tickets (
    ticket_id               BIGINT          NOT NULL PRIMARY KEY,
    cw_company_id           BIGINT          NOT NULL,
    summary                 NVARCHAR(256)   NULL,
    status_name             NVARCHAR(64)    NULL,
    priority_name           NVARCHAR(64)    NULL,
    type_name               NVARCHAR(64)    NULL,
    date_entered            DATETIME2       NULL,
    last_updated            DATETIME2       NULL,
    synced_at               DATETIME2       NOT NULL DEFAULT SYSUTCDATETIME(),
    source_etag             NVARCHAR(128)   NULL
);
GO

IF OBJECT_ID('raw_cw.configurations') IS NULL
CREATE TABLE raw_cw.configurations (
    configuration_id        BIGINT          NOT NULL PRIMARY KEY,
    cw_company_id           BIGINT          NOT NULL,
    configuration_name      NVARCHAR(256)   NULL,
    configuration_type_name NVARCHAR(128)   NULL,
    manufacturer_name       NVARCHAR(128)   NULL,
    model_number            NVARCHAR(128)   NULL,
    serial_number           NVARCHAR(128)   NULL,
    status_name             NVARCHAR(64)    NULL,
    installation_date       DATETIME2       NULL,
    synced_at               DATETIME2       NOT NULL DEFAULT SYSUTCDATETIME(),
    source_etag             NVARCHAR(128)   NULL
);
GO

IF OBJECT_ID('raw_cw.time_entries') IS NULL
CREATE TABLE raw_cw.time_entries (
    cw_company_id           BIGINT          NOT NULL,
    entry_date              DATE            NOT NULL,
    total_hours             DECIMAL(10,2)   NOT NULL DEFAULT 0,
    billable_hours          DECIMAL(10,2)   NOT NULL DEFAULT 0,
    entry_count             INT             NOT NULL DEFAULT 0,
    synced_at               DATETIME2       NOT NULL DEFAULT SYSUTCDATETIME(),
    source_etag             NVARCHAR(128)   NULL,
    CONSTRAINT pk_raw_cw_time_entries PRIMARY KEY (cw_company_id, entry_date)
);
GO
SQLEOF

      # ── 006_create_pseudo_person_map.sql ──────────────────────────────────────
      cat > /tmp/sql/006_create_pseudo_person_map.sql << 'SQLEOF'
IF SCHEMA_ID('pseudo') IS NULL EXEC('CREATE SCHEMA pseudo');
GO

IF OBJECT_ID('pseudo.person_map') IS NULL
CREATE TABLE pseudo.person_map (
    tenant_id               NVARCHAR(64)    NOT NULL,
    email_lower             NVARCHAR(320)   NOT NULL,
    person_pid              CHAR(64)        NOT NULL,
    salt_version            NVARCHAR(64)    NOT NULL,
    created_at              DATETIME2       NOT NULL DEFAULT SYSUTCDATETIME(),
    retired_at              DATETIME2       NULL,
    CONSTRAINT pk_pseudo_person_map PRIMARY KEY (tenant_id, email_lower, salt_version)
);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'ix_pseudo_person_map_pid')
CREATE INDEX ix_pseudo_person_map_pid ON pseudo.person_map (person_pid);
GO
SQLEOF

      # ── 007_create_ai_zone_shapes.sql ─────────────────────────────────────────
      cat > /tmp/sql/007_create_ai_zone_shapes.sql << 'SQLEOF'
IF OBJECT_ID('ai_zone.customer_snapshot') IS NULL
CREATE TABLE ai_zone.customer_snapshot (
    cw_company_id           BIGINT          NOT NULL PRIMARY KEY,
    tier                    NVARCHAR(32)    NULL,
    industry_bucket         NVARCHAR(64)    NULL,
    employee_band           NVARCHAR(32)    NULL,
    region                  NVARCHAR(64)    NULL,
    lifecycle_stage         NVARCHAR(32)    NULL,
    ai_opt_out              BIT             NOT NULL DEFAULT 0,
    cui_flag                BIT             NOT NULL DEFAULT 0,
    synced_at               DATETIME2       NOT NULL DEFAULT SYSUTCDATETIME()
);
GO

IF OBJECT_ID('ai_zone.customer_features_cw') IS NULL
CREATE TABLE ai_zone.customer_features_cw (
    cw_company_id           BIGINT          NOT NULL PRIMARY KEY,
    open_ticket_count       INT             NOT NULL DEFAULT 0,
    avg_age_days_bucket     NVARCHAR(32)    NULL,
    top_keyword_flags       NVARCHAR(MAX)   NULL,
    time_entries_h_30d_bucket NVARCHAR(32)  NULL,
    synced_at               DATETIME2       NOT NULL DEFAULT SYSUTCDATETIME()
);
GO

IF OBJECT_ID('ai_zone.timeseries_aggregate') IS NULL
CREATE TABLE ai_zone.timeseries_aggregate (
    cw_company_id           BIGINT          NOT NULL,
    month                   DATE            NOT NULL,
    metric_name             NVARCHAR(64)    NOT NULL,
    value_bucketed          NVARCHAR(64)    NULL,
    synced_at               DATETIME2       NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT pk_ai_zone_timeseries_aggregate PRIMARY KEY (cw_company_id, month, metric_name)
);
GO

IF OBJECT_ID('ai_zone.customer_memory') IS NULL
CREATE TABLE ai_zone.customer_memory (
    cw_company_id           BIGINT          NOT NULL,
    memory_kind             NVARCHAR(64)    NOT NULL,
    summary_text            NVARCHAR(2000)  NULL,
    source_kind             NVARCHAR(64)    NULL,
    last_observed_month     DATE            NULL,
    synced_at               DATETIME2       NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT pk_ai_zone_customer_memory PRIMARY KEY (cw_company_id, memory_kind)
);
GO
SQLEOF

      # ── 001_etl_grants.sql ────────────────────────────────────────────────────
      cat > /tmp/sql/001_etl_grants.sql << 'SQLEOF'
IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = 'mi-bary-etl')
    EXEC('CREATE USER [mi-bary-etl] FROM EXTERNAL PROVIDER');

GRANT SELECT, INSERT, UPDATE, DELETE ON SCHEMA::raw_cw TO [mi-bary-etl];
GRANT SELECT, INSERT, UPDATE ON SCHEMA::pseudo TO [mi-bary-etl];
GRANT SELECT, INSERT, DELETE ON SCHEMA::ai_zone TO [mi-bary-etl];
DENY SELECT, INSERT, UPDATE, DELETE ON SCHEMA::audit TO [mi-bary-etl];
GO
SQLEOF

      # ── 002_audit_grants.sql ──────────────────────────────────────────────────
      cat > /tmp/sql/002_audit_grants.sql << 'SQLEOF'
IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = 'mi-bary-audit')
    EXEC('CREATE USER [mi-bary-audit] FROM EXTERNAL PROVIDER');

GRANT SELECT, UPDATE ON OBJECT::audit.chain_state TO [mi-bary-audit];
DENY SELECT, INSERT, UPDATE, DELETE ON SCHEMA::raw_cw TO [mi-bary-audit];
DENY SELECT, INSERT, UPDATE, DELETE ON SCHEMA::ai_zone TO [mi-bary-audit];
DENY SELECT, INSERT, UPDATE, DELETE ON SCHEMA::pseudo TO [mi-bary-audit];
GO
SQLEOF

      # ── 003_admin_revoke.sql ──────────────────────────────────────────────────
      cat > /tmp/sql/003_admin_revoke.sql << 'SQLEOF'
IF EXISTS (SELECT 1 FROM sys.database_principals WHERE name = 'mi-bary-admin')
BEGIN
    REVOKE SELECT, INSERT, UPDATE, DELETE, EXECUTE ON SCHEMA::raw_cw   FROM [mi-bary-admin];
    REVOKE SELECT, INSERT, UPDATE, DELETE, EXECUTE ON SCHEMA::ai_zone  FROM [mi-bary-admin];
    REVOKE SELECT, INSERT, UPDATE, DELETE, EXECUTE ON SCHEMA::audit    FROM [mi-bary-admin];
    REVOKE SELECT, INSERT, UPDATE, DELETE, EXECUTE ON SCHEMA::pseudo   FROM [mi-bary-admin];
    ALTER ROLE db_owner DROP MEMBER [mi-bary-admin];
    ALTER ROLE db_datareader DROP MEMBER [mi-bary-admin];
    ALTER ROLE db_datawriter DROP MEMBER [mi-bary-admin];
    DROP USER [mi-bary-admin];
END
GO
CREATE USER [mi-bary-admin] FROM EXTERNAL PROVIDER;
GO
SQLEOF

      # ── 004_platform_grants.sql ───────────────────────────────────────────────
      cat > /tmp/sql/004_platform_grants.sql << 'SQLEOF'
IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = 'mi-bary-platform')
    EXEC('CREATE USER [mi-bary-platform] FROM EXTERNAL PROVIDER');

GRANT SELECT ON SCHEMA::ai_zone TO [mi-bary-platform];
DENY SELECT, INSERT, UPDATE, DELETE ON SCHEMA::raw_cw TO [mi-bary-platform];
DENY SELECT, INSERT, UPDATE, DELETE ON SCHEMA::audit TO [mi-bary-platform];
DENY SELECT, INSERT, UPDATE, DELETE ON SCHEMA::pseudo TO [mi-bary-platform];
GO
SQLEOF

      # ── 001_chain_genesis.sql ─────────────────────────────────────────────────
      cat > /tmp/sql/001_chain_genesis.sql << 'SQLEOF'
IF NOT EXISTS (SELECT 1 FROM audit.chain_state WHERE id = 1)
INSERT INTO audit.chain_state (id, head_digest, updated_by)
VALUES (1, REPLICATE('0', 64), 'genesis-seed');
GO

SELECT id, head_digest, updated_at, updated_by FROM audit.chain_state WHERE id = 1;
GO
SQLEOF

      run_sql() {
        local FILE="$1"
        echo ">> Applying $FILE"
        sqlcmd -S "$SQL_FQDN" -d barycenter -G --access-token "$TOKEN" -i "$FILE" -b
      }

      # Order: schemas first, then grants, then seed.
      run_sql /tmp/sql/001_create_raw_cw.sql
      run_sql /tmp/sql/002_create_ai_zone.sql
      run_sql /tmp/sql/003_create_audit.sql
      run_sql /tmp/sql/004_create_pseudo.sql
      run_sql /tmp/sql/005_create_raw_cw_remaining.sql
      run_sql /tmp/sql/006_create_pseudo_person_map.sql
      run_sql /tmp/sql/007_create_ai_zone_shapes.sql
      run_sql /tmp/sql/001_etl_grants.sql
      run_sql /tmp/sql/002_audit_grants.sql
      run_sql /tmp/sql/003_admin_revoke.sql
      run_sql /tmp/sql/004_platform_grants.sql
      run_sql /tmp/sql/001_chain_genesis.sql

      echo "All SQL files applied successfully."
    '''
  }
}

output deploymentScriptId string = grantsScript.id
