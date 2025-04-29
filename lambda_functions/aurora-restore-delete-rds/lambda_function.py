#!/usr/bin/env python3
"""
Lambda function to delete an existing RDS cluster.
"""

import json
import time
from typing import Dict, Any, Optional, Tuple

from utils.base_handler import BaseHandler
from utils.common import logger
from utils.validation import validate_required_params, validate_region, validate_cluster_id
from utils.aws_utils import get_client, handle_aws_error
from utils.state_utils import trigger_next_step

class DeleteRdsHandler(BaseHandler):
    """Handler for deleting RDS clusters."""
    
    def __init__(self):
        """Initialize the delete RDS handler."""
        super().__init__('delete_rds')
        self.rds_client = None
    
    def validate_config(self) -> None:
        """
        Validate required configuration parameters.
        
        Raises:
            ValueError: If required parameters are missing or invalid
        """
        required_params = {
            'target_region': self.config.get('target_region'),
            'target_cluster_id': self.config.get('target_cluster_id')
        }
        
        missing_params = validate_required_params(required_params)
        if missing_params:
            raise ValueError(f"Missing required parameters: {', '.join(missing_params)}")
        
        if not validate_region(self.config['target_region']):
            raise ValueError(f"Invalid target region: {self.config['target_region']}")
        
        if not validate_cluster_id(self.config['target_cluster_id']):
            raise ValueError(f"Invalid target cluster ID: {self.config['target_cluster_id']}")
    
    def initialize_rds_client(self) -> None:
        """
        Initialize RDS client for target region.
        
        Raises:
            ValueError: If target region is not set
        """
        if not self.config.get('target_region'):
            raise ValueError("Target region is required")
        
        self.rds_client = get_client('rds', self.config['target_region'])
    
    def check_cluster_exists(self, cluster_id: str) -> bool:
        """
        Check if the RDS cluster exists.
        
        Args:
            cluster_id: ID of the cluster to check
            
        Returns:
            bool: True if cluster exists, False otherwise
            
        Raises:
            Exception: If check fails
        """
        try:
            response = self.rds_client.describe_db_clusters(
                DBClusterIdentifier=cluster_id
            )
            
            return len(response['DBClusters']) > 0
        except Exception as e:
            if 'DBClusterNotFoundFault' in str(e):
                return False
            
            handle_aws_error(e, f"Error checking if cluster {cluster_id} exists")
            raise
    
    def delete_cluster(self, cluster_id: str) -> Dict[str, Any]:
        """
        Delete an RDS cluster.
        
        Args:
            cluster_id: ID of the cluster to delete
            
        Returns:
            Dict[str, Any]: Delete response
            
        Raises:
            Exception: If deletion fails
        """
        try:
            # First, get the cluster details to check if it's in a deletable state
            response = self.rds_client.describe_db_clusters(
                DBClusterIdentifier=cluster_id
            )
            
            if not response['DBClusters']:
                raise ValueError(f"Cluster {cluster_id} not found")
            
            cluster = response['DBClusters'][0]
            
            # Check if cluster is in a deletable state
            if cluster['Status'] not in ['available', 'stopped', 'failed']:
                raise ValueError(f"Cluster {cluster_id} is in state {cluster['Status']}, cannot delete")
            
            # Delete the cluster
            delete_response = self.rds_client.delete_db_cluster(
                DBClusterIdentifier=cluster_id,
                SkipFinalSnapshot=True  # Skip final snapshot to speed up deletion
            )
            
            return delete_response['DBCluster']
        except Exception as e:
            handle_aws_error(e, f"Error deleting cluster {cluster_id}")
            raise
    
    def process(self, event: Dict[str, Any], context: Any) -> Dict[str, Any]:
        """
        Process the Lambda event.
        
        Args:
            event: Lambda event
            context: Lambda context
            
        Returns:
            Dict[str, Any]: Lambda response
        """
        try:
            # Get operation ID
            operation_id = self.get_operation_id(event)
            
            # Validate configuration
            self.validate_config()
            
            # Initialize RDS client
            self.initialize_rds_client()
            
            # Get cluster ID
            cluster_id = self.config['target_cluster_id']
            
            # Check if cluster exists
            cluster_exists = self.check_cluster_exists(cluster_id)
            
            if not cluster_exists:
                # Cluster doesn't exist, no need to delete
                logger.info(f"Cluster {cluster_id} does not exist, no need to delete")
                
                # Save state
                state_data = {
                    'target_cluster_id': cluster_id,
                    'cluster_exists': False,
                    'delete_status': 'skipped',
                    'status': 'completed',
                    'success': True
                }
                
                self.save_state(state_data)
                
                # Log audit
                self.log_audit(operation_id, 'SUCCESS', {
                    'target_cluster_id': cluster_id,
                    'message': 'Cluster does not exist, no need to delete'
                })
                
                # Update metrics
                self.update_metrics(operation_id, 'cluster_not_found', 1)
                
                # Trigger next step
                trigger_next_step(operation_id, 'restore_snapshot', state_data)
                
                return self.create_response(operation_id, {
                    'message': f"Cluster {cluster_id} does not exist, no need to delete",
                    'target_cluster_id': cluster_id,
                    'next_step': 'restore_snapshot'
                })
            
            # Delete the cluster
            delete_response = self.delete_cluster(cluster_id)
            
            # Save state
            state_data = {
                'target_cluster_id': cluster_id,
                'cluster_exists': True,
                'delete_status': delete_response['Status'],
                'status': 'deleting',
                'success': True
            }
            
            self.save_state(state_data)
            
            # Log audit
            self.log_audit(operation_id, 'SUCCESS', {
                'target_cluster_id': cluster_id,
                'delete_status': delete_response['Status']
            })
            
            # Update metrics
            self.update_metrics(operation_id, 'cluster_deleted', 1)
            
            # Trigger next step
            trigger_next_step(operation_id, 'restore_snapshot', state_data)
            
            return self.create_response(operation_id, {
                'message': f"Cluster {cluster_id} deletion initiated",
                'target_cluster_id': cluster_id,
                'delete_status': delete_response['Status'],
                'next_step': 'restore_snapshot'
            })
        except Exception as e:
            return self.handle_error(operation_id, e, {
                'target_cluster_id': self.config.get('target_cluster_id')
            })

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler function.
    
    Args:
        event: Lambda event
        context: Lambda context
        
    Returns:
        Dict[str, Any]: Lambda response
    """
    handler = DeleteRdsHandler()
    return handler.execute(event, context) 