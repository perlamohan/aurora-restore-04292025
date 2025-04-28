#!/bin/bash

# Exit on error
set -e

# Default values
ENVIRONMENT="dev"
REGION="us-east-1"
STACK_PREFIX="aurora-restore"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --environment)
      ENVIRONMENT="$2"
      shift 2
      ;;
    --region)
      REGION="$2"
      shift 2
      ;;
    --stack-prefix)
      STACK_PREFIX="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

echo "Setting up configuration for Aurora Restore Pipeline in $ENVIRONMENT environment"

# Network Configuration
read -p "Enter VPC ID: " VPC_ID
read -p "Enter Subnet IDs (comma-separated): " SUBNET_IDS
read -p "Enter Security Group IDs (comma-separated): " SECURITY_GROUP_IDS

# Aurora Configuration
read -p "Enter Source Cluster ID: " SOURCE_CLUSTER_ID
read -p "Enter Target Cluster ID: " TARGET_CLUSTER_ID
read -p "Enter Snapshot Prefix: " SNAPSHOT_PREFIX

# KMS Configuration
read -p "Enter Source Account ID: " SOURCE_ACCOUNT_ID
read -p "Enter Target Account ID: " TARGET_ACCOUNT_ID
read -p "Enter Source KMS Key ID: " SOURCE_KMS_KEY_ID
read -p "Enter Target KMS Key ID: " TARGET_KMS_KEY_ID
read -p "Enter Source KMS Key ARN: " SOURCE_KMS_KEY_ARN
read -p "Enter Target KMS Key ARN: " TARGET_KMS_KEY_ARN

# Create SSM parameters
echo "Creating SSM parameters..."

# Network Configuration
aws ssm put-parameter \
    --name "/${STACK_PREFIX}/${ENVIRONMENT}/vpc-id" \
    --value "$VPC_ID" \
    --type String \
    --region "$REGION"

aws ssm put-parameter \
    --name "/${STACK_PREFIX}/${ENVIRONMENT}/subnet-ids" \
    --value "$SUBNET_IDS" \
    --type StringList \
    --region "$REGION"

aws ssm put-parameter \
    --name "/${STACK_PREFIX}/${ENVIRONMENT}/security-group-ids" \
    --value "$SECURITY_GROUP_IDS" \
    --type StringList \
    --region "$REGION"

# Aurora Configuration
aws ssm put-parameter \
    --name "/${STACK_PREFIX}/${ENVIRONMENT}/source-cluster-id" \
    --value "$SOURCE_CLUSTER_ID" \
    --type String \
    --region "$REGION"

aws ssm put-parameter \
    --name "/${STACK_PREFIX}/${ENVIRONMENT}/target-cluster-id" \
    --value "$TARGET_CLUSTER_ID" \
    --type String \
    --region "$REGION"

aws ssm put-parameter \
    --name "/${STACK_PREFIX}/${ENVIRONMENT}/snapshot-prefix" \
    --value "$SNAPSHOT_PREFIX" \
    --type String \
    --region "$REGION"

# KMS Configuration
aws ssm put-parameter \
    --name "/${STACK_PREFIX}/${ENVIRONMENT}/source-account-id" \
    --value "$SOURCE_ACCOUNT_ID" \
    --type String \
    --region "$REGION"

aws ssm put-parameter \
    --name "/${STACK_PREFIX}/${ENVIRONMENT}/target-account-id" \
    --value "$TARGET_ACCOUNT_ID" \
    --type String \
    --region "$REGION"

aws ssm put-parameter \
    --name "/${STACK_PREFIX}/${ENVIRONMENT}/source-kms-key-id" \
    --value "$SOURCE_KMS_KEY_ID" \
    --type String \
    --region "$REGION"

aws ssm put-parameter \
    --name "/${STACK_PREFIX}/${ENVIRONMENT}/target-kms-key-id" \
    --value "$TARGET_KMS_KEY_ID" \
    --type String \
    --region "$REGION"

aws ssm put-parameter \
    --name "/${STACK_PREFIX}/${ENVIRONMENT}/source-kms-key-arn" \
    --value "$SOURCE_KMS_KEY_ARN" \
    --type String \
    --region "$REGION"

aws ssm put-parameter \
    --name "/${STACK_PREFIX}/${ENVIRONMENT}/target-kms-key-arn" \
    --value "$TARGET_KMS_KEY_ARN" \
    --type String \
    --region "$REGION"

echo "Configuration setup complete!" 