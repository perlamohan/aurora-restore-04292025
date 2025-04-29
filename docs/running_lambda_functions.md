# Running Aurora Restore Lambda Functions in Sequence

This document provides instructions for running the Aurora restore Lambda functions in sequence using the new configuration management system in the Dev environment.

## Prerequisites

Before running the Lambda functions, ensure you have:

1. AWS CLI configured with appropriate credentials for the Dev environment
2. Required AWS permissions to invoke Lambda functions and access related services
3. Configuration values for the Dev environment (see [Configuration Sources](../configuration_sources.md))

## Configuration Setup

The Lambda functions use a hierarchical configuration system with the following priority:

1. Event data (passed directly to the Lambda)
2. State data (from previous Lambda executions)
3. Environment variables
4. SSM Parameter Store
5. Default values

For the Dev environment, you should set up the configuration in SSM Parameter Store:

```bash
# Set up base configuration for Dev environment
aws ssm put-parameter \
  --name "/aurora-restore/dev/config" \
  --value '{
    "source_region": "us-east-1",
    "target_region": "us-west-2",
    "source_cluster_id": "dev-source-cluster",
    "target_cluster_id": "dev-target-cluster",
    "target_subnet_group": "dev-subnet-group",
    "target_security_groups": ["sg-12345678"],
    "master_credentials_secret_id": "dev/master-credentials",
    "notification_topic_arn": "arn:aws:sns:us-west-2:123456789012:dev-notifications",
    "notification_queue_url": "https://sqs.us-west-2.amazonaws.com/123456789012/dev-notifications",
    "log_bucket": "dev-aurora-restore-logs",
    "log_prefix": "aurora-restore-logs"
  }' \
  --type String \
  --overwrite

# Set up database users configuration
aws ssm put-parameter \
  --name "/aurora-restore/dev/db_users" \
  --value '[
    {
      "username": "app_user",
      "password": "app_password",
      "privileges": ["SELECT", "INSERT", "UPDATE", "DELETE"]
    },
    {
      "username": "readonly_user",
      "password": "readonly_password",
      "privileges": ["SELECT"]
    }
  ]' \
  --type String \
  --overwrite
```

## Running the Lambda Functions in Sequence

### 1. Snapshot Check Lambda

This Lambda checks if a snapshot exists for the specified date.

```bash
# Invoke the snapshot check Lambda
aws lambda invoke \
  --function-name aurora-restore-snapshot-check-dev \
  --payload '{
    "operation_id": "dev-restore-2023-06-01",
    "target_date": "2023-06-01"
  }' \
  response.json

# Check the response
cat response.json
```

Expected response:
```json
{
  "operation_id": "dev-restore-2023-06-01",
  "status": "success",
  "message": "Snapshot exists",
  "snapshot_exists": true,
  "snapshot_name": "dev-source-cluster-snapshot-2023-06-01",
  "next_step": "copy_snapshot"
}
```

### 2. Copy Snapshot Lambda

This Lambda copies the snapshot to the target region.

```bash
# Invoke the copy snapshot Lambda
aws lambda invoke \
  --function-name aurora-restore-copy-snapshot-dev \
  --payload '{
    "operation_id": "dev-restore-2023-06-01",
    "snapshot_name": "dev-source-cluster-snapshot-2023-06-01"
  }' \
  response.json

# Check the response
cat response.json
```

Expected response:
```json
{
  "operation_id": "dev-restore-2023-06-01",
  "status": "success",
  "message": "Snapshot copy initiated",
  "source_snapshot": "dev-source-cluster-snapshot-2023-06-01",
  "target_snapshot": "dev-source-cluster-snapshot-2023-06-01-copy",
  "next_step": "check_copy_status"
}
```

### 3. Check Copy Status Lambda

This Lambda checks the status of the snapshot copy operation.

```bash
# Invoke the check copy status Lambda
aws lambda invoke \
  --function-name aurora-restore-check-copy-status-dev \
  --payload '{
    "operation_id": "dev-restore-2023-06-01",
    "target_snapshot": "dev-source-cluster-snapshot-2023-06-01-copy"
  }' \
  response.json

# Check the response
cat response.json
```

