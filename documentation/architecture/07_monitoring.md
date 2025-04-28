# Monitoring and Observability

This document outlines the monitoring and observability strategy for the Aurora Restore Pipeline, providing guidance on monitoring setup, key metrics, alerting, and troubleshooting.

## Monitoring Strategy

The Aurora Restore Pipeline implements a comprehensive monitoring approach that encompasses:

1. **Metrics Collection**: Capturing performance and operational data
2. **Logging**: Detailed event and error logging
3. **Alerting**: Proactive notification of issues
4. **Dashboards**: Visual representation of pipeline health
5. **Audit Trail**: Historical record of pipeline operations

## CloudWatch Metrics

The following key metrics are emitted by the pipeline components:

### Lambda Function Metrics

| Metric Name | Description | Dimensions | Threshold |
|-------------|-------------|------------|-----------|
| `AuroraRestoreDuration` | Duration of each Lambda execution | `operation_id`, `function_name` | > 60 seconds |
| `AuroraRestoreSuccess` | Successful executions (1=success, 0=failure) | `operation_id`, `function_name` | < 1 |
| `AuroraRestoreErrors` | Count of errors encountered | `operation_id`, `function_name`, `error_type` | > 0 |
| `AuroraRestoreRetries` | Count of retry attempts | `operation_id`, `function_name` | > 2 |

### Step Functions Metrics

| Metric Name | Description | Dimensions | Threshold |
|-------------|-------------|------------|-----------|
| `ExecutionTime` | Duration of Step Function execution | `StateMachineArn` | > 8 hours |
| `ExecutionThrottled` | Count of throttled executions | `StateMachineArn` | > 0 |
| `ExecutionsSucceeded` | Count of successful executions | `StateMachineArn` | N/A (tracking) |
| `ExecutionsFailed` | Count of failed executions | `StateMachineArn` | > 0 |
| `ExecutionsTimedOut` | Count of timed out executions | `StateMachineArn` | > 0 |

### RDS/Aurora Metrics

| Metric Name | Description | Dimensions | Threshold |
|-------------|-------------|------------|-----------|
| `DBClusterIdentifier` | Cluster identifier | `DBClusterIdentifier` | N/A |
| `CPUUtilization` | Percentage of CPU utilization | `DBClusterIdentifier` | > 80% |
| `FreeableMemory` | Amount of available RAM | `DBClusterIdentifier` | < 2GB |
| `DatabaseConnections` | Number of client connections | `DBClusterIdentifier` | > 100 |
| `NetworkThroughput` | Network traffic to/from the instance | `DBClusterIdentifier` | N/A (tracking) |

## CloudWatch Logs

The pipeline uses structured logging to capture detailed information about execution:

### Log Groups

- `/aws/lambda/aurora-restore-snapshot-check`
- `/aws/lambda/aurora-restore-copy-snapshot`
- `/aws/lambda/aurora-restore-check-copy-status`
- `/aws/lambda/aurora-restore-restore-snapshot`
- `/aws/lambda/aurora-restore-check-restore-status`
- `/aws/lambda/aurora-restore-setup-db-users`
- `/aws/lambda/aurora-restore-delete-rds`
- `/aws/lambda/aurora-restore-check-delete-status`
- `/aws/lambda/aurora-restore-archive-snapshot`
- `/aws/lambda/aurora-restore-sns-notification`
- `/aws/states/aurora-restore-state-machine`

### Log Format

The pipeline uses a standard JSON log format for easier querying and analysis:

```json
{
  "timestamp": "2023-05-15T12:34:56.789Z",
  "level": "INFO",
  "operation_id": "restore-20230515-123456",
  "function_name": "aurora-restore-copy-snapshot",
  "message": "Starting snapshot copy operation",
  "source_snapshot_id": "rds:database-1-snapshot-20230515",
  "target_snapshot_name": "copy-database-1-snapshot-20230515",
  "duration_ms": 120,
  "aws_request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

## Metrics Collection Implementation

Metrics are captured using the CloudWatch PutMetricData API. The implementation is in the `utils/metrics.py` file:

```python
def put_metric(
    metric_name: str,
    value: float,
    dimensions: dict = None,
    namespace: str = "AuroraRestore"
) -> None:
    """Put a metric to CloudWatch."""
    try:
        cw_client = boto3.client('cloudwatch')
        
        metric_data = {
            'MetricName': metric_name,
            'Value': value,
            'Unit': 'None',
            'Dimensions': [
                {'Name': name, 'Value': str(value)}
                for name, value in (dimensions or {}).items()
            ]
        }
        
        cw_client.put_metric_data(
            Namespace=namespace,
            MetricData=[metric_data]
        )
    except Exception as e:
        # Log but don't fail on metrics errors
        logger.warning(f"Failed to publish metric {metric_name}: {str(e)}")
```

## CloudWatch Dashboard

A pre-configured CloudWatch dashboard provides visibility into the pipeline's operations:

```
AuroraRestorePipelineDashboard
├── Pipeline Execution Status
│   ├── Success Rate (%) 
│   ├── Average Duration (minutes)
│   ├── Execution Count by Status
│   └── Error Count by Type
├── Lambda Function Metrics
│   ├── Duration by Function (p50, p90, p99)
│   ├── Error Count by Function
│   ├── Throttles by Function
│   └── Memory Utilization by Function
├── Step Function Metrics
│   ├── Execution Timeline
│   ├── State Transitions
│   ├── Execution Status Count
│   └── Average Execution Duration
└── RDS Metrics
    ├── CPU Utilization
    ├── Free Memory
    ├── Database Connections
    └── Storage Utilization
