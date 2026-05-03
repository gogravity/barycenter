-- ENC-02: pseudo.person_map — versioned pseudonyms supporting salt rotation.
-- (tenant_id, email_lower) -> (person_pid, salt_version). Multiple rows per person
-- during dual-write windows; old rows retired at T+30 days per runbook.
-- Field-class: tenant_id (INTERNAL), email_lower (RESTRICTED — never read by AI zone),
--              person_pid (SENSITIVE), salt_version (INTERNAL).
IF SCHEMA_ID('pseudo') IS NULL EXEC('CREATE SCHEMA pseudo');
GO

IF OBJECT_ID('pseudo.person_map') IS NULL
CREATE TABLE pseudo.person_map (
    tenant_id               NVARCHAR(64)    NOT NULL,
    email_lower             NVARCHAR(320)   NOT NULL,    -- RFC 5321 max
    person_pid              CHAR(64)        NOT NULL,    -- SHA-256 hex
    salt_version            NVARCHAR(64)    NOT NULL,
    created_at              DATETIME2       NOT NULL DEFAULT SYSUTCDATETIME(),
    retired_at              DATETIME2       NULL,
    CONSTRAINT pk_pseudo_person_map PRIMARY KEY (tenant_id, email_lower, salt_version)
);
GO

-- Index for reverse lookup by pid (erasure flow needs this)
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'ix_pseudo_person_map_pid')
CREATE INDEX ix_pseudo_person_map_pid ON pseudo.person_map (person_pid);
GO
