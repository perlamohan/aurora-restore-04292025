# Aurora Restore Pipeline: Batch Operations Guide

This guide provides instructions and best practices for running batch operations with the Aurora Restore Pipeline, enabling you to efficiently manage multiple database restores concurrently or in sequence.

## Batch Restore Use Cases

Common scenarios for batch restore operations include:

- **Test data refreshes**: Regularly refreshing multiple test/dev environments
- **Disaster recovery testing**: Validating restore procedures across multiple databases
- **Data analytics**: Creating point-in-time copies of production databases for analysis
- **Multi-environment deployments**: Synchronizing databases across development tiers
- **Database fleet management**: Managing consistent database states across services

## Batch Operation Strategies

### Concurrent Execution

Running multiple restore operations simultaneously:

```bash
# Example script to launch 3 concurrent restore operations
for db in "customer-db" "product-db" "order-db"; do
  aws stepfunctions start-execution \
    --state-machine-arn arn:aws:states:us-east-1:123456789012:stateMachine:AuroraRestorePipeline \
    --input "{\"cluster_name\": \"${db}\", \"snapshot_date\": \"2023-10-15\", \"target_region\": \"us-east-1\"}"
done
```

#### Considerations for Concurrent Execution

- **Resource Limits**: Monitor AWS service quotas, particularly:
  - Lambda concurrent executions (default: 1,000 per region)
  - API rate limits for RDS operations
  - DynamoDB read/write capacity

- **Throttling Management**: Implement exponential backoff for AWS API calls:

  ```python
  # Example of retry logic with exponential backoff
  def aws_api_call_with_backoff(func, max_retries=5, **kwargs):
      retries = 0
      while retries < max_retries:
          try:
              return func(**kwargs)
          except ClientError as e:
              if e.response['Error']['Code'] in ['Throttling', 'ThrottlingException']:
                  wait_time = min(2 ** retries, 60)  # Cap at 60 seconds
                  time.sleep(wait_time)
                  retries += 1
              else:
                  raise
      raise Exception(f"Maximum retries ({max_retries}) exceeded")
  ```

### Sequential Batch Processing

Running restores in a controlled sequence:

```bash
#!/bin/bash
# Sequential batch restore script

DATABASES=("customer-db" "product-db" "order-db")
SNAPSHOT_DATE="2023-10-15"
TARGET_REGION="us-east-1"

for db in "${DATABASES[@]}"; do
  echo "Starting restore for ${db}..."
  
  # Start execution
  EXECUTION_ARN=$(aws stepfunctions start-execution \
    --state-machine-arn arn:aws:states:us-east-1:123456789012:stateMachine:AuroraRestorePipeline \
    --input "{\"cluster_name\": \"${db}\", \"snapshot_date\": \"${SNAPSHOT_DATE}\", \"target_region\": \"${TARGET_REGION}\"}" \
    --query executionArn --output text)
  
  echo "Execution ARN: ${EXECUTION_ARN}"
  
  # Wait for completion
  while true; do
    STATUS=$(aws stepfunctions describe-execution \
      --execution-arn ${EXECUTION_ARN} \
      --query status --output text)
    
    echo "Status: ${STATUS}"
    
    if [[ "${STATUS}" == "SUCCEEDED" ]]; then
      echo "Restore complete for ${db}"
      break
    elif [[ "${STATUS}" == "FAILED" || "${STATUS}" == "TIMED_OUT" || "${STATUS}" == "ABORTED" ]]; then
      echo "Restore failed for ${db}"
      exit 1
    fi
    
    sleep 30
  done
done

echo "All database restores completed successfully"
```

## Efficient Batch Configuration

### Resource Allocation

Optimize resource allocation to avoid contention:

1. **Lambda Memory Allocation**:
   - Allocate more memory to critical functions involved in batch operations

