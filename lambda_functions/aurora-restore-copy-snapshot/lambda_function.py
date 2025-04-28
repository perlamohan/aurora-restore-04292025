#!/usr/bin/env python3
"""
Lambda function to copy a snapshot from source to target region.
"""

import json
import time
import boto3
from typing import Dict, Any, Optional
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

def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    """
    Copy a snapshot from source to target region.
    
    Args:
        event: Lambda event containing:
            - operation_id: Optional operation ID for retry scenarios
            - snapshot_name: Name of the snapshot to copy
            - source_region: Source region of the snapshot
            - target_region: Target region for the copy
            - target_snapshot_name: Optional custom name for the target snapshot
        context: Lambda context
        
    Returns:
        dict: Response containing:
            - statusCode: HTTP status code
            - body: Response body with operation details
    """
    start_time = time.time()
    operation_id = get_operation_id(event)
    
    try:
        # Get configuration with fallbacks
        config = get_config()
        source_region = event.get('source_region') or config.get('source_region')
        target_region = event.get('target_region') or config.get('target_region')
        
        # Load previous state
        state = load_state(operation_id)
        if not state:
            logger.info(f"No previous state found for operation {operation_id}")
            state = {'operation_id': operation_id}
        elif not state.get('success', False):
            logger.warning(f"Previous step failed for operation {operation_id}")
            return {
                'statusCode': 400,
                'body': {
                    'message': 'Previous step failed',
                    'operation_id': operation_id,
                    'error': state.get('error', 'Unknown error')
                }
            }
        
        # Get snapshot details from previous state or event
        snapshot_name = state.get('snapshot_name') or event.get('snapshot_name')
        snapshot_arn = state.get('snapshot_arn') or event.get('snapshot_arn')
        
        # Validate required parameters
        required_params = {
            'snapshot_name': snapshot_name,
            'snapshot_arn': snapshot_arn,
            'source_region': source_region,
            'target_region': target_region
        }
        
        missing_params = validate_required_params(required_params)
        if missing_params:
            error_msg = f"Missing required parameters: {', '.join(missing_params)}"
            logger.error(error_msg)
            
            # Log audit event for failure
            log_audit_event(
                operation_id=operation_id,
                event_type='copy_snapshot',
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
        
        # Validate parameters - basic checks
        if not snapshot_name or len(snapshot_name) < 1:
            error_msg = "Invalid snapshot name"
            logger.error(error_msg)
            
            log_audit_event(
                operation_id=operation_id,
                event_type='copy_snapshot',
                status='failed',
                details={
                    'error': error_msg,
                    'snapshot_name': snapshot_name
                }
            )
            
            return {
                'statusCode': 400,
                'body': {
                    'message': error_msg,
                    'operation_id': operation_id
                }
            }
        
        if not source_region or not target_region:
            error_msg = "Invalid source or target region"
            logger.error(error_msg)
            
            log_audit_event(
                operation_id=operation_id,
                event_type='copy_snapshot',
                status='failed',
                details={
                    'error': error_msg,
                    'source_region': source_region,
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
        
        # Check if source and target regions are the same
        if source_region == target_region:
            logger.info(f"Source and target regions are the same: {source_region}")
            
            # Update state
            state = {
                'operation_id': operation_id,
                'snapshot_name': snapshot_name,
                'snapshot_arn': snapshot_arn,
                'source_region': source_region,
                'target_region': target_region,
                'target_snapshot_name': snapshot_name,
                'copy_status': 'available',
                'status': 'completed',
                'timestamp': int(time.time()),
                'success': True
            }
            save_state(operation_id, state)
            
            # Log audit event
            log_audit_event(
                operation_id=operation_id,
                event_type='copy_snapshot',
                details={
                    'snapshot_name': snapshot_name,
                    'snapshot_arn': snapshot_arn,
                    'source_region': source_region,
                    'target_region': target_region,
                    'target_snapshot_name': snapshot_name,
                    'note': 'Source and target regions are the same'
                }
            )
            
            # Update metrics
            duration = time.time() - start_time
            update_metrics(
                operation_id=operation_id,
                metric_name='copy_snapshot_duration',
                value=duration,
                unit='Seconds'
            )
            
            # Trigger next step
            trigger_next_step(
                operation_id=operation_id,
                next_step='check_copy_status',
                event_data=state
            )
            
            return {
                'statusCode': 200,
                'body': {
                    'message': 'No need to copy snapshot, regions are the same',
                    'operation_id': operation_id,
                    'snapshot_name': snapshot_name,
                    'source_region': source_region,
                    'target_region': target_region
                }
            }
        
        # Generate target snapshot name
        target_snapshot_name = event.get('target_snapshot_name') or state.get('target_snapshot_name') or f"{snapshot_name}-copy"
        
        # Create RDS client for target region
        target_rds_client = boto3.client('rds', region_name=target_region)
        
        # Copy snapshot
        try:
            logger.info(f"Copying snapshot {snapshot_name} from {source_region} to {target_region}")
            
            # Prepare copy parameters
            copy_params = {
                'SourceDBClusterSnapshotIdentifier': snapshot_arn,
                'TargetDBClusterSnapshotIdentifier': target_snapshot_name,
                'SourceRegion': source_region,
                'CopyTags': True
            }
            
            # Add KMS key if available
            kms_key_id = config.get('kms_key_id')
            if kms_key_id:
                copy_params['KmsKeyId'] = kms_key_id
            
            # Copy the snapshot
            response = target_rds_client.copy_db_cluster_snapshot(**copy_params)
            
            # Extract copy status and target snapshot details
            target_snapshot = response['DBClusterSnapshot']
            target_snapshot_name = target_snapshot['DBClusterSnapshotIdentifier']
            target_snapshot_arn = target_snapshot['DBClusterSnapshotArn']
            copy_status = target_snapshot['Status']
            
            # Update state
            state = {
                'operation_id': operation_id,
                'snapshot_name': snapshot_name,
                'snapshot_arn': snapshot_arn,
                'source_region': source_region,
                'target_region': target_region,
                'target_snapshot_name': target_snapshot_name,
                'target_snapshot_arn': target_snapshot_arn,
                'copy_status': copy_status,
                'status': 'copying',
                'timestamp': int(time.time()),
                'success': True
            }
            save_state(operation_id, state)
            
            # Log audit event
            log_audit_event(
                operation_id=operation_id,
                event_type='copy_snapshot',
                details={
                    'snapshot_name': snapshot_name,
                    'snapshot_arn': snapshot_arn,
                    'source_region': source_region,
                    'target_region': target_region,
                    'target_snapshot_name': target_snapshot_name,
                    'target_snapshot_arn': target_snapshot_arn,
                    'copy_status': copy_status
                }
            )
            
            # Update metrics
            duration = time.time() - start_time
            update_metrics(
                operation_id=operation_id,
                metric_name='copy_snapshot_duration',
                value=duration,
                unit='Seconds'
            )
            
            # Trigger next step
            trigger_next_step(
                operation_id=operation_id,
                next_step='check_copy_status',
                event_data=state,
                delay_seconds=60  # Check after 60 seconds
            )
            
            return {
                'statusCode': 200,
                'body': {
                    'message': 'Snapshot copy initiated',
                    'operation_id': operation_id,
                    'snapshot_name': snapshot_name,
                    'source_region': source_region,
                    'target_region': target_region,
                    'target_snapshot_name': target_snapshot_name,
                    'copy_status': copy_status
                }
            }
            
        except ClientError as e:
            error_info = handle_aws_error(e, operation_id, 'copy_snapshot')
            return {
                'statusCode': error_info.get('statusCode', 500),
                'body': {
                    'message': error_info.get('message', 'Failed to copy snapshot'),
                    'operation_id': operation_id,
                    'error': error_info.get('error', str(e)),
                    'error_type': error_info.get('error_type')
                }
            }
            
    except Exception as e:
        logger.error(f"Error in copy_snapshot: {str(e)}", exc_info=True)
        
        # Update state with error
        error_state = {
            'operation_id': operation_id,
            'error': str(e),
            'timestamp': int(time.time()),
            'success': False
        }
        save_state(operation_id, error_state)
        
        # Log audit event for failure
        log_audit_event(
            operation_id=operation_id,
            event_type='copy_snapshot',
            status='failed',
            details={
                'error': str(e)
            }
        )
        
        # Update metrics for failure
        duration = time.time() - start_time
        update_metrics(
            operation_id=operation_id,
            metric_name='copy_snapshot_duration',
            value=duration,
            unit='Seconds'
        )
        update_metrics(
            operation_id=operation_id,
            metric_name='copy_snapshot_failures',
            value=1,
            unit='Count'
        )
        
        return {
            'statusCode': 500,
            'body': {
                'message': 'Failed to copy snapshot',
                'operation_id': operation_id,
                'error': str(e)
            }
        } 