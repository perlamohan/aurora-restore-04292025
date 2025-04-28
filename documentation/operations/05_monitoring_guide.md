# Aurora Restore Pipeline: Monitoring Guide

This document provides guidance on setting up comprehensive monitoring for the Aurora Restore Pipeline to ensure its optimal performance, detect issues early, and facilitate troubleshooting.

## Key Metrics to Monitor

### Lambda Function Metrics

| Metric | Description | Recommended Threshold | Action |
|--------|-------------|----------------------|--------|
| `Errors` | Count of execution errors | >0 for critical functions | Investigate logs |
| `Throttles` | Number of throttled executions | >0 | Increase concurrency limit |
| `Duration` | Execution time | >75% of timeout | Optimize code or increase timeout |
| `Invocations` | Number of function invocations | Significant deviation from baseline | Investigate unusual activity |
| `ConcurrentExecutions` | Number of functions executing simultaneously | >80% of account limit | Request limit increase |
| `IteratorAge` | Age of the last record processed (for event sources) | >1 hour | Check stream processing |

### Step Functions Metrics

| Metric | Description | Recommended Threshold | Action |
|--------|-------------|----------------------|--------|
| `ExecutionsFailed` | Count of failed state machine executions | >0 | Investigate execution history |
| `ExecutionsTimedOut` | Count of timed-out executions | >0 | Review state transition timeouts |
| `ExecutionThrottled` | Count of throttled executions | >0 | Review API call limits |
| `ExecutionTime` | Time to complete execution | >expected duration | Identify slow steps |

### DynamoDB Metrics

| Metric | Description | Recommended Threshold | Action |
|--------|-------------|----------------------|--------|
| `ReadThrottleEvents` | Count of throttled read events | >0 | Increase read capacity |
| `WriteThrottleEvents` | Count of throttled write events | >0 | Increase write capacity |
| `ConsumedReadCapacityUnits` | RCUs consumed | >80% of provisioned | Increase capacity |
| `ConsumedWriteCapacityUnits` | WCUs consumed | >80% of provisioned | Increase capacity |
| `SystemErrors` | Count of 5xx errors from DynamoDB | >0 | Check AWS service health |

### RDS/Aurora Metrics

| Metric | Description | Recommended Threshold | Action |
|--------|-------------|----------------------|--------|
| `CPUUtilization` | Percentage of CPU utilization | >80% | Increase instance size |
| `FreeableMemory` | Available memory | <20% of total | Increase memory |
| `DatabaseConnections` | Number of connections | >80% of max | Check for connection leaks |
| `ReadIOPS`/`WriteIOPS` | I/O operations per second | Sustained high values | Optimize queries or increase IOPS |
| `VolumeBytesUsed` | Storage space used | >80% of allocated | Increase storage |

### Custom Metrics

| Metric | Description | Recommended Threshold | Action |
|--------|-------------|----------------------|--------|
| `RestoreOperationCount` | Number of restore operations started | N/A (tracking metric) | N/A |
| `RestoreOperationDuration` | Time to complete a restore operation | >expected duration | Investigate slow steps |
| `RestoreOperationSuccess` | Count of successful restore operations | <100% success rate | Investigate failures |
| `RestoreOperationFailure` | Count of failed restore operations | >0 | Investigate failures by error type |
| `SnapshotCopyDuration` | Time to copy a snapshot | >expected duration | Check network/region issues |

## Setting Up CloudWatch Dashboards

### Main Dashboard Creation

Create a comprehensive dashboard for the Aurora Restore Pipeline:

```bash
aws cloudwatch put-dashboard \
  --dashboard-name AuroraRestorePipeline \
  --dashboard-body file://cloudwatch/dashboard-definitions/main-dashboard.json
```

### Dashboard Sections

Structure your dashboard with these sections:

1. **Overview**
   - Key health indicators
   - Operation counts by status
   - Success/failure rates

2. **Lambda Functions**
   - Error counts
   - Duration metrics
   - Throttle events

3. **Step Functions**
   - Execution counts
   - Duration metrics
   - Failure counts

4. **Database Metrics**
   - Snapshot copy status
   - RDS cluster metrics
   - Database user setup status

5. **DynamoDB Metrics**
   - Throughput consumption
   - Throttling events
   - Error counts

### Sample Dashboard JSON

