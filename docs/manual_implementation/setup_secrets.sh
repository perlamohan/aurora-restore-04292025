#!/bin/bash

# Exit on error
set -e

# Check required environment variables
if [ -z "$ENVIRONMENT" ]; then
    echo "Error: ENVIRONMENT variable not set"
    exit 1
fi

if [ -z "$REGION" ]; then
    echo "Error: REGION variable not set"
    exit 1
fi

# Create secrets
echo "Creating secrets for environment: $ENVIRONMENT in region: $REGION"

# Create master credentials secret
aws secretsmanager create-secret \
    --name "aurora-restore/${ENVIRONMENT}/master-credentials-${ENVIRONMENT}" \
    --description "Master credentials for Aurora restore in ${ENVIRONMENT}" \
    --secret-string '{"username":"admin","password":"CHANGE_ME"}' \
    --region $REGION

# Create application credentials secret
aws secretsmanager create-secret \
    --name "aurora-restore/${ENVIRONMENT}/app-credentials-${ENVIRONMENT}" \
    --description "Application credentials for Aurora restore in ${ENVIRONMENT}" \
    --secret-string '{"username":"app_user","password":"CHANGE_ME"}' \
    --region $REGION

# Create IAM role for Lambda
echo "Creating IAM role for Lambda functions"
aws iam create-role \
    --role-name "aurora-restore-lambda-role-${ENVIRONMENT}" \
    --assume-role-policy-document '{
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {
                "Service": "lambda.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        }]
    }'

# Attach basic execution policy
aws iam attach-role-policy \
    --role-name "aurora-restore-lambda-role-${ENVIRONMENT}" \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

# Attach VPC access policy
aws iam attach-role-policy \
    --role-name "aurora-restore-lambda-role-${ENVIRONMENT}" \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole

# Attach secrets access policy
aws iam put-role-policy \
    --role-name "aurora-restore-lambda-role-${ENVIRONMENT}" \
    --policy-name "aurora-restore-secrets-access-${ENVIRONMENT}" \
    --policy-document file://lambda-secrets-policy.json

# Create IAM role for DBA team
echo "Creating IAM role for DBA team"
aws iam create-role \
    --role-name "aurora-restore-dba-role-${ENVIRONMENT}" \
    --assume-role-policy-document '{
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {
                "AWS": "arn:aws:iam::YOUR_ACCOUNT_ID:role/DBA-Team-Role"
            },
            "Action": "sts:AssumeRole"
        }]
    }'

# Attach secrets access policy for DBA team
aws iam put-role-policy \
    --role-name "aurora-restore-dba-role-${ENVIRONMENT}" \
    --policy-name "aurora-restore-dba-secrets-access-${ENVIRONMENT}" \
    --policy-document file://dba-secrets-policy.json

echo "Setup complete! Please update the secrets with proper credentials."
echo "You can update the secrets using:"
echo "aws secretsmanager update-secret --secret-id aurora-restore/${ENVIRONMENT}/master-credentials-${ENVIRONMENT} --secret-string '{\"username\":\"actual_username\",\"password\":\"actual_password\"}'"
echo "aws secretsmanager update-secret --secret-id aurora-restore/${ENVIRONMENT}/app-credentials-${ENVIRONMENT} --secret-string '{\"username\":\"actual_username\",\"password\":\"actual_password\"}'" 