2. **DynamoDB Capacity Planning**:
   - Pre-warm DynamoDB tables before large batch operations:
   
   ```bash
   # Increase capacity before batch operations
   aws dynamodb update-table \
     --table-name AuroraRestoreState \
     --provisioned-throughput ReadCapacityUnits=100,WriteCapacityUnits=100
   
   # Run batch operations...
   
   # Reset capacity after completion
   aws dynamodb update-table \
     --table-name AuroraRestoreState \
     --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5
   ```

### Batch Processing Template

Use CloudFormation to parameterize batch operations:

```yaml
AWSTemplateFormatVersion: '2010-09-09'
Description: 'Aurora Restore Pipeline - Batch Operations'

Parameters:
  DatabaseList:
    Type: CommaDelimitedList
    Description: List of database names to restore
    Default: "db1,db2,db3"
  
  SnapshotDate:
    Type: String
    Description: Date of snapshot to restore (YYYY-MM-DD)
    Default: "2023-10-15"
  
  TargetRegion:
    Type: String
    Description: Target AWS region
    Default: "us-east-1"
  
  ConcurrentExecutions:
    Type: Number
    Description: Maximum number of concurrent executions
    Default: 3
    MinValue: 1
    MaxValue: 10

Resources:
  BatchProcessorFunction:
    Type: AWS::Lambda::Function
    Properties:
      Runtime: python3.9
      Handler: index.handler
      Role: !GetAtt BatchProcessorRole.Arn
      Code:
        ZipFile: |
          import boto3
          import json
          import time
          import os
          from datetime import datetime
          
          def handler(event, context):
              step_functions = boto3.client('stepfunctions')
              state_machine_arn = os.environ['STATE_MACHINE_ARN']
              db_list = event['DatabaseList']
              snapshot_date = event['SnapshotDate']
              target_region = event['TargetRegion']
              concurrent_limit = int(event['ConcurrentExecutions'])
              
              active_executions = []
              results = []
              
              for db in db_list:
                  # Wait if we've reached concurrent limit
                  while len(active_executions) >= concurrent_limit:
                      # Check for completed executions
                      still_active = []
                      for exec_arn in active_executions:
                          status = step_functions.describe_execution(executionArn=exec_arn)['status']
                          if status in ['RUNNING', 'PENDING']:
                              still_active.append(exec_arn)
                          else:
                              results.append({'database': db, 'status': status})
                      
                      active_executions = still_active
                      if len(active_executions) >= concurrent_limit:
                          time.sleep(30)
                  
                  # Start new execution
                  execution = step_functions.start_execution(
                      stateMachineArn=state_machine_arn,
                      input=json.dumps({
                          'cluster_name': db, 
                          'snapshot_date': snapshot_date, 
                          'target_region': target_region
                      })
                  )
                  
                  active_executions.append(execution['executionArn'])
              
              # Wait for all remaining executions to complete
              while active_executions:
                  still_active = []
                  for exec_arn in active_executions:
                      status = step_functions.describe_execution(executionArn=exec_arn)['status']
                      if status in ['RUNNING', 'PENDING']:
                          still_active.append(exec_arn)
                      else:
                          results.append({'execution_arn': exec_arn, 'status': status})
                  
                  active_executions = still_active
                  if active_executions:
                      time.sleep(30)
              
              return {
                  'timestamp': datetime.utcnow().isoformat(),
                  'results': results
              }
      Environment:
        Variables:
          STATE_MACHINE_ARN: !Ref RestorePipelineStateMachine
      Timeout: 900  # 15 minutes
  
  BatchProcessorRole:
    Type: AWS::IAM::Role
    Properties:
      AssumeRolePolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Principal:
              Service: lambda.amazonaws.com
            Action: 'sts:AssumeRole'
      ManagedPolicyArns:
        - 'arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'
      Policies:
        - PolicyName: StepFunctionsAccess
          PolicyDocument:
            Version: '2012-10-17'
            Statement:
              - Effect: Allow
                Action:
                  - 'states:StartExecution'
                  - 'states:DescribeExecution'
                Resource: !Ref RestorePipelineStateMachine
  
  RestorePipelineStateMachine:
    Type: AWS::StepFunctions::StateMachine
    Properties:
      StateMachineType: STANDARD
      RoleArn: !GetAtt StateMachineRole.Arn
      DefinitionString: !Sub |
        {
          "Comment": "Aurora Restore Pipeline",
          "StartAt": "CheckSnapshot",
          "States": {
            "CheckSnapshot": {
              "Type": "Task",
              "Resource": "arn:aws:lambda:${AWS::Region}:${AWS::AccountId}:function:aurora-restore-snapshot-check",
              "Next": "CopySnapshot"
            },
            "CopySnapshot": {
              "Type": "Task",
              "Resource": "arn:aws:lambda:${AWS::Region}:${AWS::AccountId}:function:aurora-restore-copy-snapshot",
              "Next": "CheckCopyStatus"
            },
            "CheckCopyStatus": {
              "Type": "Task",
              "Resource": "arn:aws:lambda:${AWS::Region}:${AWS::AccountId}:function:aurora-restore-check-copy-status",
              "Next": "RestoreSnapshot"
            },
            "RestoreSnapshot": {
              "Type": "Task",
              "Resource": "arn:aws:lambda:${AWS::Region}:${AWS::AccountId}:function:aurora-restore-restore-snapshot",
              "Next": "CheckRestoreStatus"
            },
            "CheckRestoreStatus": {
              "Type": "Task",
              "Resource": "arn:aws:lambda:${AWS::Region}:${AWS::AccountId}:function:aurora-restore-check-restore-status",
              "Next": "SetupDbUsers"
            },
            "SetupDbUsers": {
              "Type": "Task",
              "Resource": "arn:aws:lambda:${AWS::Region}:${AWS::AccountId}:function:aurora-restore-setup-db-users",
              "Next": "SendNotification"
            },
            "SendNotification": {
              "Type": "Task",
              "Resource": "arn:aws:lambda:${AWS::Region}:${AWS::AccountId}:function:aurora-restore-sns-notification",
              "End": true
            }
          }
        }
  
  StateMachineRole:
    Type: AWS::IAM::Role
    Properties:
      AssumeRolePolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Principal:
              Service: states.amazonaws.com
            Action: 'sts:AssumeRole'
      ManagedPolicyArns:
        - 'arn:aws:iam::aws:policy/service-role/AWSLambdaRole'

Outputs:
  BatchProcessorFunction:
    Description: Lambda function for processing batch restores
    Value: !Ref BatchProcessorFunction
  
  StateMachineArn:
    Description: State machine ARN
    Value: !Ref RestorePipelineStateMachine
```

