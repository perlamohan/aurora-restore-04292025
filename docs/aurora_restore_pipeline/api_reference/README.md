# Aurora Restore Pipeline API Reference

This document provides detailed API documentation for all Lambda functions in the Aurora Restore Pipeline.

## Overview

The Aurora Restore Pipeline consists of several Lambda functions that work together to automate the process of restoring Aurora database clusters from snapshots. Each Lambda function has a specific role in the restore process and exposes a well-defined API.

## Common Utility Functions

All Lambda functions in the pipeline use the consolidated `utils.aurora_utils` module which provides standardized utilities:

### State Management
- `get_operation_id(event)`: Extracts or generates a unique operation ID
- `load_state(operation_id, step=None)`: Loads the state for an operation 
- `save_state(operation_id, state)`: Saves state information to DynamoDB

### Validation and Configuration
- `get_config()`: Retrieves configuration from SSM Parameter Store
- `validate_required_params(params)`: Validates the presence of required parameters
- `validate_cluster_id(cluster_id)`: Validates RDS cluster ID format
- `validate_snapshot_id(snapshot_id)`: Validates snapshot ID format
- `validate_region(region)`: Validates AWS region format
- `validate_vpc_config(vpc_id, subnet_ids, security_group_ids)`: Validates VPC configuration
- `validate_db_credentials(credentials)`: Validates database credentials

### AWS Service Interaction
- `handle_aws_error(error, operation_id, step)`: Standardized AWS error handling
- `get_ssm_parameter(param_name, default=None)`: Retrieves SSM parameters
- `get_secret(secret_name)`: Retrieves secrets from Secrets Manager
- `send_notification(topic_arn, subject, message)`: Sends SNS notifications

### Pipeline Orchestration  
- `trigger_next_step(operation_id, next_step, event_data, delay_seconds=0)`: Triggers the next Lambda function

### Metrics and Logging
- `log_audit_event(operation_id, event_type, status, details)`: Logs audit events
- `update_metrics(operation_id, metric_name, value, unit)`: Updates CloudWatch metrics

## Common Response Format

All Lambda functions return responses in the following format:

```json
{
  "statusCode": 200,
  "body": {
    "message": "Operation completed successfully",
    "operation_id": "op-123456789",
    "data": {
      // Function-specific data
    }
  }
}
```

In case of errors, the response will have a non-200 status code and an error message:

```json
{
  "statusCode": 400,
  "body": {
    "message": "Error message describing what went wrong",
    "operation_id": "op-123456789",
    "error": "Detailed error information",
    "error_type": "ValidationError"
  }
}
```

## Lambda Functions

### 1. snapshot-check

**Purpose**: Validates the source snapshot and checks its availability.

**Input**:
```json
{
  "date": "2023-05-15", // Optional, uses yesterday's date if not provided
  "operation_id": "op-123456" // Optional, generated if not provided
}
```

**Output (Success)**:
```json
{
  "statusCode": 200,
  "body": {
    "message": "Snapshot found successfully",
    "operation_id": "op-123456",
    "snapshot_name": "my-snapshot",
    "snapshot_arn": "arn:aws:rds:us-east-1:123456789012:cluster-snapshot:my-snapshot",
    "source_region": "us-east-1",
    "target_region": "us-west-2",
    "snapshot_status": "available"
  }
}
```

**Output (Error)**:
```json
{
  "statusCode": 404,
  "body": {
    "message": "Snapshot not found in region us-east-1",
    "operation_id": "op-123456",
    "source_region": "us-east-1",
    "snapshot_name": "my-snapshot"
  }
}
```

**Error Codes**:
- 400: Invalid input parameters
- 404: Snapshot not found
- 500: Internal server error

### 2. copy-snapshot

**Purpose**: Copies the snapshot from the source region to the target region.

**Input**:
```json
{
  "operation_id": "op-123456",
  "snapshot_name": "my-snapshot",
  "snapshot_arn": "arn:aws:rds:us-east-1:123456789012:cluster-snapshot:my-snapshot",
  "source_region": "us-east-1",
  "target_region": "us-west-2",
  "target_snapshot_name": "my-snapshot-copy" // Optional
}
```

**Output (Success)**:
```json
{
  "statusCode": 200,
  "body": {
    "message": "Snapshot copy initiated",
    "operation_id": "op-123456",
    "snapshot_name": "my-snapshot",
    "source_region": "us-east-1",
    "target_region": "us-west-2",
    "target_snapshot_name": "my-snapshot-copy",
    "copy_status": "copying"
  }
}
```

