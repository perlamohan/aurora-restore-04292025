# Aurora Restore Pipeline - State Flow Example

## 1. Initial State (snapshot-check)

```json
{
    "operation_id": "op-001",
    "step": "snapshot-check",
    "status": "SUCCESS",
    "timestamp": "2024-03-20 00:05:00",
    "details": {
        "snapshot_name": "daily-backup-2024-03-20",
        "snapshot_arn": "arn:aws:rds:us-east-1:123456789012:cluster-snapshot:daily-backup-2024-03-20",
        "source_account_id": "123456789012",
        "target_account_id": "987654321098",
        "source_region": "us-east-1",
        "target_region": "us-west-2"
    }
}
```

## 2. Copy Snapshot State

```json
{
    "operation_id": "op-001",
    "step": "copy-snapshot",
    "status": "SUCCESS",
    "timestamp": "2024-03-20 00:06:00",
    "details": {
        "source_snapshot": "daily-backup-2024-03-20",
        "target_snapshot": "daily-backup-2024-03-20-copy",
        "source_account_id": "123456789012",
        "target_account_id": "987654321098",
        "source_region": "us-east-1",
        "target_region": "us-west-2",
        "copy_status": "creating",
        "copy_snapshot_id": "copy-snapshot-123"
    }
}
```

## 3. Check Copy Status State

```json
{
    "operation_id": "op-001",
    "step": "check-copy-status",
    "status": "SUCCESS",
    "timestamp": "2024-03-20 00:15:00",
    "details": {
        "source_snapshot": "daily-backup-2024-03-20",
        "target_snapshot": "daily-backup-2024-03-20-copy",
        "source_account_id": "123456789012",
        "target_account_id": "987654321098",
        "source_region": "us-east-1",
        "target_region": "us-west-2",
        "copy_status": "available",
        "copy_snapshot_id": "copy-snapshot-123",
        "snapshot_arn": "arn:aws:rds:us-west-2:987654321098:cluster-snapshot:daily-backup-2024-03-20-copy"
    }
}
```

## 4. Delete RDS State

```json
{
    "operation_id": "op-001",
    "step": "delete-rds",
    "status": "SUCCESS",
    "timestamp": "2024-03-20 00:16:00",
    "details": {
        "source_snapshot": "daily-backup-2024-03-20",
        "target_snapshot": "daily-backup-2024-03-20-copy",
        "source_account_id": "123456789012",
        "target_account_id": "987654321098",
        "source_region": "us-east-1",
        "target_region": "us-west-2",
        "copy_status": "available",
        "copy_snapshot_id": "copy-snapshot-123",
        "snapshot_arn": "arn:aws:rds:us-west-2:987654321098:cluster-snapshot:daily-backup-2024-03-20-copy",
        "deleted_cluster_id": "old-cluster-id"
    }
}
```

## 5. Restore Snapshot State

```json
{
    "operation_id": "op-001",
    "step": "restore-snapshot",
    "status": "SUCCESS",
    "timestamp": "2024-03-20 00:17:00",
    "details": {
        "source_snapshot": "daily-backup-2024-03-20",
        "target_snapshot": "daily-backup-2024-03-20-copy",
        "source_account_id": "123456789012",
        "target_account_id": "987654321098",
        "source_region": "us-east-1",
        "target_region": "us-west-2",
        "copy_status": "available",
        "copy_snapshot_id": "copy-snapshot-123",
        "snapshot_arn": "arn:aws:rds:us-west-2:987654321098:cluster-snapshot:daily-backup-2024-03-20-copy",
        "deleted_cluster_id": "old-cluster-id",
        "new_cluster_id": "new-cluster-id",
        "restore_status": "creating",
        "vpc_id": "vpc-12345678",
        "subnet_ids": ["subnet-12345678", "subnet-87654321"],
        "security_group_ids": ["sg-12345678"]
    }
}
```

## 6. Check Restore Status State

```json
{
    "operation_id": "op-001",
    "step": "check-restore-status",
    "status": "SUCCESS",
    "timestamp": "2024-03-20 00:45:00",
    "details": {
        "source_snapshot": "daily-backup-2024-03-20",
        "target_snapshot": "daily-backup-2024-03-20-copy",
        "source_account_id": "123456789012",
        "target_account_id": "987654321098",
        "source_region": "us-east-1",
        "target_region": "us-west-2",
        "copy_status": "available",
        "copy_snapshot_id": "copy-snapshot-123",
        "snapshot_arn": "arn:aws:rds:us-west-2:987654321098:cluster-snapshot:daily-backup-2024-03-20-copy",
        "deleted_cluster_id": "old-cluster-id",
        "new_cluster_id": "new-cluster-id",
        "restore_status": "available",
        "cluster_endpoint": "new-cluster-id.cluster-123456789012.us-west-2.rds.amazonaws.com",
        "cluster_port": 5432,
        "vpc_id": "vpc-12345678",
        "subnet_ids": ["subnet-12345678", "subnet-87654321"],
        "security_group_ids": ["sg-12345678"]
    }
}
```

## How State is Tracked and Passed

1. **Operation ID**: 
   - Generated at the start of the process
   - Used to track all steps of a single restore operation
   - Stored in DynamoDB as the partition key

2. **State Passing**:
   - Each Lambda function reads the previous state from DynamoDB using the operation_id
   - Adds its own information to the state
   - Writes the updated state back to DynamoDB
   - Passes the complete state to the next Lambda function

3. **Status Checking**:
   - `check-copy-status` and `check-restore-status` functions:
     - Read the operation_id from the event
     - Query DynamoDB for the latest state
     - Use the `copy_snapshot_id` or `new_cluster_id` from the state to check status
     - Update the state with the new status
     - Write back to DynamoDB

4. **Error Handling**:
   - If any step fails:
     - Status is set to "FAILED"
     - Error details are added to the state
     - SNS notification is triggered
     - Process stops at that step

5. **DynamoDB Table Structure**:
```json
{
    "operation_id": "String (Partition Key)",
    "step": "String (Sort Key)",
    "status": "String",
    "timestamp": "String",
    "details": "Map"
}
```

This structure allows for:
- Quick lookup of all steps for an operation
- Tracking the progress of multiple concurrent operations
- Maintaining a complete audit trail
- Easy querying of operation status 