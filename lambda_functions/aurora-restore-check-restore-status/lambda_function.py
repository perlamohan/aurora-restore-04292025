#!/usr/bin/env python3
"""
Lambda function to check the status of a cluster restore operation.
"""

import json
import time
import boto3
from typing import Dict, Any
from botocore.exceptions import ClientError

from utils.common import (
    logger,
    get_config,
    log_audit_event,
    update_metrics,
    validate_required_params,
    validate_region,
    get_operation_id,
    save_state,
    handle_aws_error,
    trigger_next_step
)

def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    """
    Check the status of a cluster restore operation.
    
    Args:
        event: Lambda event containing:
            - operation_id: Optional operation ID for retry scenarios
            - target_cluster_id: ID of the cluster being restored
            - target_region: AWS region where the cluster exists
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
        
        # Load previous state
        state = load_state(operation_id)
        if not state:
            error_msg = f"No previous state found for operation {operation_id}"
            logger.error(error_msg)
            log_audit_event(
                operation_id=operation_id,
                event_type='check_restore_status',
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
                event_type='check_restore_status',
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
        
        # Get cluster details from state or config
        target_cluster_id = state.get('target_cluster_id') or config.get('target_cluster_id')
        target_region = state.get('target_region') or config.get('target_region')
        
        # Validate required parameters
        required_params = {
            'target_cluster_id': target_cluster_id,
            'target_region': target_region
        }
        
        missing_params = validate_required_params(required_params)
        if missing_params:
            error_msg = f"Missing required parameters: {', '.join(missing_params)}"
            logger.error(error_msg)
            log_audit_event(
                operation_id=operation_id,
                event_type='check_restore_status',
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
                event_type='check_restore_status',
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
        
        # Initialize RDS client
        try:
            rds_client = boto3.client('rds', region_name=target_region)
        except Exception as e:
            error_msg = f"Failed to initialize RDS client: {str(e)}"
            logger.error(error_msg, exc_info=True)
            log_audit_event(
                operation_id=operation_id,
                event_type='check_restore_status',
                status='failed',
                details={'error': error_msg, 'target_region': target_region}
            )
            
            # Update metrics
            update_metrics(
                operation_id=operation_id,
                metric_name='check_restore_status_failures',
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
        
        # Check cluster status
        try:
            logger.info(f"Checking status of cluster {target_cluster_id} in {target_region}")
            response = rds_client.describe_db_clusters(
                DBClusterIdentifier=target_cluster_id
            )
            
            if not response.get('DBClusters'):
                error_msg = f"Cluster {target_cluster_id} not found in {target_region}"
                logger.error(error_msg)
                log_audit_event(
                    operation_id=operation_id,
                    event_type='check_restore_status',
                    status='failed',
                    details={
                        'error': error_msg,
                        'target_cluster_id': target_cluster_id,
                        'target_region': target_region
                    }
                )
                
                # Update metrics
                update_metrics(
                    operation_id=operation_id,
                    metric_name='check_restore_status_failures',
                    value=1,
                    unit='Count'
                )
                
                return {
                    'statusCode': 404,
                    'body': {
                        'message': error_msg,
                        'operation_id': operation_id,
                        'target_cluster_id': target_cluster_id,
                        'target_region': target_region,
                        'success': False
                    }
                }
            
            cluster = response['DBClusters'][0]
            status = cluster['Status']
            
            # Get cluster endpoint information
            cluster_endpoint = cluster.get('Endpoint')
            cluster_port = cluster.get('Port')
            
            logger.info(f"Cluster {target_cluster_id} status: {status}")
            
            # Check if cluster is available
            if status == 'available':
                # Update state with success
                state_update = {
                    'operation_id': operation_id,
                    'target_cluster_id': target_cluster_id,
                    'target_region': target_region,
                    'cluster_status': status,
                    'cluster_endpoint': cluster_endpoint,
                    'cluster_port': cluster_port,
                    'engine': cluster.get('Engine'),
                    'engine_version': cluster.get('EngineVersion'),
                    'success': True
                }
                save_state(operation_id, state_update)
                
                # Log audit event
                log_audit_event(
                    operation_id=operation_id,
                    event_type='check_restore_status',
                    status='success',
                    details={
                        'cluster_id': target_cluster_id,
                        'region': target_region,
                        'status': status,
                        'cluster_endpoint': cluster_endpoint,
                        'cluster_port': cluster_port,
                        'message': 'Cluster restore complete'
                    }
                )
                
                # Update metrics
                duration = time.time() - start_time
                update_metrics(
                    operation_id=operation_id,
                    metric_name='check_restore_status_duration',
                    value=duration,
                    unit='Seconds'
                )
                
                # Return success
                return {
                    'statusCode': 200,
                    'body': {
                        'message': 'Cluster restore complete',
                        'operation_id': operation_id,
                        'cluster_id': target_cluster_id,
                        'region': target_region,
                        'status': status,
                        'cluster_endpoint': cluster_endpoint,
                        'cluster_port': cluster_port,
                        'success': True
                    }
                }
                
            elif status in ['failed', 'incompatible-restore']:
                # Update state with failure
                state_update = {
                    'operation_id': operation_id,
                    'target_cluster_id': target_cluster_id,
                    'target_region': target_region,
                    'cluster_status': status,
                    'success': False
                }
                save_state(operation_id, state_update)
                
                # Log audit event
                error_msg = f"Cluster restore failed with status: {status}"
                log_audit_event(
                    operation_id=operation_id,
                    event_type='check_restore_status',
                    status='failed',
                    details={
                        'cluster_id': target_cluster_id,
                        'region': target_region,
                        'status': status,
                        'error': error_msg
                    }
                )
                
                # Update metrics
                update_metrics(
                    operation_id=operation_id,
                    metric_name='check_restore_status_failures',
                    value=1,
                    unit='Count'
                )
                
                # Return failure
                return {
                    'statusCode': 400,
                    'body': {
                        'message': error_msg,
                        'operation_id': operation_id,
                        'cluster_id': target_cluster_id,
                        'region': target_region,
                        'status': status,
                        'success': False
                    }
                }
            else:
                # Cluster still being created, save current state
                state_update = {
                    'operation_id': operation_id,
                    'target_cluster_id': target_cluster_id,
                    'target_region': target_region,
                    'cluster_status': status,
                    'success': True
                }
                save_state(operation_id, state_update)
                
                # Log audit event
                log_audit_event(
                    operation_id=operation_id,
                    event_type='check_restore_status',
                    status='success',
                    details={
                        'cluster_id': target_cluster_id,
                        'region': target_region,
                        'status': status,
                        'message': 'Cluster restore in progress'
                    }
                )
                
                # Update metrics
                duration = time.time() - start_time
                update_metrics(
                    operation_id=operation_id,
                    metric_name='check_restore_status_duration',
                    value=duration,
                    unit='Seconds'
                )
                
                # Return in-progress status
                return {
                    'statusCode': 200,
                    'body': {
                        'message': 'Cluster restore in progress',
                        'operation_id': operation_id,
                        'cluster_id': target_cluster_id,
                        'region': target_region,
                        'status': status,
                        'success': True
                    }
                }
                
        except ClientError as e:
            error_details = handle_aws_error(e, operation_id, 'check_restore_status')
            
            # Update metrics
            update_metrics(
                operation_id=operation_id,
                metric_name='check_restore_status_failures',
                value=1,
                unit='Count'
            )
            
            return {
                'statusCode': error_details.get('statusCode', 500),
                'body': {
                    'message': error_details.get('message', 'Failed to check cluster status'),
                    'operation_id': operation_id,
                    'error': error_details.get('error', str(e)),
                    'success': False
                }
            }
        
    except Exception as e:
        error_msg = f"Error in check_restore_status: {str(e)}"
        logger.error(error_msg, exc_info=True)
        
        # Log audit event for failure
        log_audit_event(
            operation_id=operation_id,
            event_type='check_restore_status',
            status='failed',
            details={
                'error': error_msg
            }
        )
        
        # Update metrics
        update_metrics(
            operation_id=operation_id,
            metric_name='check_restore_status_failures',
            value=1,
            unit='Count'
        )
        
        return {
            'statusCode': 500,
            'body': {
                'message': 'Failed to check cluster restore status',
                'operation_id': operation_id,
                'error': str(e),
                'success': False
            }
        } 