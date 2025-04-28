"""
Function-specific utility functions and imports for Aurora restore Lambda functions.
"""

import boto3
import psycopg2
from typing import Dict, Any, Optional
from botocore.exceptions import ClientError

def validate_db_credentials(credentials: Dict[str, str], is_master: bool = True) -> None:
    """
    Validate the database credentials retrieved from Secrets Manager.
    
    Args:
        credentials: Dictionary containing database credentials
        is_master: Boolean indicating if these are master credentials
        
    Raises:
        ValueError: If any required credential is missing
    """
    if is_master:
        required_fields = ['database', 'username', 'password']
    else:
        required_fields = ['app_username', 'app_password', 'readonly_username', 'readonly_password']
    
    missing_fields = [field for field in required_fields if field not in credentials]
    
    if missing_fields:
        raise ValueError(f"Missing required database credential fields: {', '.join(missing_fields)}")

def validate_snapshot_name(snapshot_name: str) -> None:
    """
    Validate the snapshot name format.
    
    Args:
        snapshot_name: Name of the snapshot to validate
        
    Raises:
        ValueError: If the snapshot name is invalid
    """
    if not snapshot_name:
        raise ValueError("Snapshot name cannot be empty")
    
    if len(snapshot_name) > 255:
        raise ValueError("Snapshot name cannot be longer than 255 characters")
    
    if not snapshot_name[0].isalnum():
        raise ValueError("Snapshot name must start with an alphanumeric character")
    
    valid_chars = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-')
    if not all(c in valid_chars for c in snapshot_name):
        raise ValueError("Snapshot name can only contain letters, numbers, and hyphens")

def validate_cluster_id(cluster_id: str) -> None:
    """
    Validate the cluster ID format.
    
    Args:
        cluster_id: ID of the cluster to validate
        
    Raises:
        ValueError: If the cluster ID is invalid
    """
    if not cluster_id:
        raise ValueError("Cluster ID cannot be empty")
    
    if len(cluster_id) > 63:
        raise ValueError("Cluster ID cannot be longer than 63 characters")
    
    if not cluster_id[0].isalnum():
        raise ValueError("Cluster ID must start with an alphanumeric character")
    
    valid_chars = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-')
    if not all(c in valid_chars for c in cluster_id):
        raise ValueError("Cluster ID can only contain letters, numbers, and hyphens") 