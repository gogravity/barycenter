-- FOUND-04 layer 1: mi-bary-platform gets SELECT on ai_zone only. NO raw_cw, NO audit.
-- Phase 3 gateway runtime executes as this identity.

IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = 'mi-bary-platform')
    EXEC('CREATE USER [mi-bary-platform] FROM EXTERNAL PROVIDER');

GRANT SELECT ON SCHEMA::ai_zone TO [mi-bary-platform];

DENY SELECT, INSERT, UPDATE, DELETE ON SCHEMA::raw_cw TO [mi-bary-platform];
DENY SELECT, INSERT, UPDATE, DELETE ON SCHEMA::audit TO [mi-bary-platform];
DENY SELECT, INSERT, UPDATE, DELETE ON SCHEMA::pseudo TO [mi-bary-platform];
GO