Expected response (if copy is still in progress):
```json
{
  "operation_id": "dev-restore-2023-06-01",
  "status": "success",
  "message": "Snapshot copy in progress",
  "target_snapshot": "dev-source-cluster-snapshot-2023-06-01-copy",
  "copy_status": "in-progress",
  "next_step": "check_copy_status"
}
```

Expected response (if copy is complete):
```json
{
  "operation_id": "dev-restore-2023-06-01",
  "status": "success",
  "message": "Snapshot copy completed",
  "target_snapshot": "dev-source-cluster-snapshot-2023-06-01-copy",
  "copy_status": "available",
  "next_step": "delete_rds"
}
```

### 4. Delete RDS Lambda

This Lambda deletes the existing RDS cluster in the target region.

```bash
# Invoke the delete RDS Lambda
aws lambda invoke \
  --function-name aurora-restore-delete-rds-dev \
  --payload '{
    "operation_id": "dev-restore-2023-06-01"
  }' \
  response.json

# Check the response
cat response.json
```

Expected response (if cluster exists and deletion is in progress):
```json
{
  "operation_id": "dev-restore-2023-06-01",
  "status": "success",
  "message": "Cluster deletion in progress",
  "target_cluster_id": "dev-target-cluster",
  "deletion_status": "in-progress",
  "next_step": "delete_rds"
}
```

