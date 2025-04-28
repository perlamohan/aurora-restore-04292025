# Aurora Restore Pipeline Configuration Guide

This document provides detailed instructions for configuring the Aurora Restore Pipeline.

## Environment Variables

The Aurora Restore Pipeline uses environment variables for configuration. These variables can be set in the Lambda function configuration or in a configuration file.

### Required Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `ENVIRONMENT` | The environment (e.g., dev, test, prod) | `dev` |
| `REGION` | The AWS region where the pipeline will be deployed | `us-east-1` |
| `DYNAMODB_TABLE_NAME` | The name of the DynamoDB table for storing state and audit information | `aurora-restore-state` |
| `SNS_TOPIC_ARN` | The ARN of the SNS topic for sending notifications | `arn:aws:sns:us-east-1:123456789012:aurora-restore-notifications` |
| `KMS_KEY_ID` | The ID of the KMS key for encrypting sensitive data | `arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012` |
| `VPC_ID` | The ID of the VPC where the Lambda functions will be deployed | `vpc-12345678` |
| `SUBNET_IDS` | The IDs of the subnets where the Lambda functions will be deployed | `subnet-12345678,subnet-87654321` |
| `SECURITY_GROUP_IDS` | The IDs of the security groups to be associated with the Lambda functions | `sg-12345678` |

### Optional Environment Variables

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `LOG_LEVEL` | The log level for the Lambda functions | `INFO` | `DEBUG` |
| `MAX_RETRIES` | The maximum number of retries for the Step Functions state machine | `3` | `5` |
| `RETRY_INTERVAL_SECONDS` | The initial retry interval for the Step Functions state machine | `3` | `5` |
| `RETRY_BACKOFF_RATE` | The backoff rate for the Step Functions state machine | `2` | `1.5` |
| `STATE_MACHINE_TIMEOUT_SECONDS` | The timeout for the entire state machine execution | `7200` | `3600` |
| `LAMBDA_TIMEOUT_SECONDS` | The timeout for the Lambda functions | `300` | `600` |
| `LAMBDA_MEMORY_SIZE` | The memory size for the Lambda functions | `256` | `512` |

## Secrets

The Aurora Restore Pipeline uses AWS Secrets Manager to store sensitive configuration, such as database credentials and KMS key IDs.

### Required Secrets

| Secret Name | Description | Example |
|-------------|-------------|---------|
| `aurora-restore/master-credentials` | The master credentials for the Aurora cluster | `{"username": "admin", "password": "password"}` |
| `aurora-restore/app-credentials` | The application credentials for the Aurora cluster | `{"username": "app", "password": "password"}` |

### Creating Secrets

You can create secrets using the AWS Management Console or AWS CLI.

#### Using AWS Management Console

1. Navigate to the AWS Secrets Manager console.
2. Click on "Store a new secret".
3. Select "Other type of secret" and enter the secret value as a JSON string.
4. Enter the secret name and description.
5. Click on "Next" and then "Store".

#### Using AWS CLI

```bash
aws secretsmanager create-secret \
    --name aurora-restore/master-credentials \
    --description "Master credentials for the Aurora cluster" \
    --secret-string '{"username": "admin", "password": "password"}'

aws secretsmanager create-secret \
    --name aurora-restore/app-credentials \
    --description "Application credentials for the Aurora cluster" \
    --secret-string '{"username": "app", "password": "password"}'
```

## DynamoDB Tables

The Aurora Restore Pipeline uses two DynamoDB tables for storing state and audit information.

### State Table

The State Table stores the current state of each restore operation.

| Attribute | Type | Description |
|-----------|------|-------------|
| `operation_id` | String | The primary key, a unique identifier for the restore operation |
| `state` | Map | The current state of the restore operation |
| `timestamp` | String | The timestamp of the last update |
| `status` | String | The status of the restore operation |

### Audit Table

The Audit Table stores a detailed audit trail of all operations.

| Attribute | Type | Description |
|-----------|------|-------------|
| `operation_id` | String | The primary key, a unique identifier for the restore operation |
| `timestamp` | String | The sort key, the timestamp of the audit event |
| `step` | String | The step of the restore process |
| `status` | String | The status of the step |
| `details` | Map | Additional details about the step |

### Creating DynamoDB Tables

You can create DynamoDB tables using the AWS Management Console or AWS CLI.

#### Using AWS Management Console

1. Navigate to the AWS DynamoDB console.
2. Click on "Create table".
3. Enter the table name and primary key.
4. Configure the table settings and click on "Create".

#### Using AWS CLI

