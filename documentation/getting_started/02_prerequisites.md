# Prerequisites for Aurora Restore Pipeline

This document outlines the prerequisites needed to deploy and use the Aurora Restore Pipeline.

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
   - AWS CLI v2 installed and configured
   - Python 3.9+ installed
   - Git (for cloning the repository)
   - Terminal or command prompt

3. **AWS Regions**
   - Identify source region (where the original snapshot exists)
   - Identify target region (where you want to restore the database)
   - Ensure you have access to both regions

## Essential Resources

The following AWS resources are required for the Aurora Restore Pipeline:

1. **DynamoDB Tables**
   - State table for tracking pipeline state
   - Audit table for logging operations

2. **S3 Bucket**
   - For storing Lambda deployment packages

3. **SNS Topic**
   - For notifications about pipeline status

4. **Secrets**
   - Master database credentials
   - Application user credentials
   - KMS key for encryption

5. **IAM Roles and Policies**
   - Lambda execution role
   - Secrets access policies

## Network Requirements

1. **VPC Configuration**
   - VPC with private subnets for the restored Aurora cluster
   - Security groups allowing database access
   - NAT Gateway or VPC Endpoints for Lambda to access AWS services

2. **Connectivity**
   - Access between Lambda functions and Aurora clusters
   - Access to AWS services (RDS, DynamoDB, SNS, etc.)

## Snapshot Requirements

1. **Source Snapshot**
   - Manual or automated Aurora cluster snapshot
   - Appropriate permissions to access the snapshot
   - If cross-account, proper sharing configuration

## Security Requirements

1. **Encryption**
   - KMS key for encrypting secrets
   - Encryption settings for the restored database

2. **Authentication**
   - Database master user credentials
   - Application user credentials
   - IAM permissions for accessing the pipeline

## Next Steps

After ensuring you have all the prerequisites in place:

1. Follow the [Quick Start Guide](./03_quick_start.md) for a simple deployment
2. For detailed setup instructions, refer to the [Implementation Guide](../implementation_guide/01_prerequisites.md)

## Checklist

Use this checklist to verify you have everything prepared:

- [ ] AWS account access with required permissions
- [ ] AWS CLI configured with appropriate credentials
- [ ] Source and target regions identified
- [ ] VPC, subnets, and security groups identified or ready to create
- [ ] Source snapshot identified and accessible
- [ ] Tools installed (AWS CLI, Python, Git)
- [ ] KMS key strategy determined (new or existing)
- [ ] Database credentials strategy determined
- [ ] Notification recipients identified 