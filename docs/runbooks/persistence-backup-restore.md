# Persistence Backup and Restore

## Trigger

- `EnvelopeKeyRotationOverdue` alert fires (severity: warning)
- Scheduled rotation SLA breach
- Disaster recovery drill

## Impact

- Encryption key rotation overdue increases risk of key compromise
- Backup integrity may be affected if rotation is not completed
- Affected subsystem: persistence (PostgreSQL, Redis coordination state)

## Diagnosis

1. Check rotation status:

   ```sql
   SELECT key_id, created_at, expires_at, status
   FROM encryption_keys
   WHERE status = 'active'
   ORDER BY expires_at ASC;
   ```

2. Verify backup timestamps and integrity:

   ```bash
   # Check latest backup age
   pgbackrest info --stanza=agropredict

   # Verify backup integrity
   pgbackrest check --stanza=agropredict --type=backup
   ```

3. Check envelope-encryption rotation metrics:

   ```
   agropredict_encryption_rotation_due_total > 0
   agropredict_encryption_last_rotation_seconds
   ```

## Remediation

### Step 1: Rotate encryption keys

1. Trigger key rotation through the admin API or Helm config update:

   ```bash
   kubectl exec -n agropredict deploy/backend -- \
     python -m backend.persistence.rotate_keys --force
   ```

2. Verify rotation completed:

   ```sql
   SELECT key_id, created_at, status
   FROM encryption_keys
   WHERE status = 'active'
   ORDER BY created_at DESC
   LIMIT 1;
   ```

### Step 2: Verify backup integrity after rotation

1. Run a fresh backup after key rotation:

   ```bash
   pgbackrest backup --stanza=agropredict --type=full
   ```

2. Verify restore capability:

   ```bash
   pgbackrest check --stanza=agropredict --type=backup
   ```

### Step 3: Restore Redis coordination state

If Redis state was lost during rotation:

1. Identify the latest consistent checkpoint from PostgreSQL:

   ```sql
   SELECT checkpoint_id, tenant_id, created_at
   FROM checkpoints
   ORDER BY created_at DESC
   LIMIT 10;
   ```

2. Repopulate Redis from durable checkpoint rows:

   ```bash
   kubectl exec -n agropredict deploy/backend -- \
     python -m backend.persistence.restore_redis --from-checkpoint latest
   ```

3. Verify readiness before accepting traffic:

   ```bash
   curl -s http://localhost:8000/health/ready | jq
   ```

## Rollback

If key rotation causes issues:

1. Revert to the previous active key:

   ```sql
   UPDATE encryption_keys
   SET status = 'active'
   WHERE key_id = '<previous_key_id>';
   ```

2. Invalidate the rotated key:

   ```sql
   UPDATE encryption_keys
   SET status = 'revoked'
   WHERE key_id = '<rotated_key_id>';
   ```

3. Restart backend pods to pick up the reverted key:

   ```bash
   kubectl rollout restart -n agropredict deploy/backend
   ```

## Evidence Checklist

- [ ] Backup identifier and verification timestamp recorded
- [ ] Key rotation completion timestamp recorded
- [ ] Restore drill outcome documented
- [ ] Operator rationale recorded if any waiver was applied
