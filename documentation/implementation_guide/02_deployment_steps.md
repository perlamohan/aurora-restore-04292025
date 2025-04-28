# Aurora Restore Pipeline Deployment Steps

This document provides step-by-step instructions for deploying the Aurora Restore Pipeline.

## Prerequisites

Before proceeding with the deployment, ensure that you have completed all the prerequisites listed in the [Prerequisites](./01_prerequisites.md) document.

## Deployment Overview

The deployment process consists of the following steps:

1. Configure environment variables
2. Build Lambda functions
3. Deploy CloudFormation stacks
4. Configure Step Functions
5. Verify deployment

## Step 1: Configure Environment Variables

Create a `.env` file in the project root directory:

```bash
# AWS settings
export AWS_REGION="us-east-1"
export AWS_PROFILE="default"
export ENVIRONMENT="dev"

# S3 bucket for Lambda code deployment
export S3_BUCKET="aurora-restore-lambda-$ENVIRONMENT"

# DynamoDB tables
export STATE_TABLE="aurora-restore-state-$ENVIRONMENT"
export AUDIT_TABLE="aurora-restore-audit-$ENVIRONMENT"

# SNS topic
export SNS_TOPIC_NAME="aurora-restore-notifications-$ENVIRONMENT"
```

Load the environment variables:

```bash
source .env
```

## Step 2: Build Lambda Functions

Run the Lambda packaging script:

```bash
./build_lambda_packages.sh
```

This script will:
- Create an S3 bucket if it doesn't exist
- Package each Lambda function with its dependencies
- Upload the packages to S3

## Step 3: Deploy CloudFormation Stacks

Run the deployment script:

```bash
./deploy.sh
```

This script will:
- Package the CloudFormation templates
- Deploy the stacks with the specified parameters
- Create all necessary resources (Lambda functions, DynamoDB tables, IAM roles, etc.)

## Step 4: Configure Step Functions

1. Get the ARNs of the deployed Lambda functions:

```bash
# Example for retrieving one Lambda function ARN
SNAPSHOT_CHECK_ARN=$(aws lambda get-function --function-name aurora-restore-snapshot-check-$ENVIRONMENT --query 'Configuration.FunctionArn' --output text)
```

2. Create the Step Functions state machine:

```bash
# Create Step Functions state machine
aws stepfunctions create-state-machine \
  --name aurora-restore-$ENVIRONMENT \
  --definition file://infrastructure/step-functions.json \
  --role-arn $ROLE_ARN
```

## Step 5: Verify Deployment

Verify that all resources were created successfully:

```bash
# Verify Lambda functions
aws lambda list-functions --query "Functions[?starts_with(FunctionName, 'aurora-restore')].FunctionName" --output table

# Verify Step Functions state machine
aws stepfunctions list-state-machines --query "stateMachines[?name=='aurora-restore-$ENVIRONMENT']" --output table

# Verify DynamoDB tables
aws dynamodb list-tables --query "TableNames[?contains(@, 'aurora-restore')]" --output table
```

## Test the Pipeline

Start a test execution of the Step Functions state machine:

```bash
# Get the state machine ARN
STATE_MACHINE_ARN=$(aws stepfunctions list-state-machines --query "stateMachines[?name=='aurora-restore-$ENVIRONMENT'].stateMachineArn" --output text)

# Start an execution
aws stepfunctions start-execution \
  --state-machine-arn $STATE_MACHINE_ARN \
  --name test-execution-$(date +%s) \
  --input '{
    "snapshot_name": "aurora-snapshot-2023-01-01",
    "source_region": "us-east-1",
    "target_region": "us-west-2",
    "target_cluster_id": "restored-cluster",
    "db_subnet_group_name": "default",
    "vpc_security_group_ids": ["sg-12345678"]
  }'
```

## Monitoring and Automation

### Set Up CloudWatch Events Trigger

To automatically trigger the pipeline on a schedule:

```bash
# Create CloudWatch Events rule
aws events put-rule \
  --name aurora-restore-daily-$ENVIRONMENT \
  --schedule-expression "cron(0 2 * * ? *)" \
  --state ENABLED

# Add target to CloudWatch Events rule
aws events put-targets \
  --rule aurora-restore-daily-$ENVIRONMENT \
  --targets '[{
    "Id": "1",
    "Arn": "'"$STATE_MACHINE_ARN"'",
    "RoleArn": "'"$ROLE_ARN"'",
    "Input": "{\"snapshot_name\":\"aurora-snapshot-$(date +%Y-%m-%d)\",\"source_region\":\"us-east-1\",\"target_region\":\"us-west-2\",\"target_cluster_id\":\"restored-cluster\",\"db_subnet_group_name\":\"default\",\"vpc_security_group_ids\":[\"sg-12345678\"]}"
  }]'
```

### Set Up CloudWatch Alarms

Create alarms to monitor the pipeline:

```bash
# Create CloudWatch Alarm for Step Functions failures
aws cloudwatch put-metric-alarm \
  --alarm-name aurora-restore-step-functions-failure-$ENVIRONMENT \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1 \
  --metric-name ExecutionsFailed \
  --namespace AWS/States \
  --period 300 \
  --statistic Sum \
  --threshold 0 \
  --alarm-description "Alarm when Aurora Restore Step Functions execution fails" \
  --dimensions Name=StateMachineArn,Value=$STATE_MACHINE_ARN \
  --alarm-actions $SNS_TOPIC_ARN
```

## Next Steps

Now that you have successfully deployed the Aurora Restore Pipeline, you can:

1. Review the CloudFormation outputs for important information about the deployed resources
2. Configure additional CloudWatch alarms for monitoring
3. Set up cross-account access if needed
4. Learn more about monitoring and troubleshooting the pipeline in the [Troubleshooting](../troubleshooting/01_common_issues.md) section 