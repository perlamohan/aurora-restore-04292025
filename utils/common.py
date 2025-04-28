#!/usr/bin/env python3
"""
Common utility functions for Aurora restore operations.
This module provides standardized utilities for AWS service interactions,
state management, logging, metrics, and validation.
"""

import os
import json
import time
import logging
import boto3
import datetime
import re
import uuid
from typing import Dict, Any, Optional, List, Union, Tuple, Callable
from botocore.exceptions import ClientError
from pythonjsonlogger import jsonlogger

# Configure JSON logging
logger = logging.getLogger()
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter()
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)
logger.setLevel(logging.INFO)

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
dynamodb_client = boto3.client('dynamodb')
rds_client = boto3.client('rds')
events_client = boto3.client('events')
cloudwatch = boto3.client('cloudwatch')
ssm = boto3.client('ssm')
secretsmanager = boto3.client('secretsmanager')
sns = boto3.client('sns')
lambda_client = boto3.client('lambda')

# Get environment variables
STATE_TABLE_NAME = os.environ.get('STATE_TABLE_NAME', 'aurora-restore-state')
STATE_INDEX_TABLE_NAME = os.environ.get('STATE_INDEX_TABLE_NAME', 'aurora-restore-state-index')
AUDIT_TABLE_NAME = os.environ.get('AUDIT_TABLE_NAME', 'aurora-restore-audit')
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
AWS_ACCOUNT_ID = os.environ.get('AWS_ACCOUNT_ID', '')

# Constants for retry mechanism
MAX_ATTEMPTS = 10
INITIAL_INTERVAL = 30  # seconds

# Get DynamoDB tables
state_table = dynamodb.Table(STATE_TABLE_NAME)
state_index_table = dynamodb.Table(STATE_INDEX_TABLE_NAME)
audit_table = dynamodb.Table(AUDIT_TABLE_NAME)

def get_config() -> Dict[str, Any]:
    """
    Get configuration from environment variables and SSM Parameter Store.
    
    Returns:
        dict: Configuration dictionary
    """
    config = {
        'source_region': os.environ.get('SOURCE_REGION', ''),
        'target_region': os.environ.get('TARGET_REGION', ''),
        'source_cluster_id': os.environ.get('SOURCE_CLUSTER_ID', ''),
        'target_cluster_id': os.environ.get('TARGET_CLUSTER_ID', ''),
        'snapshot_prefix': os.environ.get('SNAPSHOT_PREFIX', 'aurora-snapshot'),
        'vpc_security_group_ids': os.environ.get('VPC_SECURITY_GROUP_IDS', ''),
        'db_subnet_group_name': os.environ.get('DB_SUBNET_GROUP_NAME', ''),
        'kms_key_id': os.environ.get('KMS_KEY_ID', ''),
        'master_credentials_secret_id': os.environ.get('MASTER_CREDENTIALS_SECRET_ID', ''),
        'app_credentials_secret_id': os.environ.get('APP_CREDENTIALS_SECRET_ID', ''),
        'copy_status_retry_delay': int(os.environ.get('COPY_STATUS_RETRY_DELAY', '60')),
        'restore_status_retry_delay': int(os.environ.get('RESTORE_STATUS_RETRY_DELAY', '60')),
        'delete_status_retry_delay': int(os.environ.get('DELETE_STATUS_RETRY_DELAY', '60'))
    }
    
    # Try to get additional config from SSM
    try:
        ssm_config = get_ssm_parameter(f'/aurora-restore/{ENVIRONMENT}/config', '{}')
        config.update(json.loads(ssm_config))
    except Exception as e:
        logger.warning(f"Failed to load SSM config: {str(e)}")
    
    return config

def get_operation_id(event: Dict[str, Any]) -> str:
    """
    Get or generate a unique operation ID.
    
    Args:
        event: Event data that may contain an operation_id
        
    Returns:
        str: The operation ID
    """
    if event and isinstance(event, dict):
        if 'operation_id' in event:
            return event['operation_id']
        if 'body' in event and isinstance(event['body'], dict) and 'operation_id' in event['body']:
            return event['body']['operation_id']
    
    return f"op-{int(time.time())}-{uuid.uuid4().hex[:8]}"

