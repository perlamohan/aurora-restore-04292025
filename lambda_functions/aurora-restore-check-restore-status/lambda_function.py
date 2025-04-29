#!/usr/bin/env python3
"""
Lambda function to check the status of a cluster restore operation.
"""

import json
import time
from typing import Dict, Any, Optional, Tuple

from utils.base_handler import BaseHandler
from utils.common import logger
from utils.validation import validate_required_params, validate_region, validate_cluster_id
from utils.aws_utils import get_client, handle_aws_error
from utils.state_utils import trigger_next_step

class CheckRestoreStatusHandler(BaseHandler):
    """Handler for checking cluster restore status."""
    
    def __init__(self):
        """Initialize the check restore status handler."""
        super().__init__('check_restore_status')
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
    
    def check_cluster_status(self, cluster_id: str) -> Dict[str, Any]:
        """
        Check the status of a restored cluster.
        
        Args:
            cluster_id: ID of the cluster to check
            
        Returns:
            Dict[str, Any]: Cluster details
            
        Raises:
            Exception: If check fails
        """
        try:
            response = self.rds_client.describe_db_clusters(
                DBClusterIdentifier=cluster_id
            )
            
            if not response['DBClusters']:
                raise ValueError(f"Cluster {cluster_id} not found")
            
            return response['DBClusters'][0]
        except Exception as e:
            if 'DBClusterNotFoundFault' in str(e):
                raise ValueError(f"Cluster {cluster_id} not found")
            
            handle_aws_error(e, f"Error checking status of cluster {cluster_id}")
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
            
            # Get cluster details
            cluster_id = self.config['target_cluster_id']
            
            # Check cluster status
            cluster = self.check_cluster_status(cluster_id)
            status = cluster['Status']
            
            # Save state
            state_data = {
                'target_cluster_id': cluster_id,
                'cluster_status': status,
                'cluster_arn': cluster['DBClusterArn'],
                'vpc_id': cluster['VpcId'],
                'db_subnet_group': cluster['DBSubnetGroup'],
                'status': 'checking',
                'success': True
            }
            
            self.save_state(state_data)
            
            # Log audit
            self.log_audit(operation_id, 'SUCCESS', {
                'target_cluster_id': cluster_id,
                'cluster_status': status
            })
            
            # Update metrics
            self.update_metrics(operation_id, 'cluster_status_check', 1)
            
            # Check if restore is complete
            if status == 'available':
                # Restore is complete, trigger next step
                trigger_next_step(operation_id, 'setup_db_users', state_data)
                
                return self.create_response(operation_id, {
                    'message': f"Cluster {cluster_id} restore completed",
                    'target_cluster_id': cluster_id,
                    'cluster_status': status,
                    'next_step': 'setup_db_users'
                })
            elif status in ['failed', 'incompatible-restore']:
                # Restore failed
                error_message = f"Cluster {cluster_id} restore failed with status {status}"
                logger.error(error_message)
                
                # Update state with error
                state_data.update({
                    'status': 'failed',
                    'success': False,
                    'error': error_message
                })
                
                self.save_state(state_data)
                
                # Log audit with failure
                self.log_audit(operation_id, 'FAILED', {
                    'target_cluster_id': cluster_id,
                    'cluster_status': status,
                    'error': error_message
                })
                
                # Update metrics with failure
                self.update_metrics(operation_id, 'restore_failure', 1)
                
                return self.create_response(operation_id, {
                    'message': error_message,
                    'target_cluster_id': cluster_id,
                    'cluster_status': status,
                    'next_step': None
                }, 500)
            else:
                # Restore still in progress
                return self.create_response(operation_id, {
                    'message': f"Cluster {cluster_id} restore in progress (status: {status})",
                    'target_cluster_id': cluster_id,
                    'cluster_status': status,
                    'next_step': 'check_restore_status'
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
    handler = CheckRestoreStatusHandler()
    return handler.execute(event, context) 