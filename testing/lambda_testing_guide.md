# Aurora Restore Pipeline - Lambda Testing Guide

This guide provides detailed instructions for testing each Lambda function in the Aurora restore pipeline. Follow these steps to verify the functionality of each component before deploying the complete pipeline.

## Prerequisites

Before testing, ensure you have:

1. AWS CLI configured with appropriate permissions
2. Access to both source and target AWS accounts
3. Required SSM parameters and secrets configured
4. DynamoDB table `aurora-restore-audit` created
5. SNS topic `aurora-restore-notifications` created

## Testing Environment Setup

### 1. Configure SSM Parameters

First, set up the required SSM parameters:

```bash
# Source account parameters
aws ssm put-parameter \
    --name "/aurora-restore/source-account-id" \
    --value "123456789012" \
    --type String

aws ssm put-parameter \
    --name "/aurora-restore/source-region" \
    --value "us-east-1" \
    --type String

aws ssm put-parameter \
    --name "/aurora-restore/source-cluster-id" \
    --value "source-aurora-cluster" \
    --type String

# Target account parameters
aws ssm put-parameter \
    --name "/aurora-restore/target-account-id" \
    --value "987654321098" \
    --type String

aws ssm put-parameter \
    --name "/aurora-restore/target-region" \
    --value "us-west-2" \
    --type String

aws ssm put-parameter \
    --name "/aurora-restore/target-cluster-id" \
    --value "target-aurora-cluster" \
    --type String

aws ssm put-parameter \
    --name "/aurora-restore/snapshot-prefix" \
    --value "daily-backup" \
    --type String
```

### 2. Configure Secrets Manager

Set up the database credentials secret:

```bash
aws secretsmanager create-secret \
    --name "/aurora-restore/db-credentials" \
    --secret-string '{
        "master_username": "admin",
        "master_password": "your-secure-password",
        "database": "mydb",
        "app_username": "app_user",
        "app_password": "app-password",
        "readonly_username": "readonly_user",
        "readonly_password": "readonly-password"
    }'
```

### 3. Create SNS Topic

Create an SNS topic for notifications:

```bash
aws sns create-topic --name aurora-restore-notifications
```

## Testing Individual Lambda Functions

### 1. Testing `aurora-restore-snapshot-check`

This function checks if the daily snapshot exists in the source account.

**Test Input:**
```json
{}
```

**Expected Output:**
```json
{
  "snapshot_name": "daily-backup-2023-05-15",
  "snapshot_arn": "arn:aws:rds:us-east-1:123456789012:cluster-snapshot:daily-backup-2023-05-15",
  "source_account_id": "123456789012",
  "target_account_id": "987654321098",
  "source_region": "us-east-1",
  "target_region": "us-west-2"
}
```

**Testing Steps:**
1. Create a test event in the Lambda console with the empty JSON object `{}`
2. Execute the function
3. Verify the output contains the snapshot details
4. Check the DynamoDB table for the audit log entry

### 2. Testing `aurora-restore-copy-snapshot`

This function copies the snapshot from source account to target account.

**Test Input:**
```json
{
  "snapshot_name": "daily-backup-2023-05-15",
  "snapshot_arn": "arn:aws:rds:us-east-1:123456789012:cluster-snapshot:daily-backup-2023-05-15",
  "source_account_id": "123456789012",
  "target_account_id": "987654321098",
  "source_region": "us-east-1",
  "target_region": "us-west-2"
}
```

**Expected Output:**
```json
{
  "source_snapshot": "daily-backup-2023-05-15",
  "target_snapshot": "daily-backup-2023-05-15-copy",
  "source_account_id": "123456789012",
  "target_account_id": "987654321098",
  "source_region": "us-east-1",
  "target_region": "us-west-2",
  "copy_status": "creating"
}
```

**Testing Steps:**
1. Create a test event in the Lambda console with the JSON input
2. Execute the function
3. Verify the output contains the target snapshot name and copy status
4. Check the DynamoDB table for the audit log entry

### 3. Testing `aurora-restore-check-copy-status`

This function checks the status of the snapshot copy operation.

**Test Input:**
```json
{
  "source_snapshot": "daily-backup-2023-05-15",
  "target_snapshot": "daily-backup-2023-05-15-copy",
  "source_account_id": "123456789012",
  "target_account_id": "987654321098",
  "source_region": "us-east-1",
  "target_region": "us-west-2",
  "copy_status": "creating"
}
```

**Expected Output:**
```json
{
  "source_snapshot": "daily-backup-2023-05-15",
  "target_snapshot": "daily-backup-2023-05-15-copy",
  "source_account_id": "123456789012",
  "target_account_id": "987654321098",
  "source_region": "us-east-1",
  "target_region": "us-west-2",
  "copy_status": "available",
  "snapshot_arn": "arn:aws:rds:us-west-2:987654321098:cluster-snapshot:daily-backup-2023-05-15-copy"
}
```

