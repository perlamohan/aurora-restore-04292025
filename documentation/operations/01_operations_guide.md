# Operations Guide

This document provides guidance for day-to-day operations of the Aurora Restore Pipeline, including routine tasks, monitoring, management, and troubleshooting procedures.

## Routine Operations

### Daily Checks

| Task | Description | Command/Procedure |
|------|-------------|-------------------|
| Verify pipeline health | Check that the pipeline is operational | Review CloudWatch dashboard `AuroraRestorePipelineDashboard` |
| Review recent restores | Check status of recent restore operations | Query DynamoDB table `AuroraRestoreState` for recent operations |
| Check alarm status | Verify no active alarms | Review CloudWatch Alarms section |
| Validate snapshot availability | Ensure daily snapshots are available | `aws rds describe-db-cluster-snapshots --snapshot-type automated` |

### Weekly Tasks

| Task | Description | Command/Procedure |
|------|-------------|-------------------|
| Review audit logs | Check audit trail for anomalies | Query `AuroraRestoreAudit` table for last 7 days |
| Verify metrics | Review operational metrics for trends | Analyze CloudWatch metrics in dashboard |
| Check resource utilization | Monitor resource usage for optimization | Review Lambda duration and memory metrics |
| Test notifications | Ensure SNS notifications are working | Send test notification using SNS console |

### Monthly Tasks

| Task | Description | Command/Procedure |
|------|-------------|-------------------|
| Security review | Review IAM permissions and security groups | Analyze IAM Access Analyzer findings |
| Cost optimization | Analyze cost and identify optimization opportunities | Review AWS Cost Explorer with tag filters |
| Dependency updates | Check for outdated dependencies | Review Lambda layer versions and dependencies |
| Disaster recovery test | Validate pipeline can be restored | Execute DR runbook (see section below) |

## Monitoring Procedures

### Monitoring Dashboard

The primary monitoring interface is the CloudWatch dashboard `AuroraRestorePipelineDashboard`. Key sections to review:

1. **Pipeline Execution Status**
   - Success Rate (%) - Should be close to 100%
   - Average Duration (minutes) - Track for increases over time
   - Error Count by Type - Investigate any non-zero values

2. **Lambda Function Metrics**
   - Duration by Function - Watch for increases indicating performance issues
   - Error Count by Function - Investigate any non-zero values
   - Throttles by Function - Increase concurrency limits if throttling occurs

3. **Step Functions Metrics**
   - Execution Timeline - Review for extended durations
   - Execution Status Count - Monitor failure rates

4. **RDS Metrics**
   - CPU Utilization - Should be below 80% under normal load
   - Free Memory - Should have adequate headroom
   - Database Connections - Watch for connection limits being approached

### Useful CloudWatch Logs Insights Queries

Save these queries in CloudWatch Logs Insights for quick troubleshooting:

1. **Errors by Lambda Function**:
```
filter level = "ERROR"
| stats count(*) as errorCount by function_name
| sort errorCount desc
```

2. **Operation Duration Analysis**:
```
filter message like "Operation completed"
| parse message "in * seconds" as duration
| stats avg(duration), max(duration), min(duration) by function_name
```

3. **Track Specific Operation**:
```
filter operation_id = "restore-YYYYMMDD-HHMMSS"
| sort @timestamp asc
| display @timestamp, level, function_name, message
```

## State Management

### Understanding State Data

State data is stored in the DynamoDB table `AuroraRestoreState`. Key fields include:

- `operation_id`: Unique identifier for the operation
- `status`: Current status of the operation
- `start_time`: When the operation began
- `last_updated_time`: When the state was last updated
- `parameters`: Input parameters for the operation
- `snapshot_details`: Information about the snapshot being restored
- `restore_details`: Information about the restore operation
- `error`: Error information if the operation failed

### Querying State Data

Use the AWS CLI or console to query state data:

```bash
# Get state for a specific operation
aws dynamodb get-item \
  --table-name AuroraRestoreState \
  --key '{"operation_id": {"S": "restore-20230615-123456"}}'

# Query recent operations with a specific status
aws dynamodb scan \
  --table-name AuroraRestoreState \
  --filter-expression "status = :status AND start_time > :time" \
  --expression-attribute-values '{
    ":status": {"S": "FAILED"},
    ":time": {"S": "2023-06-01T00:00:00Z"}
  }'
```

### Managing State Data

The state table has TTL enabled to automatically remove old records. However, you may need to:

1. **Archive old state data**:
   ```bash
   # Export state data to S3 for long-term retention
   aws dynamodb export-table-to-point-in-time \
     --table-arn arn:aws:dynamodb:$REGION:$ACCOUNT_ID:table/AuroraRestoreState \
     --s3-bucket aurora-restore-archives \
     --s3-prefix state-data/$(date +%Y-%m-%d)
   ```

2. **Clean up stuck operations**:
   ```bash
   # Update state for a stuck operation
   aws dynamodb update-item \
     --table-name AuroraRestoreState \
     --key '{"operation_id": {"S": "restore-20230615-123456"}}' \
     --update-expression "SET #status = :status, error = :error" \
     --expression-attribute-names '{"#status": "status"}' \
     --expression-attribute-values '{
       ":status": {"S": "FAILED"},
       ":error": {"M": {"message": {"S": "Manually marked as failed"}, "code": {"S": "MANUAL_INTERVENTION"}}}
     }'
   ```

## Managing Restores

### Initiating a Restore

To initiate a restore operation:

```bash
aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:$REGION:$ACCOUNT_ID:stateMachine:aurora-restore-state-machine \
  --name restore-$(date +%Y%m%d-%H%M%S) \
  --input '{
    "source_snapshot_date": "2023-06-15",
    "source_region": "us-east-1",
    "target_region": "us-west-2",
    "target_cluster_id": "aurora-restored-cluster",
    "db_instance_class": "db.r5.large",
    "vpc_security_group_ids": ["sg-12345678"],
    "db_subnet_group_name": "default-vpc-subnet-group",
    "delete_cluster_if_exists": true
  }'
```

### Monitoring a Restore

Track the progress of a restore operation:

1. **Via Step Functions console**:
   - Navigate to AWS Step Functions
   - Select the state machine `aurora-restore-state-machine`
   - Find and select the execution
   - View the visual workflow and execution status

2. **Via DynamoDB**:
   - Query the `AuroraRestoreState` table for the operation ID
   - Check the `status` field for current status
   - Check the `error` field if the status is `FAILED`

3. **Via CloudWatch Logs**:
   - Search across all Lambda function logs for the operation ID
   - View the execution history chronologically

### Cancelling a Restore

To cancel an in-progress restore:

1. **Via Step Functions console**:
   - Navigate to the execution in the Step Functions console
   - Click "Stop execution"
   - Select "Error" for the cause and provide a reason

2. **Via AWS CLI**:
   ```bash
   aws stepfunctions stop-execution \
     --execution-arn arn:aws:states:$REGION:$ACCOUNT_ID:execution:aurora-restore-state-machine:restore-20230615-123456 \
     --error "ManualCancellation" \
     --cause "Restore cancelled by operator"
   ```

3. **Clean up resources**:
   - Check if any snapshots were created and delete if necessary
   - Check if a partial cluster was created and delete if necessary

## Troubleshooting

### Common Issues and Resolutions

| Issue | Potential Causes | Resolution |
|-------|------------------|------------|
| Snapshot not found | Incorrect date format, snapshot deleted | Verify snapshot exists with correct date format |
| Copy snapshot failed | Insufficient permissions, KMS key issues | Check IAM roles, KMS key policies, retry operation |
| Restore operation timeout | Large database size, network issues | Increase Step Functions timeout, check network connectivity |
| Database user setup failed | Connection issues, permission problems | Check security groups, network connectivity, retry setup |
| SNS notification failed | Topic deleted, policy issues | Verify SNS topic exists and has correct permissions |