def load_state(operation_id: str, step: Optional[str] = None) -> Dict[str, Any]:
    """
    Load state from DynamoDB.
    
    Args:
        operation_id: The unique identifier for this restore operation
        step: Optional step to load. If None, loads the latest step.
        
    Returns:
        dict: The state object
    """
    try:
        if step:
            # Load specific step
            response = state_table.get_item(
                Key={
                    'operation_id': operation_id,
                    'step': step
                }
            )
        else:
            # Load latest step
            response = state_table.query(
                KeyConditionExpression='operation_id = :op_id',
                ExpressionAttributeValues={
                    ':op_id': operation_id
                },
                ScanIndexForward=False,  # Descending order
                Limit=1
            )
            
        if 'Item' in response:
            return response['Item']
        elif 'Items' in response and response['Items']:
            return response['Items'][0]
            
        return {}
    except Exception as e:
        logger.error(f"Error loading state: {str(e)}", exc_info=True)
        return {}

def save_state(operation_id: str, state: Dict[str, Any]) -> bool:
    """
    Save state to DynamoDB.
    
    Args:
        operation_id: The unique identifier for this restore operation
        state: The state object to save
        
    Returns:
        bool: True if successful
    """
    try:
        # Ensure operation_id is in the state
        state['operation_id'] = operation_id
        
        # Add timestamp if not present
        if 'timestamp' not in state:
            state['timestamp'] = int(time.time())
            
        state_table.put_item(Item=state)
        return True
    except Exception as e:
        logger.error(f"Error saving state: {str(e)}", exc_info=True)
        return False

def log_audit_event(operation_id: str = "", event_type: str = "", status: str = "success", details: Dict[str, Any] = None) -> bool:
    """
    Log audit event to DynamoDB.
    
    Args:
        operation_id: The unique identifier for this restore operation
        event_type: The type of event
        status: The status of the event
        details: Additional details about the event
        
    Returns:
        bool: True if successful
    """
    if details is None:
        details = {}
        
    try:
        timestamp = datetime.datetime.now().isoformat()
        
        item = {
            'event_id': f"{event_type}_{timestamp}",
            'event_type': event_type,
            'status': status,
            'timestamp': timestamp,
            'details': json.dumps(details),
            'environment': ENVIRONMENT,
            'ttl': int(time.time()) + (30 * 24 * 60 * 60)  # 30 days TTL
        }
        
        if operation_id:
            item['operation_id'] = operation_id
            
        audit_table.put_item(Item=item)
        logger.info(f"Logged audit event: {event_type} - {status}")
        return True
    except Exception as e:
        logger.error(f"Error logging audit event: {str(e)}", exc_info=True)
        return False

def update_metrics(operation_id: str, metric_name: str, value: float, unit: str = "Count") -> bool:
    """
    Update CloudWatch metrics for monitoring.
    
    Args:
        operation_id: The unique identifier for this restore operation
        metric_name: The name of the metric
        value: The value of the metric
        unit: The unit of the metric
        
    Returns:
        bool: True if successful
    """
    try:
        # Update metric
        cloudwatch.put_metric_data(
            Namespace='AuroraRestore',
            MetricData=[
                {
                    'MetricName': metric_name,
                    'Value': value,
                    'Unit': unit,
                    'Dimensions': [
                        {'Name': 'OperationId', 'Value': operation_id},
                        {'Name': 'Environment', 'Value': ENVIRONMENT}
                    ]
                }
            ]
        )
            
        logger.info(f"Updated metric {metric_name} with value {value}")
        return True
    except Exception as e:
        logger.error(f"Error updating metrics: {str(e)}", exc_info=True)
        # Don't raise exception for metric updates
        return False

def get_ssm_parameter(param_name: str, default: Optional[str] = None) -> str:
    """
    Retrieve parameter from SSM Parameter Store.
    
    Args:
        param_name: The name of the parameter to retrieve
        default: Default value if parameter not found
        
    Returns:
        str: The parameter value or default
    """
    try:
        response = ssm.get_parameter(Name=param_name, WithDecryption=True)
        return response['Parameter']['Value']
    except ClientError as e:
        if e.response['Error']['Code'] == 'ParameterNotFound' and default is not None:
            logger.warning(f"Parameter {param_name} not found in SSM, using default")
            return default
        logger.error(f"Error retrieving SSM parameter {param_name}: {str(e)}")
        raise

