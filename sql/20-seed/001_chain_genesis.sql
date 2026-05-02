-- D-05: seed audit.chain_state with the genesis row. Idempotent.
-- The genesis hash is exactly 64 zero hex chars (matches GENESIS_HASH constant in
-- packages/barycenter-audit/src/barycenter/audit/chain.py).

IF NOT EXISTS (SELECT 1 FROM audit.chain_state WHERE id = 1)
INSERT INTO audit.chain_state (id, head_digest, updated_by)
VALUES (1, REPLICATE('0', 64), 'genesis-seed');
GO

-- Verification (the deploy-script captures stdout for evidence):
SELECT id, head_digest, updated_at, updated_by FROM audit.chain_state WHERE id = 1;
GO