### Handling Stuck Operations

If an operation is stuck in a specific state:

1. **Identify the current step**:
   - Check Step Functions execution to see current state
   - Review CloudWatch Logs for the most recent Lambda invocation

2. **Manual intervention options**:
   - For stuck snapshot copy: Check RDS console for copy status, may need to delete partial copy
   - For stuck restore: Check RDS console for cluster status, may need to delete partial cluster
   - For stuck delete: Check RDS console for cluster status, may need to force deletion

3. **Restart operation**:
   - Update state in DynamoDB to mark as failed
   - Initiate a new restore operation with the same parameters

### Escalation Procedures

When to escalate issues to the development team:

1. **Critical issues**:
   - Multiple consecutive restore failures
   - Security-related issues
   - Data integrity problems

2. **Escalation path**:
   - Level 1: Operations team attempts resolution using this guide
   - Level 2: DevOps team for infrastructure or AWS service issues
   - Level 3: Development team for code-related issues

3. **Information to include**:
   - Operation ID
   - Step Functions execution ARN
   - Relevant CloudWatch logs
   - Error messages and stack traces
   - Actions already taken to resolve

## Maintenance Procedures

### Updating Lambda Functions

To update Lambda functions with new code:

1. **Prepare the update**:
   ```bash
   # Package the Lambda code
   ./scripts/build_lambda_packages.sh
   ```

2. **Deploy the update**:
   ```bash
   # Deploy with CloudFormation
   aws cloudformation update-stack \
     --stack-name aurora-restore-pipeline \
     --template-body file://infrastructure/aurora-restore-pipeline.yaml \
     --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM
   ```

3. **Verify the update**:
   - Check Lambda console for updated versions
   - Execute a test restore to verify functionality

### Updating Step Functions State Machine

To update the state machine definition:

1. **Update the definition**:
   ```bash
   aws stepfunctions update-state-machine \
     --state-machine-arn arn:aws:states:$REGION:$ACCOUNT_ID:stateMachine:aurora-restore-state-machine \
     --definition file://infrastructure/step_functions_definition.json
   ```

2. **Verify the update**:
   - Check the state machine visualization in the console
   - Execute a test restore to verify workflow

### Database Parameter Groups

To update database parameter groups used by the pipeline:

1. **Create or modify parameter group**:
   ```bash
   aws rds create-db-cluster-parameter-group \
     --db-cluster-parameter-group-name aurora-restore-params \
     --db-parameter-group-family aurora-mysql5.7 \
     --description "Parameter group for restored Aurora clusters"
   
   aws rds modify-db-cluster-parameter-group \
     --db-cluster-parameter-group-name aurora-restore-params \
     --parameters "ParameterName=innodb_file_format,ParameterValue=Barracuda,ApplyMethod=immediate"
   ```

2. **Update pipeline configuration**:
   - Update the CloudFormation template or
   - Update the default parameter group in the Lambda function code

## Disaster Recovery

### Backup Procedures

1. **Export DynamoDB tables**:
   ```bash
   aws dynamodb export-table-to-point-in-time \
     --table-arn arn:aws:dynamodb:$REGION:$ACCOUNT_ID:table/AuroraRestoreState \
     --s3-bucket aurora-restore-dr-backup \
     --s3-prefix state-table/$(date +%Y-%m-%d)
   
   aws dynamodb export-table-to-point-in-time \
     --table-arn arn:aws:dynamodb:$REGION:$ACCOUNT_ID:table/AuroraRestoreAudit \
     --s3-bucket aurora-restore-dr-backup \
     --s3-prefix audit-table/$(date +%Y-%m-%d)
   ```