```

## CloudWatch Alarms

The following alarms are implemented to monitor pipeline health:

### Critical Alarms

| Alarm Name | Description | Threshold | Period | Actions |
|------------|-------------|-----------|--------|---------|
| `AuroraRestorePipelineFailure` | Step Function execution failure | ≥ 1 | 1 minute | SNS notification, PagerDuty |
| `AuroraRestoreLongRunning` | Step Function execution taking too long | > 8 hours | 8 hours | SNS notification |
| `AuroraRestoreDynamoDBAccessFailure` | Lambda functions unable to access DynamoDB | ≥ 3 | 5 minutes | SNS notification, PagerDuty |

### Warning Alarms

| Alarm Name | Description | Threshold | Period | Actions |
|------------|-------------|-----------|--------|---------|
| `AuroraRestoreLambdaThrottling` | Lambda functions being throttled | ≥ 2 | 5 minutes | SNS notification |
| `AuroraRestoreLambdaErrors` | Lambda functions encountering errors | ≥ 3 | 5 minutes | SNS notification |
| `AuroraRestoreRDSHighCPU` | RDS instance CPU too high | > 85% | 15 minutes | SNS notification |

## DynamoDB Audit Trail

The pipeline maintains a comprehensive audit trail in the `AuroraRestoreAudit` DynamoDB table:

### Table Structure

| Attribute | Type | Description |
|-----------|------|-------------|
| `operation_id` | String | Unique identifier for the restore operation (HASH) |
| `timestamp` | String | ISO 8601 timestamp of the event (RANGE) |
| `event_type` | String | Type of event (e.g., "START", "COMPLETE", "ERROR") |
| `function_name` | String | Lambda function that generated the event |
| `details` | Map | Additional context about the event |
| `status` | String | Status of the operation at this point |

### Sample Query Patterns

```python
# Get all events for a specific operation
def get_operation_audit_trail(operation_id):
    response = dynamodb.query(
        TableName='AuroraRestoreAudit',
        KeyConditionExpression='operation_id = :opId',
        ExpressionAttributeValues={':opId': {'S': operation_id}},
        ScanIndexForward=True  # Ascending order by timestamp
    )
    return response['Items']

# Get error events across all operations in a time range
def get_error_events(start_time, end_time):
    response = dynamodb.scan(
        TableName='AuroraRestoreAudit',
        FilterExpression='event_type = :errorType AND #ts BETWEEN :start AND :end',
        ExpressionAttributeNames={'#ts': 'timestamp'},
        ExpressionAttributeValues={
            ':errorType': {'S': 'ERROR'},
            ':start': {'S': start_time},
            ':end': {'S': end_time}
        }
    )
    return response['Items']
```

## Monitoring Setup

To enable the monitoring components, follow these steps:

1. **Enable CloudWatch Metrics**:
   ```bash
   aws cloudwatch put-metric-alarm \
     --alarm-name AuroraRestorePipelineFailure \
     --alarm-description "Alert on pipeline execution failures" \
     --metric-name ExecutionsFailed \
     --namespace AWS/States \
     --statistic Sum \
     --period 60 \
     --threshold 1 \
     --comparison-operator GreaterThanOrEqualToThreshold \
     --dimensions Name=StateMachineArn,Value=arn:aws:states:$REGION:$ACCOUNT_ID:stateMachine:aurora-restore-state-machine \
     --evaluation-periods 1 \
     --alarm-actions arn:aws:sns:$REGION:$ACCOUNT_ID:aurora-restore-alerts
   ```

2. **Create Dashboard**:
   ```bash
   aws cloudwatch put-dashboard \
     --dashboard-name AuroraRestorePipelineDashboard \
     --dashboard-body file://monitoring/dashboard.json
   ```

3. **Configure Log Retention**:
   ```bash
   aws logs put-retention-policy \
     --log-group-name /aws/lambda/aurora-restore-snapshot-check \
     --retention-in-days 30
   ```

## Troubleshooting Guide

To troubleshoot issues with the Aurora Restore Pipeline:

1. **Check Step Function Execution**:
   - Navigate to AWS Step Functions console
   - Select the `aurora-restore-state-machine`
   - Find the execution by ID or status and inspect the visual workflow

2. **Review Lambda Logs**:
   - Check CloudWatch Logs for the relevant Lambda function
   - Filter by `operation_id` to track a specific restore operation
   - Look for ERROR level logs indicating failure points

3. **Examine DynamoDB Audit Trail**:
   - Query the `AuroraRestoreAudit` table for the `operation_id`
   - Review the sequence of events to identify where the issue occurred

4. **Verify RDS Status**:
   - Check the RDS console for cluster status
   - Verify snapshot availability and status
   - Check for quota limits or throttling events

5. **Network Connectivity Issues**:
   - Ensure Lambda functions in VPC have proper subnet and security group configuration
   - Verify that VPC endpoints are configured correctly for AWS services
   - Check that security groups allow necessary traffic between components

## Best Practices

1. **Set Appropriate Retention Periods**:
   - Configure log retention based on operational and compliance requirements
   - Consider costs of long-term log storage

2. **Use Metric Filters**:
   - Create metric filters on log groups to extract additional metrics
   - Alert on critical errors or patterns indicating issues

3. **Tag Resources**:
   - Apply consistent tagging to all resources for cost allocation
   - Use tags to filter resources in the console for easier management

4. **Implement Log Insights Queries**:
   - Create saved queries for common troubleshooting scenarios
   - Share queries with the operations team

5. **Regular Log Analysis**:
   - Periodically review logs for patterns or trends
   - Use insights to improve pipeline reliability and performance

## Next Steps

For more detailed information about monitoring specific components, refer to:
- [Troubleshooting Guide](../troubleshooting/01_common_issues.md)
- [Implementation Guide](../implementation_guide/04_monitoring_setup.md) 