**Testing Steps:**
1. Create a test event in the Lambda console with the JSON input
2. Execute the function
3. Verify the output contains the updated copy status
4. Check the DynamoDB table for the audit log entry

### 4. Testing `aurora-restore-delete-rds`

This function deletes the existing RDS cluster in the target account.

**Test Input:**
```json
{
  "source_snapshot": "daily-backup-2023-05-15",
  "target_snapshot": "daily-backup-2023-05-15-copy",
  "source_account_id": "123456789012",
  "target_account_id": "987654321098",
  "source_region": "us-east-1",
  "target_region": "us-west-2",
  "copy_status": "available",
  "snapshot_arn": "arn:aws:rds:us-west-2:987654321098:cluster-snapshot:daily-backup-2023-05-15-copy"
}
```

**Expected Output:**
```json
{
  "source_snapshot": "daily-backup-2023-05-15",
  "target_snapshot": "daily-backup-2023-05-15-copy",
  "source_account_id": "123456789012",
  "target_account_id": "987654321098",
  "source_region": "us-east-1",
  "target_region": "us-west-2",
  "copy_status": "available",
  "snapshot_arn": "arn:aws:rds:us-west-2:987654321098:cluster-snapshot:daily-backup-2023-05-15-copy"
}
```

**Testing Steps:**
1. Create a test event in the Lambda console with the JSON input
2. Execute the function
3. Verify the output is the same as the input
4. Check the DynamoDB table for the audit log entry
5. Verify the cluster is deleted in the target account

### 5. Testing `aurora-restore-restore-snapshot`

This function restores the snapshot to create a new RDS cluster.

**Test Input:**
```json
{
  "source_snapshot": "daily-backup-2023-05-15",
  "target_snapshot": "daily-backup-2023-05-15-copy",
  "source_account_id": "123456789012",
  "target_account_id": "987654321098",
  "source_region": "us-east-1",
  "target_region": "us-west-2",
  "copy_status": "available",
  "snapshot_arn": "arn:aws:rds:us-west-2:987654321098:cluster-snapshot:daily-backup-2023-05-15-copy"
}
```

**Expected Output:**
```json
{
  "source_snapshot": "daily-backup-2023-05-15",
  "target_snapshot": "daily-backup-2023-05-15-copy",
  "source_account_id": "123456789012",
  "target_account_id": "987654321098",
  "source_region": "us-east-1",
  "target_region": "us-west-2",
  "copy_status": "available",
  "snapshot_arn": "arn:aws:rds:us-west-2:987654321098:cluster-snapshot:daily-backup-2023-05-15-copy",
  "restore_status": "creating"
}
```

**Testing Steps:**
1. Create a test event in the Lambda console with the JSON input
2. Execute the function
3. Verify the output contains the restore status
4. Check the DynamoDB table for the audit log entry

### 6. Testing `aurora-restore-check-restore-status`

This function checks the status of the cluster restore operation.

**Test Input:**
```json
{
  "source_snapshot": "daily-backup-2023-05-15",
  "target_snapshot": "daily-backup-2023-05-15-copy",
  "source_account_id": "123456789012",
  "target_account_id": "987654321098",
  "source_region": "us-east-1",
  "target_region": "us-west-2",
  "copy_status": "available",
  "snapshot_arn": "arn:aws:rds:us-west-2:987654321098:cluster-snapshot:daily-backup-2023-05-15-copy",
  "restore_status": "creating"
}
```

**Expected Output:**
```json
{
  "source_snapshot": "daily-backup-2023-05-15",
  "target_snapshot": "daily-backup-2023-05-15-copy",
  "source_account_id": "123456789012",
  "target_account_id": "987654321098",
  "source_region": "us-east-1",
  "target_region": "us-west-2",
  "copy_status": "available",
  "snapshot_arn": "arn:aws:rds:us-west-2:987654321098:cluster-snapshot:daily-backup-2023-05-15-copy",
  "restore_status": "available",
  "cluster_endpoint": "target-aurora-cluster.cluster-123456789012.us-west-2.rds.amazonaws.com",
  "cluster_port": 5432
}
```

**Testing Steps:**
1. Create a test event in the Lambda console with the JSON input
2. Execute the function
3. Verify the output contains the updated restore status and cluster endpoint
4. Check the DynamoDB table for the audit log entry

### 7. Testing `aurora-restore-setup-db-users`

This function sets up database users and permissions after restore.

**Test Input:**
```json
{
  "source_snapshot": "daily-backup-2023-05-15",
  "target_snapshot": "daily-backup-2023-05-15-copy",
  "source_account_id": "123456789012",
  "target_account_id": "987654321098",
  "source_region": "us-east-1",
  "target_region": "us-west-2",
  "copy_status": "available",
  "snapshot_arn": "arn:aws:rds:us-west-2:987654321098:cluster-snapshot:daily-backup-2023-05-15-copy",
  "restore_status": "available",
  "cluster_endpoint": "target-aurora-cluster.cluster-123456789012.us-west-2.rds.amazonaws.com",
  "cluster_port": 5432
}
```

