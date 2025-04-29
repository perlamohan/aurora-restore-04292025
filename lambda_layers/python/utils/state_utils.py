#!/usr/bin/env python3
"""
State management utilities for Aurora restore operations.
This module provides standardized utilities for state management.
"""

import os
import json
import time
import uuid
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from utils.core import ENVIRONMENT
from utils.aws_utils import get_resource

# Configure logging
logger = logging.getLogger()

# Get environment variables
STATE_TABLE_NAME = os.environ.get('STATE_TABLE_NAME', 'aurora-restore-state')
STATE_INDEX_TABLE_NAME = os.environ.get('STATE_INDEX_TABLE_NAME', 'aurora-restore-state-index')
AUDIT_TABLE_NAME = os.environ.get('AUDIT_TABLE_NAME', 'aurora-restore-audit')

# Get DynamoDB tables
state_table = get_resource('dynamodb').Table(STATE_TABLE_NAME)
state_index_table = get_resource('dynamodb').Table(STATE_INDEX_TABLE_NAME)
audit_table = get_resource('dynamodb').Table(AUDIT_TABLE_NAME)

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
        timestamp = datetime.now().isoformat()
        
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
        cloudwatch = get_resource('cloudwatch').meta.client
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