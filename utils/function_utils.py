#!/usr/bin/env python3
"""
Function-specific utilities for Aurora restore Lambda functions.
This module provides utilities specific to Lambda function operations.
"""

import boto3
import psycopg2
from typing import Dict, Any, Optional, Tuple
from botocore.exceptions import ClientError
from tenacity import retry, stop_after_attempt, wait_exponential

from utils.core import get_config
from utils.aws_utils import get_client
from utils.validation import validate_db_credentials

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def test_db_connection(host: str, port: int, database: str, username: str, password: str) -> Tuple[bool, Optional[str]]:
    """
    Test database connection.
    
    Args:
        host: Database host
        port: Database port
        database: Database name
        username: Database username
        password: Database password
        
    Returns:
        Tuple[bool, Optional[str]]: (success, error_message)
    """
    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=username,
            password=password,
            connect_timeout=5
        )
        conn.close()
        return True, None
    except Exception as e:
        return False, str(e)

def get_db_connection_info(cluster_id: str, region: str) -> Dict[str, Any]:
    """
    Get database connection information for an Aurora cluster.
    
    Args:
        cluster_id: The cluster ID
        region: AWS region
        
    Returns:
        Dict[str, Any]: Connection information
    """
    try:
        rds = get_client('rds', region)
        response = rds.describe_db_clusters(DBClusterIdentifier=cluster_id)
        
        if not response['DBClusters']:
            raise ValueError(f"Cluster {cluster_id} not found")
            
        cluster = response['DBClusters'][0]
        
        return {
            'host': cluster['Endpoint'],
            'port': cluster['Port'],
            'database': cluster['DatabaseName'],
            'status': cluster['Status']
        }
    except ClientError as e:
        raise ValueError(f"Error getting cluster info: {str(e)}")

def wait_for_cluster_available(cluster_id: str, region: str, max_attempts: int = 60, delay_seconds: int = 30) -> bool:
    """
    Wait for an Aurora cluster to become available.
    
    Args:
        cluster_id: The cluster ID
        region: AWS region
        max_attempts: Maximum number of attempts
        delay_seconds: Delay between attempts
        
    Returns:
        bool: True if cluster is available
    """
    rds = get_client('rds', region)
    
    @retry(stop=stop_after_attempt(max_attempts), wait=wait_exponential(multiplier=delay_seconds, min=delay_seconds, max=300))
    def check_status() -> bool:
        response = rds.describe_db_clusters(DBClusterIdentifier=cluster_id)
        status = response['DBClusters'][0]['Status']
        
        if status == 'available':
            return True
        elif status in ['failed', 'incompatible-restore']:
            raise ValueError(f"Cluster {cluster_id} is in {status} state")
            
        raise Exception(f"Cluster {cluster_id} is in {status} state")
    
    try:
        return check_status()
    except Exception:
        return False 