```bash
aws dynamodb create-table \
    --table-name aurora-restore-state \
    --attribute-definitions AttributeName=operation_id,AttributeType=S \
    --key-schema AttributeName=operation_id,KeyType=HASH \
    --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5

aws dynamodb create-table \
    --table-name aurora-restore-audit \
    --attribute-definitions AttributeName=operation_id,AttributeType=S AttributeName=timestamp,AttributeType=S \
    --key-schema AttributeName=operation_id,KeyType=HASH AttributeName=timestamp,KeyType=RANGE \
    --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5
```

## SNS Topics

The Aurora Restore Pipeline uses an SNS topic for sending notifications about the status of restore operations.

### Creating SNS Topics

You can create SNS topics using the AWS Management Console or AWS CLI.

#### Using AWS Management Console

1. Navigate to the AWS SNS console.
2. Click on "Create topic".
3. Enter the topic name and display name.
4. Click on "Create topic".

#### Using AWS CLI

```bash
aws sns create-topic --name aurora-restore-notifications
```

## KMS Keys

The Aurora Restore Pipeline uses AWS KMS keys to encrypt sensitive data, such as database credentials and snapshots.

### Creating KMS Keys

You can create KMS keys using the AWS Management Console or AWS CLI.

#### Using AWS Management Console

1. Navigate to the AWS KMS console.
2. Click on "Create key".
3. Configure the key settings and click on "Create key".

#### Using AWS CLI

```bash
aws kms create-key \
    --description "KMS key for Aurora Restore Pipeline" \
    --key-usage ENCRYPT_DECRYPT \
    --origin AWS_KMS \
    --policy '{
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "AWS": "arn:aws:iam::123456789012:root"
                },
                "Action": "kms:*",
                "Resource": "*"
            }
        ]
    }'
```

## VPC Configuration

The Aurora Restore Pipeline deploys Lambda functions in a VPC for enhanced security.

### Required VPC Configuration

- A VPC with at least two subnets in different Availability Zones
- Security groups with the necessary inbound and outbound rules
- NAT Gateway or VPC Endpoints for accessing AWS services from the VPC

### Creating VPC Resources

You can create VPC resources using the AWS Management Console or AWS CLI.

#### Using AWS Management Console

1. Navigate to the AWS VPC console.
2. Create a VPC with at least two subnets in different Availability Zones.
3. Create security groups with the necessary inbound and outbound rules.
4. Create a NAT Gateway or VPC Endpoints for accessing AWS services from the VPC.

#### Using AWS CLI

```bash
# Create a VPC
aws ec2 create-vpc --cidr-block 10.0.0.0/16

# Create subnets
aws ec2 create-subnet --vpc-id vpc-12345678 --cidr-block 10.0.1.0/24 --availability-zone us-east-1a
aws ec2 create-subnet --vpc-id vpc-12345678 --cidr-block 10.0.2.0/24 --availability-zone us-east-1b

# Create security groups
aws ec2 create-security-group --group-name aurora-restore-sg --description "Security group for Aurora Restore Pipeline"

# Create NAT Gateway
aws ec2 create-nat-gateway --subnet-id subnet-12345678 --allocation-id eipalloc-12345678
```

## Step Functions State Machine

The Aurora Restore Pipeline uses a Step Functions state machine to orchestrate the restore process.

### State Machine Configuration

The Step Functions state machine is configured with the following settings:

- **Timeout**: The timeout for the entire state machine execution
- **Retry Strategy**: The retry strategy for the Lambda functions
- **Error Handling**: The error handling paths for the Lambda functions

### Creating Step Functions State Machine

You can create a Step Functions state machine using the AWS Management Console or AWS CLI.

#### Using AWS Management Console

1. Navigate to the AWS Step Functions console.
2. Click on "Create state machine".
3. Enter the state machine definition and configure the settings.
4. Click on "Create state machine".

#### Using AWS CLI

```bash
aws stepfunctions create-state-machine \
    --name aurora-restore-state-machine \
    --definition '{
        "Comment": "Aurora Restore Pipeline State Machine",
        "StartAt": "SnapshotCheck",
        "States": {
            "SnapshotCheck": {
                "Type": "Task",
                "Resource": "arn:aws:lambda:us-east-1:123456789012:function:aurora-restore-snapshot-check",
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
                        "Next": "HandleFailure"
                    }
                ]
            }
        }
    }' \
    --role-arn arn:aws:iam::123456789012:role/aurora-restore-step-functions-role
```

## Lambda Functions

The Aurora Restore Pipeline uses Lambda functions to execute individual steps of the restore process.

### Lambda Function Configuration

Each Lambda function is configured with the following settings:

