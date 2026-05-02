-- D-05: audit schema with single-row chain_state table.
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

-- Future: audit.events_overflow added in Phase 2 if LA ingestion lag is observed.
