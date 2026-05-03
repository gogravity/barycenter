# Salt Rotation Fire Drill Evidence

> ENC-02 / Phase 2 success criterion 5.

## Status: DEFERRED

fire drill: deferred

Reason: No non-production Azure SQL instance with the `pseudo` schema deployed at time of Phase 2 execution. The `SaltRotation` implementation and runbook are complete and unit-tested (test_salt_rotation.py passes). The fire drill requires a live dev SQL + Key Vault environment to execute against.

## What to do when a dev SQL instance is available

1. Deploy the Phase 2 schema to the dev SQL instance (`sql/00-schemas/00*.sql`)
2. Run the fire drill script:

```python
import os
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
import pyodbc
from barycenter.audit import AuditClient
from barycenter.etl.framework.salt_rotation import SaltRotation

TEST_TENANT = "synthetic-firedrill-001"  # never a real customer

cred = DefaultAzureCredential()
kv = SecretClient(vault_url=os.environ["KEY_VAULT_URL"], credential=cred)
sql = pyodbc.connect(os.environ["SQL_CONNECTION_STRING"])
audit = AuditClient(...)

# Step 1: create new KV secret version
# az keyvault secret set --vault-name "$KV" --name "salt-${TEST_TENANT}" --value "$(openssl rand -hex 32)"

# Step 2: open dual-write window
sr = SaltRotation(kv, sql, audit)
sr.open_window(TEST_TENANT, old_version=OLD, new_version=NEW)

# Step 3: exercise dual-write
result = sr.dual_write("test@synthetic.example.com", TEST_TENANT, old_version=OLD, new_version=NEW)
assert result.pid_old != result.pid_new

# Step 4: cut over
sr.cut_over(TEST_TENANT)

# Step 5: disable old version
# az keyvault secret set-attributes --vault-name "$KV" --name "salt-${TEST_TENANT}" --version "$OLD" --enabled false
```

3. Fill in the fields below and remove the DEFERRED status.

---

## Evidence (fill in after fire drill)

```
tenant_id: synthetic-firedrill-001  (non-prod / synthetic)
old_version:
new_version:
pid_old != pid_new: (confirmed / not yet run)
operator: craig.vickers@gmail.com
completed_at:
audit_query_result: (paste output of SELECT verb, COUNT(*) FROM audit.events WHERE verb LIKE 'salt.rotate.%')
```