## Monitoring Batch Operations

### Batch Operation Dashboard

Create a CloudWatch dashboard specifically for monitoring batch operations:

```bash
aws cloudwatch put-dashboard \
  --dashboard-name AuroraRestoreBatchOperations \
  --dashboard-body file://batch-dashboard.json
```

Example `batch-dashboard.json`:

```json
{
  "widgets": [
    {
      "type": "metric",
      "width": 24,
      "height": 6,
      "properties": {
        "metrics": [
          [ "AuroraRestorePipeline", "BatchOperationCount", { "stat": "SampleCount" } ],
          [ ".", "BatchOperationSuccessCount", { "stat": "SampleCount" } ],
          [ ".", "BatchOperationFailureCount", { "stat": "SampleCount" } ]
        ],
        "view": "timeSeries",
        "stacked": false,
        "region": "us-east-1",
        "title": "Batch Operation Metrics",
        "period": 300
      }
    },
    {
      "type": "metric",
      "width": 12,
      "height": 6,
      "properties": {
        "metrics": [
          [ "AuroraRestorePipeline", "RestoreDuration", { "stat": "Average" } ],
          [ "...", { "stat": "Maximum" } ],
          [ "...", { "stat": "Minimum" } ]
        ],
        "view": "timeSeries",
        "stacked": false,
        "region": "us-east-1",
        "title": "Restore Duration",
        "period": 300
      }
    },
    {
      "type": "metric",
      "width": 12,
      "height": 6,
      "properties": {
        "metrics": [
          [ "AWS/Lambda", "ConcurrentExecutions", "FunctionName", "aurora-restore-copy-snapshot" ],
          [ "...", "aurora-restore-restore-snapshot" ],
          [ "...", "aurora-restore-check-copy-status" ],
          [ "...", "aurora-restore-check-restore-status" ]
        ],
        "view": "timeSeries",
        "stacked": false,
        "region": "us-east-1",
        "title": "Lambda Concurrency",
        "period": 60
      }
    }
  ]
}
```