```json
{
  "widgets": [
    {
      "type": "metric",
      "x": 0,
      "y": 0,
      "width": 12,
      "height": 6,
      "properties": {
        "metrics": [
          [ "AWS/Lambda", "Errors", "FunctionName", "aurora-restore-snapshot-check" ],
          [ "...", "aurora-restore-copy-snapshot" ],
          [ "...", "aurora-restore-restore-snapshot" ],
          [ "...", "aurora-restore-setup-db-users" ],
          [ "...", "aurora-restore-archive-snapshot" ]
        ],
        "view": "timeSeries",
        "stacked": false,
        "region": "us-east-1",
        "period": 300,
        "title": "Lambda Errors"
      }
    },
    {
      "type": "metric",
      "x": 12,
      "y": 0,
      "width": 12,
      "height": 6,
      "properties": {
        "metrics": [
          [ "AWS/Lambda", "Duration", "FunctionName", "aurora-restore-snapshot-check", { "stat": "Average" } ],
          [ "...", "aurora-restore-copy-snapshot", { "stat": "Average" } ],
          [ "...", "aurora-restore-restore-snapshot", { "stat": "Average" } ],
          [ "...", "aurora-restore-setup-db-users", { "stat": "Average" } ],
          [ "...", "aurora-restore-archive-snapshot", { "stat": "Average" } ]
        ],
        "view": "timeSeries",
        "stacked": false,
        "region": "us-east-1",
        "period": 300,
        "title": "Lambda Duration"
      }
    }
    // Additional widgets would be defined here
  ]
}
```

## CloudWatch Alarms

### Critical Alarms

Set up these critical alarms to notify when the pipeline experiences issues:

```bash
# Lambda error alarm
aws cloudwatch put-metric-alarm \
  --alarm-name AuroraRestore-LambdaErrors \
  --alarm-description "Alarm for Lambda errors in Aurora Restore Pipeline" \
  --metric-name Errors \
  --namespace AWS/Lambda \
  --statistic Sum \
  --dimensions Name=FunctionName,Value=aurora-restore-snapshot-check \
  --period 300 \
  --evaluation-periods 1 \
  --threshold 1 \
  --comparison-operator GreaterThanOrEqualToThreshold \
  --alarm-actions arn:aws:sns:region:account-id:AuroraRestore-Alerts

# Step Functions failure alarm
aws cloudwatch put-metric-alarm \
  --alarm-name AuroraRestore-StateMachineFailures \
  --alarm-description "Alarm for Step Functions failures in Aurora Restore Pipeline" \
  --metric-name ExecutionsFailed \
  --namespace AWS/States \
  --statistic Sum \
  --dimensions Name=StateMachineArn,Value=arn:aws:states:region:account-id:stateMachine:AuroraRestorePipeline \
  --period 300 \
  --evaluation-periods 1 \
  --threshold 1 \
  --comparison-operator GreaterThanOrEqualToThreshold \
  --alarm-actions arn:aws:sns:region:account-id:AuroraRestore-Alerts

# DynamoDB throttling alarm
aws cloudwatch put-metric-alarm \
  --alarm-name AuroraRestore-DynamoDBThrottles \
  --alarm-description "Alarm for DynamoDB throttles in Aurora Restore Pipeline" \
  --metric-name WriteThrottleEvents \
  --namespace AWS/DynamoDB \
  --statistic Sum \
  --dimensions Name=TableName,Value=AuroraRestoreStateTable \
  --period 300 \
  --evaluation-periods 1 \
  --threshold 1 \
  --comparison-operator GreaterThanOrEqualToThreshold \
  --alarm-actions arn:aws:sns:region:account-id:AuroraRestore-Alerts
```

### Performance Alarms

```bash
# Lambda duration alarm
aws cloudwatch put-metric-alarm \
  --alarm-name AuroraRestore-LambdaDuration \
  --alarm-description "Alarm for high Lambda duration in Aurora Restore Pipeline" \
  --metric-name Duration \
  --namespace AWS/Lambda \
  --statistic Average \
  --dimensions Name=FunctionName,Value=aurora-restore-copy-snapshot \
  --period 300 \
  --evaluation-periods 3 \
  --threshold 10000 \
  --comparison-operator GreaterThanOrEqualToThreshold \
  --alarm-actions arn:aws:sns:region:account-id:AuroraRestore-Alerts

# Step Functions execution time alarm
aws cloudwatch put-metric-alarm \
  --alarm-name AuroraRestore-StateMachineDuration \
  --alarm-description "Alarm for high Step Functions execution time" \
  --metric-name ExecutionTime \
  --namespace AWS/States \
  --statistic Average \
  --dimensions Name=StateMachineArn,Value=arn:aws:states:region:account-id:stateMachine:AuroraRestorePipeline \
  --period 300 \
  --evaluation-periods 1 \
  --threshold 900000 \
  --comparison-operator GreaterThanOrEqualToThreshold \
  --alarm-actions arn:aws:sns:region:account-id:AuroraRestore-Alerts
```

