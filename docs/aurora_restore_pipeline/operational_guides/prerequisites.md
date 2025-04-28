# Aurora Restore Pipeline Prerequisites

This document lists the prerequisites for deploying and using the Aurora Restore Pipeline.

## AWS Account Requirements

- An AWS account with administrative access or sufficient permissions to create and manage the following AWS resources:
  - Step Functions
  - Lambda Functions
  - DynamoDB Tables
  - SNS Topics
  - CloudWatch Logs
  - CloudWatch Alarms
  - Secrets Manager
  - KMS Keys
  - IAM Roles and Policies
  - VPC, Subnets, and Security Groups

## AWS CLI and Tools

- AWS CLI version 2.0 or later
- AWS CloudFormation
- AWS SAM CLI (optional, for local testing)

## Required AWS Services

- **Step Functions**: For orchestrating the restore process
- **Lambda**: For executing the individual steps of the restore process
- **DynamoDB**: For storing state and audit information
- **SNS**: For sending notifications about the restore process
- **CloudWatch**: For storing logs and monitoring the health of the pipeline
- **Secrets Manager**: For storing sensitive configuration
- **KMS**: For encrypting sensitive data
- **IAM**: For managing permissions
- **VPC**: For deploying Lambda functions in a VPC

## Required Permissions

- **Step Functions**:
  - `states:CreateStateMachine`
  - `states:DeleteStateMachine`
  - `states:DescribeStateMachine`
  - `states:UpdateStateMachine`
  - `states:StartExecution`
  - `states:StopExecution`
  - `states:DescribeExecution`
  - `states:GetExecutionHistory`

- **Lambda**:
  - `lambda:CreateFunction`
  - `lambda:DeleteFunction`
  - `lambda:GetFunction`
  - `lambda:UpdateFunctionCode`
  - `lambda:UpdateFunctionConfiguration`
  - `lambda:InvokeFunction`
  - `lambda:AddPermission`
  - `lambda:RemovePermission`

- **DynamoDB**:
  - `dynamodb:CreateTable`
  - `dynamodb:DeleteTable`
  - `dynamodb:DescribeTable`
  - `dynamodb:PutItem`
  - `dynamodb:GetItem`
  - `dynamodb:UpdateItem`
  - `dynamodb:DeleteItem`
  - `dynamodb:Query`
  - `dynamodb:Scan`

- **SNS**:
  - `sns:CreateTopic`
  - `sns:DeleteTopic`
  - `sns:GetTopicAttributes`
  - `sns:SetTopicAttributes`
  - `sns:Publish`

- **CloudWatch**:
  - `logs:CreateLogGroup`
  - `logs:DeleteLogGroup`
  - `logs:DescribeLogGroups`
  - `logs:PutLogEvents`
  - `logs:CreateLogStream`
  - `logs:DescribeLogStreams`
  - `cloudwatch:PutMetricData`
  - `cloudwatch:PutMetricAlarm`
  - `cloudwatch:DeleteAlarms`

- **Secrets Manager**:
  - `secretsmanager:CreateSecret`
  - `secretsmanager:DeleteSecret`
  - `secretsmanager:GetSecretValue`
  - `secretsmanager:PutSecretValue`
  - `secretsmanager:UpdateSecret`

- **KMS**:
  - `kms:CreateKey`
  - `kms:DeleteAlias`
  - `kms:DescribeKey`
  - `kms:EnableKey`
  - `kms:DisableKey`
  - `kms:GenerateDataKey`
  - `kms:Decrypt`
  - `kms:Encrypt`

- **IAM**:
  - `iam:CreateRole`
  - `iam:DeleteRole`
  - `iam:GetRole`
  - `iam:PutRolePolicy`
  - `iam:DeleteRolePolicy`
  - `iam:AttachRolePolicy`
  - `iam:DetachRolePolicy`
  - `iam:PassRole`

- **RDS**:
  - `rds:DescribeDBClusterSnapshots`
  - `rds:CopyDBClusterSnapshot`
  - `rds:DeleteDBCluster`
  - `rds:RestoreDBClusterFromSnapshot`
  - `rds:DescribeDBClusters`
  - `rds:ModifyDBCluster`

- **VPC**:
  - `ec2:DescribeVpcs`
  - `ec2:DescribeSubnets`
  - `ec2:DescribeSecurityGroups`

## Required Environment Variables

- `ENVIRONMENT`: The environment (e.g., dev, test, prod)
- `REGION`: The AWS region where the pipeline will be deployed
- `DYNAMODB_TABLE_NAME`: The name of the DynamoDB table for storing state and audit information
- `SNS_TOPIC_ARN`: The ARN of the SNS topic for sending notifications
- `KMS_KEY_ID`: The ID of the KMS key for encrypting sensitive data
- `VPC_ID`: The ID of the VPC where the Lambda functions will be deployed
- `SUBNET_IDS`: The IDs of the subnets where the Lambda functions will be deployed
- `SECURITY_GROUP_IDS`: The IDs of the security groups to be associated with the Lambda functions

## Required Secrets

- `aurora-restore/master-credentials`: The master credentials for the Aurora cluster
- `aurora-restore/app-credentials`: The application credentials for the Aurora cluster

## Required Network Configuration

- A VPC with at least two subnets in different Availability Zones
- Security groups with the necessary inbound and outbound rules
- NAT Gateway or VPC Endpoints for accessing AWS services from the VPC

## Required RDS Configuration

- An Aurora cluster with at least one snapshot
- Sufficient storage and compute resources for the restored cluster

## Required Python Packages

- `boto3`: For interacting with AWS services
- `botocore`: For handling AWS service exceptions
- `requests`: For making HTTP requests
- `json`: For parsing and serializing JSON data
- `datetime`: For handling date and time
- `uuid`: For generating unique identifiers
- `logging`: For logging messages
- `os`: For accessing environment variables
- `time`: For handling time-related operations
- `random`: For generating random values

## Required Development Tools

- Python 3.8 or later
- Git for version control
- A code editor or IDE (e.g., VS Code, PyCharm)
- pytest for testing

## Required Knowledge

- Understanding of AWS services and their interactions
- Understanding of serverless architecture
- Understanding of Python programming
- Understanding of database concepts
- Understanding of networking concepts
- Understanding of security concepts 