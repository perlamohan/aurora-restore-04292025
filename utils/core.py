#!/usr/bin/env python3
"""
Core utilities for Aurora restore operations.
This module provides core functionality used across other utility modules.
"""

import os
import json
import time
import uuid
import logging
from typing import Dict, Any, Optional

# Configure logging
logger = logging.getLogger()

# Get environment variables
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
AWS_ACCOUNT_ID = os.environ.get('AWS_ACCOUNT_ID', '')

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

def get_config() -> Dict[str, Any]:
    """
    Get configuration from environment variables.
    
    Returns:
        dict: Configuration dictionary
    """
    return {
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
        'delete_status_retry_delay': int(os.environ.get('DELETE_STATUS_RETRY_DELAY', '60')),
        'environment': ENVIRONMENT,
        'region': AWS_REGION,
        'account_id': AWS_ACCOUNT_ID
    } 