### Composite Alarms

Create composite alarms that trigger based on multiple conditions:

```bash
aws cloudwatch put-composite-alarm \
  --alarm-name AuroraRestore-CriticalFailure \
  --alarm-description "Critical failure in Aurora Restore Pipeline" \
  --alarm-rule "(ALARM(AuroraRestore-LambdaErrors) OR ALARM(AuroraRestore-StateMachineFailures)) AND ALARM(AuroraRestore-DynamoDBThrottles)" \
  --alarm-actions arn:aws:sns:region:account-id:AuroraRestore-Critical-Alerts
```

## Log Monitoring

### CloudWatch Logs Insights Queries

Save these queries for rapid troubleshooting:

#### Failed Lambda Executions
```
filter @type = "REPORT"
| sort @timestamp desc
| limit 20
```

#### Error Tracking
```
filter @message like "ERROR" or @message like "Exception"
| parse @message "ERROR: * " as errorMessage
| stats count(*) as errorCount by errorMessage
| sort errorCount desc
```

#### Long-Running Operations
```
filter @type = "REPORT"
| stats avg(duration) as avgDuration, max(duration) as maxDuration by @function
| sort maxDuration desc
```

#### State Transitions
```
filter @message like "State transition"
| parse @message "State transition: * -> *" as oldState, newState
| stats count(*) as transitionCount by oldState, newState
| sort transitionCount desc
```

### Log Metric Filters

Create metric filters to generate metrics from log entries:

```bash
# Error count metric filter
aws logs put-metric-filter \
  --log-group-name /aws/lambda/aurora-restore-snapshot-check \
  --filter-name ErrorCount \
  --filter-pattern "ERROR" \
  --metric-transformations \
    metricName=ErrorCount,metricNamespace=AuroraRestore,metricValue=1

# Duration metric filter for custom operations
aws logs put-metric-filter \
  --log-group-name /aws/lambda/aurora-restore-copy-snapshot \
  --filter-name CopyDuration \
  --filter-pattern "{ $.operation = \"copy_snapshot\" && $.duration_ms > 0 }" \
  --metric-transformations \
    metricName=CopySnapshotDuration,metricNamespace=AuroraRestore,metricValue=$.duration_ms
```

## Subscription Filters

Send specific log events to external tools for analysis:

```bash
# Send critical errors to a Lambda for processing
aws logs put-subscription-filter \
  --log-group-name /aws/lambda/aurora-restore-restore-snapshot \
  --filter-name CriticalErrors \
  --filter-pattern "ERROR" \
  --destination-arn arn:aws:lambda:region:account-id:function:log-processor \
  --role-arn arn:aws:iam::account-id:role/CWLtoLambdaRole
```

## X-Ray Tracing

Enable X-Ray tracing for detailed request analysis:

### Enable X-Ray for Lambda Functions

Update the Lambda function configuration:

```bash
aws lambda update-function-configuration \
  --function-name aurora-restore-snapshot-check \
  --tracing-config Mode=Active
```

### Enable X-Ray for Step Functions

Enable X-Ray in the CloudFormation template:

```yaml
AuroraRestoreStateMachine:
  Type: AWS::StepFunctions::StateMachine
  Properties:
    TracingConfiguration:
      Enabled: true
```

### X-Ray Sampling Rules

Create a custom sampling rule to ensure important operations are traced:

```bash
aws xray create-sampling-rule \
  --sampling-rule '{
    "RuleName": "AuroraRestore",
    "Priority": 10,
    "FixedRate": 1.0,
    "ReservoirSize": 100,
    "ServiceName": "aurora-restore*",
    "ServiceType": "*",
    "Host": "*",
    "HTTPMethod": "*",
    "URLPath": "*",
    "Version": 1
  }'
```

## Custom Metrics

Implement custom metrics in Lambda functions to track business-level operations:

```python
import time
from aws_lambda_powertools import Metrics

metrics = Metrics(namespace="AuroraRestore")

@metrics.log_metrics
def lambda_handler(event, context):
    start_time = time.time()
    
    # Add dimensions for this specific operation
    metrics.add_dimension(name="OperationType", value="SnapshotCheck")
    metrics.add_dimension(name="Environment", value="Production")
    
    # Your function code here
    success = process_event(event)
    
    # Record custom metrics
    duration = (time.time() - start_time) * 1000
    metrics.add_metric(name="OperationDuration", unit="Milliseconds", value=duration)
    
    if success:
        metrics.add_metric(name="SuccessCount", unit="Count", value=1)
    else:
        metrics.add_metric(name="FailureCount", unit="Count", value=1)
    
    return result
```

