# Aurora Restore Pipeline Testing Guide

This document provides detailed instructions for testing the Aurora Restore Pipeline.

## Testing Overview

The Aurora Restore Pipeline can be tested at different levels:

1. **Unit Testing**: Testing individual Lambda functions in isolation
2. **Integration Testing**: Testing the interaction between Lambda functions and AWS services
3. **End-to-End Testing**: Testing the entire pipeline from start to finish

## Prerequisites for Testing

Before testing the Aurora Restore Pipeline, ensure that you have:

- Deployed the pipeline to a test environment
- Created test snapshots in the source region
- Set up test VPC, subnets, and security groups
- Configured test environment variables and secrets
- Installed the required testing tools (pytest, boto3, moto)

## Unit Testing

Unit testing involves testing individual Lambda functions in isolation, mocking AWS service calls.

### Setting Up Unit Tests

1. Create a `tests` directory in your project.
2. Create a `unit` directory inside the `tests` directory.
3. Create test files for each Lambda function.

### Example Unit Test

```python
# tests/unit/test_snapshot_check.py
import json
import pytest
from unittest.mock import patch, MagicMock
from lambda_function import lambda_handler

@pytest.fixture
def event():
    return {
        "snapshot_id": "test-snapshot",
        "source_region": "us-east-1",
        "target_region": "us-west-2"
    }

@pytest.fixture
def context():
    return MagicMock()

@patch('lambda_function.rds_client')
def test_snapshot_check_success(mock_rds_client, event, context):
    # Mock RDS client response
    mock_rds_client.describe_db_cluster_snapshots.return_value = {
        'DBClusterSnapshots': [
            {
                'DBClusterSnapshotIdentifier': 'test-snapshot',
                'Status': 'available'
            }
        ]
    }
    
    # Call the Lambda function
    response = lambda_handler(event, context)
    
    # Assert the response
    assert response['statusCode'] == 200
    assert json.loads(response['body'])['status'] == 'success'
    assert json.loads(response['body'])['snapshot_available'] == True

@patch('lambda_function.rds_client')
def test_snapshot_check_not_found(mock_rds_client, event, context):
    # Mock RDS client response
    mock_rds_client.describe_db_cluster_snapshots.return_value = {
        'DBClusterSnapshots': []
    }
    
    # Call the Lambda function
    response = lambda_handler(event, context)
    
    # Assert the response
    assert response['statusCode'] == 404
    assert json.loads(response['body'])['status'] == 'error'
    assert json.loads(response['body'])['message'] == 'Snapshot not found'
```

### Running Unit Tests

To run unit tests, use the following command:

```bash
pytest tests/unit/
```

## Integration Testing

Integration testing involves testing the interaction between Lambda functions and AWS services.

### Setting Up Integration Tests

1. Create an `integration` directory inside the `tests` directory.
2. Create test files for each integration scenario.

### Example Integration Test

```python
# tests/integration/test_copy_snapshot.py
import json
import pytest
import boto3
from botocore.exceptions import ClientError
from lambda_function import lambda_handler

@pytest.fixture
def event():
    return {
        "snapshot_id": "test-snapshot",
        "source_region": "us-east-1",
        "target_region": "us-west-2"
    }

@pytest.fixture
def context():
    return MagicMock()

def test_copy_snapshot_integration(event, context):
    # Call the Lambda function
    response = lambda_handler(event, context)
    
    # Assert the response
    assert response['statusCode'] == 200
    assert json.loads(response['body'])['status'] == 'success'
    
    # Verify the snapshot was copied
    rds_client = boto3.client('rds', region_name=event['target_region'])
    try:
        snapshot = rds_client.describe_db_cluster_snapshots(
            DBClusterSnapshotIdentifier=f"{event['snapshot_id']}-copy"
        )
        assert snapshot['DBClusterSnapshots'][0]['Status'] == 'available'
    except ClientError as e:
        pytest.fail(f"Failed to verify snapshot copy: {e}")
```

### Running Integration Tests

To run integration tests, use the following command:

```bash
pytest tests/integration/
```

## End-to-End Testing

End-to-end testing involves testing the entire pipeline from start to finish.

### Setting Up End-to-End Tests

1. Create an `e2e` directory inside the `tests` directory.
2. Create test files for each end-to-end scenario.

### Example End-to-End Test

