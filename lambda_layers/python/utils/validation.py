#!/usr/bin/env python3
"""
Validation utilities for Aurora restore operations.
This module provides standardized validation functions for inputs and configurations.
"""

import re
from typing import Dict, Any, List, Optional

from utils.core import get_config

def validate_required_params(params: Dict[str, Any]) -> List[str]:
    """
    Validate that required parameters are present and not empty.
    
    Args:
        params: Dictionary of parameters to validate
        
    Returns:
        List[str]: List of missing parameter names
    """
    missing = []
    for key, value in params.items():
        if value is None or value == '':
            missing.append(key)
    return missing

def validate_region(region: str) -> bool:
    """
    Validate AWS region format.
    
    Args:
        region: Region to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    if not region:
        return False
    
    # AWS region format: us-east-1, eu-west-1, etc.
    pattern = r'^[a-z]{2}-[a-z]+-\d{1}$'
    return bool(re.match(pattern, region))

def validate_cluster_id(cluster_id: str) -> bool:
    """
    Validate the cluster ID format.
    
    Args:
        cluster_id: ID of the cluster to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    if not cluster_id:
        return False
    
    if len(cluster_id) > 63:
        return False
    
    if not cluster_id[0].isalnum():
        return False
    
    valid_chars = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-')
    return all(c in valid_chars for c in cluster_id)

def validate_snapshot_id(snapshot_id: str) -> bool:
    """
    Validate the snapshot ID format.
    
    Args:
        snapshot_id: ID of the snapshot to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    if not snapshot_id:
        return False
    
    if len(snapshot_id) > 255:
        return False
    
    if not snapshot_id[0].isalnum():
        return False
    
    valid_chars = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-')
    return all(c in valid_chars for c in snapshot_id)

def validate_snapshot_name(snapshot_name: str) -> bool:
    """
    Validate the snapshot name format.
    
    Args:
        snapshot_name: Name of the snapshot to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    if not snapshot_name:
        return False
    
    if len(snapshot_name) > 255:
        return False
    
    if not snapshot_name[0].isalnum():
        return False
    
    valid_chars = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-')
    return all(c in valid_chars for c in snapshot_name)

def validate_vpc_config(vpc_id: str, subnet_ids: List[str], security_group_ids: List[str]) -> bool:
    """
    Validate VPC configuration parameters.
    
    Args:
        vpc_id: VPC ID to validate
        subnet_ids: List of subnet IDs to validate
        security_group_ids: List of security group IDs to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    # Validate VPC ID
    if not vpc_id or not vpc_id.startswith('vpc-'):
        return False
    
    # Validate subnet IDs
    if not subnet_ids or not all(subnet.startswith('subnet-') for subnet in subnet_ids):
        return False
    
    # Validate security group IDs
    if not security_group_ids or not all(sg.startswith('sg-') for sg in security_group_ids):
        return False
    
    return True

def validate_db_credentials(credentials: Dict[str, str], is_master: bool = False) -> List[str]:
    """
    Validate the database credentials retrieved from Secrets Manager.
    
    Args:
        credentials: Dictionary containing database credentials
        is_master: Boolean indicating if these are master credentials
        
    Returns:
        List[str]: List of missing credential fields
    """
    if is_master:
        required_fields = ['database', 'username', 'password']
    else:
        required_fields = ['app_username', 'app_password', 'readonly_username', 'readonly_password']
    
    return [field for field in required_fields if field not in credentials] 