def get_secret(secret_name: str) -> Dict[str, Any]:
    """
    Retrieve secret from Secrets Manager.
    
    Args:
        secret_name: The name of the secret to retrieve
        
    Returns:
        dict: The secret value as a dictionary
    """
    try:
        response = secretsmanager.get_secret_value(SecretId=secret_name)
        return json.loads(response['SecretString'])
    except ClientError as e:
        logger.error(f"Error retrieving secret {secret_name}: {str(e)}")
        raise

def send_notification(topic_arn: Optional[str] = None, subject: str = "", message: str = "") -> bool:
    """
    Send notification via SNS.
    
    Args:
        topic_arn: The ARN of the SNS topic (optional, will be retrieved from SSM if not provided)
        subject: The subject of the notification
        message: The message content
        
    Returns:
        bool: True if successful
    """
    try:
        # Get topic ARN from SSM if not provided
        if not topic_arn:
            topic_arn = get_ssm_parameter(f'/aurora-restore/{ENVIRONMENT}/notification-topic-arn')
            
        sns.publish(
            TopicArn=topic_arn,
            Subject=subject,
            Message=message
        )
        logger.info(f"Sent notification: {subject}")
        return True
    except Exception as e:
        logger.error(f"Error sending notification: {str(e)}", exc_info=True)
        return False

def handle_aws_error(error: ClientError, operation_id: str = "", step: str = "") -> Dict[str, Any]:
    """
    Handle AWS API errors with standardized logging and metrics.
    
    Args:
        error: The ClientError exception
        operation_id: The unique identifier for this restore operation
        step: The step where the error occurred
        
    Returns:
        dict: Error response object
    """
    error_code = error.response['Error']['Code']
    error_message = error.response['Error']['Message']
    
    # Log the error
    logger.error(f"AWS Error in step {step}: {error_code} - {error_message}")
    
    # Update metrics
    if operation_id:
        update_metrics(operation_id, f"Error_{error_code}", 1)
    
    # Log audit event
    if operation_id:
        log_audit_event(
            operation_id=operation_id,
            event_type=step,
            status="failed",
            details={
                'error_code': error_code,
                'error_message': error_message
            }
        )
    
    # Return error response
    return {
        'statusCode': 500,
        'body': json.dumps({
            'error': error_code,
            'message': error_message,
            'operation_id': operation_id,
            'step': step
        })
    }

def trigger_next_step(operation_id: str, next_step: str, event_data: Dict[str, Any] = None, delay_seconds: int = 0) -> bool:
    """
    Trigger the next step in the workflow.
    
    Args:
        operation_id: The unique identifier for this restore operation
        next_step: The name of the next step to trigger
        event_data: Additional event data to pass to the next step
        delay_seconds: Delay before triggering the next step
        
    Returns:
        bool: True if successful
    """
    try:
        if event_data is None:
            event_data = {}
            
        # Ensure operation_id is in the event data
        event_data['operation_id'] = operation_id
        
        # Get the Lambda function name for the next step
        function_name = f"aurora-restore-{next_step}"
        
        # Invoke the Lambda function
        lambda_client.invoke(
            FunctionName=function_name,
            InvocationType='Event',
            Payload=json.dumps(event_data)
        )
        
        logger.info(f"Triggered next step: {next_step}")
        return True
    except Exception as e:
        logger.error(f"Error triggering next step: {str(e)}", exc_info=True)
        return False

def validate_required_params(params: Dict[str, Any]) -> None:
    """
    Validate required parameters.
    
    Args:
        params: Dictionary of parameters to validate
        
    Raises:
        ValueError: If any required parameter is missing or empty
    """
    missing_params = []
    
    for param_name, param_value in params.items():
        if param_value is None or (isinstance(param_value, str) and param_value.strip() == ''):
            missing_params.append(param_name)
    
    if missing_params:
        raise ValueError(f"Missing required parameters: {', '.join(missing_params)}")

