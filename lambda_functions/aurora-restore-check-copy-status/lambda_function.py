#!/usr/bin/env python3
"""
Lambda function to check the status of a snapshot copy operation.
"""

import json
import time
from typing import Dict, Any, Optional, Tuple

from utils.base_handler import BaseHandler
from utils.common import logger
from utils.validation import validate_required_params, validate_region, validate_snapshot_name
from utils.aws_utils import get_client, handle_aws_error
from utils.state_utils import trigger_next_step

class CheckCopyStatusHandler(BaseHandler):
    """Handler for checking snapshot copy status."""
    
    def __init__(self):
        """Initialize the check copy status handler."""
        super().__init__('check_copy_status')
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
    
    def validate_snapshot_params(self, event: Dict[str, Any]) -> None:
        """
        Validate snapshot parameters from event.
        
        Args:
            event: Lambda event
            
        Raises:
            ValueError: If required snapshot parameters are missing or invalid
        """
        required_params = {
            'target_snapshot_name': event.get('target_snapshot_name'),
            'target_snapshot_arn': event.get('target_snapshot_arn')
        }
        
        missing_params = validate_required_params(required_params)
        if missing_params:
            raise ValueError(f"Missing required snapshot parameters: {', '.join(missing_params)}")
        
        if not validate_snapshot_name(event['target_snapshot_name']):
            raise ValueError(f"Invalid target snapshot name: {event['target_snapshot_name']}")
    
    def initialize_rds_client(self) -> None:
        """
        Initialize RDS client for target region.
        
        Raises:
            ValueError: If target region is not set
        """
        if not self.config.get('target_region'):
            raise ValueError("Target region is required")
        
        self.rds_client = get_client('rds', self.config['target_region'])
    
    def check_copy_status(self, snapshot_arn: str) -> Dict[str, Any]:
        """
        Check the status of a snapshot copy operation.
        
        Args:
            snapshot_arn: ARN of the target snapshot
            
        Returns:
            Dict[str, Any]: Snapshot details
            
        Raises:
            Exception: If status check fails
        """
        try:
            response = self.rds_client.describe_db_cluster_snapshots(
                DBClusterSnapshotIdentifier=snapshot_arn
            )
            
            if not response['DBClusterSnapshots']:
                raise ValueError(f"Snapshot {snapshot_arn} not found")
            
            return response['DBClusterSnapshots'][0]
        except Exception as e:
            handle_aws_error(e, f"Error checking copy status for {snapshot_arn}")
            raise
    
    def handle_same_region_case(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle case where source and target regions are the same.
        
        Args:
            event: Lambda event
            
        Returns:
            Dict[str, Any]: Response
        """
        # If regions are the same, the copy is already complete
        state_data = {
            'source_snapshot_name': event.get('source_snapshot_name'),
            'source_snapshot_arn': event.get('source_snapshot_arn'),
            'target_snapshot_name': event.get('target_snapshot_name'),
            'target_snapshot_arn': event.get('target_snapshot_arn'),
            'copy_status': 'available',
            'status': 'completed',
            'success': True
        }
        
        # Save state
        self.save_state(state_data)
        
        # Trigger next step
        trigger_next_step(
            self.operation_id,
            'delete_rds',
            state_data
        )
        
        return {
            'message': 'No need to copy snapshot, regions are the same',
            'snapshot_name': event.get('target_snapshot_name'),
            'source_region': self.config.get('source_region'),
            'target_region': self.config.get('target_region'),
            'next_step': 'delete_rds'
        }
    
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
            
            # Check if source and target regions are the same
            if self.config.get('source_region') == self.config.get('target_region'):
                return self.handle_same_region_case(event)
            
            # Initialize RDS client
            self.initialize_rds_client()
            
            # Check copy status
            snapshot_details = self.check_copy_status(event['target_snapshot_arn'])
            
            # Update state
            state_data = {
                'source_snapshot_name': event.get('source_snapshot_name'),
                'source_snapshot_arn': event.get('source_snapshot_arn'),
                'target_snapshot_name': event.get('target_snapshot_name'),
                'target_snapshot_arn': event.get('target_snapshot_arn'),
                'copy_status': snapshot_details['Status'],
                'status': 'copying' if snapshot_details['Status'] == 'copying' else 'completed',
                'success': True
            }
            
            self.save_state(state_data)
            
            # Log audit
            self.log_audit(operation_id, 'SUCCESS', {
                'source_snapshot_name': event.get('source_snapshot_name'),
                'target_snapshot_name': event.get('target_snapshot_name'),
                'copy_status': snapshot_details['Status']
            })
            
            # Update metrics
            self.update_metrics(operation_id, 'copy_status_check', 1)
            
            # Check if copy is complete
            if snapshot_details['Status'] == 'available':
                # Trigger next step
                trigger_next_step(
                    operation_id,
                    'delete_rds',
                    state_data
                )
                
                return self.create_response(operation_id, {
                    'message': 'Snapshot copy completed',
                    'snapshot_name': event.get('target_snapshot_name'),
                    'source_region': self.config.get('source_region'),
                    'target_region': self.config.get('target_region'),
                    'next_step': 'delete_rds'
                })
            elif snapshot_details['Status'] == 'failed':
                # Handle copy failure
                error_message = f"Snapshot copy failed: {snapshot_details.get('Status', 'unknown status')}"
                logger.error(error_message)
                
                # Update state with failure
                state_data['status'] = 'failed'
                state_data['success'] = False
                state_data['error'] = error_message
                
                self.save_state(state_data)
                
                # Log audit with failure
                self.log_audit(operation_id, 'FAILED', {
                    'source_snapshot_name': event.get('source_snapshot_name'),
                    'target_snapshot_name': event.get('target_snapshot_name'),
                    'error': error_message
                })
                
                # Update metrics with failure
                self.update_metrics(operation_id, 'copy_failure', 1)
                
                return self.create_response(operation_id, {
                    'message': error_message,
                    'snapshot_name': event.get('target_snapshot_name'),
                    'source_region': self.config.get('source_region'),
                    'target_region': self.config.get('target_region'),
                    'next_step': None
                }, 500)
            else:
                # Copy still in progress, check again later
                delay_seconds = 60  # Check again after 60 seconds
                
                # Trigger next step with delay
                trigger_next_step(
                    operation_id,
                    'check_copy_status',
                    state_data,
                    delay_seconds=delay_seconds
                )
                
                return self.create_response(operation_id, {
                    'message': f"Snapshot copy in progress, checking again in {delay_seconds} seconds",
                    'snapshot_name': event.get('target_snapshot_name'),
                    'source_region': self.config.get('source_region'),
                    'target_region': self.config.get('target_region'),
                    'next_step': 'check_copy_status'
                })
        except Exception as e:
            return self.handle_error(operation_id, e, {
                'source_snapshot_name': event.get('source_snapshot_name'),
                'target_snapshot_name': event.get('target_snapshot_name')
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
    handler = CheckCopyStatusHandler()
    return handler.execute(event, context) 