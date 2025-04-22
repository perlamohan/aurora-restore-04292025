# Aurora Restore Pipeline Deployment Guide

This guide provides step-by-step instructions for manually deploying the Aurora restore pipeline components in AWS.

## Prerequisites

1. AWS CLI configured with appropriate permissions
2. Access to both source and target AWS accounts
3. Required SSM parameters and secrets configured

## 1. Create DynamoDB Table

Create a table to store audit logs:

```bash
aws dynamodb create-table \
    --table-name aurora-restore-audit \
    --attribute-definitions \
        AttributeName=event_id,AttributeType=S \
        AttributeName=event_type,AttributeType=S \
    --key-schema \
        AttributeName=event_id,KeyType=HASH \
        AttributeName=event_type,KeyType=RANGE \
    --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5
```

## 2. Create SNS Topic

Create an SNS topic for notifications:

```bash
aws sns create-topic --name aurora-restore-notifications
```

## 3. Create Lambda Functions

For each Lambda function:

1. Create a new Lambda function in the AWS Console
2. Choose Python 3.9 runtime
3. Set the handler to `lambda_function.lambda_handler`
4. Set the timeout to 15 minutes
5. Set memory to 256MB
6. Add the following environment variables:
   - `AUDIT_TABLE_NAME`: aurora-restore-audit
   - `SNS_TOPIC_ARN`: (ARN of the SNS topic)

Required IAM permissions for each Lambda:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "rds:DescribeDBClusterSnapshots",
                "rds:CopyDBClusterSnapshot",
                "rds:DeleteDBClusterSnapshot",
                "rds:DescribeDBClusters",
                "rds:DeleteDBCluster",
                "rds:RestoreDBClusterFromSnapshot"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "dynamodb:PutItem",
                "dynamodb:GetItem",
                "dynamodb:UpdateItem"
            ],
            "Resource": "arn:aws:dynamodb:*:*:table/aurora-restore-audit"
        },
        {
            "Effect": "Allow",
            "Action": [
                "sns:Publish"
            ],
            "Resource": "arn:aws:sns:*:*:aurora-restore-notifications"
        },
        {
            "Effect": "Allow",
            "Action": [
                "ssm:GetParameter",
                "secretsmanager:GetSecretValue"
            ],
            "Resource": "*"
        }
    ]
}
```

## 4. Create Step Functions State Machine

Create a new state machine with the following definition:

```json
{
  "Comment": "Aurora Restore Pipeline",
  "StartAt": "CheckSnapshot",
  "States": {
    "CheckSnapshot": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:REGION:ACCOUNT:function:aurora-restore-snapshot-check",
      "Next": "CopySnapshot"
    },
    "CopySnapshot": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:REGION:ACCOUNT:function:aurora-restore-copy-snapshot",
      "Next": "CheckCopyStatus"
    },
    "CheckCopyStatus": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:REGION:ACCOUNT:function:aurora-restore-check-copy-status",
      "Next": "IsCopyComplete"
    },
    "IsCopyComplete": {
      "Type": "Choice",
      "Choices": [
        {
          "Variable": "$.copy_status",
          "StringEquals": "available",
          "Next": "DeleteRDS"
        }
      ],
      "Default": "WaitForCopy"
    },
    "WaitForCopy": {
      "Type": "Wait",
      "Seconds": 300,
      "Next": "CheckCopyStatus"
    },
    "DeleteRDS": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:REGION:ACCOUNT:function:aurora-restore-delete-rds",
      "Next": "RestoreSnapshot"
    },
    "RestoreSnapshot": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:REGION:ACCOUNT:function:aurora-restore-restore-snapshot",
      "Next": "CheckRestoreStatus"
    },
    "CheckRestoreStatus": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:REGION:ACCOUNT:function:aurora-restore-check-restore-status",
      "Next": "IsRestoreComplete"
    },
    "IsRestoreComplete": {
      "Type": "Choice",
      "Choices": [
        {
          "Variable": "$.restore_status",
          "StringEquals": "available",
          "Next": "SetupDBUsers"
        }
      ],
      "Default": "WaitForRestore"
    },
    "WaitForRestore": {
      "Type": "Wait",
      "Seconds": 300,
      "Next": "CheckRestoreStatus"
    },
    "SetupDBUsers": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:REGION:ACCOUNT:function:aurora-restore-setup-db-users",
      "Next": "ArchiveSnapshot"
    },
    "ArchiveSnapshot": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:REGION:ACCOUNT:function:aurora-restore-archive-snapshot",
      "Next": "SendNotification"
    },
    "SendNotification": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:REGION:ACCOUNT:function:aurora-restore-sns-notification",
      "End": true
    }
  }
}
```

## 5. Create EventBridge Rule

Create a rule to trigger the pipeline daily:

```bash
aws events put-rule \
    --name aurora-restore-daily \
    --schedule-expression "cron(0 1 * * ? *)" \
    --state ENABLED
```

Add the Step Functions state machine as a target:

```bash
aws events put-targets \
    --rule aurora-restore-daily \
    --targets "Id"="1","Arn"="arn:aws:states:REGION:ACCOUNT:stateMachine:aurora-restore-pipeline"
```

## 6. Configure SSM Parameters

Create the required SSM parameters:

```bash
aws ssm put-parameter \
    --name "/aurora-restore/source-account-id" \
    --value "SOURCE_ACCOUNT_ID" \
    --type String

aws ssm put-parameter \
    --name "/aurora-restore/target-account-id" \
    --value "TARGET_ACCOUNT_ID" \
    --type String

aws ssm put-parameter \
    --name "/aurora-restore/source-region" \
    --value "SOURCE_REGION" \
    --type String

aws ssm put-parameter \
    --name "/aurora-restore/target-region" \
    --value "TARGET_REGION" \
    --type String

aws ssm put-parameter \
    --name "/aurora-restore/source-cluster-id" \
    --value "SOURCE_CLUSTER_ID" \
    --type String

aws ssm put-parameter \
    --name "/aurora-restore/target-cluster-id" \
    --value "TARGET_CLUSTER_ID" \
    --type String

aws ssm put-parameter \
    --name "/aurora-restore/snapshot-prefix" \
    --value "SNAPSHOT_PREFIX" \
    --type String
```

## 7. Configure Secrets Manager

Create the database credentials secret:

```bash
aws secretsmanager create-secret \
    --name "/aurora-restore/db-credentials" \
    --secret-string '{
        "master_username": "MASTER_USERNAME",
        "master_password": "MASTER_PASSWORD",
        "database": "DATABASE_NAME",
        "app_username": "APP_USERNAME",
        "app_password": "APP_PASSWORD",
        "readonly_username": "READONLY_USERNAME",
        "readonly_password": "READONLY_PASSWORD"
    }'
```

## 8. Share KMS Key

In the source account:
1. Share the KMS key used for RDS encryption with the target account
2. Ensure the target account has permission to use the key

## 9. Test the Pipeline

1. Manually trigger the Step Functions state machine
2. Monitor the execution in CloudWatch Logs
3. Check the DynamoDB audit table for progress
4. Verify SNS notifications

## Troubleshooting

1. Check CloudWatch Logs for each Lambda function
2. Review the DynamoDB audit table for detailed status
3. Verify IAM permissions if operations fail
4. Ensure KMS key sharing is properly configured
5. Check network connectivity between accounts 