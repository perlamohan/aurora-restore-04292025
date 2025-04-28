# Aurora Restore Pipeline Usage Guide

This document provides instructions on how to use the Aurora Restore Pipeline after deployment.

## Table of Contents

- [Manual Execution](#manual-execution)
- [Scheduled Execution](#scheduled-execution)
- [Input Parameters](#input-parameters)
- [Monitoring Executions](#monitoring-executions)
- [Common Use Cases](#common-use-cases)
- [Best Practices](#best-practices)

## Manual Execution

You can manually start the Aurora Restore Pipeline using the AWS CLI, AWS SDK, or the AWS Management Console.

### Using the AWS Management Console

1. Open the AWS Step Functions console: https://console.aws.amazon.com/states/
2. Navigate to the state machine list and find your Aurora Restore Pipeline state machine (e.g., `aurora-restore-dev`)
3. Click on the state machine name to view its details
4. Click the "Start execution" button
5. Enter the input parameters in JSON format:

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

6. Click "Start execution"

### Using the AWS CLI

```bash
# Get the state machine ARN
STATE_MACHINE_ARN=$(aws stepfunctions list-state-machines --query "stateMachines[?name=='aurora-restore-dev'].stateMachineArn" --output text)

# Start an execution
aws stepfunctions start-execution \
  --state-machine-arn $STATE_MACHINE_ARN \
  --name execution-$(date +%s) \
  --input '{
    "snapshot_name": "aurora-snapshot-2023-01-01",
    "source_region": "us-east-1",
    "target_region": "us-west-2",
    "target_cluster_id": "restored-cluster",
    "db_subnet_group_name": "default",
    "vpc_security_group_ids": ["sg-12345678"]
  }'
```

### Using the AWS SDK (Python Example)

```python
import boto3
import json
import time

def start_restore_pipeline(input_params):
    """
    Start the Aurora Restore Pipeline execution.
    
    Args:
        input_params (dict): Input parameters for the pipeline
    
    Returns:
        str: The execution ARN
    """
    client = boto3.client('stepfunctions')
    
    # Get the state machine ARN
    response = client.list_state_machines()
    state_machine_arn = None
    for machine in response['stateMachines']:
        if machine['name'] == 'aurora-restore-dev':
            state_machine_arn = machine['stateMachineArn']
            break
    
    if not state_machine_arn:
        raise ValueError("State machine not found")
    
    # Start the execution
    response = client.start_execution(
        stateMachineArn=state_machine_arn,
        name=f"execution-{int(time.time())}",
        input=json.dumps(input_params)
    )
    
    return response['executionArn']

# Example usage
input_params = {
    "snapshot_name": "aurora-snapshot-2023-01-01",
    "source_region": "us-east-1",
    "target_region": "us-west-2",
    "target_cluster_id": "restored-cluster",
    "db_subnet_group_name": "default",
    "vpc_security_group_ids": ["sg-12345678"]
}

execution_arn = start_restore_pipeline(input_params)
print(f"Execution started: {execution_arn}")
```

## Scheduled Execution

To automatically execute the pipeline on a schedule, you can use Amazon EventBridge (formerly CloudWatch Events).

### Setting Up a Daily Schedule

This example shows how to set up a schedule to run the pipeline daily at 2:00 AM UTC:

```bash
# Get the state machine ARN
STATE_MACHINE_ARN=$(aws stepfunctions list-state-machines --query "stateMachines[?name=='aurora-restore-dev'].stateMachineArn" --output text)

# Create an IAM role for EventBridge to invoke Step Functions
aws iam create-role \
  --role-name aurora-restore-events-role \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Principal": {
          "Service": "events.amazonaws.com"
        },
        "Action": "sts:AssumeRole"
      }
    ]
  }'

# Attach a policy to the role to allow invoking Step Functions
aws iam put-role-policy \
  --role-name aurora-restore-events-role \
  --policy-name StepFunctionsInvoke \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": [
          "states:StartExecution"
        ],
        "Resource": ["'"$STATE_MACHINE_ARN"'"]
      }
    ]
  }'

# Get the role ARN
ROLE_ARN=$(aws iam get-role --role-name aurora-restore-events-role --query 'Role.Arn' --output text)

# Create a rule that runs daily at 2:00 AM UTC
aws events put-rule \
  --name aurora-restore-daily \
  --schedule-expression "cron(0 2 * * ? *)" \
  --state ENABLED

# Add the Step Functions state machine as a target
aws events put-targets \
  --rule aurora-restore-daily \
  --targets '[{
    "Id": "1",
    "Arn": "'"$STATE_MACHINE_ARN"'",
    "RoleArn": "'"$ROLE_ARN"'",
    "Input": "{\"snapshot_name\":\"aurora-snapshot-$(date +%Y-%m-%d)\",\"source_region\":\"us-east-1\",\"target_region\":\"us-west-2\",\"target_cluster_id\":\"restored-cluster\",\"db_subnet_group_name\":\"default\",\"vpc_security_group_ids\":[\"sg-12345678\"]}"
  }]'
```

Note that the input includes a dynamic date in the snapshot name, assuming snapshots are named with the date they were created.

## Input Parameters

The Aurora Restore Pipeline requires the following input parameters:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `snapshot_name` | String | Yes | The name of the snapshot to restore. This may include a date in the format "aurora-snapshot-YYYY-MM-DD". |
| `source_region` | String | Yes | The AWS region where the source snapshot is located. |
| `target_region` | String | Yes | The AWS region where the snapshot should be restored. |
| `target_cluster_id` | String | Yes | The identifier for the new Aurora cluster to be created. |
| `db_subnet_group_name` | String | Yes | The DB subnet group to use for the new Aurora cluster. |
| `vpc_security_group_ids` | Array | Yes | An array of VPC security group IDs to associate with the new Aurora cluster. |
| `db_instance_class` | String | No | The DB instance class to use for the new Aurora cluster. Default is "db.r5.large". |
| `engine` | String | No | The database engine to use. Default is "aurora-mysql". |
| `engine_version` | String | No | The engine version to use. If not specified, the default will be used. |
| `port` | Number | No | The port on which the database accepts connections. Default is 3306. |
| `db_parameter_group_name` | String | No | The DB parameter group to associate with the new Aurora cluster. |
| `db_cluster_parameter_group_name` | String | No | The DB cluster parameter group to associate with the new Aurora cluster. |
| `deletion_protection` | Boolean | No | Enable or disable deletion protection for the new Aurora cluster. Default is false. |
| `operation_id` | String | No | A unique identifier for the operation. If not provided, a unique ID will be generated. |

Example input with optional parameters:

```json
{
  "snapshot_name": "aurora-snapshot-2023-01-01",
  "source_region": "us-east-1",
  "target_region": "us-west-2",
  "target_cluster_id": "restored-cluster",
  "db_subnet_group_name": "default",
  "vpc_security_group_ids": ["sg-12345678"],
  "db_instance_class": "db.r5.xlarge",
  "engine": "aurora-mysql",
  "engine_version": "5.7.mysql_aurora.2.10.2",
  "port": 3306,
  "db_parameter_group_name": "default.aurora-mysql5.7",
  "db_cluster_parameter_group_name": "default.aurora-mysql5.7",
  "deletion_protection": false
}
```

## Monitoring Executions

You can monitor the execution of the Aurora Restore Pipeline using the AWS Management Console, AWS CLI, or CloudWatch.

### Using the AWS Management Console

1. Open the AWS Step Functions console: https://console.aws.amazon.com/states/
2. Navigate to the state machine list and find your Aurora Restore Pipeline state machine
3. Click on the state machine name to view its details
4. In the "Executions" tab, you'll see a list of all executions
5. Click on an execution to view its details, including the visual workflow, execution input/output, and events

### Using the AWS CLI

```bash
# Get the execution ARN
EXECUTION_ARN=$(aws stepfunctions list-executions --state-machine-arn $STATE_MACHINE_ARN --query "executions[0].executionArn" --output text)

# Describe the execution
aws stepfunctions describe-execution --execution-arn $EXECUTION_ARN

# Get the execution history
aws stepfunctions get-execution-history --execution-arn $EXECUTION_ARN
```

### Using CloudWatch Logs

Each Lambda function in the pipeline logs to CloudWatch Logs. You can view these logs to debug issues or monitor progress:

```bash
# List all log groups for the Aurora Restore Pipeline
aws logs describe-log-groups --log-group-name-prefix /aws/lambda/aurora-restore

# Get logs for a specific Lambda function
aws logs filter-log-events --log-group-name /aws/lambda/aurora-restore-snapshot-check-dev

# Filter logs by operation ID
aws logs filter-log-events --log-group-name /aws/lambda/aurora-restore-snapshot-check-dev --filter-pattern "op-12345678"
```

### Using DynamoDB

You can query the state and audit tables to get information about the operation:

```bash
# Get the state record for a specific operation
aws dynamodb get-item \
  --table-name aurora-restore-state-dev \
  --key '{"operation_id":{"S":"op-12345678"}}'

# Get all audit events for a specific operation
aws dynamodb query \
  --table-name aurora-restore-audit-dev \
  --key-condition-expression "operation_id = :op_id" \
  --expression-attribute-values '{":op_id":{"S":"op-12345678"}}'
```

## Common Use Cases

### Restoring Yesterday's Snapshot

This is a common use case for testing or disaster recovery:

```bash
# Get yesterday's date in YYYY-MM-DD format
YESTERDAY=$(date -d "yesterday" +%Y-%m-%d)

# Start an execution with yesterday's snapshot
aws stepfunctions start-execution \
  --state-machine-arn $STATE_MACHINE_ARN \
  --name execution-$(date +%s) \
  --input '{
    "snapshot_name": "aurora-snapshot-'"$YESTERDAY"'",
    "source_region": "us-east-1",
    "target_region": "us-west-2",
    "target_cluster_id": "restored-cluster",
    "db_subnet_group_name": "default",
    "vpc_security_group_ids": ["sg-12345678"]
  }'
```

### Restoring to a Specific Point in Time

If you need to restore to a specific point in time, you'll need to have a snapshot from before that time and then use the RDS APIs directly:

```python
import boto3
import json
import time

def restore_to_point_in_time(cluster_id, restore_time, subnet_group, security_groups, region='us-east-1'):
    """
    Restore an Aurora cluster to a specific point in time.
    
    Args:
        cluster_id (str): The ID of the source cluster
        restore_time (str): The time to restore to, in ISO 8601 format
        subnet_group (str): The DB subnet group to use
        security_groups (list): The security groups to use
        region (str): The AWS region
    
    Returns:
        str: The new cluster ID
    """
    client = boto3.client('rds', region_name=region)
    
    # Create a new cluster ID
    new_cluster_id = f"{cluster_id}-restored-{int(time.time())}"
    
    # Restore the cluster
    response = client.restore_db_cluster_to_point_in_time(
        DBClusterIdentifier=new_cluster_id,
        SourceDBClusterIdentifier=cluster_id,
        RestoreToTime=restore_time,
        DBSubnetGroupName=subnet_group,
        VpcSecurityGroupIds=security_groups,
        UseLatestRestorableTime=False
    )
    
    print(f"Restoring to point in time: {restore_time}")
    print(f"New cluster ID: {new_cluster_id}")
    
    return new_cluster_id

# Example usage
restore_to_point_in_time(
    cluster_id='source-cluster',
    restore_time='2023-01-01T12:00:00Z',
    subnet_group='default',
    security_groups=['sg-12345678'],
    region='us-east-1'
)
```

### Cross-Account Restoration

For cross-account restoration, you'll need to:

1. Share the snapshot with the target account
2. Copy the snapshot in the target account
3. Restore the cluster from the copied snapshot

This can be implemented by extending the pipeline with cross-account IAM roles and cross-account snapshot sharing.

## Best Practices

Follow these best practices when using the Aurora Restore Pipeline:

1. **Test the Pipeline**: Always test the pipeline in a non-production environment before using it in production.

2. **Monitor Executions**: Set up CloudWatch Alarms to monitor pipeline executions and notify you of failures.

3. **Use Meaningful Names**: Use descriptive names for your clusters and snapshots to make identification easier.

4. **Clean Up Resources**: Clean up unused resources to avoid unnecessary costs. The pipeline helps with this by deleting copied snapshots after restoration.

5. **Secure Your Credentials**: Use Secrets Manager or Parameter Store for storing sensitive information, and ensure that IAM roles have the least privilege needed.

6. **Keep Track of Operations**: Use the operation_id to track operations across the pipeline, especially if you have multiple executions running concurrently.

7. **Customize for Your Needs**: Extend the pipeline to meet your specific requirements, such as adding post-restore scripts or additional validation steps.

8. **Regularly Verify Backups**: Regularly verify that your backups are valid by restoring them and running validation tests.

9. **Document Your Processes**: Document your restoration procedures, including any manual steps or verification checks needed after the pipeline completes.

10. **Plan for Disaster Recovery**: Use the pipeline as part of a broader disaster recovery strategy, ensuring that all critical systems can be restored efficiently. 