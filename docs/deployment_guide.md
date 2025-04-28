# Aurora Restore Pipeline Deployment Guide

This guide provides detailed instructions for deploying the Aurora Restore Pipeline in your AWS environment.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Architecture Overview](#architecture-overview)
3. [Deployment Steps](#deployment-steps)
4. [Configuration](#configuration)
5. [Testing](#testing)
6. [Troubleshooting](#troubleshooting)
7. [Maintenance](#maintenance)

## Prerequisites

Before deploying the Aurora Restore Pipeline, ensure you have:

- AWS CLI installed and configured with appropriate permissions
- AWS CloudFormation access
- Access to create IAM roles, Lambda functions, and Step Functions
- Access to create DynamoDB tables
- Access to create SNS topics
- Access to create CloudWatch Logs
- Access to create CloudWatch Alarms
- Access to create Secrets Manager secrets
- Access to create KMS keys
- Access to create VPC resources (if deploying in a VPC)

## Architecture Overview

The Aurora Restore Pipeline consists of the following components:

- **Step Functions State Machine**: Orchestrates the entire restore process
- **Lambda Functions**: Execute individual steps of the restore process
- **DynamoDB Tables**: Store state and audit information
- **SNS Topics**: Send notifications about the restore process
- **CloudWatch Logs**: Store logs for all components
- **CloudWatch Alarms**: Monitor the health of the pipeline
- **Secrets Manager**: Store sensitive configuration
- **KMS Keys**: Encrypt sensitive data

## Deployment Steps

### 1. Deploy Infrastructure

```bash
# Deploy DynamoDB tables
aws cloudformation deploy \
  --template-file infrastructure/dynamodb.yaml \
  --stack-name aurora-restore-dynamodb \
  --parameter-overrides \
    Environment=dev \
    StateTableName=aurora-restore-state \
    AuditTableName=aurora-restore-audit \
    ReadCapacityUnits=5 \
    WriteCapacityUnits=5

# Deploy Lambda functions
aws cloudformation deploy \
  --template-file infrastructure/lambda.yaml \
  --stack-name aurora-restore-lambda \
  --parameter-overrides \
    Environment=dev \
    StateTableName=aurora-restore-state \
    AuditTableName=aurora-restore-audit \
    VpcId=vpc-12345678 \
    SubnetIds=subnet-12345678,subnet-87654321 \
    SecurityGroupIds=sg-12345678

# Deploy Step Functions state machine
aws cloudformation deploy \
  --template-file infrastructure/step_functions.yaml \
  --stack-name aurora-restore-step-functions \
  --parameter-overrides \
    Environment=dev \
    StateTableName=aurora-restore-state \
    AuditTableName=aurora-restore-audit \
    VpcId=vpc-12345678 \
    SubnetIds=subnet-12345678,subnet-87654321 \
    SecurityGroupIds=sg-12345678 \
    SnapshotCheckFunctionArn=arn:aws:lambda:region:account:function:aurora-restore-snapshot-check \
    CopySnapshotFunctionArn=arn:aws:lambda:region:account:function:aurora-restore-copy-snapshot \
    CheckCopyStatusFunctionArn=arn:aws:lambda:region:account:function:aurora-restore-check-copy-status \
    DeleteRDSFunctionArn=arn:aws:lambda:region:account:function:aurora-restore-delete-rds \
    RestoreSnapshotFunctionArn=arn:aws:lambda:region:account:function:aurora-restore-restore-snapshot \
    CheckRestoreStatusFunctionArn=arn:aws:lambda:region:account:function:aurora-restore-check-restore-status \
    SetupDBUsersFunctionArn=arn:aws:lambda:region:account:function:aurora-restore-setup-db-users \
    ArchiveSnapshotFunctionArn=arn:aws:lambda:region:account:function:aurora-restore-archive-snapshot \
    SNSNotificationFunctionArn=arn:aws:lambda:region:account:function:aurora-restore-sns-notification
```

### 2. Configure Secrets

```bash
# Create KMS key for encryption
aws kms create-key --description "Aurora Restore Pipeline Encryption Key"

# Create alias for the key
aws kms create-alias --alias-name alias/aurora-restore --target-key-id <key-id>

# Store database credentials in Secrets Manager
aws secretsmanager create-secret \
  --name aurora-restore/db-credentials \
  --description "Database credentials for Aurora Restore Pipeline" \
  --secret-string '{"username":"admin","password":"secret-password"}'

# Store SNS topic ARN in Secrets Manager
aws secretsmanager create-secret \
  --name aurora-restore/sns-topic-arn \
  --description "SNS topic ARN for Aurora Restore Pipeline" \
  --secret-string '{"topic_arn":"arn:aws:sns:region:account:aurora-restore-notifications"}'
```

### 3. Configure CloudWatch Alarms

```bash
# Create CloudWatch alarm for Step Functions execution failures
aws cloudwatch put-metric-alarm \
  --alarm-name aurora-restore-execution-failures \
  --alarm-description "Alarm for Aurora Restore Pipeline execution failures" \
  --metric-name ExecutionsFailed \
  --namespace AWS/States \
  --statistic Sum \
  --period 300 \
  --threshold 1 \
  --comparison-operator GreaterThanOrEqualToThreshold \
  --evaluation-periods 1 \
  --alarm-actions arn:aws:sns:region:account:aurora-restore-notifications

# Create CloudWatch alarm for Lambda function errors
aws cloudwatch put-metric-alarm \
  --alarm-name aurora-restore-lambda-errors \
  --alarm-description "Alarm for Aurora Restore Pipeline Lambda function errors" \
  --metric-name Errors \
  --namespace AWS/Lambda \
  --statistic Sum \
  --period 300 \
  --threshold 1 \
  --comparison-operator GreaterThanOrEqualToThreshold \
  --evaluation-periods 1 \
  --alarm-actions arn:aws:sns:region:account:aurora-restore-notifications
```

## Configuration

### Environment Variables

The following environment variables are used by the Lambda functions:

- `ENVIRONMENT`: The environment name (dev, prod)
- `STATE_TABLE_NAME`: The name of the DynamoDB table for state management
- `AUDIT_TABLE_NAME`: The name of the DynamoDB table for audit logging
- `SNS_TOPIC_ARN`: The ARN of the SNS topic for notifications
- `KMS_KEY_ID`: The ID of the KMS key for encryption
- `SOURCE_REGION`: The source region for snapshots
- `TARGET_REGION`: The target region for snapshots
- `VPC_ID`: The ID of the VPC for Lambda functions
- `SUBNET_IDS`: The IDs of the subnets for Lambda functions
- `SECURITY_GROUP_IDS`: The IDs of the security groups for Lambda functions

### Secrets

The following secrets are stored in AWS Secrets Manager:

- `aurora-restore/db-credentials`: Database credentials
- `aurora-restore/sns-topic-arn`: SNS topic ARN
- `aurora-restore/kms-key-id`: KMS key ID

## Testing

### Unit Testing

```bash
# Run unit tests
python -m pytest tests/unit
```

### Integration Testing

```bash
# Run integration tests
python -m pytest tests/integration
```

### End-to-End Testing

```bash
# Run end-to-end tests
python -m pytest tests/e2e
```

## Troubleshooting

### Common Issues

1. **Step Functions Execution Failures**

   - Check CloudWatch Logs for the Lambda function that failed
   - Check the DynamoDB audit table for error details
   - Check the SNS topic for error notifications

2. **Lambda Function Errors**

   - Check CloudWatch Logs for the Lambda function
   - Check the DynamoDB audit table for error details
   - Check the SNS topic for error notifications

3. **DynamoDB Table Issues**

   - Check CloudWatch Logs for DynamoDB errors
   - Check the DynamoDB table capacity
   - Check the DynamoDB table permissions

4. **SNS Notification Issues**

   - Check CloudWatch Logs for SNS errors
   - Check the SNS topic permissions
   - Check the SNS topic subscriptions

5. **Secrets Manager Issues**

   - Check CloudWatch Logs for Secrets Manager errors
   - Check the Secrets Manager permissions
   - Check the KMS key permissions

### Logging

All components of the Aurora Restore Pipeline log to CloudWatch Logs. The following log groups are created:

- `/aws/lambda/aurora-restore-snapshot-check`
- `/aws/lambda/aurora-restore-copy-snapshot`
- `/aws/lambda/aurora-restore-check-copy-status`
- `/aws/lambda/aurora-restore-delete-rds`
- `/aws/lambda/aurora-restore-restore-snapshot`
- `/aws/lambda/aurora-restore-check-restore-status`
- `/aws/lambda/aurora-restore-setup-db-users`
- `/aws/lambda/aurora-restore-archive-snapshot`
- `/aws/lambda/aurora-restore-sns-notification`

### Monitoring

The following CloudWatch metrics are monitored:

- `ExecutionsFailed`: Number of Step Functions execution failures
- `Errors`: Number of Lambda function errors
- `Invocations`: Number of Lambda function invocations
- `Duration`: Duration of Lambda function executions
- `Throttles`: Number of Lambda function throttles

## Maintenance

### Backup and Restore

- The DynamoDB tables are backed up automatically
- The Lambda functions are versioned
- The Step Functions state machine is versioned
- The Secrets Manager secrets are versioned

### Updates

To update the Aurora Restore Pipeline:

1. Update the CloudFormation templates
2. Deploy the updated templates
3. Test the updated pipeline
4. Monitor the updated pipeline

### Cleanup

To clean up the Aurora Restore Pipeline:

```bash
# Delete the CloudFormation stacks
aws cloudformation delete-stack --stack-name aurora-restore-step-functions
aws cloudformation delete-stack --stack-name aurora-restore-lambda
aws cloudformation delete-stack --stack-name aurora-restore-dynamodb

# Delete the Secrets Manager secrets
aws secretsmanager delete-secret --secret-id aurora-restore/db-credentials
aws secretsmanager delete-secret --secret-id aurora-restore/sns-topic-arn
aws secretsmanager delete-secret --secret-id aurora-restore/kms-key-id

# Delete the KMS key
aws kms delete-alias --alias-name alias/aurora-restore
aws kms schedule-key-deletion --key-id <key-id> --pending-window-in-days 7
``` 