# Aurora Restore Pipeline - Sample Audit Trail

## DynamoDB Table: aurora-restore-audit

### Sample Entries for Past 10 Days

| Date | Operation ID | Step | Status | Details | Timestamp |
|------|--------------|------|---------|---------|-----------|
| 2024-03-20 | op-001 | snapshot-check | SUCCESS | Found snapshot: daily-backup-2024-03-20 | 2024-03-20 00:05:00 |
| 2024-03-20 | op-001 | copy-snapshot | SUCCESS | Started copy to target region | 2024-03-20 00:06:00 |
| 2024-03-20 | op-001 | check-copy-status | SUCCESS | Copy completed | 2024-03-20 00:15:00 |
| 2024-03-20 | op-001 | delete-rds | SUCCESS | Deleted existing cluster | 2024-03-20 00:16:00 |
| 2024-03-20 | op-001 | restore-snapshot | SUCCESS | Started restore process | 2024-03-20 00:17:00 |
| 2024-03-20 | op-001 | check-restore-status | SUCCESS | Restore completed | 2024-03-20 00:45:00 |
| 2024-03-20 | op-001 | setup-db-users | SUCCESS | Users configured | 2024-03-20 00:46:00 |
| 2024-03-20 | op-001 | archive-snapshot | SUCCESS | Snapshot archived | 2024-03-20 00:47:00 |
| 2024-03-20 | op-001 | sns-notification | SUCCESS | Notification sent | 2024-03-20 00:48:00 |
| 2024-03-19 | op-002 | snapshot-check | SUCCESS | Found snapshot: daily-backup-2024-03-19 | 2024-03-19 00:05:00 |
| 2024-03-19 | op-002 | copy-snapshot | FAILED | Invalid snapshot ID | 2024-03-19 00:06:00 |
| 2024-03-19 | op-002 | sns-notification | SUCCESS | Error notification sent | 2024-03-19 00:07:00 |
| 2024-03-18 | op-003 | snapshot-check | SUCCESS | Found snapshot: daily-backup-2024-03-18 | 2024-03-18 00:05:00 |
| 2024-03-18 | op-003 | copy-snapshot | SUCCESS | Started copy to target region | 2024-03-18 00:06:00 |
| 2024-03-18 | op-003 | check-copy-status | SUCCESS | Copy completed | 2024-03-18 00:15:00 |
| 2024-03-18 | op-003 | delete-rds | FAILED | Cluster not found | 2024-03-18 00:16:00 |
| 2024-03-18 | op-003 | sns-notification | SUCCESS | Error notification sent | 2024-03-18 00:17:00 |
| 2024-03-17 | op-004 | snapshot-check | SUCCESS | Found snapshot: daily-backup-2024-03-17 | 2024-03-17 00:05:00 |
| 2024-03-17 | op-004 | copy-snapshot | SUCCESS | Started copy to target region | 2024-03-17 00:06:00 |
| 2024-03-17 | op-004 | check-copy-status | SUCCESS | Copy completed | 2024-03-17 00:15:00 |
| 2024-03-17 | op-004 | delete-rds | SUCCESS | Deleted existing cluster | 2024-03-17 00:16:00 |
| 2024-03-17 | op-004 | restore-snapshot | FAILED | Invalid VPC configuration | 2024-03-17 00:17:00 |
| 2024-03-17 | op-004 | sns-notification | SUCCESS | Error notification sent | 2024-03-17 00:18:00 |
| 2024-03-16 | op-005 | snapshot-check | SUCCESS | Found snapshot: daily-backup-2024-03-16 | 2024-03-16 00:05:00 |
| 2024-03-16 | op-005 | copy-snapshot | SUCCESS | Started copy to target region | 2024-03-16 00:06:00 |
| 2024-03-16 | op-005 | check-copy-status | SUCCESS | Copy completed | 2024-03-16 00:15:00 |
| 2024-03-16 | op-005 | delete-rds | SUCCESS | Deleted existing cluster | 2024-03-16 00:16:00 |
| 2024-03-16 | op-005 | restore-snapshot | SUCCESS | Started restore process | 2024-03-16 00:17:00 |
| 2024-03-16 | op-005 | check-restore-status | SUCCESS | Restore completed | 2024-03-16 00:45:00 |
| 2024-03-16 | op-005 | setup-db-users | FAILED | Connection timeout | 2024-03-16 00:46:00 |
| 2024-03-16 | op-005 | sns-notification | SUCCESS | Error notification sent | 2024-03-16 00:47:00 |
| 2024-03-15 | op-006 | snapshot-check | SUCCESS | Found snapshot: daily-backup-2024-03-15 | 2024-03-15 00:05:00 |
| 2024-03-15 | op-006 | copy-snapshot | SUCCESS | Started copy to target region | 2024-03-15 00:06:00 |
| 2024-03-15 | op-006 | check-copy-status | SUCCESS | Copy completed | 2024-03-15 00:15:00 |
| 2024-03-15 | op-006 | delete-rds | SUCCESS | Deleted existing cluster | 2024-03-15 00:16:00 |
| 2024-03-15 | op-006 | restore-snapshot | SUCCESS | Started restore process | 2024-03-15 00:17:00 |
| 2024-03-15 | op-006 | check-restore-status | SUCCESS | Restore completed | 2024-03-15 00:45:00 |
| 2024-03-15 | op-006 | setup-db-users | SUCCESS | Users configured | 2024-03-15 00:46:00 |
| 2024-03-15 | op-006 | archive-snapshot | SUCCESS | Snapshot archived | 2024-03-15 00:47:00 |
| 2024-03-15 | op-006 | sns-notification | SUCCESS | Success notification sent | 2024-03-15 00:48:00 |

## Notes on Sample Data:

1. **Operation ID Format**: op-XXX (where XXX is a sequential number)
2. **Status Values**: SUCCESS, FAILED, IN_PROGRESS
3. **Time Patterns**:
   - Operations typically start at 00:05:00
   - Copy operations take ~10 minutes
   - Restore operations take ~30 minutes
   - Each step typically takes 1-2 minutes

## Common Failure Scenarios Demonstrated:

1. **Invalid Snapshot ID** (op-002)
2. **Cluster Not Found** (op-003)
3. **Invalid VPC Configuration** (op-004)
4. **Connection Timeout** (op-005)

## Success Pattern:

A successful restore operation includes all 9 steps:
1. snapshot-check
2. copy-snapshot
3. check-copy-status
4. delete-rds
5. restore-snapshot
6. check-restore-status
7. setup-db-users
8. archive-snapshot
9. sns-notification

Each successful operation takes approximately 45-50 minutes to complete. 