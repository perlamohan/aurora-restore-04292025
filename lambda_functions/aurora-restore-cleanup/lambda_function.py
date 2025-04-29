#!/usr/bin/env python3
"""
Lambda function to clean up resources after the restore process is complete.
"""

import json
import time
from typing import Dict, Any, Optional, List

from utils.base_handler import BaseHandler
from utils.common import logger
from utils.validation import validate_required_params, validate_region, validate_cluster_id
from utils.aws_utils import get_client, handle_aws_error
from utils.state_utils import get_state, update_state, delete_state

class CleanupHandler(BaseHandler):
    """Handler for cleaning up resources after restore."""
    
    def __init__(self):
        """Initialize the cleanup handler."""
        super().__init__('cleanup')
        self.rds_client = None
        self.s3_client = None
        self.dynamodb_client = None
    
    def validate_config(self) -> None:
        """
        Validate required configuration parameters.
        
        Raises:
            ValueError: If required parameters are missing or invalid
        """
        required_params = {
            'target_region': self.config.get('target_region'),
            'target_cluster_id': self.config.get('target_cluster_id'),
            'cleanup_snapshot': self.config.get('cleanup_snapshot', True),
            'cleanup_state_data': self.config.get('cleanup_state_data', True),
            'cleanup_logs': self.config.get('cleanup_logs', True)
        }
        
        missing_params = validate_required_params(required_params)
        if missing_params:
            raise ValueError(f"Missing required parameters: {', '.join(missing_params)}")
        
        if not validate_region(self.config['target_region']):
            raise ValueError(f"Invalid target region: {self.config['target_region']}")
        
        if not validate_cluster_id(self.config['target_cluster_id']):
            raise ValueError(f"Invalid target cluster ID: {self.config['target_cluster_id']}")
    
    def initialize_clients(self) -> None:
        """
        Initialize AWS clients.
        
        Raises:
            ValueError: If required parameters are missing
        """
        if not self.config.get('target_region'):
            raise ValueError("Target region is required")
        
        self.rds_client = get_client('rds', self.config['target_region'])
        self.s3_client = get_client('s3', self.config['target_region'])
        self.dynamodb_client = get_client('dynamodb', self.config['target_region'])
    
    def get_operation_details(self, operation_id: str) -> Dict[str, Any]:
        """
        Get details of the restore operation.
        
        Args:
            operation_id: ID of the operation
            
        Returns:
            Dict[str, Any]: Operation details
            
        Raises:
            Exception: If details retrieval fails
        """
        try:
            # Get state data
            state_data = get_state(operation_id)
            
            if not state_data:
                raise ValueError(f"State data not found for operation {operation_id}")
            
            return state_data
        except Exception as e:
            logger.error(f"Error getting operation details: {str(e)}")
            raise
    
    def delete_snapshot(self, snapshot_id: str) -> bool:
        """
        Delete an RDS snapshot.
        
        Args:
            snapshot_id: ID of the snapshot to delete
            
        Returns:
            bool: True if deletion was successful, False otherwise
            
        Raises:
            Exception: If deletion fails
        """
        try:
            if not snapshot_id:
                logger.warning("No snapshot ID provided for deletion")
                return False
            
            logger.info(f"Deleting snapshot {snapshot_id}")
            
            # Delete the snapshot
            self.rds_client.delete_db_cluster_snapshot(
                DBClusterSnapshotIdentifier=snapshot_id
            )
            
            logger.info(f"Successfully initiated deletion of snapshot {snapshot_id}")
            return True
        except Exception as e:
            handle_aws_error(e, f"Error deleting snapshot {snapshot_id}")
            return False
    
    def delete_state_data(self, operation_id: str) -> bool:
        """
        Delete state data for an operation.
        
        Args:
            operation_id: ID of the operation
            
        Returns:
            bool: True if deletion was successful, False otherwise
            
        Raises:
            Exception: If deletion fails
        """
        try:
            if not operation_id:
                logger.warning("No operation ID provided for state data deletion")
                return False
            
            logger.info(f"Deleting state data for operation {operation_id}")
            
            # Delete the state data
            delete_state(operation_id)
            
            logger.info(f"Successfully deleted state data for operation {operation_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting state data for operation {operation_id}: {str(e)}")
            return False
    
    def delete_logs(self, operation_id: str) -> bool:
        """
        Delete logs for an operation.
        
        Args:
            operation_id: ID of the operation
            
        Returns:
            bool: True if deletion was successful, False otherwise
            
        Raises:
            Exception: If deletion fails
        """
        try:
            if not operation_id:
                logger.warning("No operation ID provided for log deletion")
                return False
            
            logger.info(f"Deleting logs for operation {operation_id}")
            
            # Get the log bucket and prefix from config
            log_bucket = self.config.get('log_bucket')
            log_prefix = self.config.get('log_prefix', 'aurora-restore-logs')
            
            if not log_bucket:
                logger.warning("No log bucket configured, skipping log deletion")
                return False
            
            # List objects with the operation ID prefix
            prefix = f"{log_prefix}/{operation_id}/"
            
            response = self.s3_client.list_objects_v2(
                Bucket=log_bucket,
                Prefix=prefix
            )
            
            # Delete objects
            if 'Contents' in response:
                for obj in response['Contents']:
                    self.s3_client.delete_object(
                        Bucket=log_bucket,
                        Key=obj['Key']
                    )
                
                logger.info(f"Successfully deleted logs for operation {operation_id}")
                return True
            else:
                logger.info(f"No logs found for operation {operation_id}")
                return True
        except Exception as e:
            handle_aws_error(e, f"Error deleting logs for operation {operation_id}")
            return False
    
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
            
            # Initialize clients
            self.initialize_clients()
            
            # Get operation details
            operation_details = self.get_operation_details(operation_id)
            
            # Initialize cleanup results
            cleanup_results = {
                'snapshot_deleted': False,
                'state_data_deleted': False,
                'logs_deleted': False
            }
            
            # Delete snapshot if configured
            if self.config.get('cleanup_snapshot', True):
                snapshot_id = operation_details.get('snapshot_id')
                if snapshot_id:
                    cleanup_results['snapshot_deleted'] = self.delete_snapshot(snapshot_id)
            
            # Delete state data if configured
            if self.config.get('cleanup_state_data', True):
                cleanup_results['state_data_deleted'] = self.delete_state_data(operation_id)
            
            # Delete logs if configured
            if self.config.get('cleanup_logs', True):
                cleanup_results['logs_deleted'] = self.delete_logs(operation_id)
            
            # Log audit
            self.log_audit(operation_id, 'SUCCESS', {
                'target_cluster_id': operation_details.get('target_cluster_id'),
                'cleanup_results': cleanup_results
            })
            
            # Update metrics
            self.update_metrics(operation_id, 'cleanup_completed', 1)
            
            return self.create_response(operation_id, {
                'message': f"Successfully completed cleanup for operation {operation_id}",
                'target_cluster_id': operation_details.get('target_cluster_id'),
                'cleanup_results': cleanup_results,
                'next_step': None
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
    handler = CleanupHandler()
    return handler.execute(event, context) 