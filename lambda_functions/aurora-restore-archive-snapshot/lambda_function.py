#!/usr/bin/env python3
"""
Lambda function to archive a snapshot after a successful restore.
"""

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
    load_state,
    save_state,
    handle_aws_error
)

def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    """
    Archive a snapshot after a successful restore.
    
    Args:
        event: Lambda event containing:
            - operation_id: Optional operation ID for retry scenarios
            - target_snapshot_name: Name of the snapshot to archive
            - target_region: Region where the snapshot is located
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
                event_type='archive_snapshot',
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
                event_type='archive_snapshot',
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
        
        # Get target snapshot name from state
        target_snapshot_name = state.get('target_snapshot_name')
        
        # Validate required parameters
        required_params = {
            'target_region': target_region,
            'target_snapshot_name': target_snapshot_name
        }
        
        missing_params = validate_required_params(required_params)
        if missing_params:
            error_msg = f"Missing required parameters: {', '.join(missing_params)}"
            logger.error(error_msg)
            log_audit_event(
                operation_id=operation_id,
                event_type='archive_snapshot',
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
                event_type='archive_snapshot',
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
                event_type='archive_snapshot',
                status='failed',
                details={'error': error_msg, 'target_region': target_region}
            )
            return {
                'statusCode': 500,
                'body': {
                    'message': error_msg,
                    'operation_id': operation_id,
                    'success': False
                }
            }
        
        # Check if snapshot exists
        try:
            logger.info(f"Checking if snapshot {target_snapshot_name} exists in {target_region}")
            response = rds_client.describe_db_cluster_snapshots(
                DBClusterSnapshotIdentifier=target_snapshot_name
            )
            
            if not response.get('DBClusterSnapshots'):
                logger.info(f"Snapshot {target_snapshot_name} does not exist in {target_region}, no action needed")
                
                # Update state
                state_update = {
                    'operation_id': operation_id,
                    'target_snapshot_name': target_snapshot_name,
                    'target_region': target_region,
                    'archive_status': 'skipped',
                    'success': True
                }
                save_state(operation_id, state_update)
                
                # Log audit event
                log_audit_event(
                    operation_id=operation_id,
                    event_type='archive_snapshot',
                    status='success',
                    details={
                        'target_snapshot_name': target_snapshot_name,
                        'target_region': target_region,
                        'archive_status': 'skipped',
                        'message': 'Snapshot does not exist, no action needed'
                    }
                )
                
                return {
                    'statusCode': 200,
                    'body': {
                        'message': f"Snapshot {target_snapshot_name} does not exist, no action needed",
                        'operation_id': operation_id,
                        'target_snapshot_name': target_snapshot_name,
                        'target_region': target_region,
                        'archive_status': 'skipped',
                        'success': True
                    }
                }
                
        except ClientError as e:
            if e.response['Error']['Code'] == 'DBClusterSnapshotNotFoundFault':
                logger.info(f"Snapshot {target_snapshot_name} does not exist in {target_region}, no action needed")
                
                # Update state
                state_update = {
                    'operation_id': operation_id,
                    'target_snapshot_name': target_snapshot_name,
                    'target_region': target_region,
                    'archive_status': 'skipped',
                    'success': True
                }
                save_state(operation_id, state_update)
                
                # Log audit event
                log_audit_event(
                    operation_id=operation_id,
                    event_type='archive_snapshot',
                    status='success',
                    details={
                        'target_snapshot_name': target_snapshot_name,
                        'target_region': target_region,
                        'archive_status': 'skipped',
                        'message': 'Snapshot does not exist, no action needed'
                    }
                )
                
                return {
                    'statusCode': 200,
                    'body': {
                        'message': f"Snapshot {target_snapshot_name} does not exist, no action needed",
                        'operation_id': operation_id,
                        'target_snapshot_name': target_snapshot_name,
                        'target_region': target_region,
                        'archive_status': 'skipped',
                        'success': True
                    }
                }
            else:
                error_details = handle_aws_error(e, operation_id, 'archive_snapshot')
                
                # Update metrics
                update_metrics(
                    operation_id=operation_id,
                    metric_name='archive_snapshot_failures',
                    value=1,
                    unit='Count'
                )
                
                return {
                    'statusCode': error_details.get('statusCode', 500),
                    'body': {
                        'message': error_details.get('message', 'Failed to check snapshot existence'),
                        'operation_id': operation_id,
                        'error': error_details.get('error', str(e)),
                        'success': False
                    }
                }
        
        # Delete the snapshot
        try:
            logger.info(f"Deleting snapshot {target_snapshot_name} in {target_region}")
            rds_client.delete_db_cluster_snapshot(
                DBClusterSnapshotIdentifier=target_snapshot_name
            )
            
            # Update state
            state_update = {
                'operation_id': operation_id,
                'target_snapshot_name': target_snapshot_name,
                'target_region': target_region,
                'archive_status': 'deleted',
                'success': True
            }
            save_state(operation_id, state_update)
            
            # Log audit event
            log_audit_event(
                operation_id=operation_id,
                event_type='archive_snapshot',
                status='success',
                details={
                    'target_snapshot_name': target_snapshot_name,
                    'target_region': target_region,
                    'archive_status': 'deleted',
                    'message': 'Snapshot deleted successfully'
                }
            )
            
            # Update metrics
            duration = time.time() - start_time
            update_metrics(
                operation_id=operation_id,
                metric_name='archive_snapshot_duration',
                value=duration,
                unit='Seconds'
            )
            
            return {
                'statusCode': 200,
                'body': {
                    'message': f"Snapshot {target_snapshot_name} deleted successfully",
                    'operation_id': operation_id,
                    'target_snapshot_name': target_snapshot_name,
                    'target_region': target_region,
                    'archive_status': 'deleted',
                    'success': True
                }
            }
            
        except ClientError as e:
            error_details = handle_aws_error(e, operation_id, 'archive_snapshot')
            
            # Update metrics
            update_metrics(
                operation_id=operation_id,
                metric_name='archive_snapshot_failures',
                value=1,
                unit='Count'
            )
            
            return {
                'statusCode': error_details.get('statusCode', 500),
                'body': {
                    'message': error_details.get('message', 'Failed to delete snapshot'),
                    'operation_id': operation_id,
                    'error': error_details.get('error', str(e)),
                    'success': False
                }
            }
            
    except Exception as e:
        error_msg = f"Error in archive_snapshot: {str(e)}"
        logger.error(error_msg, exc_info=True)
        
        # Log audit event for failure
        log_audit_event(
            operation_id=operation_id,
            event_type='archive_snapshot',
            status='failed',
            details={
                'error': str(e)
            }
        )
        
        # Update metrics
        update_metrics(
            operation_id=operation_id,
            metric_name='archive_snapshot_failures',
            value=1,
            unit='Count'
        )
        
        return {
            'statusCode': 500,
            'body': {
                'message': 'Failed to archive snapshot',
                'operation_id': operation_id,
                'error': str(e),
                'success': False
            }
        } 