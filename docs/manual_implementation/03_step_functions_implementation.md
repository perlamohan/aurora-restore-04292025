# Manual Implementation Guide - Step Functions Implementation

## 1. Create Step Functions State Machine

1. **Create IAM Role**
```bash
# Create trust policy
cat > step-functions-trust-policy.json << EOL
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "states.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOL

# Create role
aws iam create-role \
  --role-name aurora-restore-step-functions-role \
  --assume-role-policy-document file://step-functions-trust-policy.json

# Create policy
cat > step-functions-policy.json << EOL
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "lambda:InvokeFunction"
      ],
      "Resource": [
        "arn:aws:lambda:${AWS_REGION}:${AWS_ACCOUNT_ID}:function:aurora-restore-*"
      ]
    }
  ]
}
EOL

# Attach policy
aws iam put-role-policy \
  --role-name aurora-restore-step-functions-role \
  --policy-name aurora-restore-step-functions-policy \
  --policy-document file://step-functions-policy.json
```

2. **Create State Machine Definition**
```bash
# Get Lambda function ARNs
SNAPSHOT_CHECK_ARN=$(aws lambda get-function --function-name aurora-restore-snapshot-check-dev --query 'Configuration.FunctionArn' --output text)
COPY_SNAPSHOT_ARN=$(aws lambda get-function --function-name aurora-restore-copy-snapshot-dev --query 'Configuration.FunctionArn' --output text)
CHECK_COPY_STATUS_ARN=$(aws lambda get-function --function-name aurora-restore-check-copy-status-dev --query 'Configuration.FunctionArn' --output text)
DELETE_RDS_ARN=$(aws lambda get-function --function-name aurora-restore-delete-rds-dev --query 'Configuration.FunctionArn' --output text)
RESTORE_SNAPSHOT_ARN=$(aws lambda get-function --function-name aurora-restore-restore-snapshot-dev --query 'Configuration.FunctionArn' --output text)
CHECK_RESTORE_STATUS_ARN=$(aws lambda get-function --function-name aurora-restore-check-restore-status-dev --query 'Configuration.FunctionArn' --output text)
SETUP_DB_USERS_ARN=$(aws lambda get-function --function-name aurora-restore-setup-db-users-dev --query 'Configuration.FunctionArn' --output text)
ARCHIVE_SNAPSHOT_ARN=$(aws lambda get-function --function-name aurora-restore-archive-snapshot-dev --query 'Configuration.FunctionArn' --output text)
SNS_NOTIFICATION_ARN=$(aws lambda get-function --function-name aurora-restore-sns-notification-dev --query 'Configuration.FunctionArn' --output text)

# Create state machine definition
cat > state-machine.json << EOL
{
  "Comment": "Aurora Restore Pipeline",
  "StartAt": "SnapshotCheck",
  "States": {
    "SnapshotCheck": {
      "Type": "Task",
      "Resource": "${SNAPSHOT_CHECK_ARN}",
      "Next": "CopySnapshot",
      "Retry": [
        {
          "ErrorEquals": ["States.TaskFailed"],
          "IntervalSeconds": 3,
          "MaxAttempts": 3,
          "BackoffRate": 2
        }
      ],
      "Catch": [
        {
          "ErrorEquals": ["States.ALL"],
          "Next": "HandleFailure",
          "ResultPath": "$.error"
        }
      ]
    },
    "CopySnapshot": {
      "Type": "Task",
      "Resource": "${COPY_SNAPSHOT_ARN}",
      "Next": "CheckCopyStatus",
      "Retry": [
        {
          "ErrorEquals": ["States.TaskFailed"],
          "IntervalSeconds": 3,
          "MaxAttempts": 3,
          "BackoffRate": 2
        }
      ],
      "Catch": [
        {
          "ErrorEquals": ["States.ALL"],
          "Next": "HandleFailure",
          "ResultPath": "$.error"
        }
      ]
    },
    "CheckCopyStatus": {
      "Type": "Task",
      "Resource": "${CHECK_COPY_STATUS_ARN}",
      "Next": "IsCopyComplete",
      "Retry": [
        {
          "ErrorEquals": ["States.TaskFailed"],
          "IntervalSeconds": 3,
          "MaxAttempts": 3,
          "BackoffRate": 2
        }
      ],
      "Catch": [
        {
          "ErrorEquals": ["States.ALL"],
          "Next": "HandleFailure",
          "ResultPath": "$.error"
        }
      ]
    },
    "IsCopyComplete": {
      "Type": "Choice",
      "Choices": [
        {
          "Variable": "$.body.copy_status",
          "StringEquals": "available",
          "Next": "DeleteRDS"
        }
      ],
      "Default": "WaitForCopy"
    },
    "WaitForCopy": {
      "Type": "Wait",
      "Seconds": 30,
      "Next": "CheckCopyStatus"
    },
    "DeleteRDS": {
      "Type": "Task",
      "Resource": "${DELETE_RDS_ARN}",
      "Next": "RestoreSnapshot",
      "Retry": [
        {
          "ErrorEquals": ["States.TaskFailed"],
          "IntervalSeconds": 3,
          "MaxAttempts": 3,
          "BackoffRate": 2
        }
      ],
      "Catch": [
        {
          "ErrorEquals": ["States.ALL"],
          "Next": "HandleFailure",
          "ResultPath": "$.error"
        }
      ]
    },
    "RestoreSnapshot": {
      "Type": "Task",
      "Resource": "${RESTORE_SNAPSHOT_ARN}",
      "Next": "CheckRestoreStatus",
      "Retry": [
        {
          "ErrorEquals": ["States.TaskFailed"],
          "IntervalSeconds": 3,
          "MaxAttempts": 3,
          "BackoffRate": 2
        }
      ],
      "Catch": [
        {
          "ErrorEquals": ["States.ALL"],
          "Next": "HandleFailure",
          "ResultPath": "$.error"
        }
      ]
    },
    "CheckRestoreStatus": {
      "Type": "Task",
      "Resource": "${CHECK_RESTORE_STATUS_ARN}",
      "Next": "IsRestoreComplete",
      "Retry": [
        {
          "ErrorEquals": ["States.TaskFailed"],
          "IntervalSeconds": 3,
          "MaxAttempts": 3,
          "BackoffRate": 2
        }
      ],
      "Catch": [
        {
          "ErrorEquals": ["States.ALL"],
          "Next": "HandleFailure",
          "ResultPath": "$.error"
        }
      ]
    },
    "IsRestoreComplete": {
      "Type": "Choice",
      "Choices": [
        {
          "Variable": "$.body.restore_status",
          "StringEquals": "available",
          "Next": "SetupDBUsers"
        }
      ],
      "Default": "WaitForRestore"
    },
    "WaitForRestore": {
      "Type": "Wait",
      "Seconds": 60,
      "Next": "CheckRestoreStatus"
    },
    "SetupDBUsers": {
      "Type": "Task",
      "Resource": "${SETUP_DB_USERS_ARN}",
      "Next": "ArchiveSnapshot",
      "Retry": [
        {
          "ErrorEquals": ["States.TaskFailed"],
          "IntervalSeconds": 3,
          "MaxAttempts": 3,
          "BackoffRate": 2
        }
      ],
      "Catch": [
        {
          "ErrorEquals": ["States.ALL"],
          "Next": "HandleFailure",
          "ResultPath": "$.error"
        }
      ]
    },
    "ArchiveSnapshot": {
      "Type": "Task",
      "Resource": "${ARCHIVE_SNAPSHOT_ARN}",
      "Next": "SendNotification",
      "Retry": [
        {
          "ErrorEquals": ["States.TaskFailed"],
          "IntervalSeconds": 3,
          "MaxAttempts": 3,
          "BackoffRate": 2
        }
      ],
      "Catch": [
        {
          "ErrorEquals": ["States.ALL"],
          "Next": "HandleFailure",
          "ResultPath": "$.error"
        }
      ]
    },
    "SendNotification": {
      "Type": "Task",
      "Resource": "${SNS_NOTIFICATION_ARN}",
      "End": true,
      "Retry": [
        {
          "ErrorEquals": ["States.TaskFailed"],
          "IntervalSeconds": 3,
          "MaxAttempts": 3,
          "BackoffRate": 2
        }
      ],
      "Catch": [
        {
          "ErrorEquals": ["States.ALL"],
          "Next": "HandleFailure",
          "ResultPath": "$.error"
        }
      ]
    },
    "HandleFailure": {
      "Type": "Task",
      "Resource": "${SNS_NOTIFICATION_ARN}",
      "End": true,
      "Parameters": {
        "operation_id.$": "$.operation_id",
        "step": "pipeline",
        "status": "FAILED",
        "error.$": "$.error",
        "details": {
          "error_message.$": "$.error.Cause",
          "error_type.$": "$.error.Error"
        }
      }
    }
  }
}
EOL

# Create state machine
aws stepfunctions create-state-machine \
  --name aurora-restore-pipeline-dev \
  --role-arn arn:aws:iam::${AWS_ACCOUNT_ID}:role/aurora-restore-step-functions-role \
  --definition file://state-machine.json
```

