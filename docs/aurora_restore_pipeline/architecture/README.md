# Aurora Restore Pipeline Architecture

## Overview

The Aurora Restore Pipeline is a serverless application designed to automate the process of restoring Aurora database clusters from snapshots. This document provides a detailed overview of the architecture, components, and data flow of the pipeline.

## Architecture Diagram

![System Architecture](../diagrams/system_architecture.png)

## Components

### 1. Lambda Functions

The pipeline consists of the following Lambda functions:

1. **snapshot-check**: Validates the source snapshot and checks its availability.
2. **copy-snapshot**: Copies the snapshot from the source region to the target region.
3. **check-copy-status**: Checks the status of the snapshot copy operation.
4. **delete-rds**: Deletes an existing RDS cluster in the target region (if needed).
5. **check-delete-status**: Checks the status of the cluster deletion operation.
6. **restore-snapshot**: Restores the Aurora cluster from the snapshot.
7. **check-restore-status**: Checks the status of the restore operation.
8. **setup-db-users**: Sets up database users and permissions.
9. **archive-snapshot**: Archives the snapshot after successful restore.
10. **sns-notification**: Sends notifications about the status of the restore process.

Each Lambda function is designed to be idempotent, with standardized error handling and logging through the shared utilities module.

### 2. Utility Module

The pipeline uses a consolidated utility module `utils/aurora_utils.py` which provides standardized functions for all Lambda functions:

#### State Management
- Operation ID generation
- Loading and saving state to DynamoDB
- Pipeline state tracking

#### Validation
- Input parameter validation
- AWS resource ID validation
- Database credential validation

#### AWS Service Interaction
- Standardized AWS API error handling
- Secure credential retrieval
- Configuration parameter management

#### Metrics and Logging
- Structured JSON logging
- CloudWatch metrics
- Audit trail logging to DynamoDB

#### Pipeline Orchestration
- Lambda function invocation
- Delayed execution through EventBridge
- Event data management

### 3. DynamoDB Tables

The pipeline uses two DynamoDB tables:

1. **State Table**: Stores the current state of each restore operation.
   - Primary Key: `operation_id` (String)
   - Sort Key: `step` (String)
   - Attributes: `timestamp` (Number), `success` (Boolean), `status` (String), and operation-specific data

2. **Audit Table**: Stores a detailed audit trail of all operations.
   - Primary Key: `event_id` (String)
   - Global Secondary Index: `operation_id` (String)
   - Attributes: `event_type` (String), `status` (String), `timestamp` (String), `details` (Map)

### 4. SNS Topics

The pipeline uses an SNS topic to send notifications about the status of restore operations. Notifications are sent for:
- Successful completion of the restore process
- Failures and errors during any step
- Important state transitions

### 5. CloudWatch Metrics and Logs

All components of the pipeline log to CloudWatch Logs and publish metrics to CloudWatch. The following metrics are tracked:
- Duration of each step
- Success/failure of each step
- Number of retries
- Total operation duration

### 6. Secrets Manager and SSM Parameter Store

The pipeline retrieves configuration from:
- **Secrets Manager**: Secure storage of database credentials
- **SSM Parameter Store**: Configuration parameters such as regions, cluster IDs, and VPC details

## Data Flow

The pipeline follows this general flow:

1. **Initiate Pipeline**: An event (manual or scheduled) triggers the `snapshot-check` function.

2. **Snapshot Check**: The function validates that the source snapshot exists and is available.

3. **Copy Snapshot**: 
   - If source and target regions differ: The snapshot is copied to the target region.
   - If regions are the same: This step is skipped, and the process continues.

4. **Check Copy Status**:
   - If copying: The function checks status until complete or failed.
   - If same region: This step confirms snapshot availability and continues.

5. **Delete Existing Cluster** (optional):
   - If a cluster with the target name exists, it is deleted.
   - The `check-delete-status` function monitors until deletion is complete.

6. **Restore Snapshot**: The snapshot is restored to create a new Aurora cluster.

7. **Check Restore Status**: The function monitors the restore operation until complete.

8. **Setup Database Users**: Once the cluster is available, database users are configured.

9. **Archive Snapshot** (optional): The target snapshot is archived if no longer needed.

10. **Send Notification**: A notification is sent upon successful completion or failure.

## Error Handling

The pipeline implements robust error handling:

1. **Standardized AWS Error Handling**: All AWS API errors are handled through the `handle_aws_error` utility function, which:
   - Logs detailed error information
   - Records the error in the audit table
   - Returns standardized error responses
   - Updates CloudWatch metrics

2. **State Persistence**: All operations save their state to DynamoDB, allowing for:
   - Recovery from failures
   - Resumability
   - Audit trail of operations

3. **Retry Logic**: 
   - Transient errors are retried with exponential backoff
   - CloudWatch alarms alert on repeated failures
   - Metrics track retry counts

4. **Fallbacks**:
   - Configuration retrieval implements fallbacks to environment variables
   - Lambda functions handle missing state by reconstructing from available information

## Security

The Aurora Restore Pipeline implements comprehensive security measures:

1. **IAM Roles**: Each function has a dedicated IAM role with least-privilege permissions.

2. **Secrets Management**: Database credentials are stored in AWS Secrets Manager and accessed securely at runtime.

3. **Encryption**: 
   - Data at rest encryption for snapshots
   - KMS encryption for sensitive DynamoDB data
   - In-transit encryption for all API calls

4. **Validation**: All inputs are validated before processing to prevent injection attacks.

5. **VPC Configuration**: Lambda functions can run within a VPC with appropriate security groups.

## Monitoring and Alerting

The pipeline provides comprehensive monitoring capabilities:

1. **CloudWatch Metrics**: All functions publish metrics for:
   - Operation duration
   - Success/failure counts
   - Resource utilization

2. **CloudWatch Alarms**: Configured to alert on:
   - Function failures
   - Excessive duration
   - Repeated retry attempts

3. **Audit Trail**: A detailed audit trail in DynamoDB records:
   - All operation steps
   - Success/failure status
   - Detailed error information
   - Timing information

4. **Notifications**: SNS notifications for:
   - Operation completion (success/failure)
   - Critical error conditions

## Deployment

The pipeline is deployed using infrastructure as code (CloudFormation/Terraform) with:
- Environment-specific configurations
- Version-controlled templates
- CI/CD pipeline integration

## Conclusion

The Aurora Restore Pipeline provides a robust, secure, and scalable solution for automating Aurora database restores from snapshots. The consolidated utilities module ensures consistent behavior across all functions, with standardized error handling, state management, and logging. 