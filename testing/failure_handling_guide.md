# Aurora Restore Pipeline - Failure Handling and Recovery Guide

## 1. Interruption Scenarios

### A. During Copy Snapshot
```json
{
    "operation_id": "op-001",
    "step": "copy-snapshot",
    "status": "IN_PROGRESS",
    "timestamp": "2024-03-20 00:06:00",
    "details": {
        "source_snapshot": "daily-backup-2024-03-20",
        "target_snapshot": "daily-backup-2024-03-20-copy",
        "copy_status": "creating",
        "copy_snapshot_id": "copy-snapshot-123"
    }
}
```

**Recovery Process**:
1. Check if copy operation exists in target region
2. If exists and status is "creating":
   - Continue monitoring with `check-copy-status`
3. If exists and status is "failed":
   - Delete failed copy
   - Retry copy operation
4. If doesn't exist:
   - Start new copy operation

### B. During Restore
```json
{
    "operation_id": "op-001",
    "step": "restore-snapshot",
    "status": "IN_PROGRESS",
    "timestamp": "2024-03-20 00:17:00",
    "details": {
        "new_cluster_id": "new-cluster-id",
        "restore_status": "creating"
    }
}
```

**Recovery Process**:
1. Check if cluster exists in target region
2. If exists and status is "creating":
   - Continue monitoring with `check-restore-status`
3. If exists and status is "failed":
   - Delete failed cluster
   - Retry restore operation
4. If doesn't exist:
   - Start new restore operation

## 2. Failure Scenarios

### A. Invalid Snapshot
```json
{
    "operation_id": "op-002",
    "step": "copy-snapshot",
    "status": "FAILED",
    "timestamp": "2024-03-19 00:06:00",
    "details": {
        "error": "InvalidSnapshot.NotFound",
        "error_message": "Snapshot daily-backup-2024-03-19 not found"
    }
}
```

**Recovery Process**:
1. Verify snapshot exists in source region
2. If snapshot exists:
   - Retry copy operation
3. If snapshot doesn't exist:
   - Notify user
   - End operation

### B. VPC Configuration Error
```json
{
    "operation_id": "op-004",
    "step": "restore-snapshot",
    "status": "FAILED",
    "timestamp": "2024-03-17 00:17:00",
    "details": {
        "error": "InvalidVPCConfiguration",
        "error_message": "VPC vpc-12345678 does not exist"
    }
}
```

**Recovery Process**:
1. Verify VPC configuration in SSM
2. Update VPC parameters if needed
3. Retry restore operation

### C. Database Connection Timeout
```json
{
    "operation_id": "op-005",
    "step": "setup-db-users",
    "status": "FAILED",
    "timestamp": "2024-03-16 00:46:00",
    "details": {
        "error": "ConnectionTimeout",
        "error_message": "Could not connect to database"
    }
}
```

**Recovery Process**:
1. Verify cluster is available
2. Check security group rules
3. Verify network connectivity
4. Retry user setup

## 3. Restart Scenarios

### A. Manual Restart
```bash
# Restart from specific step
aws lambda invoke \
  --function-name aurora-restore-restart \
  --payload '{
    "operation_id": "op-001",
    "restart_from_step": "copy-snapshot"
  }'
```

**Process**:
1. Load last successful state from DynamoDB
2. Validate prerequisites for restart step
3. Execute from specified step
4. Continue normal flow

### B. Automatic Retry
```json
{
    "operation_id": "op-003",
    "step": "delete-rds",
    "status": "FAILED",
    "timestamp": "2024-03-18 00:16:00",
    "details": {
        "error": "ClusterNotFound",
        "retry_count": 0,
        "max_retries": 3
    }
}
```

**Retry Logic**:
1. Implement exponential backoff
2. Maximum 3 retries per step
3. Different retry strategies per step:
   - Copy/Restore: Longer intervals (5, 10, 15 minutes)
   - User Setup: Shorter intervals (1, 2, 3 minutes)

## 4. Cleanup Scenarios

### A. Partial Restore
```json
{
    "operation_id": "op-004",
    "step": "restore-snapshot",
    "status": "FAILED",
    "timestamp": "2024-03-17 00:17:00",
    "details": {
        "error": "InvalidVPCConfiguration",
        "cleanup_required": true
    }
}
```

**Cleanup Process**:
1. Delete any created resources:
   - Copied snapshots
   - Partially restored clusters
2. Update audit trail
3. Notify user of cleanup

### B. Orphaned Resources
```json
{
    "operation_id": "op-005",
    "step": "check-restore-status",
    "status": "FAILED",
    "timestamp": "2024-03-16 00:45:00",
    "details": {
        "error": "ClusterNotFound",
        "orphaned_resources": ["copy-snapshot-123"]
    }
}
```

**Cleanup Process**:
1. Identify orphaned resources
2. Delete unused snapshots
3. Update audit trail
4. Notify user

## 5. Best Practices for Recovery

1. **State Management**:
   - Always maintain complete state in DynamoDB
   - Include retry counts and timestamps
   - Track cleanup status

2. **Error Handling**:
   - Implement proper error categorization
   - Include detailed error messages
   - Log stack traces for debugging

3. **Recovery Procedures**:
   - Document recovery steps
   - Implement automated recovery where possible
   - Provide manual recovery instructions

4. **Monitoring**:
   - Set up CloudWatch alarms
   - Monitor retry attempts
   - Track cleanup operations

5. **Testing**:
   - Test all failure scenarios
   - Verify recovery procedures
   - Document test results

## 6. Implementation Example

```python
def handle_failure(operation_id, step, error):
    # Load current state
    state = load_state(operation_id)
    
    # Update state with error
    state['status'] = 'FAILED'
    state['error'] = error
    state['retry_count'] = state.get('retry_count', 0) + 1
    
    # Determine recovery action
    if state['retry_count'] < MAX_RETRIES:
        # Implement retry logic
        schedule_retry(operation_id, step, state)
    else:
        # Initiate cleanup
        cleanup_resources(operation_id, state)
        notify_failure(operation_id, state)
    
    # Update audit trail
    save_state(state)
```

## 7. Common Recovery Patterns

1. **Copy Snapshot Failures**:
   - Verify source snapshot
   - Check cross-account permissions
   - Validate KMS keys
   - Retry with exponential backoff

2. **Restore Failures**:
   - Verify VPC configuration
   - Check subnet availability
   - Validate security groups
   - Ensure sufficient capacity

3. **Database Connection Failures**:
   - Verify network connectivity
   - Check security group rules
   - Validate credentials
   - Test connection from Lambda

4. **Resource Cleanup**:
   - Implement idempotent cleanup
   - Track cleanup status
   - Verify resource deletion
   - Update audit trail 