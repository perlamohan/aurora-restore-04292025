# Quick Start Guide

This guide provides the fastest path to deploying the Aurora Restore Pipeline in your AWS environment.

## Prerequisites

Before starting, ensure you have:
- AWS account with administrative permissions
- AWS CLI installed and configured
- Git installed
- Python 3.9+ installed

## Clone the Repository

First, clone the Aurora Restore Pipeline repository:

```bash
git clone https://github.com/your-organization/aurora-restore.git
cd aurora-restore
```

## Setup Environment Variables

Set up the basic environment variables needed for deployment:

```bash
export ENVIRONMENT=dev
export REGION=us-east-1  # Target region for restoration
export SOURCE_REGION=us-east-1  # Region where snapshots exist
export STACK_PREFIX=aurora-restore
```

## Create Required Secrets

Create the necessary secrets in AWS Secrets Manager:

```bash
# Master credentials
aws secretsmanager create-secret \
  --name aurora-restore/dev/master-credentials \
  --secret-string '{"username":"master","password":"YOUR_SECURE_PASSWORD"}' \
  --region $REGION

# Application credentials
aws secretsmanager create-secret \
  --name aurora-restore/dev/app-credentials \
  --secret-string '{
    "application_user": {"username":"app_user","password":"APP_PASSWORD"},
    "readonly_user": {"username":"readonly_user","password":"READONLY_PASSWORD"}
  }' \
  --region $REGION
```

**Note**: Replace the placeholder passwords with secure passwords.

## Deploy the Solution

Run the deployment script to set up all required resources:

```bash
./deploy.sh --environment $ENVIRONMENT --region $REGION --stack-prefix $STACK_PREFIX
```

The deployment script will:
1. Create necessary S3 buckets
2. Package Lambda functions
3. Deploy DynamoDB tables
4. Deploy all Lambda functions
5. Set up the Step Functions state machine
6. Configure IAM roles and policies

## Verify Deployment

Verify the deployment was successful:

```bash
# List CloudFormation stacks
aws cloudformation describe-stacks --query "Stacks[?contains(StackName, '$STACK_PREFIX')].StackName" --output table --region $REGION

# List Lambda functions
aws lambda list-functions --query "Functions[?contains(FunctionName, '$STACK_PREFIX')].FunctionName" --output table --region $REGION

# List Step Functions state machines
aws stepfunctions list-state-machines --query "stateMachines[?contains(name, '$STACK_PREFIX')].name" --output table --region $REGION
```

## Test the Pipeline

To test the pipeline:

1. Identify a source snapshot to restore:

```bash
aws rds describe-db-cluster-snapshots --query "DBClusterSnapshots[*].[DBClusterSnapshotIdentifier,SnapshotCreateTime]" --output table --region $SOURCE_REGION
```

2. Start the pipeline execution with the selected snapshot:

```bash
aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:$REGION:$(aws sts get-caller-identity --query Account --output text):stateMachine:$STACK_PREFIX-state-machine \
  --input '{
    "snapshot_name": "YOUR_SNAPSHOT_NAME",
    "source_region": "'$SOURCE_REGION'",
    "target_region": "'$REGION'",
    "target_cluster_id": "restored-cluster",
    "db_subnet_group_name": "YOUR_SUBNET_GROUP",
    "vpc_security_group_ids": ["YOUR_SECURITY_GROUP_ID"]
  }'
```

**Note**: Replace placeholders with actual values for your environment.

3. Monitor the execution in the AWS Step Functions console or via CLI:

```bash
# Get the execution ARN from the previous command output
aws stepfunctions describe-execution \
  --execution-arn EXECUTION_ARN
```

## Next Steps

After the successful deployment and test:

1. Set up monitoring and alerting for the pipeline
2. Customize configurations in CloudFormation templates
3. Integrate with your CI/CD process
4. Review the [Implementation Guide](../implementation_guide/01_prerequisites.md) for advanced configurations

## Troubleshooting

If you encounter issues during deployment or execution:

1. Check CloudWatch Logs for Lambda function errors:
```bash
aws logs filter-log-events --log-group-name "/aws/lambda/$STACK_PREFIX-snapshot-check" --region $REGION
```

2. Check the AWS Step Functions execution history for state transitions:
```bash
aws stepfunctions get-execution-history --execution-arn EXECUTION_ARN
```

3. Verify that all prerequisites are met

4. See the [Troubleshooting Guide](../troubleshooting/01_common_issues.md) for common issues and solutions 