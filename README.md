# Aurora PostgreSQL Snapshot Restore Pipeline

This project implements a serverless pipeline for automating the restoration of Aurora PostgreSQL snapshots across AWS accounts and regions.

## Architecture

The pipeline consists of the following components:

- **EventBridge**: Triggers the pipeline daily at 1:00 AM
- **Lambda Functions**: Execute each stage of the process
- **Step Functions**: Orchestrates the workflow
- **DynamoDB**: Logs audit data and supports restartability
- **SNS**: Sends notifications
- **Secrets Manager**: Stores database credentials
- **SSM Parameter Store**: Stores configuration

## Lambda Functions

1. `aurora-restore-snapshot-check`: Verifies snapshot existence
2. `aurora-restore-copy-snapshot`: Copies snapshot to target account
3. `aurora-restore-check-copy-status`: Monitors copy progress
4. `aurora-restore-delete-rds`: Removes existing cluster
5. `aurora-restore-restore-snapshot`: Restores snapshot
6. `aurora-restore-check-restore-status`: Monitors restore progress
7. `aurora-restore-setup-db-users`: Configures database users
8. `aurora-restore-archive-snapshot`: Archives the snapshot
9. `aurora-restore-sns-notification`: Sends notifications

## Configuration

Required SSM Parameters:
- `/aurora-restore/source-account-id`
- `/aurora-restore/target-account-id`
- `/aurora-restore/source-region`
- `/aurora-restore/target-region`
- `/aurora-restore/source-cluster-id`
- `/aurora-restore/target-cluster-id`
- `/aurora-restore/snapshot-prefix`

Required Secrets:
- `/aurora-restore/db-credentials`

## Deployment

Each component can be deployed manually in the AWS Console. Follow the deployment guide in the `deployment` directory.

## Monitoring

The pipeline logs all operations to DynamoDB for audit and monitoring purposes. SNS notifications are sent for both successful completion and failures. 