## 2. Test State Machine

1. **Create Test Input**
```bash
cat > test-input.json << EOL
{
  "body": {
    "operation_id": "op-test002",
    "snapshot_id": "rds:my-source-snapshot",
    "source_region": "us-east-1",
    "target_region": "us-west-2",
    "target_cluster_id": "new-cluster-id"
  }
}
EOL
```

2. **Start Execution**
```bash
# Get state machine ARN
STATE_MACHINE_ARN=$(aws stepfunctions list-state-machines --query 'stateMachines[?name==`aurora-restore-pipeline-dev`].stateMachineArn' --output text)

# Start execution
aws stepfunctions start-execution \
  --state-machine-arn $STATE_MACHINE_ARN \
  --input file://test-input.json
```

3. **Monitor Execution**
```bash
# Get execution ARN from previous command output
EXECUTION_ARN="YOUR_EXECUTION_ARN"

# Check execution status
aws stepfunctions describe-execution \
  --execution-arn $EXECUTION_ARN

# Get execution history
aws stepfunctions get-execution-history \
  --execution-arn $EXECUTION_ARN
```

## 3. Monitoring and Troubleshooting

1. **CloudWatch Logs**
```bash
# View logs for each Lambda function
aws logs get-log-events \
  --log-group-name /aws/lambda/aurora-restore-copy-snapshot-dev \
  --log-stream-name $(aws logs describe-log-streams \
    --log-group-name /aws/lambda/aurora-restore-copy-snapshot-dev \
    --order-by LastEventTime \
    --descending \
    --max-items 1 \
    --query 'logStreams[0].logStreamName' \
    --output text)
```

2. **DynamoDB State**
```bash
# Check state table
aws dynamodb get-item \
  --table-name aurora-restore-state \
  --key '{"operation_id":{"S":"op-test002"}}'

# Check audit trail
aws dynamodb query \
  --table-name aurora-restore-audit \
  --key-condition-expression "operation_id = :id" \
  --expression-attribute-values '{":id":{"S":"op-test002"}}'
```

3. **SNS Notifications**
```bash
# List SNS subscriptions
aws sns list-subscriptions-by-topic \
  --topic-arn $SNS_TOPIC_ARN
```

## Next Steps

After successfully testing the Step Functions state machine:
1. Verify end-to-end pipeline execution
2. Test error handling and recovery
3. Set up monitoring and alerting
4. Document operational procedures
5. See [04_production_deployment.md](04_production_deployment.md) for production deployment steps 