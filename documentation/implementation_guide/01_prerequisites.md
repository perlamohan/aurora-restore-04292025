# Implementation Guide - Prerequisites

This document provides detailed instructions for setting up all prerequisites needed for implementing the Aurora Restore Pipeline.

## AWS Account Requirements

1. **AWS Account Access**
   - AWS Console access with Administrator privileges
   - AWS CLI configured with appropriate credentials
   - Access to create and manage resources in:
     - Lambda
     - DynamoDB
     - RDS (Aurora)
     - Step Functions
     - IAM
     - S3
     - CloudWatch
     - SNS
     - Secrets Manager
     - KMS

2. **Required Tools**
   - AWS CLI installed and configured
   - Python 3.9 installed
   - Text editor or IDE
   - Git (optional, for version control)

3. **AWS Regions**
   - Identify source region (e.g., us-east-1)
   - Identify target region (e.g., us-west-2)
   - Ensure you have access to both regions

## Initial Setup

### 1. Create S3 Bucket for Lambda Code

```bash
# Set your account ID and regions
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export AWS_REGION=us-east-1  # Change to your preferred region

# Create the bucket
aws s3 mb s3://aurora-restore-lambda-code-${AWS_ACCOUNT_ID}-${AWS_REGION} --region ${AWS_REGION}

# Enable versioning for the bucket
aws s3api put-bucket-versioning \
  --bucket aurora-restore-lambda-code-${AWS_ACCOUNT_ID}-${AWS_REGION} \
  --versioning-configuration Status=Enabled
```

### 2. Create DynamoDB Tables

```bash
# State Table
aws dynamodb create-table \
  --table-name aurora-restore-state \
  --attribute-definitions AttributeName=operation_id,AttributeType=S \
  --key-schema AttributeName=operation_id,KeyType=HASH \
  --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5 \
  --region ${AWS_REGION}

# Audit Table
aws dynamodb create-table \
  --table-name aurora-restore-audit \
  --attribute-definitions \
    AttributeName=operation_id,AttributeType=S \
    AttributeName=timestamp,AttributeType=S \
  --key-schema \
    AttributeName=operation_id,KeyType=HASH \
    AttributeName=timestamp,KeyType=RANGE \
  --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5 \
  --region ${AWS_REGION}
```

### 3. Create SNS Topic

```bash
# Create SNS topic
aws sns create-topic --name aurora-restore-notifications --region ${AWS_REGION}
```

### 4. Create KMS Key for Secrets Encryption

```bash
# Create KMS key
aws kms create-key \
  --description "Aurora Restore Secrets Encryption Key" \
  --key-usage ENCRYPT_DECRYPT \
  --region ${AWS_REGION}

# Save the KMS key ID
export KMS_KEY_ID=$(aws kms list-keys --query "Keys[?contains(KeyId, 'Aurora')].KeyId" --output text --region ${AWS_REGION})

# Create alias for the key
aws kms create-alias \
  --alias-name alias/aurora-restore-secrets \
  --target-key-id ${KMS_KEY_ID} \
  --region ${AWS_REGION}
```

### 5. Create Required Secrets

```bash
# Create secret for master user credentials
aws secretsmanager create-secret \
  --name aurora-restore/dev/master-credentials \
  --kms-key-id ${KMS_KEY_ID} \
  --secret-string '{"username":"master","password":"PLACEHOLDER"}' \
  --tags Key=Environment,Value=dev,Key=Type,Value=master-credentials \
  --region ${AWS_REGION}

# Create secret for application user credentials
aws secretsmanager create-secret \
  --name aurora-restore/dev/app-credentials \
  --kms-key-id ${KMS_KEY_ID} \
  --secret-string '{
    "application_user": {"username":"app_user","password":"APP_PASSWORD"},
    "readonly_user": {"username":"readonly_user","password":"READONLY_PASSWORD"},
    "devops_user": {"username":"devops_user","password":"DEVOPS_PASSWORD"}
  }' \
  --tags Key=Environment,Value=dev,Key=Type,Value=app-credentials \
  --region ${AWS_REGION}

# Create secret for KMS key
aws secretsmanager create-secret \
  --name aurora-restore/dev/kms-key \
  --kms-key-id ${KMS_KEY_ID} \
  --secret-string '{"key_id":"'${KMS_KEY_ID}'"}' \
  --tags Key=Environment,Value=dev \
  --region ${AWS_REGION}
```

### 6. Set Up IAM Policies for Secrets Access

