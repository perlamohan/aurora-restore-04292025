# Manual Implementation Guide - Prerequisites

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

1. **Create S3 Bucket for Lambda Code**
```bash
aws s3 mb s3://aurora-restore-lambda-code-${AWS_ACCOUNT_ID}-${AWS_REGION} --region ${AWS_REGION}
aws s3api put-bucket-versioning --bucket aurora-restore-lambda-code-${AWS_ACCOUNT_ID}-${AWS_REGION} --versioning-configuration Status=Enabled
```

2. **Create DynamoDB Tables**
```bash
# State Table
aws dynamodb create-table \
  --table-name aurora-restore-state \
  --attribute-definitions AttributeName=operation_id,AttributeType=S \
  --key-schema AttributeName=operation_id,KeyType=HASH \
  --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5

# Audit Table
aws dynamodb create-table \
  --table-name aurora-restore-audit \
  --attribute-definitions \
    AttributeName=operation_id,AttributeType=S \
    AttributeName=timestamp,AttributeType=N \
  --key-schema \
    AttributeName=operation_id,KeyType=HASH \
    AttributeName=timestamp,KeyType=RANGE \
  --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5
```

3. **Create SNS Topic**
```bash
aws sns create-topic --name aurora-restore-notifications
```

4. **Create KMS Key for Secrets Encryption**
```bash
# Create KMS key
aws kms create-key \
  --description "Aurora Restore Secrets Encryption Key" \
  --key-usage ENCRYPT_DECRYPT \
  --origin AWS_KMS \
  --policy '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Principal": {
          "AWS": "arn:aws:iam::${AWS_ACCOUNT_ID}:root"
        },
        "Action": "kms:*",
        "Resource": "*"
      }
    ]
  }'

# Get key ID
KMS_KEY_ID=$(aws kms list-keys --query 'Keys[?Description==`Aurora Restore Secrets Encryption Key`].KeyId' --output text)

# Create alias for the key
aws kms create-alias \
  --alias-name alias/aurora-restore-secrets \
  --target-key-id $KMS_KEY_ID
```

5. **Create Required Secrets**
```bash
# Create secret for master user credentials (DBA team will update this)
aws secretsmanager create-secret \
  --name aurora-restore/dev/master-credentials \
  --kms-key-id $KMS_KEY_ID \
  --secret-string '{"username":"master","password":"PLACEHOLDER"}' \
  --tags Key=Environment,Value=dev,Key=Type,Value=master-credentials

# Create secret for application user credentials
aws secretsmanager create-secret \
  --name aurora-restore/dev/app-credentials \
  --kms-key-id $KMS_KEY_ID \
  --secret-string '{
    "application_user": {"username":"app_user","password":"APP_PASSWORD"},
    "readonly_user": {"username":"readonly_user","password":"READONLY_PASSWORD"},
    "devops_user": {"username":"devops_user","password":"DEVOPS_PASSWORD"}
  }' \
  --tags Key=Environment,Value=dev,Key=Type,Value=app-credentials

# Create secret for KMS key
aws secretsmanager create-secret \
  --name aurora-restore/dev/kms-key \
  --kms-key-id $KMS_KEY_ID \
  --secret-string '{"key_id":"'$KMS_KEY_ID'"}' \
  --tags Key=Environment,Value=dev
```

6. **Set Up IAM Policies for Secrets Access**
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
          "AWS": "arn:aws:iam::${AWS_ACCOUNT_ID}:user/dba-team"
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

7. **Set Environment Variables**
```bash
# Set these in your shell for testing
export ENVIRONMENT=dev
export STATE_TABLE_NAME=aurora-restore-state
export AUDIT_TABLE_NAME=aurora-restore-audit
export SNS_TOPIC_ARN=$(aws sns list-topics --query 'Topics[?contains(TopicArn,`aurora-restore-notifications`)].TopicArn' --output text)
export SOURCE_REGION=us-east-1
export TARGET_REGION=us-west-2
export KMS_KEY_ID=$KMS_KEY_ID
export MASTER_SECRET_NAME=aurora-restore/dev/master-credentials
export APP_SECRET_NAME=aurora-restore/dev/app-credentials
```

## Directory Structure Setup

1. **Create Project Directory**
```bash
mkdir -p aurora-restore/{lambda,utils,tests,infrastructure}
cd aurora-restore
```

2. **Create Required Files**
```bash
# Create directories
mkdir -p lambda/utils
mkdir -p tests/unit
mkdir -p tests/integration

# Create placeholder files
touch lambda/utils/__init__.py
touch lambda/utils/aurora_utils.py
touch lambda/copy_snapshot.py
touch lambda/check_copy_status.py
touch lambda/delete_rds.py
touch lambda/restore_snapshot.py
touch lambda/check_restore_status.py
touch lambda/setup_db_users.py
touch lambda/archive_snapshot.py
touch lambda/sns_notification.py
```

## Next Steps

Once you have completed these prerequisites:
1. Verify all resources are created successfully
2. Test access to all services
3. Proceed to implementing the Lambda functions
4. Follow the testing guide for each component

See [02_lambda_implementation.md](02_lambda_implementation.md) for the next steps. 