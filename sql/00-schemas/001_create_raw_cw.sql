-- FOUND-01: raw zone for ConnectWise mirror. Populated by ETL in Phase 2.
-- All columns must appear in compliance/field-class-registry.yaml (VER-02).
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
    ai_opt_out_classes      NVARCHAR(MAX)   NULL,  -- JSON list (Phase 3)
    synced_at               DATETIME2       NOT NULL DEFAULT SYSUTCDATETIME(),
    source_etag             NVARCHAR(128)   NULL
);
GO
