#!/usr/bin/env python3
"""
Common configuration and logging setup for Aurora restore operations.
This module provides standardized configuration management and logging setup.
"""

import os
import json
import logging
from typing import Dict, Any
from pythonjsonlogger import jsonlogger

from utils.core import get_config, get_operation_id
from utils.aws_utils import get_ssm_parameter

# Configure JSON logging
logger = logging.getLogger()
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter()
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)
logger.setLevel(logging.INFO)

# Get environment variables
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
AWS_ACCOUNT_ID = os.environ.get('AWS_ACCOUNT_ID', '')

def get_full_config() -> Dict[str, Any]:
    """
    Get configuration from environment variables and SSM Parameter Store.
    
    Returns:
        dict: Configuration dictionary
    """
    config = get_config()
    
    # Try to get additional config from SSM
    try:
        ssm_config = get_ssm_parameter(f'/aurora-restore/{config["environment"]}/config', '{}')
        config.update(json.loads(ssm_config))
    except Exception as e:
        logger.warning(f"Failed to load SSM config: {str(e)}")
    
    return config 