**Special Case (Same Region)**:
```json
{
  "statusCode": 200,
  "body": {
    "message": "No need to copy snapshot, regions are the same",
    "operation_id": "op-123456",
    "snapshot_name": "my-snapshot",
    "source_region": "us-east-1",
    "target_region": "us-east-1"
  }
}
```

**Error Codes**:
- 400: Invalid input parameters
- 500: Internal server error

### 3. check-copy-status

**Purpose**: Checks the status of the snapshot copy operation.

**Input**:
```json
{
  "operation_id": "op-123456",
  "target_snapshot_name": "my-snapshot-copy",
  "target_region": "us-west-2",
  "source_region": "us-east-1"
}
```

**Output (Success - Available)**:
```json
{
  "statusCode": 200,
  "body": {
    "message": "Snapshot copy is complete",
    "operation_id": "op-123456",
    "target_snapshot_name": "my-snapshot-copy",
    "region": "us-west-2",
    "status": "available"
  }
}
```

**Output (In Progress)**:
```json
{
  "statusCode": 202,
  "body": {
    "message": "Snapshot copy is still in progress",
    "operation_id": "op-123456",
    "target_snapshot_name": "my-snapshot-copy",
    "region": "us-west-2",
    "status": "copying",
    "retry_after": 60
  }
}
```

**Output (Same Region)**:
```json
{
  "statusCode": 200,
  "body": {
    "message": "No need to check copy status, source and target regions are the same",
    "operation_id": "op-123456",
    "target_snapshot_name": "my-snapshot",
    "region": "us-east-1",
    "status": "available"
  }
}
```

**Error Codes**:
- 400: Invalid input parameters
- 404: Snapshot not found
- 500: Internal server error

### 4. delete-rds

**Purpose**: Deletes an existing RDS cluster in the target region (if needed).

**Input**:
```json
{
  "operation_id": "op-123456",
  "target_cluster_id": "my-cluster",
  "target_region": "us-west-2",
  "skip_final_snapshot": true // Optional, defaults to true
}
```

**Output (Success)**:
```json
{
  "statusCode": 200,
  "body": {
    "message": "Cluster deletion initiated",
    "operation_id": "op-123456",
    "target_cluster_id": "my-cluster",
    "target_region": "us-west-2",
    "status": "deleting"
  }
}
```

**Error Codes**:
- 400: Invalid input parameters
- 404: Cluster not found
- 500: Internal server error

### 5. check-delete-status

**Purpose**: Checks the status of a cluster deletion operation.

**Input**:
```json
{
  "operation_id": "op-123456",
  "target_cluster_id": "my-cluster",
  "target_region": "us-west-2"
}
```

**Output (Success - Deleted)**:
```json
{
  "statusCode": 200,
  "body": {
    "message": "Cluster deletion completed",
    "operation_id": "op-123456",
    "target_cluster_id": "my-cluster",
    "target_region": "us-west-2"
  }
}
```

**Output (In Progress)**:
```json
{
  "statusCode": 202,
  "body": {
    "message": "Cluster deletion is still in progress",
    "operation_id": "op-123456",
    "target_cluster_id": "my-cluster",
    "target_region": "us-west-2",
    "status": "deleting",
    "retry_after": 60
  }
}
```

**Error Codes**:
- 400: Invalid input parameters
- 500: Internal server error

### 6. restore-snapshot

**Purpose**: Restores the Aurora cluster from the snapshot.

**Input**:
```json
{
  "operation_id": "op-123456",
  "target_snapshot_name": "my-snapshot-copy",
  "target_region": "us-west-2",
  "target_cluster_id": "my-restored-cluster",
  "db_subnet_group_name": "my-subnet-group",
  "vpc_security_group_ids": ["sg-12345678"]
}
```

**Output (Success)**:
```json
{
  "statusCode": 200,
  "body": {
    "message": "Snapshot restore initiated",
    "operation_id": "op-123456",
    "target_snapshot_name": "my-snapshot-copy",
    "target_region": "us-west-2",
    "target_cluster_id": "my-restored-cluster",
    "status": "creating"
  }
}
```

**Error Codes**:
- 400: Invalid input parameters
- 404: Snapshot not found
- 500: Internal server error

### 7. check-restore-status

**Purpose**: Checks the status of the restore operation.

**Input**:
```json
{
  "operation_id": "op-123456",
  "target_cluster_id": "my-restored-cluster",
  "target_region": "us-west-2"
}
```

