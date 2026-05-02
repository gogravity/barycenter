-- FOUND-01: ai_zone holds pseudonymized projections. Populated by Phase 2 ETL via
-- the four canonical shapes (TOOL-03). Phase 3 adds AI-safe views over these.
IF SCHEMA_ID('ai_zone') IS NULL EXEC('CREATE SCHEMA ai_zone');
GO
-- Tables added in Phase 2; schema must exist now so grants in plan 05 can reference it.
