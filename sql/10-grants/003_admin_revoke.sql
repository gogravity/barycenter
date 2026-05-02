-- Pitfall 1 + IDENT-02: mi-bary-admin gets ZERO standing grants. PIM JIT only.
-- This file ensures no historical grant accidentally remains. Idempotent.

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
-- Re-create as a contained user with NO grants and NO role membership.
-- PIM activation in plan 03's eligibility schedule is the only path to elevate.
CREATE USER [mi-bary-admin] FROM EXTERNAL PROVIDER;
GO
