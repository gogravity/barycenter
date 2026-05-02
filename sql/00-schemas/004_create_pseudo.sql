-- FOUND-03: pseudo schema holds the pseudonym map (cw_company_id+email -> person_pid).
-- Populated by Phase 2 ETL using KV sign-derived person_pid. ERAS-01 erasure cascade
-- targets this table.
IF SCHEMA_ID('pseudo') IS NULL EXEC('CREATE SCHEMA pseudo');
GO
-- Tables added in Phase 2; schema must exist now so grants in plan 05 can reference it.
