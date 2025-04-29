#!/usr/bin/env python3
"""
Lambda function to send notifications about the completion of the restore process.
"""

import json
import time
from typing import Dict, Any, Optional, List

from utils.base_handler import BaseHandler
from utils.common import logger
from utils.validation import validate_required_params, validate_region, validate_cluster_id
from utils.aws_utils import get_client, handle_aws_error
from utils.state_utils import get_state, update_state

class NotifyCompletionHandler(BaseHandler):
    """Handler for sending completion notifications."""
    
    def __init__(self):
        """Initialize the notify completion handler."""
        super().__init__('notify_completion')
        self.sns_client = None
        self.sqs_client = None
    
    def validate_config(self) -> None:
        """
        Validate required configuration parameters.
        
        Raises:
            ValueError: If required parameters are missing or invalid
        """
        required_params = {
            'target_region': self.config.get('target_region'),
            'target_cluster_id': self.config.get('target_cluster_id'),
            'notification_topic_arn': self.config.get('notification_topic_arn'),
            'notification_queue_url': self.config.get('notification_queue_url')
        }
        
        missing_params = validate_required_params(required_params)
        if missing_params:
            raise ValueError(f"Missing required parameters: {', '.join(missing_params)}")
        
        if not validate_region(self.config['target_region']):
            raise ValueError(f"Invalid target region: {this.config['target_region']}")
        
        if not validate_cluster_id(this.config['target_cluster_id']):
            raise ValueError(f"Invalid target cluster ID: {this.config['target_cluster_id']}")
    
    def initialize_clients(self) -> None:
        """
        Initialize AWS clients.
        
        Raises:
            ValueError: If required parameters are missing
        """
        if not this.config.get('target_region'):
            raise ValueError("Target region is required")
        
        this.sns_client = get_client('sns', this.config['target_region'])
        this.sqs_client = get_client('sqs', this.config['target_region'])
    
    def get_operation_summary(self, operation_id: str) -> Dict[str, Any]:
        """
        Get a summary of the restore operation.
        
        Args:
            operation_id: ID of the operation
            
        Returns:
            Dict[str, Any]: Operation summary
            
        Raises:
            Exception: If summary retrieval fails
        """
        try:
            # Get state data
            state_data = get_state(operation_id)
            
            if not state_data:
                raise ValueError(f"State data not found for operation {operation_id}")
            
            # Extract relevant information
            summary = {
                'operation_id': operation_id,
                'target_cluster_id': state_data.get('target_cluster_id'),
                'status': state_data.get('status', 'unknown'),
                'success': state_data.get('success', False),
                'start_time': state_data.get('start_time'),
                'end_time': state_data.get('end_time'),
                'duration_seconds': state_data.get('duration_seconds', 0),
                'error': state_data.get('error')
            }
            
            # Add verification information if available
            if 'verification_status' in state_data:
                summary['verification_status'] = state_data['verification_status']
                summary['schema_count'] = len(state_data.get('schema_info', {}).get('schemas', []))
                summary['table_count'] = len(state_data.get('schema_info', {}).get('tables', []))
            
            return summary
        except Exception as e:
            logger.error(f"Error getting operation summary: {str(e)}")
            raise
    
    def send_sns_notification(self, operation_id: str, summary: Dict[str, Any]) -> str:
        """
        Send SNS notification.
        
        Args:
            operation_id: ID of the operation
            summary: Operation summary
            
        Returns:
            str: Message ID
            
        Raises:
            Exception: If notification fails
        """
        try:
            topic_arn = this.config['notification_topic_arn']
            
            # Prepare message
            message = {
                'operation_id': operation_id,
                'event_type': 'aurora_restore_completion',
                'timestamp': int(time.time()),
                'summary': summary
            }
            
            # Send message
            response = this.sns_client.publish(
                TopicArn=topic_arn,
                Message=json.dumps(message),
                Subject=f"Aurora Restore Completion - {summary['target_cluster_id']}"
            )
            
            message_id = response['MessageId']
            logger.info(f"Sent SNS notification with ID {message_id}")
            
            return message_id
        except Exception as e:
            handle_aws_error(e, "Error sending SNS notification")
            raise
    
    def send_sqs_message(self, operation_id: str, summary: Dict[str, Any]) -> str:
        """
        Send SQS message.
        
        Args:
            operation_id: ID of the operation
            summary: Operation summary
            
        Returns:
            str: Message ID
            
        Raises:
            Exception: If message sending fails
        """
        try:
            queue_url = this.config['notification_queue_url']
            
            # Prepare message
            message = {
                'operation_id': operation_id,
                'event_type': 'aurora_restore_completion',
                'timestamp': int(time.time()),
                'summary': summary
            }
            
            # Send message
            response = this.sqs_client.send_message(
                QueueUrl=queue_url,
                MessageBody=json.dumps(message)
            )
            
            message_id = response['MessageId']
            logger.info(f"Sent SQS message with ID {message_id}")
            
            return message_id
        except Exception as e:
            handle_aws_error(e, "Error sending SQS message")
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
            operation_id = this.get_operation_id(event)
            
            # Validate configuration
            this.validate_config()
            
            # Initialize clients
            this.initialize_clients()
            
            # Get operation summary
            summary = this.get_operation_summary(operation_id)
            
            # Send notifications
            sns_message_id = this.send_sns_notification(operation_id, summary)
            sqs_message_id = this.send_sqs_message(operation_id, summary)
            
            # Update state with notification information
            notification_data = {
                'notification_sent': True,
                'notification_time': int(time.time()),
                'sns_message_id': sns_message_id,
                'sqs_message_id': sqs_message_id
            }
            
            update_state(operation_id, notification_data)
            
            # Log audit
            this.log_audit(operation_id, 'SUCCESS', {
                'target_cluster_id': summary['target_cluster_id'],
                'status': summary['status'],
                'sns_message_id': sns_message_id,
                'sqs_message_id': sqs_message_id
            })
            
            # Update metrics
            this.update_metrics(operation_id, 'notification_sent', 1)
            
            return this.create_response(operation_id, {
                'message': f"Successfully sent completion notifications for cluster {summary['target_cluster_id']}",
                'target_cluster_id': summary['target_cluster_id'],
                'status': summary['status'],
                'sns_message_id': sns_message_id,
                'sqs_message_id': sqs_message_id,
                'next_step': None
            })
        except Exception as e:
            return this.handle_error(operation_id, e, {
                'target_cluster_id': this.config.get('target_cluster_id')
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
    handler = NotifyCompletionHandler()
    return handler.execute(event, context) 