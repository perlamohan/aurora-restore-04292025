# Manual Implementation Guide for Aurora Restore Pipeline

This guide provides step-by-step instructions for manually implementing the Aurora Restore Pipeline without using CloudFormation. This approach is useful when you need to implement the pipeline in environments where CloudFormation deployment is not possible or when you need to customize the implementation for specific requirements.

## Prerequisites

- AWS CLI installed and configured with appropriate credentials
- Access to create IAM roles and policies
- Access to create and manage AWS Secrets Manager secrets
- Access to create and manage Lambda functions
- Access to create and manage Step Functions state machines
- Access to create and manage DynamoDB tables
- Access to create and manage SNS topics
- Access to create and manage CloudWatch Logs and Alarms

## Implementation Steps

### 1. Set Up Environment Variables

Before running any scripts, set the required environment variables:

```bash
export ENVIRONMENT="dev"  # or "prod", "staging", etc.
export REGION="us-east-1"  # or your preferred region
```

### 2. Create Secrets and IAM Roles

Run the setup script to create the necessary secrets and IAM roles:

```bash
chmod +x setup_secrets.sh
./setup_secrets.sh
```

This script will:
- Create master credentials secret in Secrets Manager
- Create application credentials secret in Secrets Manager
- Create IAM role for Lambda functions with necessary permissions
- Create IAM role for DBA team with necessary permissions

After running the script, update the secrets with actual credentials using the commands provided in the script output.

### 3. Create DynamoDB Tables

Create the DynamoDB tables for storing the Aurora restore audit trail:

```bash
aws dynamodb create-table \
    --table-name "aurora-restore-audit-${ENVIRONMENT}" \
    --attribute-definitions \
        AttributeName=operation_id,AttributeType=S \
        AttributeName=timestamp,AttributeType=S \
    --key-schema \
        AttributeName=operation_id,KeyType=HASH \
        AttributeName=timestamp,KeyType=RANGE \
    --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5 \
    --region $REGION
```

### 4. Create SNS Topics

Create SNS topics for notifications:

```bash
aws sns create-topic \
    --name "aurora-restore-notifications-${ENVIRONMENT}" \
    --region $REGION
```

### 5. Create Lambda Functions

For each Lambda function in the pipeline:

1. Create a ZIP file containing the function code and dependencies
2. Create the Lambda function using the AWS CLI
3. Configure environment variables, VPC settings, and other parameters

Example for the copy-snapshot function:

```bash
# Create deployment package
cd lambda
zip -r ../copy-snapshot.zip copy_snapshot.py utils/

# Create Lambda function
aws lambda create-function \
    --function-name "aurora-restore-copy-snapshot-${ENVIRONMENT}" \
    --runtime python3.9 \
    --handler copy_snapshot.lambda_handler \
    --role "arn:aws:iam::YOUR_ACCOUNT_ID:role/aurora-restore-lambda-role-${ENVIRONMENT}" \
    --zip-file fileb://copy-snapshot.zip \
    --timeout 300 \
    --memory-size 256 \
    --environment "Variables={ENVIRONMENT=${ENVIRONMENT},DYNAMODB_TABLE=aurora-restore-audit-${ENVIRONMENT},SNS_TOPIC=arn:aws:sns:${REGION}:YOUR_ACCOUNT_ID:aurora-restore-notifications-${ENVIRONMENT}}" \
    --vpc-config SubnetIds=subnet-xxxxx,subnet-yyyyy,SecurityGroupIds=sg-zzzzz \
    --region $REGION
```

Repeat this process for all Lambda functions in the pipeline.

### 6. Create Step Functions State Machine

Create the Step Functions state machine:

```bash
aws stepfunctions create-state-machine \
    --name "aurora-restore-pipeline-${ENVIRONMENT}" \
    --definition file://state-machine-definition.json \
    --role-arn "arn:aws:iam::YOUR_ACCOUNT_ID:role/aurora-restore-stepfunctions-role-${ENVIRONMENT}" \
    --region $REGION
```

### 7. Set Up CloudWatch Alarms

Create CloudWatch alarms for monitoring:

```bash
aws cloudwatch put-metric-alarm \
    --alarm-name "aurora-restore-pipeline-failures-${ENVIRONMENT}" \
    --alarm-description "Alarm for Aurora restore pipeline failures" \
    --metric-name "ExecutionsFailed" \
    --namespace "AWS/States" \
    --statistic "Sum" \
    --period 300 \
    --threshold 1 \
    --comparison-operator "GreaterThanOrEqualToThreshold" \
    --evaluation-periods 1 \
    --alarm-actions "arn:aws:sns:${REGION}:YOUR_ACCOUNT_ID:aurora-restore-notifications-${ENVIRONMENT}" \
    --dimensions Name=StateMachineArn,Value="arn:aws:states:${REGION}:YOUR_ACCOUNT_ID:stateMachine:aurora-restore-pipeline-${ENVIRONMENT}" \
    --region $REGION
```

## Testing the Implementation

1. Test each Lambda function individually using the AWS Console or AWS CLI
2. Test the Step Functions state machine with a sample execution
3. Verify that notifications are being sent to the SNS topic
4. Verify that audit events are being recorded in the DynamoDB table

## Troubleshooting

If you encounter issues during the implementation:

1. Check CloudWatch Logs for Lambda function errors
2. Verify IAM permissions for all roles
3. Ensure all environment variables are set correctly
4. Check VPC configuration for Lambda functions
5. Verify that secrets are accessible to the Lambda functions

## Maintenance

Regular maintenance tasks:

1. Update Lambda function code as needed
2. Rotate secrets periodically
3. Monitor CloudWatch alarms and logs
4. Review and update IAM permissions as needed
5. Backup DynamoDB tables regularly

## Cleanup

To remove all resources created during the manual implementation:

1. Delete the Step Functions state machine
2. Delete all Lambda functions
3. Delete the DynamoDB tables
4. Delete the SNS topics
5. Delete the secrets from Secrets Manager
6. Delete the IAM roles and policies

## Security Considerations

- Regularly rotate secrets and credentials
- Use the principle of least privilege for IAM roles
- Enable encryption for all resources
- Monitor and audit access to resources
- Implement proper network security with VPC and security groups 