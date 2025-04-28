#!/usr/bin/env python3
"""
Lambda function to check the status of a snapshot copy operation.
"""

import json
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
    validate_snapshot_name,
    validate_region,
    get_operation_id,
    load_state,
    save_state,
    handle_aws_error,
    trigger_next_step
)

def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    """
    Check the status of a snapshot copy operation.
    
    Args:
        event: Lambda event containing:
            - operation_id: Optional operation ID for retry scenarios
            - target_snapshot_name: Name of the target snapshot
            - target_region: AWS region where the snapshot is being copied to
            - source_region: AWS region where the snapshot is being copied from
        _context: Lambda context
        
    Returns:
        dict: Response containing:
            - statusCode: HTTP status code
            - body: Response body with operation details
    """
    start_time = time.time()
    operation_id = get_operation_id(event)
    
    # Initialize variables for local scope
    target_snapshot_name = None
    target_region = None
    source_region = None
    snapshot_status = None
    
    try:
        # Get configuration
        config = get_config()
        
        # Load previous state
        state = load_state(operation_id)
        if not state:
            error_msg = f"No previous state found for operation {operation_id}"
            logger.error(error_msg)
            
            # Log audit event for failure
            log_audit_event(
                operation_id=operation_id,
                event_type='check_copy_status',
                status='failed',
                details={
                    'error': error_msg
                }
            )
            
            # Update metrics for failure
            update_metrics(
                operation_id=operation_id,
                metric_name='check_copy_status_failures',
                value=1,
                unit='Count'
            )
            
            return {
                'statusCode': 400,
                'body': {
                    'message': error_msg,
                    'operation_id': operation_id
                }
            }
        
        # Check if previous step failed
        if state and not state.get('success', False):
            error_msg = f"Previous step failed for operation {operation_id}: {state.get('error', 'Unknown error')}"
            logger.warning(error_msg)
            
            # Update metrics for skipped operation
            update_metrics(
                operation_id=operation_id,
                metric_name='check_copy_status_skipped',
                value=1,
                unit='Count'
            )
            
            # Log audit event for skipped step
            log_audit_event(
                operation_id=operation_id,
                event_type='check_copy_status',
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
        
        # Load parameters from state with fallback to event and config
        target_snapshot_name = state.get('target_snapshot_name') or event.get('target_snapshot_name') or config.get('target_snapshot_name')
        target_region = state.get('target_region') or event.get('target_region') or config.get('target_region')
        source_region = state.get('source_region') or event.get('source_region') or config.get('source_region')
        
        # Validate required parameters
        required_params = {
            'target_snapshot_name': target_snapshot_name,
            'target_region': target_region,
            'source_region': source_region
        }
        
        missing_params = validate_required_params(required_params)
        if missing_params:
            error_msg = f"Missing required parameters: {', '.join(missing_params)}"
            logger.error(error_msg)
            
            # Log audit event for failure
            log_audit_event(
                operation_id=operation_id,
                event_type='check_copy_status',
                status='failed',
                details={
                    'error': error_msg,
                    'missing_params': missing_params
                }
            )
            
            # Update metrics for failure
            update_metrics(
                operation_id=operation_id,
                metric_name='check_copy_status_failures',
                value=1,
                unit='Count'
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
            validate_snapshot_name(target_snapshot_name)
        except ValueError as e:
            error_msg = f"Invalid snapshot name: {str(e)}"
            logger.error(error_msg)
            
            # Log audit event for failure
            log_audit_event(
                operation_id=operation_id,
                event_type='check_copy_status',
                status='failed',
                details={
                    'error': error_msg,
                    'target_snapshot_name': target_snapshot_name
                }
            )
            
            # Update metrics for failure
            update_metrics(
                operation_id=operation_id,
                metric_name='check_copy_status_failures',
                value=1,
                unit='Count'
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
            validate_region(source_region)
        except ValueError as e:
            error_msg = f"Invalid region: {str(e)}"
            logger.error(error_msg)
            
            # Log audit event for failure
            log_audit_event(
                operation_id=operation_id,
                event_type='check_copy_status',
                status='failed',
                details={
                    'error': error_msg,
                    'target_region': target_region,
                    'source_region': source_region
                }
            )
            
            # Update metrics for failure
            update_metrics(
                operation_id=operation_id,
                metric_name='check_copy_status_failures',
                value=1,
                unit='Count'
            )
            
            return {
                'statusCode': 400,
                'body': {
                    'message': error_msg,
                    'operation_id': operation_id
                }
            }
        
        # Check if source and target regions are the same
        if source_region == target_region:
            logger.info(f"Source and target regions are the same ({source_region}). No copy needed, proceeding to next step")
            
            # Create success state
            state = {
                'operation_id': operation_id,
                'target_snapshot_name': target_snapshot_name,
                'target_region': target_region,
                'source_region': source_region,
                'status': 'available',
                'message': 'No copy needed, regions are the same',
                'timestamp': int(time.time()),
                'success': True
            }
            save_state(operation_id, state)
            
            # Log audit event
            log_audit_event(
                operation_id=operation_id,
                event_type='check_copy_status',
                status='completed',
                details={
                    'snapshot_name': target_snapshot_name,
                    'source_region': source_region,
                    'target_region': target_region,
                    'status': 'available',
                    'note': 'No copy needed, regions are the same'
                }
            )
            
            # Update metrics
            duration = time.time() - start_time
            update_metrics(
                operation_id=operation_id,
                metric_name='check_copy_status_duration',
                value=duration,
                unit='Seconds'
            )
            
            # Trigger next step
            trigger_next_step(
                operation_id=operation_id,
                next_step='delete_rds',
                event_data=state
            )
            
            return {
                'statusCode': 200,
                'body': {
                    'message': 'No copy needed, regions are the same',
                    'operation_id': operation_id,
                    'snapshot_name': target_snapshot_name,
                    'region': target_region,
                    'status': 'available',
                    'next_step': 'delete_rds'
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
                event_type='check_copy_status',
                status='failed',
                details={
                    'error': error_msg,
                    'target_region': target_region
                }
            )
            
            # Update metrics for failure
            update_metrics(
                operation_id=operation_id,
                metric_name='check_copy_status_failures',
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
        
        # Check snapshot status
        try:
            # First check manual snapshots
            response = rds_client.describe_db_cluster_snapshots(
                DBClusterSnapshotIdentifier=target_snapshot_name,
                SnapshotType='manual'
            )
            
            if not response['DBClusterSnapshots']:
                # If no manual snapshots, check for shared snapshots
                response = rds_client.describe_db_cluster_snapshots(
                    DBClusterSnapshotIdentifier=target_snapshot_name,
                    SnapshotType='shared'
                )
                
            snapshots = response['DBClusterSnapshots']
            if not snapshots:
                # Add one more check for automated snapshots as fallback
                response = rds_client.describe_db_cluster_snapshots(
                    DBClusterSnapshotIdentifier=target_snapshot_name,
                    SnapshotType='automated'
                )
                snapshots = response['DBClusterSnapshots']
            
            if not snapshots:
                error_msg = f"Snapshot {target_snapshot_name} not found in region {target_region}"
                logger.error(error_msg)
                
                # Log audit event for failure
                log_audit_event(
                    operation_id=operation_id,
                    event_type='check_copy_status',
                    status='failed',
                    details={
                        'error': error_msg,
                        'target_snapshot_name': target_snapshot_name,
                        'target_region': target_region
                    }
                )
                
                # Update metrics for failure
                update_metrics(
                    operation_id=operation_id,
                    metric_name='check_copy_status_failures',
                    value=1,
                    unit='Count'
                )
                
                return {
                    'statusCode': 404,
                    'body': {
                        'message': error_msg,
                        'operation_id': operation_id
                    }
                }
            
            snapshot = snapshots[0]
            snapshot_status = snapshot['Status']
            logger.info(f"Snapshot {target_snapshot_name} status: {snapshot_status}")
            
            # Handle different snapshot statuses
            if snapshot_status == 'available':
                # Success - snapshot is available
                logger.info(f"Snapshot {target_snapshot_name} is available")
                
                # Create success state
                state = {
                    'operation_id': operation_id,
                    'target_snapshot_name': target_snapshot_name,
                    'target_region': target_region,
                    'source_region': source_region,
                    'status': snapshot_status,
                    'message': 'Snapshot copy completed successfully',
                    'timestamp': int(time.time()),
                    'success': True
                }
                save_state(operation_id, state)
                
                # Log audit event
                log_audit_event(
                    operation_id=operation_id,
                    event_type='check_copy_status',
                    status='completed',
                    details={
                        'snapshot_name': target_snapshot_name,
                        'source_region': source_region,
                        'target_region': target_region,
                        'status': snapshot_status
                    }
                )
                
                # Update metrics
                duration = time.time() - start_time
                update_metrics(
                    operation_id=operation_id,
                    metric_name='check_copy_status_duration',
                    value=duration,
                    unit='Seconds'
                )
                
                # Trigger next step
                trigger_next_step(
                    operation_id=operation_id,
                    next_step='delete_rds',
                    event_data=state
                )
                
                return {
                    'statusCode': 200,
                    'body': {
                        'message': 'Snapshot copy completed successfully',
                        'operation_id': operation_id,
                        'snapshot_name': target_snapshot_name,
                        'region': target_region,
                        'status': snapshot_status,
                        'next_step': 'delete_rds'
                    }
                }
                
            elif snapshot_status == 'failed':
                # Error - snapshot copy failed
                error_msg = f"Snapshot copy failed for {target_snapshot_name}"
                logger.error(error_msg)
                
                # Create error state
                error_state = {
                    'operation_id': operation_id,
                    'target_snapshot_name': target_snapshot_name,
                    'target_region': target_region,
                    'source_region': source_region,
                    'status': snapshot_status,
                    'error': error_msg,
                    'timestamp': int(time.time()),
                    'success': False
                }
                save_state(operation_id, error_state)
                
                # Log audit event for failure
                log_audit_event(
                    operation_id=operation_id,
                    event_type='check_copy_status',
                    status='failed',
                    details={
                        'error': error_msg,
                        'snapshot_name': target_snapshot_name,
                        'source_region': source_region,
                        'target_region': target_region,
                        'status': snapshot_status
                    }
                )
                
                # Update metrics for failure
                duration = time.time() - start_time
                update_metrics(
                    operation_id=operation_id,
                    metric_name='check_copy_status_duration',
                    value=duration,
                    unit='Seconds'
                )
                update_metrics(
                    operation_id=operation_id,
                    metric_name='check_copy_status_failures',
                    value=1,
                    unit='Count'
                )
                
                return {
                    'statusCode': 500,
                    'body': {
                        'message': error_msg,
                        'operation_id': operation_id,
                        'snapshot_name': target_snapshot_name,
                        'region': target_region,
                        'status': snapshot_status
                    }
                }
                
            else:
                # Still in progress (copying, creating, etc.)
                logger.info(f"Snapshot copy still in progress for {target_snapshot_name}, status: {snapshot_status}")
                
                # Create in-progress state
                state = {
                    'operation_id': operation_id,
                    'target_snapshot_name': target_snapshot_name,
                    'target_region': target_region,
                    'source_region': source_region,
                    'status': snapshot_status,
                    'message': f'Snapshot copy in progress, status: {snapshot_status}',
                    'timestamp': int(time.time()),
                    'success': True
                }
                save_state(operation_id, state)
                
                # Log audit event
                log_audit_event(
                    operation_id=operation_id,
                    event_type='check_copy_status',
                    status='in_progress',
                    details={
                        'snapshot_name': target_snapshot_name,
                        'source_region': source_region,
                        'target_region': target_region,
                        'status': snapshot_status
                    }
                )
                
                # Update metrics
                duration = time.time() - start_time
                update_metrics(
                    operation_id=operation_id,
                    metric_name='check_copy_status_duration',
                    value=duration,
                    unit='Seconds'
                )
                
                # Trigger the same step again to check status later
                trigger_next_step(
                    operation_id=operation_id,
                    next_step='check_copy_status',
                    event_data=state
                )
                
                return {
                    'statusCode': 202,
                    'body': {
                        'message': f'Snapshot copy in progress, status: {snapshot_status}',
                        'operation_id': operation_id,
                        'snapshot_name': target_snapshot_name,
                        'region': target_region,
                        'status': snapshot_status,
                        'next_step': 'check_copy_status'
                    }
                }
                
        except ClientError as e:
            # Handle specific AWS errors
            if e.response['Error']['Code'] == 'DBClusterSnapshotNotFoundFault':
                error_msg = f"Snapshot {target_snapshot_name} not found in region {target_region}"
                logger.warning(error_msg)
                
                # Log audit event
                log_audit_event(
                    operation_id=operation_id,
                    event_type='check_copy_status',
                    status='waiting',
                    details={
                        'snapshot_name': target_snapshot_name,
                        'source_region': source_region,
                        'target_region': target_region,
                        'status': 'waiting',
                        'note': 'Snapshot not found yet, copy may still be starting'
                    }
                )
                
                # Create waiting state
                state = {
                    'operation_id': operation_id,
                    'target_snapshot_name': target_snapshot_name,
                    'target_region': target_region,
                    'source_region': source_region,
                    'status': 'waiting',
                    'message': 'Snapshot not found yet, copy may still be starting',
                    'timestamp': int(time.time()),
                    'success': True
                }
                save_state(operation_id, state)
                
                # Update metrics
                duration = time.time() - start_time
                update_metrics(
                    operation_id=operation_id,
                    metric_name='check_copy_status_duration',
                    value=duration,
                    unit='Seconds'
                )
                
                # Trigger the same step again to check status later
                trigger_next_step(
                    operation_id=operation_id,
                    next_step='check_copy_status',
                    event_data=state
                )
                
                return {
                    'statusCode': 202,
                    'body': {
                        'message': 'Snapshot copy may still be starting',
                        'operation_id': operation_id,
                        'snapshot_name': target_snapshot_name,
                        'region': target_region,
                        'status': 'waiting',
                        'next_step': 'check_copy_status'
                    }
                }
            
            # Handle other AWS errors
            error_info = handle_aws_error(e, operation_id, 'check_copy_status')
            
            # Update metrics for failure
            update_metrics(
                operation_id=operation_id,
                metric_name='check_copy_status_failures',
                value=1,
                unit='Count'
            )
            
            return {
                'statusCode': error_info.get('statusCode', 500),
                'body': {
                    'message': error_info.get('message', 'Failed to check snapshot status'),
                    'operation_id': operation_id,
                    'error': error_info.get('error', str(e)),
                    'error_type': error_info.get('error_type')
                }
            }
            
    except Exception as e:
        error_msg = f"Error in check_copy_status: {str(e)}"
        logger.error(error_msg, exc_info=True)
        
        # Create error state
        error_state = {
            'operation_id': operation_id,
            'error': str(e),
            'target_snapshot_name': target_snapshot_name,
            'target_region': target_region,
            'source_region': source_region,
            'status': snapshot_status,
            'timestamp': int(time.time()),
            'success': False
        }
        save_state(operation_id, error_state)
        
        # Log audit event for failure
        log_audit_event(
            operation_id=operation_id,
            event_type='check_copy_status',
            status='failed',
            details={
                'error': str(e),
                'snapshot_name': target_snapshot_name,
                'source_region': source_region,
                'target_region': target_region
            }
        )
        
        # Update metrics for failure
        duration = time.time() - start_time if 'start_time' in locals() else 0
        update_metrics(
            operation_id=operation_id,
            metric_name='check_copy_status_duration',
            value=duration,
            unit='Seconds'
        )
        update_metrics(
            operation_id=operation_id,
            metric_name='check_copy_status_failures',
            value=1,
            unit='Count'
        )
        
        return {
            'statusCode': 500,
            'body': {
                'message': 'Failed to check snapshot status',
                'operation_id': operation_id,
                'error': str(e)
            }
        } 