```python
# tests/e2e/test_restore_pipeline.py
import json
import pytest
import boto3
import time
from botocore.exceptions import ClientError

def test_restore_pipeline_e2e():
    # Create a Step Functions client
    stepfunctions = boto3.client('stepfunctions')
    
    # Start the state machine execution
    execution = stepfunctions.start_execution(
        stateMachineArn='arn:aws:states:us-east-1:123456789012:stateMachine:aurora-restore-state-machine',
        input=json.dumps({
            "snapshot_id": "test-snapshot",
            "source_region": "us-east-1",
            "target_region": "us-west-2",
            "vpc_id": "vpc-12345678",
            "subnet_ids": ["subnet-12345678", "subnet-87654321"],
            "security_group_ids": ["sg-12345678"]
        })
    )
    
    # Wait for the execution to complete
    execution_arn = execution['executionArn']
    while True:
        execution_status = stepfunctions.describe_execution(
            executionArn=execution_arn
        )
        if execution_status['status'] == 'SUCCEEDED':
            break
        elif execution_status['status'] == 'FAILED':
            pytest.fail(f"State machine execution failed: {execution_status}")
        time.sleep(30)
    
    # Verify the restored cluster
    rds_client = boto3.client('rds', region_name='us-west-2')
    try:
        cluster = rds_client.describe_db_clusters(
            DBClusterIdentifier='test-cluster-restored'
        )
        assert cluster['DBClusters'][0]['Status'] == 'available'
    except ClientError as e:
        pytest.fail(f"Failed to verify restored cluster: {e}")
```

### Running End-to-End Tests

To run end-to-end tests, use the following command:

```bash
pytest tests/e2e/
```

## Testing with AWS SAM

AWS SAM provides a local testing environment for Lambda functions and Step Functions.

### Setting Up AWS SAM

1. Install AWS SAM CLI.
2. Create a `template.yaml` file for your Lambda functions and Step Functions state machine.
3. Create a `samconfig.toml` file for your SAM configuration.

### Example template.yaml

```yaml
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31

Resources:
  SnapshotCheckFunction:
    Type: AWS::Serverless::Function
    Properties:
      CodeUri: lambda/
      Handler: snapshot_check.lambda_handler
      Runtime: python3.8
      Events:
        SnapshotCheckApi:
          Type: Api
          Properties:
            Path: /snapshot-check
            Method: post

  CopySnapshotFunction:
    Type: AWS::Serverless::Function
    Properties:
      CodeUri: lambda/
      Handler: copy_snapshot.lambda_handler
      Runtime: python3.8
      Events:
        CopySnapshotApi:
          Type: Api
          Properties:
            Path: /copy-snapshot
            Method: post

  AuroraRestoreStateMachine:
    Type: AWS::Serverless::StateMachine
    Properties:
      DefinitionUri: statemachine/aurora_restore.asl.json
      Policies:
        - LambdaInvokePolicy:
            FunctionName: !Ref SnapshotCheckFunction
        - LambdaInvokePolicy:
            FunctionName: !Ref CopySnapshotFunction
```

### Running Tests with AWS SAM

To run tests with AWS SAM, use the following commands:

```bash
# Build the SAM application
sam build

# Run the SAM application locally
sam local start-api

# Invoke a Lambda function locally
sam local invoke SnapshotCheckFunction --event events/snapshot_check_event.json

# Start a Step Functions execution locally
sam local start-state-machine --name AuroraRestoreStateMachine --event events/restore_event.json
```

## Testing with Moto

Moto is a library that allows you to mock AWS services in your tests.

### Setting Up Moto

1. Install Moto.
2. Use Moto decorators to mock AWS services.

### Example Test with Moto

```python
# tests/unit/test_dynamodb.py
import pytest
import boto3
from moto import mock_dynamodb
from lambda_function import lambda_handler

@pytest.fixture
def event():
    return {
        "operation_id": "test-operation"
    }

@pytest.fixture
def context():
    return MagicMock()

@mock_dynamodb
def test_save_state(event, context):
    # Create a DynamoDB table
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    table = dynamodb.create_table(
        TableName='aurora-restore-state',
        KeySchema=[
            {
                'AttributeName': 'operation_id',
                'KeyType': 'HASH'
            }
        ],
        AttributeDefinitions=[
            {
                'AttributeName': 'operation_id',
                'AttributeType': 'S'
            }
        ],
        ProvisionedThroughput={
            'ReadCapacityUnits': 5,
            'WriteCapacityUnits': 5
        }
    )
    
    # Call the Lambda function
    response = lambda_handler(event, context)
    
    # Assert the response
    assert response['statusCode'] == 200
    
    # Verify the state was saved
    saved_state = table.get_item(Key={'operation_id': 'test-operation'})
    assert saved_state['Item']['status'] == 'in_progress'
```

### Running Tests with Moto

To run tests with Moto, use the following command:

```bash
pytest tests/unit/test_dynamodb.py
```

## Testing Best Practices

1. **Test Coverage**: Aim for high test coverage, especially for critical components.
2. **Test Isolation**: Ensure that tests are isolated and do not depend on each other.
3. **Test Data**: Use realistic test data that represents actual use cases.
4. **Test Environment**: Use a dedicated test environment that is separate from production.
5. **Test Automation**: Automate tests as part of your CI/CD pipeline.
6. **Test Documentation**: Document tests and test scenarios for future reference.

## Conclusion

This testing guide provides detailed instructions for testing the Aurora Restore Pipeline. By following these instructions, you can effectively test the pipeline to ensure its reliability and correctness. 