#!/usr/bin/env python3
"""
Lambda function to check if the daily snapshot exists in the source account.
"""

import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple

from utils.base_handler import BaseHandler
from utils.common import logger
from utils.validation import validate_required_params, validate_region, validate_snapshot_name
from utils.aws_utils import get_client, handle_aws_error
from utils.state_utils import trigger_next_step

class SnapshotCheckHandler(BaseHandler):
    """Handler for checking Aurora snapshots."""
    
    def __init__(self):
        """Initialize the snapshot check handler."""
        super().__init__('snapshot_check')
        self.rds_client = None
    
    def validate_config(self) -> None:
        """
        Validate required configuration parameters.
        
        Raises:
            ValueError: If required parameters are missing or invalid
        """
        required_params = {
            'source_region': self.config.get('source_region'),
            'source_cluster_id': self.config.get('source_cluster_id')
        }
        
        missing_params = validate_required_params(required_params)
        if missing_params:
            raise ValueError(f"Missing required parameters: {', '.join(missing_params)}")
        
        if not validate_region(self.config['source_region']):
            raise ValueError(f"Invalid source region: {self.config['source_region']}")
    
    def get_target_date(self, event: Dict[str, Any]) -> datetime.date:
        """
        Get target date from event or use yesterday.
        
        Args:
            event: Lambda event
            
        Returns:
            datetime.date: Target date
        """
        if event and isinstance(event, dict):
            if 'target_date' in event:
                try:
                    return datetime.strptime(event['target_date'], '%Y-%m-%d').date()
                except ValueError:
                    logger.warning(f"Invalid target_date format: {event['target_date']}, using yesterday")
            
            if 'body' in event and isinstance(event['body'], dict) and 'target_date' in event['body']:
                try:
                    return datetime.strptime(event['body']['target_date'], '%Y-%m-%d').date()
                except ValueError:
                    logger.warning(f"Invalid target_date format: {event['body']['target_date']}, using yesterday")
        
        # Default to yesterday
        return (datetime.now() - timedelta(days=1)).date()
    
    def get_snapshot_name(self, target_date: datetime.date) -> str:
        """
        Generate snapshot name based on target date.
        
        Args:
            target_date: Target date
            
        Returns:
            str: Snapshot name
        """
        snapshot_prefix = self.config.get('snapshot_prefix', 'aurora-snapshot')
        cluster_id = self.config.get('source_cluster_id', '')
        
        # Format: prefix-cluster-id-YYYY-MM-DD
        snapshot_name = f"{snapshot_prefix}-{cluster_id}-{target_date.strftime('%Y-%m-%d')}"
        
        # Validate snapshot name
        if not validate_snapshot_name(snapshot_name):
            raise ValueError(f"Invalid snapshot name: {snapshot_name}")
        
        return snapshot_name
    
    def initialize_rds_client(self) -> None:
        """
        Initialize RDS client.
        
        Raises:
            ValueError: If source region is not set
        """
        if not self.config.get('source_region'):
            raise ValueError("Source region is required")
        
        self.rds_client = get_client('rds', self.config['source_region'])
    
    def check_snapshot(self, snapshot_name: str) -> Tuple[bool, Optional[Dict]]:
        """
        Check if snapshot exists.
        
        Args:
            snapshot_name: Name of the snapshot to check
            
        Returns:
            Tuple[bool, Optional[Dict]]: (exists, snapshot_details)
        """
        try:
            response = self.rds_client.describe_db_cluster_snapshots(
                DBClusterSnapshotIdentifier=snapshot_name
            )
            
            if response['DBClusterSnapshots']:
                return True, response['DBClusterSnapshots'][0]
            return False, None
        except Exception as e:
            handle_aws_error(e, f"Error checking snapshot {snapshot_name}")
            return False, None
    
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
            
            # Get target date
            target_date = self.get_target_date(event)
            logger.info(f"Target date: {target_date}")
            
            # Generate snapshot name
            snapshot_name = self.get_snapshot_name(target_date)
            logger.info(f"Snapshot name: {snapshot_name}")
            
            # Initialize RDS client
            self.initialize_rds_client()
            
            # Check if snapshot exists
            snapshot_exists, snapshot_details = self.check_snapshot(snapshot_name)
            
            # Save state
            state_data = {
                'target_date': target_date.strftime('%Y-%m-%d'),
                'snapshot_name': snapshot_name,
                'snapshot_exists': snapshot_exists
            }
            
            if snapshot_details:
                state_data['snapshot_arn'] = snapshot_details.get('DBClusterSnapshotArn')
                state_data['snapshot_status'] = snapshot_details.get('Status')
                state_data['snapshot_type'] = snapshot_details.get('SnapshotType')
            
            self.save_initial_state(operation_id, state_data)
            
            # Log audit
            self.log_audit(operation_id, 'SUCCESS', {
                'target_date': target_date.strftime('%Y-%m-%d'),
                'snapshot_name': snapshot_name,
                'snapshot_exists': snapshot_exists
            })
            
            # Update metrics
            self.update_metrics(operation_id, 'snapshot_check', 1)
            if snapshot_exists:
                self.update_metrics(operation_id, 'snapshot_found', 1)
            else:
                self.update_metrics(operation_id, 'snapshot_not_found', 1)
            
            # Trigger next step if snapshot exists
            if snapshot_exists:
                trigger_next_step(operation_id, 'copy_snapshot', state_data)
                return self.create_response(operation_id, {
                    'message': f"Snapshot {snapshot_name} exists, triggering copy",
                    'snapshot_name': snapshot_name,
                    'snapshot_arn': snapshot_details.get('DBClusterSnapshotArn'),
                    'next_step': 'copy_snapshot'
                })
            else:
                return self.create_response(operation_id, {
                    'message': f"Snapshot {snapshot_name} does not exist",
                    'snapshot_name': snapshot_name,
                    'next_step': None
                })
        except Exception as e:
            return self.handle_error(operation_id, e, {
                'target_date': target_date.strftime('%Y-%m-%d') if 'target_date' in locals() else None,
                'snapshot_name': snapshot_name if 'snapshot_name' in locals() else None
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
    handler = SnapshotCheckHandler()
    return handler.execute(event, context) 