2. **Back up Lambda code**:
   ```bash
   # Create a backup of Lambda functions
   for function in $(aws lambda list-functions --query "Functions[?starts_with(FunctionName, 'aurora-restore')].FunctionName" --output text); do
     aws lambda get-function --function-name $function --query 'Code.Location' --output text | \
     xargs curl -o lambda-backups/$function.zip
   done
   ```

3. **Back up CloudFormation templates**:
   ```bash
   aws s3 cp infrastructure/ s3://aurora-restore-dr-backup/infrastructure/$(date +%Y-%m-%d)/ --recursive
   ```

### Recovery Procedures

To recover the pipeline in a disaster scenario:

1. **Deploy infrastructure**:
   ```bash
   aws cloudformation create-stack \
     --stack-name aurora-restore-pipeline \
     --template-body file://infrastructure/aurora-restore-pipeline.yaml \
     --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM
   ```

2. **Restore DynamoDB tables if needed**:
   ```bash
   aws dynamodb import-table \
     --s3-bucket-source '{"S3Bucket":"aurora-restore-dr-backup","S3KeyPrefix":"state-table/YYYY-MM-DD"}' \
     --table-creation-parameters '{"TableName":"AuroraRestoreState","KeySchema":[{"AttributeName":"operation_id","KeyType":"HASH"}],"AttributeDefinitions":[{"AttributeName":"operation_id","AttributeType":"S"}],"BillingMode":"PAY_PER_REQUEST"}'
   ```

3. **Verify recovery**:
   - Check that all components are deployed
   - Execute a test restore operation
   - Verify SNS notifications are working

## Reference Information

### Key Resources

| Resource Type | Name/ARN | Description |
|---------------|----------|-------------|
| State Machine | aurora-restore-state-machine | Main workflow orchestrator |
| DynamoDB Table | AuroraRestoreState | Stores operation state |
| DynamoDB Table | AuroraRestoreAudit | Stores audit events |
| SNS Topic | aurora-restore-notifications | Notifications for restore operations |
| CloudWatch Dashboard | AuroraRestorePipelineDashboard | Main monitoring dashboard |
| Lambda Functions | aurora-restore-* | Individual pipeline steps |

### Environment Variables

| Name | Description | Default Value |
|------|-------------|---------------|
| STATE_TABLE_NAME | DynamoDB table for state | AuroraRestoreState |
| AUDIT_TABLE_NAME | DynamoDB table for audit | AuroraRestoreAudit |
| SNS_TOPIC_ARN | ARN for notifications | arn:aws:sns:$REGION:$ACCOUNT_ID:aurora-restore-notifications |
| DEFAULT_DB_INSTANCE_CLASS | Default instance type | db.r5.large |
| DEFAULT_SOURCE_REGION | Default source region | us-east-1 |
| ADMIN_SECRET_ID | Secret for admin credentials | aurora-restore/admin-credentials |

### Useful AWS CLI Commands

```bash
# Get list of all pipeline components
aws cloudformation describe-stack-resources --stack-name aurora-restore-pipeline

# Get recent Step Function executions
aws stepfunctions list-executions \
  --state-machine-arn arn:aws:states:$REGION:$ACCOUNT_ID:stateMachine:aurora-restore-state-machine \
  --max-results 10

# Get CloudWatch Logs for specific Lambda function
aws logs filter-log-events \
  --log-group-name /aws/lambda/aurora-restore-snapshot-check \
  --filter-pattern "ERROR"

# Get SNS subscription status
aws sns list-subscriptions-by-topic \
  --topic-arn arn:aws:sns:$REGION:$ACCOUNT_ID:aurora-restore-notifications
```

## Next Steps

For more detailed information, refer to:
- [Implementation Guide](../implementation_guide/01_prerequisites.md)
- [Troubleshooting Guide](../troubleshooting/01_common_issues.md)
- [Architecture Documentation](../architecture/01_overview.md) 