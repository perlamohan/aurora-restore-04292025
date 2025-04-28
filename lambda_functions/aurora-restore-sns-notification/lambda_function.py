#!/usr/bin/env python3
"""
Lambda function to send SNS notification about the restore process completion.
"""

import json
import time
from typing import Dict, Any
from botocore.exceptions import ClientError

from utils.common import (
    logger,
    get_config,
    log_audit_event,
    update_metrics,
    validate_required_params,
    validate_region,
    send_notification,
    get_operation_id,
    save_state,
    handle_aws_error,
    trigger_next_step
)

def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    """
    Send SNS notification about the restore process completion.
    
    Args:
        event: Lambda event containing:
            - operation_id: Optional operation ID for retry scenarios
            - target_region: Target region of the restored cluster
            - cluster_endpoint: Optional endpoint of the restored cluster
        context: Lambda context
        
    Returns:
        dict: Response containing:
            - statusCode: HTTP status code
            - body: Response body with operation details
    """
    start_time = time.time()
    operation_id = get_operation_id(event)
    
    try:
        # Get configuration
        config = get_config()
        target_region = config.get('target_region')
        
        # Load previous state
        state = load_state(operation_id)
        if not state:
            error_msg = f"No previous state found for operation {operation_id}"
            logger.error(error_msg)
            log_audit_event(
                operation_id=operation_id,
                event_type='sns_notification',
                status='failed',
                details={'error': error_msg}
            )
            return {
                'statusCode': 400,
                'body': {
                    'message': error_msg,
                    'operation_id': operation_id,
                    'success': False
                }
            }
            
        if not state.get('success', False):
            error_msg = f"Previous step failed for operation {operation_id}"
            logger.warning(error_msg)
            log_audit_event(
                operation_id=operation_id,
                event_type='sns_notification',
                status='failed',
                details={'error': error_msg, 'previous_state': state}
            )
            return {
                'statusCode': 400,
                'body': {
                    'message': error_msg,
                    'operation_id': operation_id,
                    'previous_state': state,
                    'success': False
                }
            }
        
        # Get details from state
        target_cluster_id = state.get('target_cluster_id', config.get('target_cluster_id'))
        cluster_endpoint = state.get('cluster_endpoint')
        cluster_port = state.get('cluster_port')
        target_snapshot_name = state.get('target_snapshot_name')
        archive_status = state.get('archive_status')
        
        # Validate required parameters
        required_params = {
            'target_region': target_region,
            'target_cluster_id': target_cluster_id
        }
        
        missing_params = validate_required_params(required_params)
        if missing_params:
            error_msg = f"Missing required parameters: {', '.join(missing_params)}"
            logger.error(error_msg)
            log_audit_event(
                operation_id=operation_id,
                event_type='sns_notification',
                status='failed',
                details={'error': error_msg, 'missing_params': missing_params}
            )
            return {
                'statusCode': 400,
                'body': {
                    'message': error_msg,
                    'operation_id': operation_id,
                    'success': False
                }
            }
        
        # Validate region
        if not validate_region(target_region):
            error_msg = f"Invalid region: {target_region}"
            logger.error(error_msg)
            log_audit_event(
                operation_id=operation_id,
                event_type='sns_notification',
                status='failed',
                details={'error': error_msg, 'target_region': target_region}
            )
            return {
                'statusCode': 400,
                'body': {
                    'message': error_msg,
                    'operation_id': operation_id,
                    'success': False
                }
            }
        
        # Get SNS topic ARN from config
        sns_topic_arn = config.get('sns_topic_arn')
        if not sns_topic_arn:
            error_msg = f"Missing sns_topic_arn in config for operation {operation_id}"
            logger.error(error_msg)
            log_audit_event(
                operation_id=operation_id,
                event_type='sns_notification',
                status='failed',
                details={'error': error_msg}
            )
            
            # Update metrics
            update_metrics(
                operation_id=operation_id,
                metric_name='sns_notification_failures',
                value=1,
                unit='Count'
            )
            
            return {
                'statusCode': 400,
                'body': {
                    'message': error_msg,
                    'operation_id': operation_id,
                    'success': False
                }
            }
        
        # Prepare notification message
        timestamp = int(time.time())
        message = {
            'operation_id': operation_id,
            'status': 'SUCCESS',
            'timestamp': timestamp,
            'cluster_id': target_cluster_id,
            'region': target_region,
            'endpoint': cluster_endpoint,
            'port': cluster_port,
            'target_snapshot_name': target_snapshot_name,
            'archive_status': archive_status
        }
        
        # Send notification
        try:
            logger.info(f"Sending notification for operation {operation_id}")
            send_notification(
                topic_arn=sns_topic_arn,
                subject=f"Aurora Restore Complete - {target_cluster_id}",
                message=json.dumps(message, indent=2)
            )
        except Exception as e:
            error_msg = f"Failed to send notification: {str(e)}"
            logger.error(error_msg, exc_info=True)
            log_audit_event(
                operation_id=operation_id,
                event_type='sns_notification',
                status='failed',
                details={'error': error_msg}
            )
            
            # Update metrics
            update_metrics(
                operation_id=operation_id,
                metric_name='sns_notification_failures',
                value=1,
                unit='Count'
            )
            
            return {
                'statusCode': 500,
                'body': {
                    'message': error_msg,
                    'operation_id': operation_id,
                    'success': False
                }
            }
        
        # Update state
        state_update = {
            'operation_id': operation_id,
            'target_cluster_id': target_cluster_id,
            'target_region': target_region,
            'cluster_endpoint': cluster_endpoint,
            'cluster_port': cluster_port,
            'notification_sent': True,
            'timestamp': timestamp,
            'success': True
        }
        save_state(operation_id, state_update)
        
        # Log audit event
        log_audit_event(
            operation_id=operation_id,
            event_type='sns_notification',
            status='success',
            details={
                'target_cluster_id': target_cluster_id,
                'target_region': target_region,
                'cluster_endpoint': cluster_endpoint,
                'notification_sent': True,
                'timestamp': timestamp
            }
        )
        
        # Update metrics
        duration = time.time() - start_time
        update_metrics(
            operation_id=operation_id,
            metric_name='sns_notification_duration',
            value=duration,
            unit='Seconds'
        )
        
        return {
            'statusCode': 200,
            'body': {
                'message': 'Notification sent successfully',
                'operation_id': operation_id,
                'target_cluster_id': target_cluster_id,
                'target_region': target_region,
                'cluster_endpoint': cluster_endpoint,
                'timestamp': timestamp,
                'success': True
            }
        }
        
    except ClientError as e:
        error_details = handle_aws_error(e, operation_id, 'sns_notification')
        
        # Update metrics
        update_metrics(
            operation_id=operation_id,
            metric_name='sns_notification_failures',
            value=1,
            unit='Count'
        )
        
        return {
            'statusCode': error_details.get('statusCode', 500),
            'body': {
                'message': error_details.get('message', 'Failed to send notification'),
                'operation_id': operation_id,
                'error': error_details.get('error', str(e)),
                'success': False
            }
        }
        
    except Exception as e:
        error_msg = f"Error in sns_notification: {str(e)}"
        logger.error(error_msg, exc_info=True)
        
        # Log audit event for failure
        log_audit_event(
            operation_id=operation_id,
            event_type='sns_notification',
            status='failed',
            details={
                'error': str(e)
            }
        )
        
        # Update metrics
        update_metrics(
            operation_id=operation_id,
            metric_name='sns_notification_failures',
            value=1,
            unit='Count'
        )
        
        return {
            'statusCode': 500,
            'body': {
                'message': 'Failed to send notification',
                'operation_id': operation_id,
                'error': str(e),
                'success': False
            }
        } 