### Batch Monitoring Script

Create a script to monitor the status of all active batch operations:

```python
#!/usr/bin/env python3

import boto3
import time
import argparse
from datetime import datetime, timedelta
from tabulate import tabulate

def parse_args():
    parser = argparse.ArgumentParser(description='Monitor Aurora Restore Batch Operations')
    parser.add_argument('--state-machine', required=True, 
                      help='ARN of the Step Functions state machine')
    parser.add_argument('--region', default='us-east-1',
                      help='AWS region')
    parser.add_argument('--refresh-interval', type=int, default=30,
                      help='Refresh interval in seconds')
    parser.add_argument('--hours', type=int, default=24,
                      help='Show executions from the past N hours')
    return parser.parse_args()

def main():
    args = parse_args()
    
    # Initialize clients
    sfn = boto3.client('stepfunctions', region_name=args.region)
    cloudwatch = boto3.client('cloudwatch', region_name=args.region)
    
    # Get state machine ARN
    state_machine_arn = args.state_machine
    
    try:
        while True:
            # Clear screen
            print("\033c", end="")
            
            # Get executions
            start_date = datetime.utcnow() - timedelta(hours=args.hours)
            
            executions = []
            next_token = None
            
            while True:
                if next_token:
                    response = sfn.list_executions(
                        stateMachineArn=state_machine_arn,
                        statusFilter='ALL',
                        maxResults=100,
                        nextToken=next_token
                    )
                else:
                    response = sfn.list_executions(
                        stateMachineArn=state_machine_arn,
                        statusFilter='ALL',
                        maxResults=100
                    )
                
                for execution in response['executions']:
                    if execution['startDate'] >= start_date:
                        # Get execution input
                        exec_details = sfn.describe_execution(
                            executionArn=execution['executionArn']
                        )
                        
                        input_data = exec_details.get('input', '{}')
                        try:
                            import json
                            input_json = json.loads(input_data)
                            cluster_name = input_json.get('cluster_name', 'N/A')
                        except:
                            cluster_name = 'Error parsing input'
                        
                        executions.append({
                            'database': cluster_name,
                            'status': execution['status'],
                            'start_time': execution['startDate'].strftime('%Y-%m-%d %H:%M:%S'),
                            'execution_arn': execution['executionArn'].split(':')[-1]
                        })
                
                next_token = response.get('nextToken')
                if not next_token:
                    break
            
            # Get metrics
            now = datetime.utcnow()
            response = cloudwatch.get_metric_statistics(
                Namespace='AuroraRestorePipeline',
                MetricName='RestoreDuration',
                Dimensions=[],
                StartTime=now - timedelta(hours=args.hours),
                EndTime=now,
                Period=3600,
                Statistics=['Average', 'Maximum', 'Minimum']
            )
            
            metrics = {}
            if response['Datapoints']:
                latest = max(response['Datapoints'], key=lambda x: x['Timestamp'])
                metrics['avg_duration'] = round(latest['Average'] / 60, 2)  # Convert to minutes
                metrics['max_duration'] = round(latest['Maximum'] / 60, 2)
                metrics['min_duration'] = round(latest['Minimum'] / 60, 2)
            
            # Display summary
            print(f"Aurora Restore Batch Operations - {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
            print(f"State Machine: {state_machine_arn}")
            print(f"Showing executions from the past {args.hours} hours\n")
            
            # Status counts
            status_counts = {}
            for execution in executions:
                status = execution['status']
                status_counts[status] = status_counts.get(status, 0) + 1
            
            print("Status Summary:")
            for status, count in status_counts.items():
                print(f"  {status}: {count}")
            
            # Display metrics if available
            if metrics:
                print("\nRestore Duration (minutes):")
                print(f"  Average: {metrics['avg_duration']}")
                print(f"  Maximum: {metrics['max_duration']}")
                print(f"  Minimum: {metrics['min_duration']}")
            
            # Display executions
            print("\nRecent Executions:")
            if executions:
                headers = ['Database', 'Status', 'Start Time', 'Execution ID']
                table_data = [[e['database'], e['status'], e['start_time'], e['execution_arn']] 
                             for e in sorted(executions, key=lambda x: x['start_time'], reverse=True)]
                print(tabulate(table_data, headers=headers, tablefmt='grid'))
            else:
                print("No executions found in the specified time range.")
            
            print(f"\nRefreshing in {args.refresh_interval} seconds (Ctrl+C to exit)...")
            time.sleep(args.refresh_interval)
            
    except KeyboardInterrupt:
        print("\nMonitoring stopped.")

if __name__ == "__main__":
    main()
```

