#!/usr/bin/env python3
"""
Lambda function to delete an existing RDS cluster.
"""

import time
import boto3
from typing import Dict, Any, Optional, List
from botocore.exceptions import ClientError

from utils.common import (
    logger,
    get_config,
    log_audit_event,
    update_metrics,
    validate_required_params,
    validate_region,
    get_operation_id,
    load_state,
    save_state,
    handle_aws_error,
    trigger_next_step
)
from utils.function_utils import validate_cluster_id

def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    """
    Delete an existing RDS cluster.
    
    Args:
        event: Lambda event containing:
            - operation_id: Optional operation ID for retry scenarios
            - target_cluster_id: ID of the cluster to delete (can also be loaded from config)
            - target_region: AWS region where the cluster exists (can also be loaded from config)
        _context: Lambda context
        
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
        
        # Load parameters from event with fallback to config
        target_region = event.get('target_region') or config.get('target_region')
        target_cluster_id = event.get('target_cluster_id') or config.get('target_cluster_id')
        
        # Validate required parameters
        required_params = {
            'target_cluster_id': target_cluster_id,
            'target_region': target_region
        }
        
        missing_params = validate_required_params(required_params)
        if missing_params:
            error_msg = f"Missing required parameters: {', '.join(missing_params)}"
            logger.error(error_msg)
            
            # Log audit event for failure
            log_audit_event(
                operation_id=operation_id,
                event_type='delete_rds',
                status='failed',
                details={
                    'error': error_msg,
                    'missing_params': missing_params
                }
            )
            
            return {
                'statusCode': 400,
                'body': {
                    'message': error_msg,
                    'operation_id': operation_id
                }
            }
        
        # Validate parameters
        try:
            validate_cluster_id(target_cluster_id)
        except ValueError as e:
            error_msg = f"Invalid cluster ID: {str(e)}"
            logger.error(error_msg)
            
            # Log audit event for failure
            log_audit_event(
                operation_id=operation_id,
                event_type='delete_rds',
                status='failed',
                details={
                    'error': error_msg,
                    'target_cluster_id': target_cluster_id
                }
            )
            
            return {
                'statusCode': 400,
                'body': {
                    'message': error_msg,
                    'operation_id': operation_id
                }
            }
            
        try:
            validate_region(target_region)
        except ValueError as e:
            error_msg = f"Invalid region: {str(e)}"
            logger.error(error_msg)
            
            # Log audit event for failure
            log_audit_event(
                operation_id=operation_id,
                event_type='delete_rds',
                status='failed',
                details={
                    'error': error_msg,
                    'target_region': target_region
                }
            )
            
            return {
                'statusCode': 400,
                'body': {
                    'message': error_msg,
                    'operation_id': operation_id
                }
            }
        
        # Load previous state
        state = load_state(operation_id)
        if state and not state.get('success', False):
            error_msg = f"Previous step failed for operation {operation_id}: {state.get('error', 'Unknown error')}"
            logger.warning(error_msg)
            
            # Update metrics for skipped operation
            update_metrics(
                operation_id=operation_id,
                metric_name='delete_rds_skipped',
                value=1,
                unit='Count'
            )
            
            # Log audit event for skipped step
            log_audit_event(
                operation_id=operation_id,
                event_type='delete_rds',
                status='skipped',
                details={
                    'reason': 'Previous step failed',
                    'previous_error': state.get('error', 'Unknown error')
                }
            )
            
            return {
                'statusCode': 400,
                'body': {
                    'message': 'Previous step failed',
                    'operation_id': operation_id,
                    'error': state.get('error', 'Unknown error')
                }
            }
        
        # Initialize RDS client
        try:
            rds_client = boto3.client('rds', region_name=target_region)
        except Exception as e:
            error_msg = f"Failed to create RDS client for region {target_region}: {str(e)}"
            logger.error(error_msg)
            
            # Log audit event for failure
            log_audit_event(
                operation_id=operation_id,
                event_type='delete_rds',
                status='failed',
                details={
                    'error': error_msg,
                    'target_region': target_region
                }
            )
            
            # Update metrics for failure
            update_metrics(
                operation_id=operation_id,
                metric_name='delete_rds_failures',
                value=1,
                unit='Count'
            )
            
            return {
                'statusCode': 500,
                'body': {
                    'message': error_msg,
                    'operation_id': operation_id
                }
            }
        
        # Check if cluster exists
        try:
            cluster = rds_client.describe_db_clusters(DBClusterIdentifier=target_cluster_id)['DBClusters'][0]
            logger.info(f"Found cluster {target_cluster_id} in state {cluster['Status']}")
        except ClientError as e:
            if e.response['Error']['Code'] == 'DBClusterNotFoundFault':
                logger.info(f"Cluster {target_cluster_id} does not exist, nothing to delete")
                
                # Save state to indicate success
                state = {
                    'operation_id': operation_id,
                    'target_cluster_id': target_cluster_id,
                    'target_region': target_region,
                    'status': 'completed',
                    'message': 'Cluster did not exist, no deletion needed',
                    'timestamp': int(time.time()),
                    'success': True
                }
                save_state(operation_id, state)
                
                # Log audit event
                log_audit_event(
                    operation_id=operation_id,
                    event_type='delete_rds',
                    status='completed',
                    details={
                        'cluster_id': target_cluster_id,
                        'region': target_region,
                        'status': 'completed',
                        'note': 'Cluster did not exist'
                    }
                )
                
                # Update metrics
                duration = time.time() - start_time
                update_metrics(
                    operation_id=operation_id,
                    metric_name='delete_rds_duration',
                    value=duration,
                    unit='Seconds'
                )
                
                # Trigger next step - skip to restore
                trigger_next_step(
                    operation_id=operation_id,
                    next_step='restore_snapshot',
                    event_data=state
                )
                
                return {
                    'statusCode': 200,
                    'body': {
                        'message': 'Cluster does not exist, proceeding to restore',
                        'operation_id': operation_id,
                        'next_step': 'restore_snapshot'
                    }
                }
            
            # Handle other AWS errors
            error_info = handle_aws_error(e, operation_id, 'delete_rds')
            return {
                'statusCode': error_info.get('statusCode', 500),
                'body': {
                    'message': error_info.get('message', 'Failed to check cluster existence'),
                    'operation_id': operation_id,
                    'error': error_info.get('error', str(e)),
                    'error_type': error_info.get('error_type')
                }
            }
        
        # Delete cluster
        logger.info(f"Deleting cluster {target_cluster_id}")
        try:
            rds_client.delete_db_cluster(
                DBClusterIdentifier=target_cluster_id,
                SkipFinalSnapshot=True
            )
        except ClientError as e:
            # Handle special cases for deletion
            if e.response['Error']['Code'] in ('InvalidDBClusterStateFault', 'DBClusterNotFoundFault'):
                logger.warning(f"Cluster {target_cluster_id} could not be deleted: {e.response['Error']['Message']}")
                
                # Still consider this a success and move on
                state = {
                    'operation_id': operation_id,
                    'target_cluster_id': target_cluster_id,
                    'target_region': target_region,
                    'status': 'completed',
                    'message': f"Cluster deletion not needed: {e.response['Error']['Message']}",
                    'timestamp': int(time.time()),
                    'success': True
                }
                save_state(operation_id, state)
                
                # Log audit event
                log_audit_event(
                    operation_id=operation_id,
                    event_type='delete_rds',
                    status='completed',
                    details={
                        'cluster_id': target_cluster_id,
                        'region': target_region,
                        'status': 'completed',
                        'note': f"Deletion not needed: {e.response['Error']['Message']}"
                    }
                )
                
                # Update metrics
                duration = time.time() - start_time
                update_metrics(
                    operation_id=operation_id,
                    metric_name='delete_rds_duration',
                    value=duration,
                    unit='Seconds'
                )
                
                # Trigger next step - skip to restore
                trigger_next_step(
                    operation_id=operation_id,
                    next_step='restore_snapshot',
                    event_data=state
                )
                
                return {
                    'statusCode': 200,
                    'body': {
                        'message': f"Cluster deletion not needed, proceeding to restore: {e.response['Error']['Message']}",
                        'operation_id': operation_id,
                        'next_step': 'restore_snapshot'
                    }
                }
            
            # For other errors, handle normally
            error_info = handle_aws_error(e, operation_id, 'delete_rds')
            
            # Update metrics for failure
            duration = time.time() - start_time
            update_metrics(
                operation_id=operation_id,
                metric_name='delete_rds_duration',
                value=duration,
                unit='Seconds'
            )
            update_metrics(
                operation_id=operation_id,
                metric_name='delete_rds_failures',
                value=1,
                unit='Count'
            )
            
            return {
                'statusCode': error_info.get('statusCode', 500),
                'body': {
                    'message': error_info.get('message', 'Failed to delete cluster'),
                    'operation_id': operation_id,
                    'error': error_info.get('error', str(e)),
                    'error_type': error_info.get('error_type')
                }
            }
        
        # Save state
        state = {
            'operation_id': operation_id,
            'target_cluster_id': target_cluster_id,
            'target_region': target_region,
            'status': 'deleting',
            'timestamp': int(time.time()),
            'success': True
        }
        save_state(operation_id, state)
        
        # Log audit event
        log_audit_event(
            operation_id=operation_id,
            event_type='delete_rds',
            status='deleting',
            details={
                'cluster_id': target_cluster_id,
                'region': target_region,
                'status': 'deleting'
            }
        )
        
        # Update metrics
        duration = time.time() - start_time
        update_metrics(
            operation_id=operation_id,
            metric_name='delete_rds_duration',
            value=duration,
            unit='Seconds'
        )
        
        # Trigger next step
        trigger_next_step(
            operation_id=operation_id,
            next_step='check_delete_status',
            event_data=state
        )
        
        return {
            'statusCode': 200,
            'body': {
                'message': 'Cluster deletion initiated',
                'operation_id': operation_id,
                'cluster_id': target_cluster_id,
                'region': target_region
            }
        }
        
    except Exception as e:
        logger.error(f"Error in delete_rds: {str(e)}", exc_info=True)
        
        # Create error state
        error_state = {
            'operation_id': operation_id,
            'error': str(e),
            'target_cluster_id': target_cluster_id if 'target_cluster_id' in locals() else None,
            'target_region': target_region if 'target_region' in locals() else None,
            'timestamp': int(time.time()),
            'success': False
        }
        save_state(operation_id, error_state)
        
        # Log audit event for failure
        log_audit_event(
            operation_id=operation_id,
            event_type='delete_rds',
            status='failed',
            details={
                'error': str(e)
            }
        )
        
        # Update metrics for failure
        duration = time.time() - start_time
        update_metrics(
            operation_id=operation_id,
            metric_name='delete_rds_duration',
            value=duration,
            unit='Seconds'
        )
        update_metrics(
            operation_id=operation_id,
            metric_name='delete_rds_failures',
            value=1,
            unit='Count'
        )
        
        return {
            'statusCode': 500,
            'body': {
                'message': 'Failed to delete cluster',
                'operation_id': operation_id,
                'error': str(e)
            }
        } 