**Expected Output:**
```json
{
  "source_snapshot": "daily-backup-2023-05-15",
  "target_snapshot": "daily-backup-2023-05-15-copy",
  "source_account_id": "123456789012",
  "target_account_id": "987654321098",
  "source_region": "us-east-1",
  "target_region": "us-west-2",
  "copy_status": "available",
  "snapshot_arn": "arn:aws:rds:us-west-2:987654321098:cluster-snapshot:daily-backup-2023-05-15-copy",
  "restore_status": "available",
  "cluster_endpoint": "target-aurora-cluster.cluster-123456789012.us-west-2.rds.amazonaws.com",
  "cluster_port": 5432
}
```

**Testing Steps:**
1. Create a test event in the Lambda console with the JSON input
2. Execute the function
3. Verify the output is the same as the input
4. Check the DynamoDB table for the audit log entry
5. Connect to the database and verify the users are created with correct permissions

### 8. Testing `aurora-restore-archive-snapshot`

This function archives the snapshot after successful restore.

**Test Input:**
```json
{
  "source_snapshot": "daily-backup-2023-05-15",
  "target_snapshot": "daily-backup-2023-05-15-copy",
  "source_account_id": "123456789012",
  "target_account_id": "987654321098",
  "source_region": "us-east-1",
  "target_region": "us-west-2",
  "copy_status": "available",
  "snapshot_arn": "arn:aws:rds:us-west-2:987654321098:cluster-snapshot:daily-backup-2023-05-15-copy",
  "restore_status": "available",
  "cluster_endpoint": "target-aurora-cluster.cluster-123456789012.us-west-2.rds.amazonaws.com",
  "cluster_port": 5432
}
```

**Expected Output:**
```json
{
  "source_snapshot": "daily-backup-2023-05-15",
  "target_snapshot": "daily-backup-2023-05-15-copy",
  "source_account_id": "123456789012",
  "target_account_id": "987654321098",
  "source_region": "us-east-1",
  "target_region": "us-west-2",
  "copy_status": "available",
  "snapshot_arn": "arn:aws:rds:us-west-2:987654321098:cluster-snapshot:daily-backup-2023-05-15-copy",
  "restore_status": "available",
  "cluster_endpoint": "target-aurora-cluster.cluster-123456789012.us-west-2.rds.amazonaws.com",
  "cluster_port": 5432
}
```

**Testing Steps:**
1. Create a test event in the Lambda console with the JSON input
2. Execute the function
3. Verify the output is the same as the input
4. Check the DynamoDB table for the audit log entry
5. Verify the snapshot is deleted in the target account

### 9. Testing `aurora-restore-sns-notification`

This function sends SNS notification about the restore process completion.

**Test Input:**
```json
{
  "source_snapshot": "daily-backup-2023-05-15",
  "target_snapshot": "daily-backup-2023-05-15-copy",
  "source_account_id": "123456789012",
  "target_account_id": "987654321098",
  "source_region": "us-east-1",
  "target_region": "us-west-2",
  "copy_status": "available",
  "snapshot_arn": "arn:aws:rds:us-west-2:987654321098:cluster-snapshot:daily-backup-2023-05-15-copy",
  "restore_status": "available",
  "cluster_endpoint": "target-aurora-cluster.cluster-123456789012.us-west-2.rds.amazonaws.com",
  "cluster_port": 5432
}
```

**Expected Output:**
```json
{
  "status": "SUCCESS",
  "message": "Notification sent successfully"
}
```

**Testing Steps:**
1. Create a test event in the Lambda console with the JSON input
2. Execute the function
3. Verify the output contains the success message
4. Check the DynamoDB table for the audit log entry
5. Verify the SNS notification is sent

## End-to-End Testing

To test the entire pipeline:

1. Create a test event for the first Lambda function (`aurora-restore-snapshot-check`)
2. Execute the function and capture the output
3. Use the output as input for the next Lambda function
4. Repeat for each Lambda function in the pipeline
5. Verify the final state of the Aurora cluster in the target account

## Troubleshooting

If you encounter issues during testing:

1. Check CloudWatch Logs for each Lambda function
2. Verify the IAM permissions are correctly configured
3. Ensure the SSM parameters and secrets are properly set up
4. Check network connectivity between accounts
5. Verify the KMS key sharing is properly configured

## Testing in a Development Environment

For initial testing, consider using a smaller Aurora cluster or a snapshot with less data to reduce the time required for copy and restore operations. This will allow you to test the pipeline more quickly and identify any issues before deploying to production. 