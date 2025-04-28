# Aurora Restore Pipeline Troubleshooting Guide

This guide provides detailed information on how to diagnose and resolve common issues with the Aurora Restore Pipeline.

## Table of Contents

1. [General Troubleshooting Steps](#general-troubleshooting-steps)
2. [Step Functions Issues](#step-functions-issues)
3. [Lambda Function Issues](#lambda-function-issues)
4. [DynamoDB Issues](#dynamodb-issues)
5. [SNS Notification Issues](#sns-notification-issues)
6. [Secrets Manager Issues](#secrets-manager-issues)
7. [RDS Issues](#rds-issues)
8. [Network Issues](#network-issues)
9. [Permission Issues](#permission-issues)
10. [Monitoring and Alerting](#monitoring-and-alerting)

## General Troubleshooting Steps

When encountering issues with the Aurora Restore Pipeline, follow these general steps:

1. **Check CloudWatch Logs**: All components of the pipeline log to CloudWatch Logs. Check the logs for error messages and stack traces.

2. **Check DynamoDB Audit Table**: The audit table contains detailed information about each step of the restore process, including error messages.

3. **Check SNS Notifications**: Error notifications are sent to the SNS topic. Check the topic for error messages.

4. **Check CloudWatch Alarms**: CloudWatch alarms are configured to monitor the health of the pipeline. Check the alarms for any triggered alerts.

5. **Check IAM Permissions**: Ensure that all components have the necessary permissions to perform their tasks.

## Step Functions Issues

### Execution Failures

If the Step Functions state machine execution fails:

1. Check the CloudWatch Logs for the Lambda function that failed.
2. Check the DynamoDB audit table for error details.
3. Check the SNS topic for error notifications.
4. Check the Step Functions execution history for error details.

### State Machine Definition Issues

If the Step Functions state machine definition is incorrect:

1. Check the CloudFormation template for the state machine definition.
2. Validate the state machine definition using the AWS Step Functions console.
3. Check the IAM permissions for the Step Functions execution role.

## Lambda Function Issues

### Function Errors

If a Lambda function fails:

1. Check the CloudWatch Logs for the Lambda function.
2. Check the DynamoDB audit table for error details.
3. Check the SNS topic for error notifications.
4. Check the Lambda function configuration for any issues.

### Function Timeouts

If a Lambda function times out:

1. Check the CloudWatch Logs for the Lambda function.
2. Check the DynamoDB audit table for error details.
3. Check the Lambda function configuration for the timeout setting.
4. Consider increasing the timeout setting if the function consistently times out.

### Function Memory Issues

If a Lambda function runs out of memory:

1. Check the CloudWatch Logs for the Lambda function.
2. Check the DynamoDB audit table for error details.
3. Check the Lambda function configuration for the memory setting.
4. Consider increasing the memory setting if the function consistently runs out of memory.

## DynamoDB Issues

### Table Capacity Issues

If the DynamoDB table capacity is exceeded:

1. Check the CloudWatch Logs for DynamoDB errors.
2. Check the DynamoDB table capacity.
3. Consider increasing the table capacity if the issue persists.

### Table Permission Issues

If the DynamoDB table permissions are incorrect:

1. Check the CloudWatch Logs for DynamoDB errors.
2. Check the IAM permissions for the Lambda functions and Step Functions execution role.
3. Ensure that the Lambda functions and Step Functions execution role have the necessary permissions to access the DynamoDB table.

## SNS Notification Issues

### Notification Delivery Issues

If SNS notifications are not delivered:

1. Check the CloudWatch Logs for SNS errors.
2. Check the SNS topic permissions.
3. Check the SNS topic subscriptions.
4. Ensure that the Lambda functions and Step Functions execution role have the necessary permissions to publish to the SNS topic.

### Notification Permission Issues

If the SNS topic permissions are incorrect:

1. Check the CloudWatch Logs for SNS errors.
2. Check the IAM permissions for the Lambda functions and Step Functions execution role.
3. Ensure that the Lambda functions and Step Functions execution role have the necessary permissions to publish to the SNS topic.

## Secrets Manager Issues

### Secret Access Issues

If a secret cannot be accessed:

1. Check the CloudWatch Logs for Secrets Manager errors.
2. Check the IAM permissions for the Lambda functions and Step Functions execution role.
3. Ensure that the Lambda functions and Step Functions execution role have the necessary permissions to access the secret.

### Secret Permission Issues

If the secret permissions are incorrect:

1. Check the CloudWatch Logs for Secrets Manager errors.
2. Check the IAM permissions for the Lambda functions and Step Functions execution role.
3. Ensure that the Lambda functions and Step Functions execution role have the necessary permissions to access the secret.

## RDS Issues

### Snapshot Issues

If there are issues with RDS snapshots:

1. Check the CloudWatch Logs for RDS errors.
2. Check the DynamoDB audit table for error details.
3. Check the RDS console for snapshot status.
4. Ensure that the Lambda functions and Step Functions execution role have the necessary permissions to access the RDS snapshots.

### Cluster Issues

If there are issues with RDS clusters:

1. Check the CloudWatch Logs for RDS errors.
2. Check the DynamoDB audit table for error details.
3. Check the RDS console for cluster status.
4. Ensure that the Lambda functions and Step Functions execution role have the necessary permissions to access the RDS clusters.

## Network Issues

### VPC Issues

If there are issues with the VPC:

1. Check the CloudWatch Logs for VPC errors.
2. Check the VPC console for VPC status.
3. Ensure that the Lambda functions are configured to use the correct VPC, subnets, and security groups.

### Subnet Issues

If there are issues with the subnets:

1. Check the CloudWatch Logs for subnet errors.
2. Check the VPC console for subnet status.
3. Ensure that the Lambda functions are configured to use the correct subnets.

### Security Group Issues

If there are issues with the security groups:

1. Check the CloudWatch Logs for security group errors.
2. Check the VPC console for security group status.
3. Ensure that the Lambda functions are configured to use the correct security groups.

## Permission Issues

### IAM Role Issues

If there are issues with the IAM roles:

1. Check the CloudWatch Logs for IAM errors.
2. Check the IAM console for role status.
3. Ensure that the IAM roles have the necessary permissions.

### IAM Policy Issues

If there are issues with the IAM policies:

1. Check the CloudWatch Logs for IAM errors.
2. Check the IAM console for policy status.
3. Ensure that the IAM policies have the necessary permissions.

## Monitoring and Alerting

### CloudWatch Alarms

The following CloudWatch alarms are configured to monitor the health of the pipeline:

- `aurora-restore-execution-failures`: Alarms when Step Functions execution failures occur.
- `aurora-restore-lambda-errors`: Alarms when Lambda function errors occur.

### CloudWatch Metrics

The following CloudWatch metrics are monitored:

- `ExecutionsFailed`: Number of Step Functions execution failures.
- `Errors`: Number of Lambda function errors.
- `Invocations`: Number of Lambda function invocations.
- `Duration`: Duration of Lambda function executions.
- `Throttles`: Number of Lambda function throttles.

### CloudWatch Logs

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