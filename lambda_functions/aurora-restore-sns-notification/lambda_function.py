#!/usr/bin/env python3
"""
Lambda function to send SNS notification about the restore process completion.
"""

import json
import time
from typing import Dict, Any, Optional

from utils.base_handler import BaseHandler
from utils.common import logger
from utils.validation import validate_required_params, validate_region
from utils.aws_utils import handle_aws_error

class SNSNotificationHandler(BaseHandler):
    """Handler for sending SNS notifications about restore process completion."""
    
    def __init__(self):
        """Initialize the SNS notification handler."""
        super().__init__('sns_notification')
    
    def validate_config(self) -> None:
        """
        Validate required configuration parameters.
        
        Raises:
            ValueError: If required parameters are missing or invalid
        """
        required_params = {
            'target_region': self.config.get('target_region'),
            'sns_topic_arn': self.config.get('sns_topic_arn')
        }
        
        missing_params = validate_required_params(required_params)
        if missing_params:
            raise ValueError(f"Missing required parameters: {', '.join(missing_params)}")
        
        if not validate_region(self.config['target_region']):
            raise ValueError(f"Invalid target region: {self.config['target_region']}")
    
    def get_notification_details(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get notification details from state or event.
        
        Args:
            event: Lambda event
            
        Returns:
            Dict[str, Any]: Notification details
            
        Raises:
            ValueError: If required details are missing
        """
        state = self.load_state()
        
        details = {
            'target_cluster_id': state.get('target_cluster_id', self.config.get('target_cluster_id')),
            'target_region': state.get('target_region', self.config.get('target_region')),
            'cluster_endpoint': state.get('cluster_endpoint'),
            'cluster_port': state.get('cluster_port'),
            'target_snapshot_name': state.get('target_snapshot_name'),
            'archive_status': state.get('archive_status')
        }
        
        if not details['target_cluster_id']:
            raise ValueError("Target cluster ID is required")
        
        if not details['target_region']:
            raise ValueError("Target region is required")
        
        return details
    
    def prepare_notification_message(self, details: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare the notification message.
        
        Args:
            details: Notification details
            
        Returns:
            Dict[str, Any]: Prepared message
        """
        return {
            'operation_id': self.operation_id,
            'status': 'SUCCESS',
            'timestamp': int(time.time()),
            'cluster_id': details['target_cluster_id'],
            'region': details['target_region'],
            'endpoint': details['cluster_endpoint'],
            'port': details['cluster_port'],
            'target_snapshot_name': details['target_snapshot_name'],
            'archive_status': details['archive_status']
        }
    
    def send_notification(self, details: Dict[str, Any], message: Dict[str, Any]) -> None:
        """
        Send the SNS notification.
        
        Args:
            details: Notification details
            message: Prepared message
            
        Raises:
            Exception: If notification fails
        """
        try:
            logger.info(f"Sending notification for operation {self.operation_id}")
            self.send_sns_notification(
                topic_arn=self.config['sns_topic_arn'],
                subject=f"Aurora Restore Complete - {details['target_cluster_id']}",
                message=json.dumps(message, indent=2)
            )
        except Exception as e:
            handle_aws_error(e, self.operation_id, self.step_name)
            raise
    
    def handle_notification_sent(self, details: Dict[str, Any], message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle successful notification.
        
        Args:
            details: Notification details
            message: Prepared message
            
        Returns:
            Dict[str, Any]: Response
        """
        # Update state
        state = {
            'target_cluster_id': details['target_cluster_id'],
            'target_region': details['target_region'],
            'cluster_endpoint': details['cluster_endpoint'],
            'cluster_port': details['cluster_port'],
            'notification_sent': True,
            'timestamp': message['timestamp'],
            'success': True
        }
        
        self.save_state(state)
        
        return {
            'message': 'Notification sent successfully',
            'target_cluster_id': details['target_cluster_id'],
            'target_region': details['target_region'],
            'cluster_endpoint': details['cluster_endpoint'],
            'timestamp': message['timestamp']
        }
    
    def process(self, event: Dict[str, Any], context: Any) -> Dict[str, Any]:
        """
        Process the SNS notification request.
        
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
            
            # Get notification details
            details = self.get_notification_details(event)
            
            # Prepare and send notification
            message = self.prepare_notification_message(details)
            self.send_notification(details, message)
            
            result = self.handle_notification_sent(details, message)
            
            # Update metrics
            duration = time.time() - start_time
            self.update_metrics('sns_notification_duration', duration, 'Seconds')
            
            return result
            
        except Exception as e:
            # Update metrics for failure
            duration = time.time() - start_time
            self.update_metrics('sns_notification_duration', duration, 'Seconds')
            self.update_metrics('sns_notification_failures', 1, 'Count')
            
            raise

# Initialize handler
handler = SNSNotificationHandler()

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for sending SNS notification about restore process completion.
    
    Args:
        event: Lambda event
        context: Lambda context
        
    Returns:
        dict: Response
    """
    return handler.execute(event, context) 