#!/usr/bin/env python3
"""
Lambda function to copy a snapshot from source to target region.
"""

import json
from typing import Dict, Any, Optional, Tuple

from utils.base_handler import BaseHandler
from utils.common import logger
from utils.validation import validate_required_params, validate_region, validate_snapshot_name
from utils.aws_utils import get_client, handle_aws_error
from utils.state_utils import trigger_next_step

class CopySnapshotHandler(BaseHandler):
    """Handler for copying Aurora snapshots."""
    
    def __init__(self):
        """Initialize the copy snapshot handler."""
        super().__init__('copy_snapshot')
        self.source_rds_client = None
        self.target_rds_client = None
    
    def validate_config(self) -> None:
        """
        Validate required configuration parameters.
        
        Raises:
            ValueError: If required parameters are missing or invalid
        """
        required_params = {
            'source_region': self.config.get('source_region'),
            'target_region': self.config.get('target_region'),
            'source_cluster_id': self.config.get('source_cluster_id')
        }
        
        missing_params = validate_required_params(required_params)
        if missing_params:
            raise ValueError(f"Missing required parameters: {', '.join(missing_params)}")
        
        if not validate_region(self.config['source_region']):
            raise ValueError(f"Invalid source region: {self.config['source_region']}")
        
        if not validate_region(self.config['target_region']):
            raise ValueError(f"Invalid target region: {self.config['target_region']}")
    
    def validate_snapshot_params(self, event: Dict[str, Any]) -> None:
        """
        Validate snapshot parameters from event.
        
        Args:
            event: Lambda event
            
        Raises:
            ValueError: If required snapshot parameters are missing or invalid
        """
        required_params = {
            'snapshot_name': event.get('snapshot_name'),
            'snapshot_arn': event.get('snapshot_arn')
        }
        
        missing_params = validate_required_params(required_params)
        if missing_params:
            raise ValueError(f"Missing required snapshot parameters: {', '.join(missing_params)}")
        
        if not validate_snapshot_name(event['snapshot_name']):
            raise ValueError(f"Invalid snapshot name: {event['snapshot_name']}")
    
    def initialize_rds_clients(self) -> None:
        """
        Initialize RDS clients for source and target regions.
        
        Raises:
            ValueError: If regions are not set
        """
        if not self.config.get('source_region'):
            raise ValueError("Source region is required")
        
        if not self.config.get('target_region'):
            raise ValueError("Target region is required")
        
        self.source_rds_client = get_client('rds', self.config['source_region'])
        self.target_rds_client = get_client('rds', self.config['target_region'])
    
    def get_snapshot_details(self, snapshot_arn: str) -> Dict[str, Any]:
        """
        Get snapshot details from source region.
        
        Args:
            snapshot_arn: ARN of the snapshot
            
        Returns:
            Dict[str, Any]: Snapshot details
            
        Raises:
            Exception: If snapshot details cannot be retrieved
        """
        try:
            response = self.source_rds_client.describe_db_cluster_snapshots(
                DBClusterSnapshotIdentifier=snapshot_arn
            )
            
            if not response['DBClusterSnapshots']:
                raise ValueError(f"Snapshot {snapshot_arn} not found")
            
            return response['DBClusterSnapshots'][0]
        except Exception as e:
            handle_aws_error(e, f"Error getting snapshot details for {snapshot_arn}")
            raise
    
    def copy_snapshot(self, snapshot_arn: str, target_snapshot_name: str) -> Dict[str, Any]:
        """
        Copy snapshot to target region.
        
        Args:
            snapshot_arn: ARN of the source snapshot
            target_snapshot_name: Name for the target snapshot
            
        Returns:
            Dict[str, Any]: Copy snapshot response
            
        Raises:
            Exception: If snapshot copy fails
        """
        try:
            response = self.target_rds_client.copy_db_cluster_snapshot(
                SourceDBClusterSnapshotIdentifier=snapshot_arn,
                TargetDBClusterSnapshotIdentifier=target_snapshot_name,
                SourceRegion=self.config['source_region'],
                KmsKeyId=self.config.get('kms_key_id')
            )
            
            return response['DBClusterSnapshot']
        except Exception as e:
            handle_aws_error(e, f"Error copying snapshot {snapshot_arn} to {target_snapshot_name}")
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
            
            # Validate snapshot parameters
            self.validate_snapshot_params(event)
            
            # Initialize RDS clients
            self.initialize_rds_clients()
            
            # Get snapshot details
            snapshot_details = self.get_snapshot_details(event['snapshot_arn'])
            
            # Generate target snapshot name
            target_snapshot_name = f"{event['snapshot_name']}-copy"
            
            # Copy snapshot
            copy_response = self.copy_snapshot(event['snapshot_arn'], target_snapshot_name)
            
            # Save state
            state_data = {
                'source_snapshot_name': event['snapshot_name'],
                'source_snapshot_arn': event['snapshot_arn'],
                'target_snapshot_name': target_snapshot_name,
                'target_snapshot_arn': copy_response['DBClusterSnapshotArn'],
                'copy_status': copy_response['Status']
            }
            
            self.save_initial_state(operation_id, state_data)
            
            # Log audit
            self.log_audit(operation_id, 'SUCCESS', {
                'source_snapshot_name': event['snapshot_name'],
                'target_snapshot_name': target_snapshot_name,
                'copy_status': copy_response['Status']
            })
            
            # Update metrics
            self.update_metrics(operation_id, 'snapshot_copy', 1)
            
            # Trigger next step
            trigger_next_step(operation_id, 'check_copy_status', state_data)
            
            return self.create_response(operation_id, {
                'message': f"Snapshot copy initiated: {target_snapshot_name}",
                'source_snapshot_name': event['snapshot_name'],
                'target_snapshot_name': target_snapshot_name,
                'target_snapshot_arn': copy_response['DBClusterSnapshotArn'],
                'copy_status': copy_response['Status'],
                'next_step': 'check_copy_status'
            })
        except Exception as e:
            return self.handle_error(operation_id, e, {
                'source_snapshot_name': event.get('snapshot_name'),
                'source_snapshot_arn': event.get('snapshot_arn')
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
    handler = CopySnapshotHandler()
    return handler.execute(event, context) 