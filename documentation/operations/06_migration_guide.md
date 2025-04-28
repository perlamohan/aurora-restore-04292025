# Migration Guide: Upgrading Aurora Restore Pipeline

This guide provides instructions for migrating from previous versions of the Aurora Restore Pipeline to the current version. It covers version-specific upgrade paths, breaking changes, and strategies for minimizing downtime during upgrades.

## Table of Contents
- [Version Compatibility Matrix](#version-compatibility-matrix)
- [Preparation Steps](#preparation-steps)
- [Upgrade Paths](#upgrade-paths)
- [Breaking Changes](#breaking-changes)
- [State Migration](#state-migration)
- [Testing Upgrades](#testing-upgrades)
- [Rollback Procedures](#rollback-procedures)

## Version Compatibility Matrix

| From Version | To Version | Direct Upgrade Possible | Notes |
|--------------|------------|-------------------------|-------|
| 1.0.x        | 2.0.x      | Yes                     | Requires DynamoDB schema update |
| 1.0.x        | 3.0.x      | No                      | Must upgrade to 2.0.x first |
| 2.0.x        | 3.0.x      | Yes                     | IAM permission changes required |

## Preparation Steps

Before upgrading the Aurora Restore Pipeline, complete these preparation steps:

1. **Backup Current State**: Ensure all DynamoDB tables are backed up
   ```bash
   aws dynamodb create-backup --table-name AuroraRestoreState --backup-name pre-upgrade-backup
   aws dynamodb create-backup --table-name AuroraRestoreAudit --backup-name pre-upgrade-backup
   ```

2. **Backup CloudFormation Stacks**: Create exports of your current CloudFormation stacks
   ```bash
   aws cloudformation get-template --stack-name aurora-restore-pipeline > aurora-restore-pipeline-template-backup.json
   ```

3. **Review Resource Usage**: Check for any in-progress operations
   ```bash
   aws dynamodb scan --table-name AuroraRestoreState --filter-expression "completed = :completed" --expression-attribute-values '{":completed": {"BOOL": false}}'
   ```

4. **Schedule Downtime**: If possible, schedule the upgrade when no restore operations are in progress

## Upgrade Paths

### Upgrading from 1.0.x to 2.0.x

1. Update the Lambda function code:
   ```bash
   ./build_lambda_packages.sh
   ```

2. Update the CloudFormation stack:
   ```bash
   aws cloudformation update-stack --stack-name aurora-restore-pipeline --template-body file://infrastructure/cloudformation/aurora-restore-pipeline.yaml --parameters file://infrastructure/cloudformation/parameters.json --capabilities CAPABILITY_IAM
   ```

3. Apply DynamoDB schema updates:
   ```bash
   python scripts/update_dynamodb_schema_v1_to_v2.py
   ```

### Upgrading from 2.0.x to 3.0.x

1. Update IAM permissions first:
   ```bash
   aws cloudformation update-stack --stack-name aurora-restore-pipeline-iam --template-body file://infrastructure/cloudformation/aurora-restore-pipeline-iam.yaml --capabilities CAPABILITY_IAM
   ```

2. Update the Lambda function code:
   ```bash
   ./build_lambda_packages.sh
   ```

3. Update the main CloudFormation stack:
   ```bash
   aws cloudformation update-stack --stack-name aurora-restore-pipeline --template-body file://infrastructure/cloudformation/aurora-restore-pipeline.yaml --parameters file://infrastructure/cloudformation/parameters.json --capabilities CAPABILITY_IAM
   ```

## Breaking Changes

### Version 2.0.x Breaking Changes
- DynamoDB schema now includes additional fields for audit tracking
- State format has changed to accommodate new error handling strategies
- Step Functions definition has been updated with additional error handling states

### Version 3.0.x Breaking Changes
- Lambda functions require additional IAM permissions for CloudWatch metrics
- SNS notification format has changed to include more detailed information
- Configuration file format has been updated with new parameters

## State Migration

When upgrading between major versions, state migration may be necessary:

1. For 1.0.x to 2.0.x, run the state migration script:
   ```bash
   python scripts/migrate_state_v1_to_v2.py
   ```

2. For 2.0.x to 3.0.x, run the enhanced state migration script:
   ```bash
   python scripts/migrate_state_v2_to_v3.py
   ```

## Testing Upgrades

Always test upgrades in a non-production environment first:

1. Create a clone of your production environment:
   ```bash
   ./scripts/clone_environment.sh production staging
   ```

2. Perform the upgrade on the staging environment
   ```bash
   ./scripts/upgrade.sh staging 3.0.0
   ```

3. Validate the upgrade by running test restore operations
   ```bash
   ./scripts/test_restore.sh staging
   ```

## Rollback Procedures

If issues occur during the upgrade, use these rollback procedures:

1. Revert to the previous CloudFormation stack:
   ```bash
   aws cloudformation update-stack --stack-name aurora-restore-pipeline --template-body file://aurora-restore-pipeline-template-backup.json --capabilities CAPABILITY_IAM
   ```

2. Restore the previous Lambda function versions:
   ```bash
   ./scripts/rollback_lambda_versions.sh
   ```

3. Restore DynamoDB tables if needed:
   ```bash
   aws dynamodb restore-table-from-backup --target-table-name AuroraRestoreState --backup-arn <backup-arn>
   ```

## Post-Migration Verification

After completing the migration, verify the following:

1. All Lambda functions are deployed with the correct versions
2. Step Functions executions can be initiated successfully
3. DynamoDB tables have the correct schema
4. Sample restore operations complete successfully
5. All monitoring and alerting is functioning as expected

For assistance with migrations, contact the support team at support@example.com. 