Expected response (if cluster doesn't exist):
```json
{
  "operation_id": "dev-restore-2023-06-01",
  "status": "success",
  "message": "Cluster does not exist, proceeding to restore",
  "target_cluster_id": "dev-target-cluster",
  "next_step": "restore_snapshot"
}
```

Expected response (if cluster deletion is complete):
```json
{
  "operation_id": "dev-restore-2023-06-01",
  "status": "success",
  "message": "Cluster deletion completed",
  "target_cluster_id": "dev-target-cluster",
  "deletion_status": "completed",
  "next_step": "restore_snapshot"
}
```

### 5. Restore Snapshot Lambda

This Lambda restores the cluster from the snapshot.

```bash
# Invoke the restore snapshot Lambda
aws lambda invoke \
  --function-name aurora-restore-restore-snapshot-dev \
  --payload '{
    "operation_id": "dev-restore-2023-06-01",
    "target_snapshot": "dev-source-cluster-snapshot-2023-06-01-copy"
  }' \
  response.json

# Check the response
cat response.json
```

Expected response:
```json
{
  "operation_id": "dev-restore-2023-06-01",
  "status": "success",
  "message": "Cluster restore initiated",
  "target_cluster_id": "dev-target-cluster",
  "target_snapshot": "dev-source-cluster-snapshot-2023-06-01-copy",
  "next_step": "check_restore_status"
}
```

### 6. Check Restore Status Lambda

This Lambda checks the status of the cluster restore operation.

```bash
# Invoke the check restore status Lambda
aws lambda invoke \
  --function-name aurora-restore-check-restore-status-dev \
  --payload '{
    "operation_id": "dev-restore-2023-06-01"
  }' \
  response.json

# Check the response
cat response.json
```

Expected response (if restore is still in progress):
```json
{
  "operation_id": "dev-restore-2023-06-01",
  "status": "success",
  "message": "Cluster restore in progress",
  "target_cluster_id": "dev-target-cluster",
  "cluster_status": "creating",
  "next_step": "check_restore_status"
}
```

Expected response (if restore is complete):
```json
{
  "operation_id": "dev-restore-2023-06-01",
  "status": "success",
  "message": "Cluster restore completed",
  "target_cluster_id": "dev-target-cluster",
  "cluster_status": "available",
  "next_step": "setup_db_users"
}
```

### 7. Setup DB Users Lambda

This Lambda sets up database users after the cluster restore.

```bash
# Invoke the setup DB users Lambda
aws lambda invoke \
  --function-name aurora-restore-setup-db-users-dev \
  --payload '{
    "operation_id": "dev-restore-2023-06-01"
  }' \
  response.json

# Check the response
cat response.json
```

Expected response:
```json
{
  "operation_id": "dev-restore-2023-06-01",
  "status": "success",
  "message": "Successfully set up 2 users for cluster dev-target-cluster",
  "target_cluster_id": "dev-target-cluster",
  "cluster_endpoint": "dev-target-cluster.cluster-123456789012.us-west-2.rds.amazonaws.com",
  "cluster_port": 5432,
  "users_created": [
    {
      "username": "app_user",
      "privileges": ["SELECT", "INSERT", "UPDATE", "DELETE"]
    },
    {
      "username": "readonly_user",
      "privileges": ["SELECT"]
    }
  ],
  "next_step": "verify_restore"
}
```

### 8. Verify Restore Lambda

This Lambda verifies the restored cluster's functionality.

```bash
# Invoke the verify restore Lambda
aws lambda invoke \
  --function-name aurora-restore-verify-restore-dev \
  --payload '{
    "operation_id": "dev-restore-2023-06-01"
  }' \
  response.json

# Check the response
cat response.json
```

Expected response:
```json
{
  "operation_id": "dev-restore-2023-06-01",
  "status": "success",
  "message": "Successfully verified cluster dev-target-cluster",
  "target_cluster_id": "dev-target-cluster",
  "cluster_endpoint": "dev-target-cluster.cluster-123456789012.us-west-2.rds.amazonaws.com",
  "cluster_port": 5432,
  "schema_info": {
    "schemas": ["public", "app_schema"],
    "tables": [
      {"schema": "public", "name": "users"},
      {"schema": "public", "name": "products"},
      {"schema": "app_schema", "name": "orders"}
    ]
  },
  "next_step": "notify_completion"
}
```

### 9. Notify Completion Lambda

This Lambda sends notifications about the completion of the restore process.

```bash
# Invoke the notify completion Lambda
aws lambda invoke \
  --function-name aurora-restore-notify-completion-dev \
  --payload '{
    "operation_id": "dev-restore-2023-06-01"
  }' \
  response.json

# Check the response
cat response.json
```

Expected response:
```json
{
  "operation_id": "dev-restore-2023-06-01",
  "status": "success",
  "message": "Successfully sent completion notifications for cluster dev-target-cluster",
  "target_cluster_id": "dev-target-cluster",
  "status": "completed",
  "sns_message_id": "12345678-1234-5678-1234-567812345678",
  "sqs_message_id": "56781234-5678-1234-5678-123456781234",
  "next_step": null
}
```

### 10. Cleanup Lambda

This Lambda cleans up resources after the restore process is complete.

```bash
# Invoke the cleanup Lambda
aws lambda invoke \
  --function-name aurora-restore-cleanup-dev \
  --payload '{
    "operation_id": "dev-restore-2023-06-01"
  }' \
  response.json

# Check the response
cat response.json
```

Expected response:
```json
{
  "operation_id": "dev-restore-2023-06-01",
  "status": "success",
  "message": "Successfully completed cleanup for operation dev-restore-2023-06-01",
  "target_cluster_id": "dev-target-cluster",
  "cleanup_results": {
    "snapshot_deleted": true,
    "state_data_deleted": true,
    "logs_deleted": true
  },
  "next_step": null
}
```

## Automated Execution Script

You can use the following script to automate the execution of the Lambda functions in sequence:

```bash
#!/bin/bash

# Set variables
OPERATION_ID="dev-restore-$(date +%Y-%m-%d)"
TARGET_DATE=$(date +%Y-%m-%d)
LAMBDA_PREFIX="aurora-restore"
ENV="dev"
REGION="us-west-2"

# Function to invoke Lambda and check response
invoke_lambda() {
  local function_name=$1
  local payload=$2
  local expected_next_step=$3
  
  echo "Invoking $function_name..."
  
  aws lambda invoke \
    --function-name "${LAMBDA_PREFIX}-${function_name}-${ENV}" \
    --region $REGION \
    --payload "$payload" \
    response.json
  
  local status=$(jq -r '.status' response.json)
  local next_step=$(jq -r '.next_step' response.json)
  
  echo "Response: $(cat response.json)"
  
  if [ "$status" != "success" ]; then
    echo "Error: Lambda invocation failed"
    exit 1
  fi
  
  if [ "$next_step" != "$expected_next_step" ] && [ "$expected_next_step" != "any" ]; then
    echo "Error: Unexpected next step. Expected $expected_next_step, got $next_step"
    exit 1
  fi
  
  return 0
}

# Step 1: Snapshot Check
invoke_lambda "snapshot-check" "{\"operation_id\": \"$OPERATION_ID\", \"target_date\": \"$TARGET_DATE\"}" "copy_snapshot"

# Step 2: Copy Snapshot
SNAPSHOT_NAME=$(jq -r '.snapshot_name' response.json)
invoke_lambda "copy-snapshot" "{\"operation_id\": \"$OPERATION_ID\", \"snapshot_name\": \"$SNAPSHOT_NAME\"}" "check_copy_status"

# Step 3: Check Copy Status (loop until complete)
TARGET_SNAPSHOT=$(jq -r '.target_snapshot' response.json)
while true; do
  invoke_lambda "check-copy-status" "{\"operation_id\": \"$OPERATION_ID\", \"target_snapshot\": \"$TARGET_SNAPSHOT\"}" "any"
  
  COPY_STATUS=$(jq -r '.copy_status' response.json)
  if [ "$COPY_STATUS" = "available" ]; then
    break
  fi
  
  echo "Snapshot copy in progress, waiting 30 seconds..."
  sleep 30
done

# Step 4: Delete RDS (loop until complete)
while true; do
  invoke_lambda "delete-rds" "{\"operation_id\": \"$OPERATION_ID\"}" "any"
  
  DELETION_STATUS=$(jq -r '.deletion_status' response.json)
  if [ "$DELETION_STATUS" = "completed" ] || [ "$DELETION_STATUS" = "" ]; then
    break
  fi
  
  echo "Cluster deletion in progress, waiting 30 seconds..."
  sleep 30
done

# Step 5: Restore Snapshot
invoke_lambda "restore-snapshot" "{\"operation_id\": \"$OPERATION_ID\", \"target_snapshot\": \"$TARGET_SNAPSHOT\"}" "check_restore_status"

# Step 6: Check Restore Status (loop until complete)
while true; do
  invoke_lambda "check-restore-status" "{\"operation_id\": \"$OPERATION_ID\"}" "any"
  
  CLUSTER_STATUS=$(jq -r '.cluster_status' response.json)
  if [ "$CLUSTER_STATUS" = "available" ]; then
    break
  fi
  
  echo "Cluster restore in progress, waiting 30 seconds..."
  sleep 30
done

# Step 7: Setup DB Users
invoke_lambda "setup-db-users" "{\"operation_id\": \"$OPERATION_ID\"}" "verify_restore"

# Step 8: Verify Restore
invoke_lambda "verify-restore" "{\"operation_id\": \"$OPERATION_ID\"}" "notify_completion"

# Step 9: Notify Completion
invoke_lambda "notify-completion" "{\"operation_id\": \"$OPERATION_ID\"}" "null"

# Step 10: Cleanup
invoke_lambda "cleanup" "{\"operation_id\": \"$OPERATION_ID\"}" "null"

echo "Aurora restore process completed successfully!"
```

Save this script as `run_aurora_restore.sh`, make it executable with `chmod +x run_aurora_restore.sh`, and run it with `./run_aurora_restore.sh`.

## Troubleshooting

If you encounter issues while running the Lambda functions, check the following:

1. **CloudWatch Logs**: Each Lambda function writes logs to CloudWatch. Check the logs for detailed error messages.

2. **State Data**: The state data is stored in DynamoDB. You can query the state data to see the current status of the operation.

```bash
aws dynamodb get-item \
  --table-name aurora-restore-state-dev \
  --key '{"operation_id": {"S": "dev-restore-2023-06-01"}}'
```

3. **Configuration**: Ensure that the configuration in SSM Parameter Store is correct and accessible to the Lambda functions.

4. **Permissions**: Ensure that the Lambda functions have the necessary permissions to access the required AWS services.

## Monitoring

You can monitor the progress of the Aurora restore process using the following:

1. **CloudWatch Metrics**: The Lambda functions publish metrics to CloudWatch. You can create dashboards to monitor the progress.

2. **SNS Notifications**: The notify completion Lambda function sends notifications to SNS. You can subscribe to these notifications to be notified of the completion of the restore process.

3. **SQS Messages**: The notify completion Lambda function also sends messages to SQS. You can process these messages to trigger additional workflows. 