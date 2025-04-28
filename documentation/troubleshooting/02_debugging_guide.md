# Aurora Restore Pipeline Debugging Guide

This guide provides detailed debugging steps for the Aurora Restore Pipeline beyond the common issues documented in the [Common Issues and Solutions](./01_common_issues.md) document.

## Table of Contents

- [Debugging Tools](#debugging-tools)
- [Step Functions Debugging](#step-functions-debugging)
- [Lambda Function Debugging](#lambda-function-debugging)
- [Database Connection Debugging](#database-connection-debugging)
- [State Management Debugging](#state-management-debugging)
- [VPC Networking Debugging](#vpc-networking-debugging)
- [Permissions and Security Debugging](#permissions-and-security-debugging)
- [Advanced Troubleshooting](#advanced-troubleshooting)

## Debugging Tools

### CloudWatch Logs

CloudWatch Logs are the primary debugging tool for AWS Lambda functions. Each Lambda function in the Aurora Restore Pipeline has its own CloudWatch Log Group:

```bash
# List all log groups for the Aurora Restore Pipeline
aws logs describe-log-groups --log-group-name-prefix /aws/lambda/aurora-restore --region us-east-1

# View logs for a specific Lambda function
aws logs filter-log-events --log-group-name /aws/lambda/aurora-restore-snapshot-check --region us-east-1

# Search for errors in logs
aws logs filter-log-events --log-group-name /aws/lambda/aurora-restore-snapshot-check --filter-pattern "ERROR" --region us-east-1
```

### CloudWatch Metrics

CloudWatch Metrics provide insights into the performance of your Lambda functions and other AWS resources:

```bash
# List all metrics for Lambda functions
aws cloudwatch list-metrics --namespace AWS/Lambda --region us-east-1

# Get invocation metrics for a specific Lambda function
aws cloudwatch get-metric-statistics --namespace AWS/Lambda --metric-name Invocations --dimensions Name=FunctionName,Value=aurora-restore-snapshot-check --start-time 2023-01-01T00:00:00Z --end-time 2023-01-02T00:00:00Z --period 3600 --statistics Sum --region us-east-1

# Get error metrics for a specific Lambda function
aws cloudwatch get-metric-statistics --namespace AWS/Lambda --metric-name Errors --dimensions Name=FunctionName,Value=aurora-restore-snapshot-check --start-time 2023-01-01T00:00:00Z --end-time 2023-01-02T00:00:00Z --period 3600 --statistics Sum --region us-east-1
```

### AWS X-Ray

AWS X-Ray provides tracing information for distributed applications, including Lambda functions:

```bash
# Enable X-Ray tracing for a Lambda function
aws lambda update-function-configuration --function-name aurora-restore-snapshot-check --tracing-config Mode=Active --region us-east-1

# List X-Ray traces for a specific Lambda function
aws xray get-service-graph --start-time 2023-01-01T00:00:00Z --end-time 2023-01-02T00:00:00Z --region us-east-1
```

### DynamoDB Debugging

DynamoDB is used for state management in the Aurora Restore Pipeline:

```bash
# List items in the state table
aws dynamodb scan --table-name aurora-restore-state --region us-east-1

# Get a specific state item by operation ID
aws dynamodb get-item --table-name aurora-restore-state --key '{"operation_id":{"S":"op-12345678"}}' --region us-east-1

# List items in the audit table
aws dynamodb scan --table-name aurora-restore-audit --region us-east-1
```

## Step Functions Debugging

### Execution Debugging

Step Functions provide a visual representation of the state machine execution:

```bash
# List all Step Functions executions
aws stepfunctions list-executions --state-machine-arn arn:aws:states:us-east-1:123456789012:stateMachine:aurora-restore --region us-east-1

# Get execution details
aws stepfunctions describe-execution --execution-arn arn:aws:states:us-east-1:123456789012:execution:aurora-restore:execution-12345678 --region us-east-1

# Get execution history
aws stepfunctions get-execution-history --execution-arn arn:aws:states:us-east-1:123456789012:execution:aurora-restore:execution-12345678 --region us-east-1
```

### State Machine Visualization

Visualizing the state machine can help identify issues in the workflow:

```bash
# Get the state machine definition
aws stepfunctions describe-state-machine --state-machine-arn arn:aws:states:us-east-1:123456789012:stateMachine:aurora-restore --region us-east-1
```

Use the AWS Step Functions console to visualize the state machine and trace the execution path.

### Input/Output Debugging

Debugging the input and output of each state can help identify issues:

```bash
# Get the input and output of a specific execution event
aws stepfunctions get-execution-history --execution-arn arn:aws:states:us-east-1:123456789012:execution:aurora-restore:execution-12345678 --region us-east-1 --query "events[?type=='TaskStateExited']"
```

## Lambda Function Debugging

### Local Testing

Test Lambda functions locally before deploying them to AWS:

```bash
# Install the AWS SAM CLI
pip install aws-sam-cli

# Invoke a Lambda function locally
sam local invoke -e event.json aurora-restore-snapshot-check

# Start a local API for testing
sam local start-api
```

### Lambda Function Logs

CloudWatch Logs provide detailed information about Lambda function execution:

```bash
# Get the last 100 log events for a Lambda function
aws logs get-log-events --log-group-name /aws/lambda/aurora-restore-snapshot-check --log-stream-name $(aws logs describe-log-streams --log-group-name /aws/lambda/aurora-restore-snapshot-check --order-by LastEventTime --descending --limit 1 --query "logStreams[0].logStreamName" --output text) --limit 100 --region us-east-1

# Filter logs by time range
aws logs filter-log-events --log-group-name /aws/lambda/aurora-restore-snapshot-check --start-time 1609459200000 --end-time 1609545600000 --region us-east-1
```

### Lambda Function Testing

Test Lambda functions directly in AWS:

```bash
# Invoke a Lambda function with a test event
aws lambda invoke --function-name aurora-restore-snapshot-check --payload '{"key1":"value1","key2":"value2"}' --region us-east-1 response.json

# View the response
cat response.json
```

### Lambda Function Configuration

Check the Lambda function configuration:

```bash
# Get Lambda function details
aws lambda get-function --function-name aurora-restore-snapshot-check --region us-east-1

# Get Lambda function configuration
aws lambda get-function-configuration --function-name aurora-restore-snapshot-check --region us-east-1
```

## Database Connection Debugging

### Testing Database Connectivity

Test connectivity to the restored Aurora database:

```bash
# Get the cluster endpoint
aws rds describe-db-clusters --db-cluster-identifier target-cluster --query "DBClusters[0].Endpoint" --region us-east-1

# Test connection using mysql client
mysql -h <cluster-endpoint> -u <username> -p<password> -e "SELECT 1;"

# Test connection using telnet
telnet <cluster-endpoint> 3306
```

### Network Connectivity

Test network connectivity from the Lambda function to the database:

```bash
# Create a temporary Lambda function for testing
cat > lambda_function.py << EOF
import socket
import json

def lambda_handler(event, context):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((event['host'], int(event['port'])))
        return {
            'statusCode': 200,
            'body': json.dumps({
                'success': result == 0,
                'result': result,
                'message': f"Connection to {event['host']}:{event['port']} {'succeeded' if result == 0 else 'failed'}"
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'success': False,
                'message': str(e)
            })
        }
EOF

zip test-function.zip lambda_function.py

# Deploy the test function
aws lambda create-function --function-name test-db-connection --runtime python3.8 --role arn:aws:iam::123456789012:role/aurora-restore-lambda-execution-role --handler lambda_function.lambda_handler --zip-file fileb://test-function.zip --vpc-config SubnetIds=subnet-12345678,subnet-87654321,SecurityGroupIds=sg-12345678 --region us-east-1

# Test the connection
aws lambda invoke --function-name test-db-connection --payload '{"host":"target-cluster.cluster-xxxxxxxx.us-east-1.rds.amazonaws.com","port":3306}' --region us-east-1 response.json

# View the response
cat response.json

# Clean up
aws lambda delete-function --function-name test-db-connection --region us-east-1
```

### Database User Permission Debugging

Debug database user permissions:

```sql
-- Connect to the database
mysql -h <cluster-endpoint> -u <master-username> -p<master-password>

-- Show existing users
SELECT User, Host FROM mysql.user;

-- Show user privileges
SHOW GRANTS FOR 'app_user'@'%';
SHOW GRANTS FOR 'readonly_user'@'%';

-- Check if the user can connect
-- (Run this from a separate terminal)
mysql -h <cluster-endpoint> -u app_user -p<app_user_password> -e "SELECT 1;"
```

## State Management Debugging

### DynamoDB State Table

The Aurora Restore Pipeline uses DynamoDB for state management:

```bash
# List all items in the state table
aws dynamodb scan --table-name aurora-restore-state --region us-east-1

# Get a specific state item
aws dynamodb get-item --table-name aurora-restore-state --key '{"operation_id":{"S":"op-12345678"}}' --region us-east-1

# Update a state item
aws dynamodb update-item --table-name aurora-restore-state --key '{"operation_id":{"S":"op-12345678"}}' --update-expression "SET #s = :s" --expression-attribute-names '{"#s":"status"}' --expression-attribute-values '{":s":{"S":"completed"}}' --region us-east-1
```

### State Visualization

Create a simple script to visualize the state of an operation:

```python
#!/usr/bin/env python3
import boto3
import json
import sys
import argparse

def visualize_state(operation_id, region):
    dynamodb = boto3.resource('dynamodb', region_name=region)
    state_table = dynamodb.Table('aurora-restore-state')
    audit_table = dynamodb.Table('aurora-restore-audit')
    
    # Get the state
    state_response = state_table.get_item(Key={'operation_id': operation_id})
    if 'Item' not in state_response:
        print(f"No state found for operation {operation_id}")
        return
    
    state = state_response['Item']
    print(f"Operation: {operation_id}")
    print(f"Status: {state.get('status', 'unknown')}")
    print(f"Step: {state.get('step', 'unknown')}")
    print(f"Started: {state.get('start_time', 'unknown')}")
    print(f"Last Updated: {state.get('update_time', 'unknown')}")
    print("\nState Data:")
    print(json.dumps(state, indent=2, default=str))
    
    # Get audit events
    audit_response = audit_table.query(
        KeyConditionExpression='operation_id = :op_id',
        ExpressionAttributeValues={':op_id': operation_id}
    )
    
    if 'Items' in audit_response:
        print("\nAudit Events:")
        for event in sorted(audit_response['Items'], key=lambda x: x.get('timestamp', '')):
            print(f"{event.get('timestamp', 'unknown')} - {event.get('event_type', 'unknown')}: {event.get('message', 'No message')}")
    
    print("\nStep Functions Execution:")
    print(f"aws stepfunctions list-executions --state-machine-arn arn:aws:states:{region}:123456789012:stateMachine:aurora-restore --query \"executions[?name=='{operation_id}']\" --region {region}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Visualize Aurora Restore Pipeline state')
    parser.add_argument('operation_id', help='Operation ID to visualize')
    parser.add_argument('--region', default='us-east-1', help='AWS region')
    args = parser.parse_args()
    
    visualize_state(args.operation_id, args.region)
```

Save this script as `visualize_state.py` and run it:

```bash
python visualize_state.py op-12345678
```

## VPC Networking Debugging

### VPC Configuration

Check the VPC configuration for Lambda functions:

```bash
# Get Lambda function VPC configuration
aws lambda get-function-configuration --function-name aurora-restore-setup-db-users --region us-east-1 --query "VpcConfig"

# Get subnet details
aws ec2 describe-subnets --subnet-ids subnet-12345678 subnet-87654321 --region us-east-1

# Get security group details
aws ec2 describe-security-groups --group-ids sg-12345678 --region us-east-1
```

### Network ACLs and Route Tables

Check Network ACLs and Route Tables for the VPC:

```bash
# Get Network ACLs for the subnets
aws ec2 describe-network-acls --filters "Name=association.subnet-id,Values=subnet-12345678,subnet-87654321" --region us-east-1

# Get Route Tables for the subnets
aws ec2 describe-route-tables --filters "Name=association.subnet-id,Values=subnet-12345678,subnet-87654321" --region us-east-1
```

### DNS Resolution

Check DNS resolution in the VPC:

```bash
# Get VPC DNS settings
aws ec2 describe-vpcs --vpc-ids vpc-12345678 --region us-east-1 --query "Vpcs[0].{EnableDnsSupport:EnableDnsSupport,EnableDnsHostnames:EnableDnsHostnames}"
```

## Permissions and Security Debugging

### IAM Role Debugging

Debug IAM roles used by Lambda functions:

```bash
# Get Lambda function role
aws lambda get-function --function-name aurora-restore-snapshot-check --query "Configuration.Role" --output text --region us-east-1

# Get role details
aws iam get-role --role-name aurora-restore-lambda-execution-role

# List policies attached to the role
aws iam list-attached-role-policies --role-name aurora-restore-lambda-execution-role

# Get policy details
aws iam get-policy --policy-arn arn:aws:iam::123456789012:policy/aurora-restore-lambda-policy

# Get policy version details
aws iam get-policy-version --policy-arn arn:aws:iam::123456789012:policy/aurora-restore-lambda-policy --version-id v1
```

### Cross-Account Role Debugging

Debug cross-account roles:

```bash
# Get cross-account role details
aws iam get-role --role-name aurora-restore-cross-account-role

# List policies attached to the cross-account role
aws iam list-attached-role-policies --role-name aurora-restore-cross-account-role

# Get assume role policy
aws iam get-role --role-name aurora-restore-cross-account-role --query "AssumeRolePolicyDocument"
```

### Secrets Manager Debugging

Debug Secrets Manager access:

```bash
# List secrets
aws secretsmanager list-secrets --region us-east-1

# Get secret details
aws secretsmanager describe-secret --secret-id aurora-restore/dev/master-credentials --region us-east-1

# Get secret value
aws secretsmanager get-secret-value --secret-id aurora-restore/dev/master-credentials --region us-east-1

# List resource policies
aws secretsmanager get-resource-policy --secret-id aurora-restore/dev/master-credentials --region us-east-1
```

## Advanced Troubleshooting

### Creating a Detailed Debug Log

Create a detailed debug log for troubleshooting:

```bash
#!/usr/bin/env python3
import boto3
import json
import sys
import argparse
import time
from datetime import datetime, timedelta

def create_debug_log(operation_id, region, days=1):
    # Set up clients
    dynamodb = boto3.resource('dynamodb', region_name=region)
    logs_client = boto3.client('logs', region_name=region)
    stepfunctions = boto3.client('stepfunctions', region_name=region)
    
    # Set up tables
    state_table = dynamodb.Table('aurora-restore-state')
    audit_table = dynamodb.Table('aurora-restore-audit')
    
    # Define log groups
    log_groups = [
        '/aws/lambda/aurora-restore-snapshot-check',
        '/aws/lambda/aurora-restore-copy-snapshot',
        '/aws/lambda/aurora-restore-check-copy-status',
        '/aws/lambda/aurora-restore-delete-rds',
        '/aws/lambda/aurora-restore-check-delete-status',
        '/aws/lambda/aurora-restore-restore-snapshot',
        '/aws/lambda/aurora-restore-check-restore-status',
        '/aws/lambda/aurora-restore-setup-db-users',
        '/aws/lambda/aurora-restore-archive-snapshot',
        '/aws/lambda/aurora-restore-sns-notification'
    ]
    
    # Create a debug log file
    log_file = f"aurora-restore-debug-{operation_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}.log"
    
    with open(log_file, 'w') as f:
        # Write header
        f.write(f"Aurora Restore Pipeline Debug Log\n")
        f.write(f"Operation ID: {operation_id}\n")
        f.write(f"Region: {region}\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n")
        f.write(f"\n{'-' * 80}\n\n")
        
        # Get state information
        f.write("State Information:\n")
        state_response = state_table.get_item(Key={'operation_id': operation_id})
        if 'Item' in state_response:
            f.write(json.dumps(state_response['Item'], indent=2, default=str))
        else:
            f.write(f"No state found for operation {operation_id}\n")
        f.write(f"\n{'-' * 80}\n\n")
        
        # Get audit events
        f.write("Audit Events:\n")
        audit_response = audit_table.query(
            KeyConditionExpression='operation_id = :op_id',
            ExpressionAttributeValues={':op_id': operation_id}
        )
        
        if 'Items' in audit_response and audit_response['Items']:
            for event in sorted(audit_response['Items'], key=lambda x: x.get('timestamp', '')):
                f.write(f"{event.get('timestamp', 'unknown')} - {event.get('event_type', 'unknown')}: {event.get('message', 'No message')}\n")
        else:
            f.write(f"No audit events found for operation {operation_id}\n")
        f.write(f"\n{'-' * 80}\n\n")
        
        # Get Step Functions execution
        f.write("Step Functions Execution:\n")
        response = stepfunctions.list_executions(
            stateMachineArn=f"arn:aws:states:{region}:123456789012:stateMachine:aurora-restore",
            maxResults=100
        )
        
        executions = [exe for exe in response.get('executions', []) if exe.get('name') == operation_id]
        
        if executions:
            exe = executions[0]
            f.write(f"Execution ARN: {exe.get('executionArn')}\n")
            f.write(f"Status: {exe.get('status')}\n")
            f.write(f"Started: {exe.get('startDate', 'unknown')}\n")
            f.write(f"Stopped: {exe.get('stopDate', 'unknown') if 'stopDate' in exe else 'still running'}\n\n")
            
            # Get execution history
            history = stepfunctions.get_execution_history(
                executionArn=exe.get('executionArn'),
                maxResults=100
            )
            
            f.write("Execution History:\n")
            for event in sorted(history.get('events', []), key=lambda x: x.get('timestamp', '')):
                event_type = event.get('type', 'unknown')
                event_id = event.get('id', 'unknown')
                timestamp = event.get('timestamp', 'unknown')
                
                f.write(f"{timestamp} - [{event_id}] {event_type}\n")
                
                if event_type in ['TaskFailed', 'LambdaFunctionFailed', 'ExecutionFailed']:
                    f.write(f"  Error: {json.dumps(event.get('taskFailedEventDetails', {}), indent=2)}\n")
                elif event_type in ['TaskSucceeded', 'LambdaFunctionSucceeded']:
                    if 'output' in event.get('taskSucceededEventDetails', {}):
                        try:
                            output = json.loads(event.get('taskSucceededEventDetails', {}).get('output', '{}'))
                            f.write(f"  Output: {json.dumps(output, indent=2)}\n")
                        except:
                            pass
        else:
            f.write(f"No Step Functions execution found for operation {operation_id}\n")
        f.write(f"\n{'-' * 80}\n\n")
        
        # Get CloudWatch Logs
        start_time = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
        end_time = int(datetime.now().timestamp() * 1000)
        
        f.write("CloudWatch Logs:\n")
        for log_group in log_groups:
            f.write(f"\nLog Group: {log_group}\n")
            
            try:
                # Get log streams
                response = logs_client.describe_log_streams(
                    logGroupName=log_group,
                    orderBy='LastEventTime',
                    descending=True,
                    limit=10
                )
                
                log_streams = response.get('logStreams', [])
                
                if not log_streams:
                    f.write("  No log streams found\n")
                    continue
                
                # Filter logs containing the operation_id
                for stream in log_streams:
                    stream_name = stream.get('logStreamName', '')
                    
                    try:
                        log_events = logs_client.filter_log_events(
                            logGroupName=log_group,
                            logStreamNames=[stream_name],
                            startTime=start_time,
                            endTime=end_time,
                            filterPattern=operation_id,
                            limit=100
                        )
                        
                        events = log_events.get('events', [])
                        
                        if events:
                            f.write(f"\n  Stream: {stream_name}\n")
                            for event in events:
                                f.write(f"  {event.get('timestamp', 'unknown')} - {event.get('message', 'No message')}\n")
                    except Exception as e:
                        f.write(f"  Error getting logs for stream {stream_name}: {str(e)}\n")
            except Exception as e:
                f.write(f"  Error getting log streams: {str(e)}\n")
        
        f.write(f"\n{'-' * 80}\n\n")
        f.write("End of Debug Log\n")
    
    print(f"Debug log created: {log_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Create a debug log for Aurora Restore Pipeline')
    parser.add_argument('operation_id', help='Operation ID to create debug log for')
    parser.add_argument('--region', default='us-east-1', help='AWS region')
    parser.add_argument('--days', type=int, default=1, help='Number of days of logs to include')
    args = parser.parse_args()
    
    create_debug_log(args.operation_id, args.region, args.days)
```

Save this script as `create_debug_log.py` and run it:

```bash
python create_debug_log.py op-12345678
```

### Running in Debug Mode

To enable more verbose logging:

1. Update the Lambda function configuration:

```bash
aws lambda update-function-configuration --function-name aurora-restore-snapshot-check --environment "Variables={LOG_LEVEL=DEBUG}" --region us-east-1
```

2. Add `LOG_LEVEL=DEBUG` to all CloudFormation templates:

```yaml
Environment:
  Variables:
    LOG_LEVEL: DEBUG
```

### Replaying a Failed Operation

To replay a failed operation:

1. Get the current state:

```bash
aws dynamodb get-item --table-name aurora-restore-state --key '{"operation_id":{"S":"op-12345678"}}' --region us-east-1
```

2. Update the state to retry from a specific step:

```bash
aws dynamodb update-item --table-name aurora-restore-state --key '{"operation_id":{"S":"op-12345678"}}' --update-expression "SET #s = :s, #st = :st" --expression-attribute-names '{"#s":"status","#st":"step"}' --expression-attribute-values '{":s":{"S":"in_progress"},":st":{"S":"check_snapshot"}}' --region us-east-1
```

3. Start a new Step Functions execution with the same input:

```bash
aws stepfunctions start-execution --state-machine-arn arn:aws:states:us-east-1:123456789012:stateMachine:aurora-restore --name op-12345678-retry --input '{"operation_id":"op-12345678","snapshot_name":"aurora-snapshot-2023-01-01","source_region":"us-east-1","target_region":"us-west-2","target_cluster_id":"restored-cluster","db_subnet_group_name":"default","vpc_security_group_ids":["sg-12345678"]}' --region us-east-1
```

### Creating a Test Environment

Create a test environment to debug issues:

1. Create a test CloudFormation stack:

```bash
aws cloudformation create-stack --stack-name aurora-restore-test --template-body file://infrastructure/lambda.yaml --parameters ParameterKey=Environment,ParameterValue=test --capabilities CAPABILITY_IAM --region us-east-1
```

2. Create test snapshots:

```bash
aws rds create-db-cluster-snapshot --db-cluster-identifier source-cluster --db-cluster-snapshot-identifier aurora-snapshot-test --region us-east-1
```

3. Run a test execution:

```bash
aws stepfunctions start-execution --state-machine-arn arn:aws:states:us-east-1:123456789012:stateMachine:aurora-restore-test --name test-execution --input '{"snapshot_name":"aurora-snapshot-test","source_region":"us-east-1","target_region":"us-east-1","target_cluster_id":"restored-cluster-test","db_subnet_group_name":"default","vpc_security_group_ids":["sg-12345678"]}' --region us-east-1
```

## Next Steps

If the debugging steps in this guide don't resolve your issue, consider the following:

1. Review the [Error Reference](./03_error_reference.md) for specific error codes and their meanings.
2. Contact the Aurora Restore Pipeline development team for assistance.
3. Open an issue in the project's issue tracker with detailed information about the problem, including logs and error messages. 