- **Runtime**: Python 3.8
- **Handler**: The handler function for the Lambda function
- **Memory**: The memory size for the Lambda function
- **Timeout**: The timeout for the Lambda function
- **VPC Configuration**: The VPC configuration for the Lambda function
- **Environment Variables**: The environment variables for the Lambda function
- **IAM Role**: The IAM role for the Lambda function

### Creating Lambda Functions

You can create Lambda functions using the AWS Management Console or AWS CLI.

#### Using AWS Management Console

1. Navigate to the AWS Lambda console.
2. Click on "Create function".
3. Enter the function name, runtime, and handler.
4. Configure the function settings and click on "Create function".

#### Using AWS CLI

```bash
aws lambda create-function \
    --function-name aurora-restore-snapshot-check \
    --runtime python3.8 \
    --handler lambda_function.lambda_handler \
    --role arn:aws:iam::123456789012:role/aurora-restore-lambda-role \
    --code S3Bucket=aurora-restore-code,S3Key=snapshot_check.zip \
    --timeout 300 \
    --memory-size 256 \
    --vpc-config SubnetIds=subnet-12345678,subnet-87654321,SecurityGroupIds=sg-12345678 \
    --environment Variables={ENVIRONMENT=dev,REGION=us-east-1,DYNAMODB_TABLE_NAME=aurora-restore-state,SNS_TOPIC_ARN=arn:aws:sns:us-east-1:123456789012:aurora-restore-notifications,KMS_KEY_ID=arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012}
```

## IAM Roles and Policies

The Aurora Restore Pipeline uses IAM roles and policies to manage permissions.

### Required IAM Roles

- **Step Functions Role**: The IAM role for the Step Functions state machine
- **Lambda Role**: The IAM role for the Lambda functions

### Creating IAM Roles and Policies

You can create IAM roles and policies using the AWS Management Console or AWS CLI.

#### Using AWS Management Console

1. Navigate to the AWS IAM console.
2. Click on "Roles" and then "Create role".
3. Select the AWS service and the use case.
4. Attach the necessary policies and click on "Next: Tags".
5. Add tags and click on "Next: Review".
6. Enter the role name and click on "Create role".

#### Using AWS CLI

```bash
# Create Step Functions role
aws iam create-role \
    --role-name aurora-restore-step-functions-role \
    --assume-role-policy-document '{
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
    }'

# Create Lambda role
aws iam create-role \
    --role-name aurora-restore-lambda-role \
    --assume-role-policy-document '{
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "lambda.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }'

# Attach policies to Step Functions role
aws iam attach-role-policy \
    --role-name aurora-restore-step-functions-role \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaRole

# Attach policies to Lambda role
aws iam attach-role-policy \
    --role-name aurora-restore-lambda-role \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
```

## CloudWatch Alarms

The Aurora Restore Pipeline uses CloudWatch alarms to monitor the health of the pipeline.

### Required CloudWatch Alarms

- **Step Functions Execution Failures**: Alerts when a Step Functions execution fails
- **Lambda Function Errors**: Alerts when a Lambda function encounters an error

### Creating CloudWatch Alarms

You can create CloudWatch alarms using the AWS Management Console or AWS CLI.

#### Using AWS Management Console

1. Navigate to the AWS CloudWatch console.
2. Click on "Alarms" and then "Create alarm".
3. Select the metric and configure the alarm settings.
4. Click on "Create alarm".

#### Using AWS CLI

```bash
aws cloudwatch put-metric-alarm \
    --alarm-name aurora-restore-step-functions-failures \
    --alarm-description "Alarm for Step Functions execution failures" \
    --metric-name ExecutionsFailed \
    --namespace AWS/States \
    --statistic Sum \
    --period 300 \
    --threshold 1 \
    --comparison-operator GreaterThanOrEqualToThreshold \
    --evaluation-periods 1 \
    --alarm-actions arn:aws:sns:us-east-1:123456789012:aurora-restore-notifications

aws cloudwatch put-metric-alarm \
    --alarm-name aurora-restore-lambda-errors \
    --alarm-description "Alarm for Lambda function errors" \
    --metric-name Errors \
    --namespace AWS/Lambda \
    --dimensions Name=FunctionName,Value=aurora-restore-snapshot-check \
    --statistic Sum \
    --period 300 \
    --threshold 1 \
    --comparison-operator GreaterThanOrEqualToThreshold \
    --evaluation-periods 1 \
    --alarm-actions arn:aws:sns:us-east-1:123456789012:aurora-restore-notifications
```

## Conclusion

This configuration guide provides detailed instructions for configuring the Aurora Restore Pipeline. By following these instructions, you can effectively configure the pipeline to meet your specific requirements. 