#!/usr/bin/env python3
"""
AWS service utilities for Aurora restore operations.
This module provides standardized utilities for AWS service interactions.
"""

import os
import json
import time
import boto3
from typing import Dict, Any, Optional, List, Union, Tuple
from botocore.exceptions import ClientError
from tenacity import retry, stop_after_attempt, wait_exponential

from utils.core import ENVIRONMENT, AWS_REGION, AWS_ACCOUNT_ID

# Constants for retry mechanism
MAX_ATTEMPTS = 10
INITIAL_INTERVAL = 30  # seconds

# Initialize AWS clients with lazy loading
_clients = {}

def get_client(service_name: str, region_name: Optional[str] = None) -> Any:
    """
    Get an AWS client with lazy loading.
    
    Args:
        service_name: Name of the AWS service
        region_name: Optional region name
        
    Returns:
        Any: AWS client
    """
    key = f"{service_name}:{region_name or AWS_REGION}"
    
    if key not in _clients:
        _clients[key] = boto3.client(service_name, region_name=region_name)
    
    return _clients[key]

def get_resource(service_name: str, region_name: Optional[str] = None) -> Any:
    """
    Get an AWS resource with lazy loading.
    
    Args:
        service_name: Name of the AWS service
        region_name: Optional region name
        
    Returns:
        Any: AWS resource
    """
    key = f"{service_name}:{region_name or AWS_REGION}"
    
    if key not in _clients:
        _clients[key] = boto3.resource(service_name, region_name=region_name)
    
    return _clients[key]

@retry(stop=stop_after_attempt(MAX_ATTEMPTS), wait=wait_exponential(multiplier=1, min=4, max=60))
def get_ssm_parameter(param_name: str, default: Optional[str] = None) -> str:
    """
    Retrieve parameter from SSM Parameter Store.
    
    Args:
        param_name: Name of the parameter
        default: Default value if parameter not found
        
    Returns:
        str: Parameter value
    """
    try:
        ssm = get_client('ssm')
        response = ssm.get_parameter(Name=param_name, WithDecryption=True)
        return response['Parameter']['Value']
    except ClientError as e:
        if e.response['Error']['Code'] == 'ParameterNotFound' and default is not None:
            return default
        raise

@retry(stop=stop_after_attempt(MAX_ATTEMPTS), wait=wait_exponential(multiplier=1, min=4, max=60))
def get_secret(secret_name: str) -> Dict[str, Any]:
    """
    Retrieve secret from Secrets Manager.
    
    Args:
        secret_name: Name of the secret
        
    Returns:
        Dict[str, Any]: Secret value
    """
    try:
        secretsmanager = get_client('secretsmanager')
        response = secretsmanager.get_secret_value(SecretId=secret_name)
        return json.loads(response['SecretString'])
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            raise ValueError(f"Secret {secret_name} not found")
        raise

@retry(stop=stop_after_attempt(MAX_ATTEMPTS), wait=wait_exponential(multiplier=1, min=4, max=60))
def send_notification(topic_arn: Optional[str] = None, subject: str = "", message: str = "") -> bool:
    """
    Send notification to SNS topic.
    
    Args:
        topic_arn: ARN of the SNS topic
        subject: Subject of the notification
        message: Message content
        
    Returns:
        bool: True if successful
    """
    if not topic_arn:
        return False
    
    try:
        sns = get_client('sns')
        sns.publish(
            TopicArn=topic_arn,
            Subject=subject,
            Message=message
        )
        return True
    except ClientError:
        return False

def handle_aws_error(error: ClientError, operation_id: str = "", step: str = "") -> Dict[str, Any]:
    """
    Handle AWS API errors in a standardized way.
    
    Args:
        error: The ClientError exception
        operation_id: Operation ID
        step: Step name
        
    Returns:
        Dict[str, Any]: Error information
    """
    error_code = error.response['Error']['Code']
    error_message = error.response['Error']['Message']
    
    # Map common error codes to appropriate HTTP status codes
    status_code_map = {
        'AccessDeniedException': 403,
        'InvalidParameterException': 400,
        'ResourceNotFoundException': 404,
        'ThrottlingException': 429,
        'ValidationException': 400
    }
    
    status_code = status_code_map.get(error_code, 500)
    
    return {
        'statusCode': status_code,
        'error': error_message,
        'error_type': error_code,
        'operation_id': operation_id,
        'step': step
    }

@retry(stop=stop_after_attempt(MAX_ATTEMPTS), wait=wait_exponential(multiplier=1, min=4, max=60))
def trigger_next_step(operation_id: str, next_step: str, event_data: Dict[str, Any] = None, delay_seconds: int = 0) -> bool:
    """
    Trigger the next step in the workflow.
    
    Args:
        operation_id: Operation ID
        next_step: Name of the next step
        event_data: Data to pass to the next step
        delay_seconds: Delay in seconds before triggering
        
    Returns:
        bool: True if successful
    """
    try:
        events = get_client('events')
        lambda_client = get_client('lambda')
        
        # Get the Lambda function name for the next step
        function_name = f"aurora-restore-{next_step}"
        
        # Prepare the event data
        if event_data is None:
            event_data = {}
        
        event_data['operation_id'] = operation_id
        
        # Create the event
        response = events.put_events(
            Entries=[
                {
                    'Source': 'com.aurora.restore',
                    'DetailType': next_step,
                    'Detail': json.dumps(event_data),
                    'EventBusName': 'default',
                    'Time': int(time.time() + delay_seconds)
                }
            ]
        )
        
        return response['FailedEntryCount'] == 0
        
    except Exception as e:
        logger.error(f"Error triggering next step: {str(e)}", exc_info=True)
        return False 