## Business Metrics Dashboard

Create a business-level dashboard focusing on restore operations:

```bash
aws cloudwatch put-dashboard \
  --dashboard-name AuroraRestoreBusinessMetrics \
  --dashboard-body file://cloudwatch/dashboard-definitions/business-metrics.json
```

### Sample Business Dashboard JSON

```json
{
  "widgets": [
    {
      "type": "metric",
      "x": 0,
      "y": 0,
      "width": 24,
      "height": 6,
      "properties": {
        "metrics": [
          [ "AuroraRestore", "RestoreOperationCount", { "stat": "Sum", "period": 86400 } ]
        ],
        "view": "timeSeries",
        "stacked": false,
        "region": "us-east-1",
        "title": "Daily Restore Operations"
      }
    },
    {
      "type": "metric",
      "x": 0,
      "y": 6,
      "width": 12,
      "height": 6,
      "properties": {
        "metrics": [
          [ "AuroraRestore", "RestoreOperationSuccess", { "stat": "Sum", "period": 86400 } ],
          [ "AuroraRestore", "RestoreOperationFailure", { "stat": "Sum", "period": 86400 } ]
        ],
        "view": "timeSeries",
        "stacked": true,
        "region": "us-east-1",
        "title": "Restore Success vs Failure"
      }
    },
    {
      "type": "metric",
      "x": 12,
      "y": 6,
      "width": 12,
      "height": 6,
      "properties": {
        "metrics": [
          [ "AuroraRestore", "RestoreOperationDuration", { "stat": "Average", "period": 86400 } ],
          [ "...", { "stat": "p90", "period": 86400 } ],
          [ "...", { "stat": "p99", "period": 86400 } ]
        ],
        "view": "timeSeries",
        "stacked": false,
        "region": "us-east-1",
        "title": "Restore Operation Duration"
      }
    }
  ]
}
```

## Monitoring Integration with Alerting

### SNS Topic Setup

Create an SNS topic for alerts:

```bash
aws sns create-topic --name AuroraRestore-Alerts

# Add email subscription
aws sns subscribe \
  --topic-arn arn:aws:sns:region:account-id:AuroraRestore-Alerts \
  --protocol email \
  --notification-endpoint team-email@example.com
```

### Integration with Incident Management Systems

For PagerDuty or OpsGenie integration:

```bash
# PagerDuty integration
aws sns subscribe \
  --topic-arn arn:aws:sns:region:account-id:AuroraRestore-Alerts \
  --protocol https \
  --notification-endpoint https://events.pagerduty.com/integration/12345/enqueue \
  --attributes '{"DeliveryPolicy": "{\"healthyRetryPolicy\":{\"numRetries\":5}}"}'
```

## Cost Monitoring

### Setting Up Cost Anomaly Detection

```bash
# Create cost anomaly monitor
aws ce create-anomaly-monitor \
  --anomaly-monitor '{
    "MonitorName": "AuroraRestoreCostMonitor",
    "MonitorType": "DIMENSIONAL",
    "MonitorSpecification": "{\"Dimensions\":{\"Key\":\"SERVICE\",\"Values\":[\"Lambda\",\"RDS\",\"DynamoDB\",\"Step Functions\"]}}"
  }'

# Create anomaly subscription
aws ce create-anomaly-subscription \
  --anomaly-subscription '{
    "SubscriptionName": "AuroraRestoreCostAlerts",
    "Threshold": 10.0,
    "Frequency": "DAILY",
    "MonitorArnList": ["arn:aws:ce::account-id:anomalymonitor/monitor-id"],
    "Subscribers": [{
      "Type": "SNS",
      "Address": "arn:aws:sns:region:account-id:AuroraRestore-Alerts"
    }]
  }'
```

### Cost Allocation Tags

Enable cost allocation tags to track expenses:

```bash
aws ce update-cost-allocation-tags-status \
  --cost-allocation-tags-status '[
    {
      "TagKey": "Application",
      "Status": "Active"
    },
    {
      "TagKey": "Environment",
      "Status": "Active"
    }
  ]'
```

## Operational Readiness Monitoring

### Health Check Lambda

