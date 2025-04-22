# Aurora Restore Pipeline - Console Testing Guide

This guide provides step-by-step instructions for testing each Lambda function in the Aurora restore pipeline directly from the AWS Console. This approach is useful for debugging and understanding the behavior of individual functions.

## Prerequisites

Before testing, ensure you have:

1. AWS Console access with appropriate permissions
2. Access to both source and target AWS accounts
3. Required SSM parameters and secrets configured
4. DynamoDB table `aurora-restore-audit` created
5. SNS topic `aurora-restore-notifications` created

## General Testing Steps

For each Lambda function, follow these general steps:

1. Navigate to the AWS Lambda console
2. Select the function you want to test
3. Click on the "Test" tab
4. Create a new test event with the provided JSON payload
5. Click "Test" to execute the function
6. Review the execution results and logs

## Testing Individual Lambda Functions

### 1. Testing `aurora-restore-snapshot-check`

**Steps:**
1. Navigate to the Lambda console and select `aurora-restore-snapshot-check`
2. Click on the "Test" tab
3. Create a new test event named "SnapshotCheckTest"
4. Use the following JSON payload:
   ```json
   {}
   ```
5. Click "Test" to execute the function
6. Review the execution results and CloudWatch logs

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

### 2. Testing `aurora-restore-copy-snapshot`

**Steps:**
1. Navigate to the Lambda console and select `aurora-restore-copy-snapshot`
2. Click on the "Test" tab
3. Create a new test event named "CopySnapshotTest"
4. Use the following JSON payload (using output from previous step):
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
5. Click "Test" to execute the function
6. Review the execution results and CloudWatch logs

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

### 3. Testing `aurora-restore-check-copy-status`

**Steps:**
1. Navigate to the Lambda console and select `aurora-restore-check-copy-status`
2. Click on the "Test" tab
3. Create a new test event named "CheckCopyStatusTest"
4. Use the following JSON payload (using output from previous step):
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
5. Click "Test" to execute the function
6. Review the execution results and CloudWatch logs

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

### 4. Testing `aurora-restore-delete-rds`

**Steps:**
1. Navigate to the Lambda console and select `aurora-restore-delete-rds`
2. Click on the "Test" tab
3. Create a new test event named "DeleteRDSTest"
4. Use the following JSON payload (using output from previous step):
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
5. Click "Test" to execute the function
6. Review the execution results and CloudWatch logs

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

### 5. Testing `aurora-restore-restore-snapshot`

**Steps:**
1. Navigate to the Lambda console and select `aurora-restore-restore-snapshot`
2. Click on the "Test" tab
3. Create a new test event named "RestoreSnapshotTest"
4. Use the following JSON payload (using output from previous step):
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
5. Click "Test" to execute the function
6. Review the execution results and CloudWatch logs

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

### 6. Testing `aurora-restore-check-restore-status`

**Steps:**
1. Navigate to the Lambda console and select `aurora-restore-check-restore-status`
2. Click on the "Test" tab
3. Create a new test event named "CheckRestoreStatusTest"
4. Use the following JSON payload (using output from previous step):
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
5. Click "Test" to execute the function
6. Review the execution results and CloudWatch logs

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

### 7. Testing `aurora-restore-setup-db-users`

**Steps:**
1. Navigate to the Lambda console and select `aurora-restore-setup-db-users`
2. Click on the "Test" tab
3. Create a new test event named "SetupDBUsersTest"
4. Use the following JSON payload (using output from previous step):
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
5. Click "Test" to execute the function
6. Review the execution results and CloudWatch logs

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

### 8. Testing `aurora-restore-archive-snapshot`

**Steps:**
1. Navigate to the Lambda console and select `aurora-restore-archive-snapshot`
2. Click on the "Test" tab
3. Create a new test event named "ArchiveSnapshotTest"
4. Use the following JSON payload (using output from previous step):
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
5. Click "Test" to execute the function
6. Review the execution results and CloudWatch logs

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

### 9. Testing `aurora-restore-sns-notification`

**Steps:**
1. Navigate to the Lambda console and select `aurora-restore-sns-notification`
2. Click on the "Test" tab
3. Create a new test event named "SNSNotificationTest"
4. Use the following JSON payload (using output from previous step):
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
5. Click "Test" to execute the function
6. Review the execution results and CloudWatch logs

**Expected Output:**
```json
{
  "status": "SUCCESS",
  "message": "Notification sent successfully"
}
```

## End-to-End Console Testing

To test the entire pipeline from the console:

1. Start with the first Lambda function (`aurora-restore-snapshot-check`)
2. Create a test event with the empty JSON object `{}`
3. Execute the function and copy the output
4. Create a new test event for the next Lambda function using the output from the previous step
5. Repeat for each Lambda function in the pipeline
6. Verify the final state of the Aurora cluster in the target account

## Troubleshooting Console Testing

If you encounter issues during console testing:

1. **Check CloudWatch Logs**: Each Lambda function writes detailed logs to CloudWatch. Review these logs for error messages and execution details.

2. **Verify IAM Permissions**: Ensure the Lambda execution role has the necessary permissions for all AWS services it interacts with.

3. **Check SSM Parameters**: Verify that all required SSM parameters are correctly configured.

4. **Validate Secrets**: Ensure the Secrets Manager secret containing database credentials is properly set up.

5. **Network Connectivity**: For cross-account operations, verify that the necessary network connectivity and permissions are in place.

6. **KMS Key Sharing**: For snapshot copying between accounts, ensure KMS keys are properly shared.

## Testing in a Development Environment

For initial testing, consider using a smaller Aurora cluster or a snapshot with less data to reduce the time required for copy and restore operations. This will allow you to test the pipeline more quickly and identify any issues before deploying to production. 