#!/usr/bin/env python3
"""
Lambda function to archive a snapshot after a successful restore.
"""

import time
from typing import Dict, Any, Optional, Tuple

from utils.base_handler import BaseHandler
from utils.common import logger
from utils.validation import validate_required_params, validate_region
from utils.aws_utils import get_client, handle_aws_error

class ArchiveSnapshotHandler(BaseHandler):
    """Handler for archiving a snapshot after a successful restore."""
    
    def __init__(self):
        """Initialize the archive snapshot handler."""
        super().__init__('archive_snapshot')
        self.rds_client = None
    
    def validate_config(self) -> None:
        """
        Validate required configuration parameters.
        
        Raises:
            ValueError: If required parameters are missing or invalid
        """
        required_params = {
            'target_region': self.config.get('target_region')
        }
        
        missing_params = validate_required_params(required_params)
        if missing_params:
            raise ValueError(f"Missing required parameters: {', '.join(missing_params)}")
        
        if not validate_region(self.config['target_region']):
            raise ValueError(f"Invalid target region: {self.config['target_region']}")
    
    def get_snapshot_details(self, event: Dict[str, Any]) -> Tuple[str, str]:
        """
        Get snapshot details from event or state.
        
        Args:
            event: Lambda event
            
        Returns:
            Tuple[str, str]: Target snapshot name and region
            
        Raises:
            ValueError: If snapshot details are missing
        """
        state = self.load_state()
        
        target_snapshot_name = state.get('target_snapshot_name')
        target_region = (
            state.get('target_region') or 
            event.get('target_region') or 
            self.config.get('target_region')
        )
        
        if not target_snapshot_name:
            raise ValueError("Target snapshot name is required")
        
        if not target_region:
            raise ValueError("Target region is required")
        
        return target_snapshot_name, target_region
    
    def initialize_rds_client(self, region: str) -> None:
        """
        Initialize RDS client for target region.
        
        Args:
            region: AWS region
            
        Raises:
            Exception: If client initialization fails
        """
        try:
            self.rds_client = get_client('rds', region_name=region)
        except Exception as e:
            raise Exception(f"Failed to create RDS client for region {region}: {str(e)}")
    
    def check_snapshot_exists(self, snapshot_name: str) -> bool:
        """
        Check if the snapshot exists.
        
        Args:
            snapshot_name: Name of the snapshot to check
            
        Returns:
            bool: True if snapshot exists, False otherwise
            
        Raises:
            Exception: If check fails
        """
        try:
            logger.info(f"Checking if snapshot {snapshot_name} exists")
            response = self.rds_client.describe_db_cluster_snapshots(
                DBClusterSnapshotIdentifier=snapshot_name
            )
            
            return bool(response.get('DBClusterSnapshots'))
            
        except Exception as e:
            if 'DBClusterSnapshotNotFoundFault' in str(e):
                logger.info(f"Snapshot {snapshot_name} does not exist")
                return False
            handle_aws_error(e, self.operation_id, self.step_name)
            raise
    
    def delete_snapshot(self, snapshot_name: str) -> None:
        """
        Delete the snapshot.
        
        Args:
            snapshot_name: Name of the snapshot to delete
            
        Raises:
            Exception: If deletion fails
        """
        try:
            logger.info(f"Deleting snapshot {snapshot_name}")
            self.rds_client.delete_db_cluster_snapshot(
                DBClusterSnapshotIdentifier=snapshot_name
            )
        except Exception as e:
            handle_aws_error(e, self.operation_id, self.step_name)
            raise
    
    def handle_snapshot_not_found(self, snapshot_name: str, region: str) -> Dict[str, Any]:
        """
        Handle case where snapshot is not found.
        
        Args:
            snapshot_name: Name of the snapshot
            region: AWS region
            
        Returns:
            Dict[str, Any]: Response
        """
        # Update state
        state = {
            'target_snapshot_name': snapshot_name,
            'target_region': region,
            'archive_status': 'skipped',
            'success': True
        }
        
        self.save_state(state)
        
        return {
            'message': f"Snapshot {snapshot_name} does not exist, no action needed",
            'target_snapshot_name': snapshot_name,
            'target_region': region,
            'archive_status': 'skipped'
        }
    
    def handle_snapshot_deleted(self, snapshot_name: str, region: str) -> Dict[str, Any]:
        """
        Handle case where snapshot is successfully deleted.
        
        Args:
            snapshot_name: Name of the snapshot
            region: AWS region
            
        Returns:
            Dict[str, Any]: Response
        """
        # Update state
        state = {
            'target_snapshot_name': snapshot_name,
            'target_region': region,
            'archive_status': 'deleted',
            'success': True
        }
        
        self.save_state(state)
        
        return {
            'message': f"Snapshot {snapshot_name} deleted successfully",
            'target_snapshot_name': snapshot_name,
            'target_region': region,
            'archive_status': 'deleted'
        }
    
    def process(self, event: Dict[str, Any], context: Any) -> Dict[str, Any]:
        """
        Process the archive snapshot request.
        
        Args:
            event: Lambda event
            context: Lambda context
            
        Returns:
            dict: Processing result
        """
        start_time = time.time()
        
        try:
            # Validate configuration
            self.validate_config()
            
            # Get snapshot details
            target_snapshot_name, target_region = self.get_snapshot_details(event)
            
            # Initialize RDS client
            self.initialize_rds_client(target_region)
            
            # Check if snapshot exists
            snapshot_exists = self.check_snapshot_exists(target_snapshot_name)
            
            if not snapshot_exists:
                result = self.handle_snapshot_not_found(target_snapshot_name, target_region)
                
                # Update metrics
                duration = time.time() - start_time
                self.update_metrics('archive_snapshot_duration', duration, 'Seconds')
                
                return result
            
            # Delete the snapshot
            self.delete_snapshot(target_snapshot_name)
            
            result = self.handle_snapshot_deleted(target_snapshot_name, target_region)
            
            # Update metrics
            duration = time.time() - start_time
            self.update_metrics('archive_snapshot_duration', duration, 'Seconds')
            
            return result
            
        except Exception as e:
            # Update metrics for failure
            duration = time.time() - start_time
            self.update_metrics('archive_snapshot_duration', duration, 'Seconds')
            self.update_metrics('archive_snapshot_failures', 1, 'Count')
            
            raise

# Initialize handler
handler = ArchiveSnapshotHandler()

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for archiving a snapshot after a successful restore.
    
    Args:
        event: Lambda event
        context: Lambda context
        
    Returns:
        dict: Response
    """
    return handler.execute(event, context) 