Implement a health check Lambda function that tests the entire pipeline:

```python
def lambda_handler(event, context):
    """
    Performs a health check on the Aurora Restore Pipeline components.
    """
    health_status = {
        "overallStatus": "HEALTHY",
        "components": []
    }
    
    # Check DynamoDB
    dynamo_status = check_dynamodb_status()
    health_status["components"].append(dynamo_status)
    
    # Check Step Functions
    stepfunctions_status = check_stepfunctions_status()
    health_status["components"].append(stepfunctions_status)
    
    # Check Lambda functions
    lambda_status = check_lambda_functions()
    health_status["components"].append(lambda_status)
    
    # Check RDS/Aurora access
    rds_status = check_rds_access()
    health_status["components"].append(rds_status)
    
    # Determine overall health
    for component in health_status["components"]:
        if component["status"] == "UNHEALTHY":
            health_status["overallStatus"] = "UNHEALTHY"
            break
    
    # Publish health status to CloudWatch
    publish_health_metrics(health_status)
    
    return health_status
```

Schedule this function to run regularly:

```bash
aws events put-rule \
  --name AuroraRestoreHealthCheck \
  --schedule-expression "rate(5 minutes)"

aws events put-targets \
  --rule AuroraRestoreHealthCheck \
  --targets '[{"Id": "1", "Arn": "arn:aws:lambda:region:account-id:function:aurora-restore-health-check"}]'
```

## Monitoring Best Practices

1. **Establish Baselines**
   - Collect data for at least two weeks to establish normal patterns
   - Document expected metrics ranges for all components
   - Update baselines after significant changes

2. **Implement Multi-level Alerting**
   - Warning level: Potential issues that need attention but not immediate
   - Critical level: Issues requiring immediate action
   - Use different notification channels based on severity

3. **Correlate Metrics and Logs**
   - When investigating issues, correlate metrics with log entries
   - Use X-Ray traces to connect activities across services
   - Create dashboards that show related metrics together

4. **Regular Monitoring Reviews**
   - Schedule monthly reviews of monitoring setup
   - Adjust thresholds based on observed patterns
   - Add new metrics as system evolves
   - Remove metrics that don't provide value

5. **Document Monitoring Setup**
   - Maintain documentation of all alarms and their thresholds
   - Document expected metric patterns
   - Create runbooks for responding to specific alarms

## Advanced Monitoring Techniques

### Synthetic Testing

Implement a test Lambda that initiates a test restore operation:

```python
def lambda_handler(event, context):
    """
    Initiates a test restore to verify the pipeline is working.
    Only runs in test environment.
    """
    # Generate a unique test operation ID
    operation_id = f"test-{int(time.time())}"
    
    # Parameters for test restore
    test_parameters = {
        "operation_id": operation_id,
        "source_snapshot_identifier": "test-snapshot",
        "source_region": "us-east-1",
        "target_region": "us-east-1",
        "new_db_cluster_identifier": f"test-restore-{operation_id}",
        "db_instance_class": "db.r5.large",
        "test_mode": True  # Flag to indicate this is a test
    }
    
    # Start the Step Functions execution
    step_functions_client = boto3.client('stepfunctions')
    response = step_functions_client.start_execution(
        stateMachineArn='arn:aws:states:region:account-id:stateMachine:AuroraRestorePipeline',
        name=f"TestExecution-{operation_id}",
        input=json.dumps(test_parameters)
    )
    
    return {
        "status": "Test initiated",
        "executionArn": response["executionArn"],
        "operation_id": operation_id
    }
```

### Anomaly Detection

Use CloudWatch Anomaly Detection to identify unusual patterns:

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name AuroraRestore-AnomalyDetection \
  --alarm-description "Detects unusual patterns in restore operation duration" \
  --metric-name RestoreOperationDuration \
  --namespace AuroraRestore \
  --statistic Average \
  --period 3600 \
  --evaluation-periods 1 \
  --threshold-metric-id ad1 \
  --comparison-operator GreaterThanUpperThreshold \
  --alarm-actions arn:aws:sns:region:account-id:AuroraRestore-Alerts \
  --threshold-metric-id "ad1" \
  --anomaly-detection-threshold 2
```

## Next Steps

For additional information on monitoring:

1. Review the [Best Practices Guide](./03_best_practices.md) for operation optimization
2. Consult the [Maintenance Guide](./04_maintenance_guide.md) for ongoing maintenance
3. Reference the [Troubleshooting Guide](../troubleshooting/01_debugging_guide.md) for addressing issues identified by monitoring 