**Output (Success - Available)**:
```json
{
  "statusCode": 200,
  "body": {
    "message": "Cluster restore completed",
    "operation_id": "op-123456",
    "target_cluster_id": "my-restored-cluster",
    "target_region": "us-west-2",
    "status": "available",
    "cluster_endpoint": "my-restored-cluster.cluster-xyz.us-west-2.rds.amazonaws.com",
    "cluster_port": 5432
  }
}
```

**Output (In Progress)**:
```json
{
  "statusCode": 202,
  "body": {
    "message": "Cluster restore is still in progress",
    "operation_id": "op-123456",
    "target_cluster_id": "my-restored-cluster",
    "target_region": "us-west-2",
    "status": "creating",
    "retry_after": 60
  }
}
```

**Error Codes**:
- 400: Invalid input parameters
- 404: Cluster not found
- 500: Internal server error

### 8. setup-db-users

**Purpose**: Sets up database users and permissions.

**Input**:
```json
{
  "operation_id": "op-123456",
  "target_cluster_id": "my-restored-cluster",
  "cluster_endpoint": "my-restored-cluster.cluster-xyz.us-west-2.rds.amazonaws.com",
  "cluster_port": 5432
}
```

**Output (Success)**:
```json
{
  "statusCode": 200,
  "body": {
    "message": "Database users configured successfully",
    "operation_id": "op-123456",
    "target_cluster_id": "my-restored-cluster",
    "cluster_endpoint": "my-restored-cluster.cluster-xyz.us-west-2.rds.amazonaws.com"
  }
}
```

**Error Codes**:
- 400: Invalid input parameters
- 500: Database connection error
- 500: Internal server error

### 9. archive-snapshot

**Purpose**: Archives the snapshot after successful restore.

**Input**:
```json
{
  "operation_id": "op-123456",
  "target_snapshot_name": "my-snapshot-copy",
  "target_region": "us-west-2"
}
```

**Output (Success)**:
```json
{
  "statusCode": 200,
  "body": {
    "message": "Snapshot archived successfully",
    "operation_id": "op-123456",
    "target_snapshot_name": "my-snapshot-copy",
    "target_region": "us-west-2"
  }
}
```

**Error Codes**:
- 400: Invalid input parameters
- 404: Snapshot not found
- 500: Internal server error

### 10. sns-notification

**Purpose**: Sends notifications about the status of the restore process.

**Input**:
```json
{
  "operation_id": "op-123456",
  "status": "success",
  "message": "Aurora restore completed successfully",
  "details": {
    "target_cluster_id": "my-restored-cluster",
    "target_region": "us-west-2",
    "cluster_endpoint": "my-restored-cluster.cluster-xyz.us-west-2.rds.amazonaws.com"
  }
}
```

**Output (Success)**:
```json
{
  "statusCode": 200,
  "body": {
    "message": "Notification sent successfully",
    "operation_id": "op-123456"
  }
}
```

**Error Codes**:
- 400: Invalid input parameters
- 500: Failed to send notification
- 500: Internal server error

## Step Functions State Machine

The Step Functions state machine orchestrates the entire restore process, coordinating the execution of Lambda functions in a specific order.

**Input**:
```json
{
  "snapshot_id": "my-snapshot",
  "source_region": "us-east-1",
  "target_region": "us-west-2",
  "vpc_id": "vpc-12345678",
  "subnet_ids": ["subnet-12345678", "subnet-87654321"],
  "security_group_ids": ["sg-12345678"]
}
```

**Output**:
The Step Functions state machine does not return a direct output. Instead, it orchestrates the execution of Lambda functions and updates the DynamoDB tables with the state and audit information.

## DynamoDB Tables

The Aurora Restore Pipeline uses two DynamoDB tables for storing state and audit information.

### State Table

**Schema**:
- Primary Key: `operation_id` (String)
- Attributes:
  - `state` (Map)
  - `timestamp` (String)
  - `status` (String)

### Audit Table

**Schema**:
- Primary Key: `operation_id` (String)
- Sort Key: `timestamp` (String)
- Attributes:
  - `step` (String)
  - `status` (String)
  - `details` (Map)

## SNS Topics

The Aurora Restore Pipeline uses an SNS topic to send notifications about the status of restore operations.

**Message Format**:
```json
{
  "operation_id": "op-123456",
  "status": "success",
  "message": "Restore operation completed successfully",
  "details": {
    "cluster_identifier": "my-restored-cluster",
    "target_region": "us-west-2"
  },
  "timestamp": "2023-01-01T12:00:00Z"
}
``` 