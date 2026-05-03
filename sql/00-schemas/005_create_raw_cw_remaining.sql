-- INT-01: raw zone for ConnectWise Manage — agreements, tickets, configurations, time_entries.
-- All columns must appear in compliance/field-class-registry.yaml (VER-02 CI gate).
-- raw_cw.tickets MUST NOT contain any body/description/resolution/notes columns
-- (Phase 2 success criterion 2; Pitfall 1; enforced by test_no_body_column.py).
-- raw_cw.companies already exists in 001_create_raw_cw.sql.
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
    summary                 NVARCHAR(256)   NULL,                  -- subject only; canary scanned
    status_name             NVARCHAR(64)    NULL,
    priority_name           NVARCHAR(64)    NULL,
    type_name               NVARCHAR(64)    NULL,
    date_entered            DATETIME2       NULL,
    last_updated            DATETIME2       NULL,
    -- DELIBERATELY ABSENT: body, initialDescription, resolution, internalAnalysis,
    -- initialInternalAnalysis, notes. test_no_body_column.py asserts none of these
    -- exist as columns. Pitfall 1 + Phase 2 success criterion 2.
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
-- AGGREGATES ONLY (per INT-01): one row per (cw_company_id, entry_date)
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