def validate_region(region: str) -> None:
    """
    Validate an AWS region.
    
    Args:
        region: AWS region to validate
        
    Raises:
        ValueError: If the region is invalid
    """
    if not region:
        raise ValueError("Region cannot be empty")
    
    # Check if region is valid
    regions = boto3.session.Session().get_available_regions('rds')
    
    if region not in regions:
        raise ValueError(f"Invalid region: {region}")

def validate_cluster_id(cluster_id: str) -> None:
    """
    Validate an RDS cluster ID.
    
    Args:
        cluster_id: RDS cluster ID to validate
        
    Raises:
        ValueError: If the cluster ID is invalid
    """
    if not cluster_id:
        raise ValueError("Cluster ID cannot be empty")
    
    # Check if cluster ID matches pattern
    pattern = r'^[a-zA-Z0-9-]+$'
    if not re.match(pattern, cluster_id):
        raise ValueError(f"Invalid cluster ID format: {cluster_id}")

def validate_snapshot_id(snapshot_id: str) -> None:
    """
    Validate an RDS snapshot ID.
    
    Args:
        snapshot_id: RDS snapshot ID to validate
        
    Raises:
        ValueError: If the snapshot ID is invalid
    """
    if not snapshot_id:
        raise ValueError("Snapshot ID cannot be empty")
    
    # Check if snapshot ID matches pattern
    pattern = r'^[a-zA-Z0-9-]+$'
    if not re.match(pattern, snapshot_id):
        raise ValueError(f"Invalid snapshot ID format: {snapshot_id}")

def validate_vpc_config(vpc_id: str, subnet_ids: List[str], security_group_ids: List[str]) -> None:
    """
    Validate VPC configuration parameters.
    
    Args:
        vpc_id: VPC ID to validate
        subnet_ids: List of subnet IDs to validate
        security_group_ids: List of security group IDs to validate
        
    Raises:
        ValueError: If any parameter is invalid
    """
    if not vpc_id:
        raise ValueError("VPC ID cannot be empty")
        
    if not subnet_ids:
        raise ValueError("At least one subnet ID is required")
        
    if not security_group_ids:
        raise ValueError("At least one security group ID is required")
        
    # Validate VPC ID format
    vpc_pattern = r'^vpc-[a-f0-9]+$'
    if not re.match(vpc_pattern, vpc_id):
        raise ValueError(f"Invalid VPC ID format: {vpc_id}")
        
    # Validate subnet ID format
    subnet_pattern = r'^subnet-[a-f0-9]+$'
    for subnet_id in subnet_ids:
        if not re.match(subnet_pattern, subnet_id):
            raise ValueError(f"Invalid subnet ID format: {subnet_id}")
            
    # Validate security group ID format
    sg_pattern = r'^sg-[a-f0-9]+$'
    for sg_id in security_group_ids:
        if not re.match(sg_pattern, sg_id):
            raise ValueError(f"Invalid security group ID format: {sg_id}")

def validate_db_credentials(credentials: Dict[str, str], is_master: bool = False) -> None:
    """
    Validate database credentials.
    
    Args:
        credentials: Dictionary containing database credentials
        is_master: Whether these are master credentials
        
    Raises:
        ValueError: If credentials are invalid
    """
    required_fields = ['username', 'password', 'host', 'port', 'database']
    
    if is_master:
        required_fields.extend(['master_username', 'master_password'])
    
    missing_fields = [field for field in required_fields if field not in credentials]
    if missing_fields:
        raise ValueError(f"Missing required credential fields: {', '.join(missing_fields)}")
    
    # Validate port is a number
    try:
        port = int(credentials['port'])
        if port < 1 or port > 65535:
            raise ValueError("Port must be between 1 and 65535")
    except ValueError:
        raise ValueError("Port must be a valid number")
    
    # Validate host format
    host = credentials['host']
    if not host or len(host) > 255:
        raise ValueError("Invalid host format")
    
    # Validate username format
    username = credentials['username']
    if not username or len(username) > 63:
        raise ValueError("Invalid username format")
    
    # Validate database name format
    database = credentials['database']
    if not database or len(database) > 63:
        raise ValueError("Invalid database name format") 