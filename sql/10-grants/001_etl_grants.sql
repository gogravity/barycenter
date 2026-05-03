-- ETL identity grants. mi-bary-etl writes to raw_cw, pseudo, ai_zone.
-- DENY on audit schema is preserved: ETL writes audit only via AuditClient.emit (audit identity).
-- Phase 1 created this file with raw_cw GRANT + DENY on others. Phase 2 (this file) extends
-- to pseudo + ai_zone. grant_drift_check.py enforces this set as the authoritative model.

DECLARE @etl_principal NVARCHAR(256) = 'mi-bary-etl';

IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = @etl_principal)
    EXEC('CREATE USER [mi-bary-etl] FROM EXTERNAL PROVIDER');

-- raw_cw: full CRUD (Phase 1)
GRANT SELECT, INSERT, UPDATE, DELETE ON SCHEMA::raw_cw TO [mi-bary-etl];

-- pseudo: read + write (Phase 2 — was DENY)
GRANT SELECT, INSERT, UPDATE ON SCHEMA::pseudo TO [mi-bary-etl];

-- ai_zone: write-only via TRUNCATE+INSERT (Phase 2 — was DENY)
GRANT SELECT, INSERT, DELETE ON SCHEMA::ai_zone TO [mi-bary-etl];

-- audit: explicit DENY — ETL must use AuditClient (audit identity), never direct write
DENY SELECT, INSERT, UPDATE, DELETE ON SCHEMA::audit TO [mi-bary-etl];
GO
