-- TOOL-03: Four canonical AI-zone shapes. Adapters contribute INTO these tables;
-- novel ai_zone tables are forbidden (Phase 2 success criterion 4). Enforced by
-- test_no_novel_ai_zone.py.
-- All AI-zone columns are PUBLIC or INTERNAL — no RESTRICTED, no un-pseudonymized SENSITIVE.
-- ai_zone schema already declared in 002_create_ai_zone.sql.

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
    top_keyword_flags       NVARCHAR(MAX)   NULL,            -- JSON dict
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
    summary_text            NVARCHAR(2000)  NULL,            -- PUBLIC; no PII
    source_kind             NVARCHAR(64)    NULL,
    last_observed_month     DATE            NULL,
    synced_at               DATETIME2       NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT pk_ai_zone_customer_memory PRIMARY KEY (cw_company_id, memory_kind)
);
GO
