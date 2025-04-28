# Common Issues and Solutions

This document provides solutions for common issues encountered when using the Aurora Restore Pipeline.

## Table of Contents

- [Deployment Issues](#deployment-issues)
- [Snapshot Check Issues](#snapshot-check-issues)
- [Snapshot Copy Issues](#snapshot-copy-issues)
- [Cluster Deletion Issues](#cluster-deletion-issues)
- [Cluster Restore Issues](#cluster-restore-issues)
- [Database User Setup Issues](#database-user-setup-issues)
- [Permission Issues](#permission-issues)
- [Configuration Issues](#configuration-issues)

## Deployment Issues

### CloudFormation Stack Creation Fails

**Issue**: CloudFormation stack creation fails during deployment.

**Solutions**:
1. Check CloudFormation events for specific errors:
   ```bash
   aws cloudformation describe-stack-events --stack-name aurora-restore-dev-lambda --region us-east-1
   ```
2. Verify that your AWS account has sufficient permissions to create all required resources.
3. Check if resource limits have been reached (e.g., Lambda function limits).
4. Validate CloudFormation templates before deployment:
   ```bash
   aws cloudformation validate-template --template-body file://infrastructure/lambda.yaml
   ```

### Lambda Function Packaging Fails

**Issue**: Lambda function packaging fails during the build process.

**Solutions**:
1. Verify that the `build_lambda_packages.sh` script has execution permissions:
   ```bash
   chmod +x build_lambda_packages.sh
   ```
2. Check if the S3 bucket exists and you have permissions to write to it.
3. Ensure that required directories and files exist:
   ```bash
   ls -la lambda_functions/
   ls -la utils/
   ```
4. Verify that Python dependencies can be installed:
   ```bash
   pip install -r requirements.txt
   ```

## Snapshot Check Issues

### Snapshot Not Found

**Issue**: The pipeline fails during the snapshot check step because the snapshot cannot be found.

**Solutions**:
1. Verify that the snapshot exists in the source region:
   ```bash
   aws rds describe-db-cluster-snapshots --snapshot-type automated --region us-east-1
   ```
2. Check if the snapshot name format matches what the pipeline expects:
   ```bash
   # Expected format: aurora-snapshot-YYYY-MM-DD
   aws rds describe-db-cluster-snapshots --db-cluster-snapshot-identifier aurora-snapshot-2023-01-01 --region us-east-1
   ```
3. Verify that you have permissions to access the snapshot:
   ```bash
   aws rds describe-db-cluster-snapshot-attributes --db-cluster-snapshot-identifier aurora-snapshot-2023-01-01 --region us-east-1
   ```

### Incorrect Snapshot Naming Convention

**Issue**: The pipeline cannot find the snapshot because it's using an incorrect naming convention.

**Solutions**:
1. Update the `snapshot_prefix` parameter in the pipeline configuration to match your snapshot naming convention.
2. Modify the Lambda function to handle different snapshot naming formats.
3. Create a custom snapshot with the expected naming convention.

## Snapshot Copy Issues

### Cross-Region Copy Fails

**Issue**: Snapshot copy fails when copying across regions.

**Solutions**:
1. Verify that the source and target regions are correctly specified:
   ```bash
   aws rds describe-db-cluster-snapshots --db-cluster-snapshot-identifier aurora-snapshot-2023-01-01 --region us-east-1
   ```
2. Check if you have permissions to copy snapshots across regions:
   ```bash
   aws rds copy-db-cluster-snapshot --source-db-cluster-snapshot-identifier arn:aws:rds:us-east-1:123456789012:cluster-snapshot:aurora-snapshot-2023-01-01 --target-db-cluster-snapshot-identifier aurora-snapshot-copy --region us-west-2
   ```
3. Verify that the KMS key is accessible in the target region (if using encryption).
4. Check CloudWatch Logs for specific error messages:
   ```bash
   aws logs filter-log-events --log-group-name /aws/lambda/aurora-restore-copy-snapshot --region us-east-1
   ```

### Copy Takes Too Long

**Issue**: Snapshot copy operation takes longer than expected.

**Solutions**:
1. Check the size of the snapshot:
   ```bash
   aws rds describe-db-cluster-snapshots --db-cluster-snapshot-identifier aurora-snapshot-2023-01-01 --region us-east-1 --query "DBClusterSnapshots[0].AllocatedStorage"
   ```
2. Increase the timeout for the Check Copy Status Lambda function.
3. Adjust the retry delay in the Step Functions state machine.
4. Consider pre-copying snapshots as part of a scheduled maintenance window.

## Cluster Deletion Issues

### Cluster Deletion Fails

**Issue**: The pipeline fails when trying to delete an existing cluster.

**Solutions**:
1. Check if the cluster has deletion protection enabled:
   ```bash
   aws rds describe-db-clusters --db-cluster-identifier target-cluster --region us-east-1 --query "DBClusters[0].DeletionProtection"
   ```
2. Verify that you have permissions to delete the cluster:
   ```bash
   aws rds delete-db-cluster --db-cluster-identifier target-cluster --skip-final-snapshot --region us-east-1
   ```
3. Check if there are DB instances in the cluster that need to be deleted first:
   ```bash
   aws rds describe-db-clusters --db-cluster-identifier target-cluster --region us-east-1 --query "DBClusters[0].DBClusterMembers"
   ```
4. Check CloudWatch Logs for specific error messages.

### Cluster Does Not Exist

**Issue**: The pipeline attempts to delete a cluster that doesn't exist.

**Solutions**:
1. Update the Lambda function to handle the case where the cluster doesn't exist gracefully.
2. Verify the cluster name in the pipeline configuration.
3. Check the AWS region being used for the operation.

## Cluster Restore Issues

### Restore Operation Fails

**Issue**: The cluster restore operation fails.

**Solutions**:
1. Check if the target DB subnet group exists:
   ```bash
   aws rds describe-db-subnet-groups --region us-east-1
   ```
2. Verify that the VPC security groups are correctly configured:
   ```bash
   aws ec2 describe-security-groups --group-ids sg-12345678 --region us-east-1
   ```
3. Check if the DB parameter group exists:
   ```bash
   aws rds describe-db-parameter-groups --region us-east-1
   ```
4. Verify that the target instance class is supported in the target region:
   ```bash
   aws rds describe-orderable-db-instance-options --engine aurora --engine-version 5.7 --region us-east-1
   ```
5. Check CloudWatch Logs for specific error messages.

### Restore Takes Too Long

**Issue**: The cluster restore operation takes longer than expected.

**Solutions**:
1. Check the size of the snapshot:
   ```bash
   aws rds describe-db-cluster-snapshots --db-cluster-snapshot-identifier aurora-snapshot-copy --region us-east-1 --query "DBClusterSnapshots[0].AllocatedStorage"
   ```
2. Increase the timeout for the Check Restore Status Lambda function.
3. Adjust the retry delay in the Step Functions state machine.
4. Consider using a larger instance class for faster restore.

## Database User Setup Issues

### Connection Failed

**Issue**: The pipeline fails to connect to the restored database to set up users.

**Solutions**:
1. Verify that the security group allows connections from the Lambda function:
   ```bash
   aws ec2 describe-security-groups --group-ids sg-12345678 --region us-east-1
   ```
2. Check if the database is publicly accessible:
   ```bash
   aws rds describe-db-clusters --db-cluster-identifier target-cluster --region us-east-1 --query "DBClusters[0].PubliclyAccessible"
   ```
3. Verify that the master username and password are correct in Secrets Manager:
   ```bash
   aws secretsmanager get-secret-value --secret-id aurora-restore/dev/master-credentials --region us-east-1
   ```
4. Check if the cluster is available:
   ```bash
   aws rds describe-db-clusters --db-cluster-identifier target-cluster --region us-east-1 --query "DBClusters[0].Status"
   ```
5. Check CloudWatch Logs for specific error messages.

### Permission Issues

**Issue**: The pipeline fails to create users due to permission issues.

**Solutions**:
1. Verify that the master user has sufficient privileges:
   ```sql
   SHOW GRANTS FOR 'master'@'%';
   ```
2. Check if the user already exists:
   ```sql
   SELECT User, Host FROM mysql.user;
   ```
3. Verify that the Lambda function has permission to access Secrets Manager:
   ```bash
   aws iam get-policy --policy-arn arn:aws:iam::123456789012:policy/aurora-restore-lambda-policy
   ```
4. Check CloudWatch Logs for specific error messages.

## Permission Issues

### IAM Role Permissions

**Issue**: Lambda functions fail due to insufficient IAM permissions.

**Solutions**:
1. Verify that the Lambda execution role has the necessary permissions:
   ```bash
   aws iam get-role --role-name aurora-restore-lambda-execution-role
   aws iam list-attached-role-policies --role-name aurora-restore-lambda-execution-role
   ```
2. Check CloudWatch Logs for specific permission errors:
   ```bash
   aws logs filter-log-events --log-group-name /aws/lambda/aurora-restore-snapshot-check --filter-pattern "AccessDenied" --region us-east-1
   ```
3. Update the IAM policy to include the necessary permissions.
4. Verify that the Lambda function can access resources in the VPC:
   ```bash
   aws lambda get-function-configuration --function-name aurora-restore-snapshot-check --region us-east-1
   ```

### Cross-Account Permissions

**Issue**: The pipeline fails when working with resources in different AWS accounts.

**Solutions**:
1. Verify that cross-account roles are correctly configured:
   ```bash
   aws iam get-role --role-name aurora-restore-cross-account-role
   ```
2. Check if snapshots are shared with the target account:
   ```bash
   aws rds describe-db-cluster-snapshot-attributes --db-cluster-snapshot-identifier aurora-snapshot-2023-01-01 --region us-east-1
   ```
3. Update resource policies to allow cross-account access.
4. Verify that KMS keys are accessible across accounts.

## Configuration Issues

### Missing Configuration Parameters

**Issue**: The pipeline fails due to missing configuration parameters.

**Solutions**:
1. Verify that all required parameters are specified in the event input:
   ```json
   {
     "snapshot_name": "aurora-snapshot-2023-01-01",
     "source_region": "us-east-1",
     "target_region": "us-west-2",
     "target_cluster_id": "restored-cluster",
     "db_subnet_group_name": "default",
     "vpc_security_group_ids": ["sg-12345678"]
   }
   ```
2. Check if environment variables are correctly set for Lambda functions:
   ```bash
   aws lambda get-function-configuration --function-name aurora-restore-snapshot-check --region us-east-1 --query "Environment"
   ```
3. Verify that required resources (e.g., subnet groups, security groups) exist in the target region.
4. Check CloudWatch Logs for specific error messages.

### Incompatible Configurations

**Issue**: The pipeline fails due to incompatible configurations.

**Solutions**:
1. Verify that the snapshot engine version is compatible with the target engine version:
   ```bash
   aws rds describe-db-cluster-snapshots --db-cluster-snapshot-identifier aurora-snapshot-2023-01-01 --region us-east-1 --query "DBClusterSnapshots[0].EngineVersion"
   ```
2. Check if the DB parameter group is compatible with the engine version:
   ```bash
   aws rds describe-db-parameter-groups --db-parameter-group-name default.aurora-mysql5.7 --region us-east-1
   ```
3. Verify that the instance class is available in the target region:
   ```bash
   aws rds describe-orderable-db-instance-options --engine aurora --engine-version 5.7 --region us-west-2
   ```
4. Check if the VPC configuration is valid (subnets, security groups, etc.).
5. Verify that the KMS key is available and accessible.

## Next Steps

If you're unable to resolve the issue using the solutions above, consider the following:

1. Review the [Debugging Guide](./02_debugging_guide.md) for more detailed troubleshooting steps.
2. Check the [Error Reference](./03_error_reference.md) for specific error codes and their meanings.
3. Contact the Aurora Restore Pipeline development team for assistance. 