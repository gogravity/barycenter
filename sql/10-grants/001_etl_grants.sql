-- FOUND-04 layer 1: mi-bary-etl gets CRUD on raw_cw schema only. NO ai_zone, NO audit.
-- Principal name format for managed identity: the MI's Entra display name.

DECLARE @etl_principal NVARCHAR(256) = 'mi-bary-etl';

IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = @etl_principal)
    EXEC('CREATE USER [mi-bary-etl] FROM EXTERNAL PROVIDER');

GRANT SELECT, INSERT, UPDATE, DELETE ON SCHEMA::raw_cw TO [mi-bary-etl];

-- Explicit denies as defense-in-depth (Pitfall 1)
DENY SELECT, INSERT, UPDATE, DELETE ON SCHEMA::ai_zone TO [mi-bary-etl];
DENY SELECT, INSERT, UPDATE, DELETE ON SCHEMA::audit TO [mi-bary-etl];
DENY SELECT, INSERT, UPDATE, DELETE ON SCHEMA::pseudo TO [mi-bary-etl];
GO