```bash
# Create policy for Lambda to read secrets
cat > lambda-secrets-policy.json << EOL
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": [
        "arn:aws:secretsmanager:${AWS_REGION}:${AWS_ACCOUNT_ID}:secret:aurora-restore/dev/app-credentials-*",
        "arn:aws:secretsmanager:${AWS_REGION}:${AWS_ACCOUNT_ID}:secret:aurora-restore/dev/kms-key-*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "kms:Decrypt",
        "kms:DescribeKey"
      ],
      "Resource": "arn:aws:kms:${AWS_REGION}:${AWS_ACCOUNT_ID}:key/${KMS_KEY_ID}"
    }
  ]
}
EOL

# Create policy for DBA team to manage master credentials
cat > dba-secrets-policy.json << EOL
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue",
        "secretsmanager:PutSecretValue",
        "secretsmanager:UpdateSecretVersionStage"
      ],
      "Resource": [
        "arn:aws:secretsmanager:${AWS_REGION}:${AWS_ACCOUNT_ID}:secret:aurora-restore/dev/master-credentials-*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "kms:Decrypt",
        "kms:DescribeKey"
      ],
      "Resource": "arn:aws:kms:${AWS_REGION}:${AWS_ACCOUNT_ID}:key/${KMS_KEY_ID}"
    }
  ]
}
EOL

# Create IAM role for DBA team
aws iam create-role \
  --role-name aurora-restore-dba-role \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Principal": {
          "AWS": "arn:aws:iam::'${AWS_ACCOUNT_ID}':root"
        },
        "Action": "sts:AssumeRole"
      }
    ]
  }'

# Attach policy to DBA role
aws iam put-role-policy \
  --role-name aurora-restore-dba-role \
  --policy-name aurora-restore-dba-secrets-policy \
  --policy-document file://dba-secrets-policy.json
```

### 7. Set Environment Variables

```bash
# Set these in your shell for development and testing
export ENVIRONMENT=dev
export STATE_TABLE_NAME=aurora-restore-state
export AUDIT_TABLE_NAME=aurora-restore-audit
export SNS_TOPIC_ARN=$(aws sns list-topics --query "Topics[?contains(TopicArn, 'aurora-restore-notifications')].TopicArn" --output text --region ${AWS_REGION})
export SOURCE_REGION=us-east-1  # Update as needed
export TARGET_REGION=us-west-2  # Update as needed
export KMS_KEY_ID=${KMS_KEY_ID}
export MASTER_SECRET_NAME=aurora-restore/dev/master-credentials
export APP_SECRET_NAME=aurora-restore/dev/app-credentials
```

## Project Setup

### 1. Clone or Create Project Directory

```bash
# Clone the repository if using Git
git clone https://github.com/your-organization/aurora-restore.git
cd aurora-restore

# Or create the directory structure manually
mkdir -p aurora-restore
cd aurora-restore
```

### 2. Create Required Directories

```bash
# Create directories for Lambda functions
mkdir -p lambda_functions/aurora-restore-snapshot-check
mkdir -p lambda_functions/aurora-restore-copy-snapshot
mkdir -p lambda_functions/aurora-restore-check-copy-status
mkdir -p lambda_functions/aurora-restore-delete-rds
mkdir -p lambda_functions/aurora-restore-check-delete-status
mkdir -p lambda_functions/aurora-restore-restore-snapshot
mkdir -p lambda_functions/aurora-restore-check-restore-status
mkdir -p lambda_functions/aurora-restore-setup-db-users
mkdir -p lambda_functions/aurora-restore-archive-snapshot
mkdir -p lambda_functions/aurora-restore-sns-notification

# Create utilities directory
mkdir -p utils

# Create infrastructure directory
mkdir -p infrastructure

# Create tests directory
mkdir -p tests/unit
mkdir -p tests/integration
```

### 3. Create Initial Files

```bash
# Create utility module
touch utils/__init__.py
touch utils/aurora_utils.py

# Create infrastructure files
touch infrastructure/lambda.yaml
touch infrastructure/dynamodb.yaml
touch infrastructure/stepfunctions.yaml

# Create deployment scripts
touch deploy.sh
touch build_lambda_packages.sh
```

### 4. Make the Scripts Executable

```bash
chmod +x deploy.sh
chmod +x build_lambda_packages.sh
```

## Verify Prerequisites

Before proceeding, verify that all prerequisites have been met:

```bash
# Verify S3 bucket
aws s3 ls s3://aurora-restore-lambda-code-${AWS_ACCOUNT_ID}-${AWS_REGION} --region ${AWS_REGION}

# Verify DynamoDB tables
aws dynamodb list-tables --region ${AWS_REGION}

# Verify SNS topic
aws sns list-topics --region ${AWS_REGION}

# Verify KMS key
aws kms list-aliases --region ${AWS_REGION}

# Verify Secrets
aws secretsmanager list-secrets --region ${AWS_REGION}

# Verify IAM role
aws iam get-role --role-name aurora-restore-dba-role
```

## Next Steps

Once you have completed these prerequisites:
1. Implement the Lambda functions (see [Lambda Implementation](./02_lambda_implementation.md))
2. Set up the Step Functions state machine (see [Step Functions Implementation](./03_step_functions_implementation.md))
3. Deploy the solution to production (see [Production Deployment](./04_production_deployment.md)) 