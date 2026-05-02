-- FOUND-04 layer 1 + D-05: mi-bary-audit gets UPDATE on audit.chain_state only.
-- It has NO read/write access to raw_cw, ai_zone, or pseudo. The audit SDK uses
-- this identity exclusively for chain_state advancement.

IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = 'mi-bary-audit')
    EXEC('CREATE USER [mi-bary-audit] FROM EXTERNAL PROVIDER');

GRANT SELECT, UPDATE ON OBJECT::audit.chain_state TO [mi-bary-audit];

DENY SELECT, INSERT, UPDATE, DELETE ON SCHEMA::raw_cw TO [mi-bary-audit];
DENY SELECT, INSERT, UPDATE, DELETE ON SCHEMA::ai_zone TO [mi-bary-audit];
DENY SELECT, INSERT, UPDATE, DELETE ON SCHEMA::pseudo TO [mi-bary-audit];
GO
