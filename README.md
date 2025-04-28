# Aurora Restore Pipeline

This project implements a pipeline for restoring Aurora database clusters from snapshots across AWS regions.

## Prerequisites

- AWS CLI installed and configured
- Python 3.9 or later
- Required AWS permissions to create and manage:
  - Lambda functions
  - DynamoDB tables
  - SNS topics
  - IAM roles and policies
  - Secrets Manager secrets
  - RDS resources

## Deployment Steps

1. **Update Configuration**
   - Edit `config.json` with your specific values:
     - Source and target regions
     - Cluster IDs
     - VPC configuration
     - Database credentials secret IDs
     - SNS topic ARN

2. **Create Secrets in AWS Secrets Manager**
   ```bash
   # Create master credentials secret
   aws secretsmanager create-secret \
       --name aurora-restore-master-credentials \
       --secret-string '{
           "username": "master_user",
           "password": "master_password",
           "database": "postgres"
       }'

   # Create app credentials secret
   aws secretsmanager create-secret \
       --name aurora-restore-app-credentials \
       --secret-string '{
           "app_username": "app_user",
           "app_password": "app_password",
           "readonly_username": "readonly_user",
           "readonly_password": "readonly_password"
       }'
   ```

3. **Run Deployment Script**
   ```bash
   chmod +x deploy.sh
   ./deploy.sh
   ```

4. **Configure VPC Settings**
   - Update each Lambda function's VPC configuration in the AWS Console:
     - Select the VPC
     - Choose subnets
     - Select security groups

## Lambda Functions

The pipeline consists of the following Lambda functions:

1. `aurora-restore-snapshot-check`: Checks for available snapshots
2. `aurora-restore-copy-snapshot`: Copies snapshot to target region
3. `aurora-restore-check-copy-status`: Monitors copy progress
4. `aurora-restore-delete-rds`: Deletes existing target cluster
5. `aurora-restore-restore-snapshot`: Restores cluster from snapshot
6. `aurora-restore-check-restore-status`: Monitors restore progress
7. `aurora-restore-setup-db-users`: Sets up database users
8. `aurora-restore-sns-notification`: Sends completion notification

## State Management

- States are stored in DynamoDB table `aurora-restore-state`
- Each state entry contains:
  - `operation_id`: Unique identifier for the restore operation
  - `step`: Current step in the pipeline
  - Additional step-specific data

## Monitoring

- CloudWatch Logs: Each Lambda function logs to its own log group
- SNS Notifications: Pipeline completion and failures
- DynamoDB: State tracking and audit trail

## Error Handling

- Each step includes comprehensive error handling
- Failed operations are logged and reported via SNS
- State is preserved for debugging and retry scenarios

## Security

- Database credentials stored in Secrets Manager
- IAM roles follow principle of least privilege
- VPC isolation for Lambda functions
- Encryption at rest for RDS and DynamoDB

## Maintenance

- Regular cleanup of old state entries recommended
- Monitor CloudWatch metrics for performance
- Review and rotate database credentials periodically

## Troubleshooting

1. Check CloudWatch Logs for detailed error messages
2. Verify VPC connectivity for Lambda functions
3. Ensure proper IAM permissions
4. Validate database credentials in Secrets Manager
5. Check RDS cluster status and permissions

## Support

For issues and feature requests, please create an issue in the repository. 