Save as `monitor_batch_operations.py` and run with:

```bash
# Install dependencies
pip install boto3 tabulate

# Run the monitoring script
python monitor_batch_operations.py \
  --state-machine "arn:aws:states:us-east-1:123456789012:stateMachine:AuroraRestorePipeline" \
  --region us-east-1 \
  --refresh-interval 15 \
  --hours 48
```

## Batch Operation Best Practices

### Performance Optimization

1. **Stagger Start Times**:
   Space out restore operations to avoid resource contention:
   
   ```python
   import time
   
   # Stagger starts by 2 minutes
   for i, db in enumerate(database_list):
       # Start restore operation for db
       # ...
       
       # Wait 2 minutes before starting next restore
       if i < len(database_list) - 1:  # Don't wait after the last one
           time.sleep(120)
   ```

2. **Priority-Based Execution**:
   Prioritize critical database restores:
   
   ```python
   # Sort databases by priority
   database_list = [
       {"name": "customer-db", "priority": 1},  # Highest priority
       {"name": "product-db", "priority": 2},
       {"name": "analytics-db", "priority": 3}  # Lowest priority
   ]
   database_list.sort(key=lambda x: x["priority"])
   
   # Process in priority order
   for db in database_list:
       # Start restore operation for db["name"]
       # ...
   ```

### Failure Handling in Batch Operations

1. **Implement Retry Mechanism**:
   
   ```python
   def batch_restore_with_retry(databases, max_retries=3):
       results = []
       
       for db in databases:
           retries = 0
           success = False
           
           while retries < max_retries and not success:
               try:
                   # Start restore operation
                   execution_arn = start_restore(db)
                   
                   # Monitor execution until completion
                   status = monitor_execution(execution_arn)
                   
                   if status == "SUCCEEDED":
                       success = True
                       results.append({"database": db, "status": "SUCCESS"})
                   else:
                       retries += 1
               except Exception as e:
                   print(f"Error restoring {db}: {str(e)}")
                   retries += 1
           
           if not success:
               results.append({"database": db, "status": "FAILED"})
       
       return results
   ```

2. **Partial Batch Recovery**:
   Continue with remaining databases when some fail:
   
   ```python
   def process_batch(databases):
       successful = []
       failed = []
       
       for db in databases:
           try:
               # Start restore operation
               if restore_database(db):
                   successful.append(db)
               else:
                   failed.append(db)
           except Exception:
               failed.append(db)
       
       # Report results
       print(f"Successfully restored: {len(successful)}/{len(databases)}")
       if failed:
           print(f"Failed databases: {', '.join(failed)}")
           
       return successful, failed
   ```

## Scheduling Regular Batch Operations

### Creating a Scheduled Batch Job

Use EventBridge (CloudWatch Events) to schedule regular batch operations:

```yaml
AWSTemplateFormatVersion: '2010-09-09'
Description: 'Schedule for Aurora Restore Batch Operations'

Resources:
  BatchRestoreSchedule:
    Type: AWS::Events::Rule
    Properties:
      Description: "Scheduled batch restore of databases every Sunday at 2 AM"
      ScheduleExpression: "cron(0 2 ? * SUN *)"
      State: ENABLED
      Targets:
        - Arn: !GetAtt BatchTriggerFunction.Arn
          Id: "BatchTriggerFunction"
          Input: |
            {
              "DatabaseList": ["test-db-1", "test-db-2", "test-db-3"],
              "SnapshotDate": "latest",
              "TargetRegion": "us-east-1",
              "ConcurrentExecutions": 2
            }
  
  BatchTriggerFunction:
    Type: AWS::Lambda::Function
    Properties:
      Runtime: python3.9
      Handler: index.handler
      Role: !GetAtt BatchTriggerRole.Arn
      Code:
        ZipFile: |
          import boto3
          import json
          import os
          from datetime import datetime, timedelta
          
          def handler(event, context):
              # If snapshot_date is "latest", calculate yesterday's date
              if event.get('SnapshotDate') == 'latest':
                  yesterday = datetime.utcnow() - timedelta(days=1)
                  event['SnapshotDate'] = yesterday.strftime('%Y-%m-%d')
              
              # Invoke the batch processor Lambda
              lambda_client = boto3.client('lambda')
              response = lambda_client.invoke(
                  FunctionName=os.environ['BATCH_PROCESSOR_FUNCTION'],
                  InvocationType='Event',
                  Payload=json.dumps(event)
              )
              
              return {
                  'statusCode': 200,
                  'body': json.dumps({
                      'message': 'Batch restore initiated',
                      'timestamp': datetime.utcnow().isoformat(),
                      'input': event
                  })
              }
      Environment:
        Variables:
          BATCH_PROCESSOR_FUNCTION: !GetAtt BatchProcessorFunction.Arn
      Timeout: 30
  
  BatchTriggerRole:
    Type: AWS::IAM::Role
    Properties:
      AssumeRolePolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Principal:
              Service: lambda.amazonaws.com
            Action: 'sts:AssumeRole'
      ManagedPolicyArns:
        - 'arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'
      Policies:
        - PolicyName: InvokeBatchProcessor
          PolicyDocument:
            Version: '2012-10-17'
            Statement:
              - Effect: Allow
                Action: 'lambda:InvokeFunction'
                Resource: !GetAtt BatchProcessorFunction.Arn
  
  # Permission for EventBridge to invoke the Lambda
  BatchTriggerPermission:
    Type: AWS::Lambda::Permission
    Properties:
      Action: 'lambda:InvokeFunction'
      FunctionName: !Ref BatchTriggerFunction
      Principal: 'events.amazonaws.com'
      SourceArn: !GetAtt BatchRestoreSchedule.Arn
  
  # Reference to the Batch Processor Lambda from previous template
  BatchProcessorFunction:
    Type: AWS::Lambda::Function
    # Properties from the previous template

Outputs:
  ScheduleRuleArn:
    Description: ARN of the scheduled rule
    Value: !GetAtt BatchRestoreSchedule.Arn
```

## Conclusion

Batch operations with the Aurora Restore Pipeline can significantly improve efficiency when managing multiple database restores. By following the strategies in this guide, you can:

1. Run concurrent restores safely without exceeding AWS service limits
2. Schedule regular batch operations for routine maintenance
3. Monitor batch operations effectively with custom dashboards
4. Handle failures gracefully within batch processes
5. Optimize resource utilization during batch operations

For additional assistance with batch operations, see the following references:

- [AWS Step Functions Concurrency Control](https://docs.aws.amazon.com/step-functions/latest/dg/concepts-concurrency.html)
- [AWS Lambda Concurrency Limits](https://docs.aws.amazon.com/lambda/latest/dg/invocation-scaling.html)
- [DynamoDB Capacity Planning](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/HowItWorks.ReadWriteCapacityMode.html)
- [Amazon RDS Quotas](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_Limits.html) 