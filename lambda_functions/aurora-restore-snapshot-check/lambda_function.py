#!/usr/bin/env python3
"""
Lambda function to check if the daily snapshot exists in the source account.
"""

import json
import time
import boto3
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
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
from utils.function_utils import validate_snapshot_name

def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    """
    Check if the daily snapshot exists and is shared with the target account.
    
    Args:
        event: Lambda event containing:
            - date: Optional date to check for snapshots (YYYY-MM-DD)
            - operation_id: Optional operation ID for retry scenarios
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
        
        # Get date from event or use yesterday
        date_str = event.get('date')
        if date_str:
            try:
                target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                error_msg = f"Invalid date format: {date_str}. Expected YYYY-MM-DD"
                logger.error(error_msg)
                
                # Log audit event for failure
                log_audit_event(
                    operation_id=operation_id,
                    event_type='snapshot_check',
                    status='failed',
                    details={
                        'error': error_msg,
                        'provided_date': date_str
                    }
                )
                
                # Update metrics for failure
                update_metrics(
                    operation_id=operation_id,
                    metric_name='snapshot_check_failures',
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
        else:
            target_date = (datetime.now() - timedelta(days=1)).date()
            logger.info(f"No date provided, using yesterday's date: {target_date.strftime('%Y-%m-%d')}")
        
        # Get required parameters
        source_region = config.get('source_region')
        source_cluster_id = config.get('source_cluster_id')
        
        # Validate required parameters
        required_params = {
            'source_region': source_region,
            'source_cluster_id': source_cluster_id
        }
        
        missing_params = validate_required_params(required_params)
        if missing_params:
            error_msg = f"Missing required parameters: {', '.join(missing_params)}"
            logger.error(error_msg)
            
            # Log audit event for failure
            log_audit_event(
                operation_id=operation_id,
                event_type='snapshot_check',
                status='failed',
                details={
                    'error': error_msg,
                    'missing_params': missing_params
                }
            )
            
            # Update metrics for failure
            update_metrics(
                operation_id=operation_id,
                metric_name='snapshot_check_failures',
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
        
        # Validate region
        if not validate_region(source_region):
            error_msg = f"Invalid source region: {source_region}"
            logger.error(error_msg)
            
            # Log audit event for failure
            log_audit_event(
                operation_id=operation_id,
                event_type='snapshot_check',
                status='failed',
                details={
                    'error': error_msg,
                    'source_region': source_region
                }
            )
            
            # Update metrics for failure
            update_metrics(
                operation_id=operation_id,
                metric_name='snapshot_check_failures',
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
        
        # Get snapshot prefix from config or use default
        snapshot_prefix = config.get('snapshot_prefix', 'aurora-snapshot')
        snapshot_name = f"{snapshot_prefix}-{target_date.strftime('%Y-%m-%d')}"
        logger.info(f"Looking for snapshot with name: {snapshot_name}")
        
        # Validate snapshot name
        if not validate_snapshot_name(snapshot_name):
            error_msg = f"Invalid snapshot name: {snapshot_name}"
            logger.error(error_msg)
            
            # Log audit event for failure
            log_audit_event(
                operation_id=operation_id,
                event_type='snapshot_check',
                status='failed',
                details={
                    'error': error_msg,
                    'snapshot_name': snapshot_name
                }
            )
            
            # Update metrics for failure
            update_metrics(
                operation_id=operation_id,
                metric_name='snapshot_check_failures',
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
        
        # Create RDS client for source region
        try:
            rds_client = boto3.client('rds', region_name=source_region)
        except Exception as e:
            error_msg = f"Failed to create RDS client for region {source_region}: {str(e)}"
            logger.error(error_msg)
            
            # Log audit event for failure
            log_audit_event(
                operation_id=operation_id,
                event_type='snapshot_check',
                status='failed',
                details={
                    'error': error_msg,
                    'source_region': source_region
                }
            )
            
            # Update metrics for failure
            update_metrics(
                operation_id=operation_id,
                metric_name='snapshot_check_failures',
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
        
        # Check if snapshot exists
        try:
            # Save initial state before checking for snapshot
            initial_state = {
                'operation_id': operation_id,
                'snapshot_name': snapshot_name,
                'source_region': source_region,
                'source_cluster_id': source_cluster_id,
                'target_region': config.get('target_region'),
                'target_cluster_id': config.get('target_cluster_id'),
                'status': 'checking',
                'timestamp': int(time.time())
            }
            save_state(operation_id, initial_state)
            
            logger.info(f"Checking for snapshot {snapshot_name} in region {source_region}, including snapshots shared with this account")
            
            # Check shared snapshots first
            snapshot_found, snapshot_details = check_snapshot(
                rds_client, 
                snapshot_name, 
                'shared', 
                source_region
            )
            
            # If not found in shared, check manual snapshots
            if not snapshot_found:
                logger.info(f"Trying to find snapshot {snapshot_name} in manual snapshots")
                snapshot_found, snapshot_details = check_snapshot(
                    rds_client, 
                    snapshot_name, 
                    'manual', 
                    source_region
                )
            
            # If snapshot not found in either location
            if not snapshot_found:
                error_msg = f"Snapshot {snapshot_name} not found in shared or manual snapshots in region {source_region}"
                logger.error(error_msg)
                
                # Log audit event for failure
                log_audit_event(
                    operation_id=operation_id,
                    event_type='snapshot_check',
                    status='failed',
                    details={
                        'error': error_msg,
                        'source_region': source_region,
                        'snapshot_name': snapshot_name,
                        'source_cluster_id': source_cluster_id
                    }
                )
                
                # Update metrics for failure
                duration = time.time() - start_time
                update_metrics(
                    operation_id=operation_id,
                    metric_name='snapshot_check_duration',
                    value=duration,
                    unit='Seconds'
                )
                update_metrics(
                    operation_id=operation_id,
                    metric_name='snapshot_check_failures',
                    value=1,
                    unit='Count'
                )
                
                # Save failed state
                failed_state = {
                    'operation_id': operation_id,
                    'snapshot_name': snapshot_name,
                    'source_region': source_region,
                    'source_cluster_id': source_cluster_id,
                    'target_region': config.get('target_region'),
                    'target_cluster_id': config.get('target_cluster_id'),
                    'status': 'failed',
                    'error': error_msg,
                    'timestamp': int(time.time()),
                    'success': False
                }
                save_state(operation_id, failed_state)
                
                return {
                    'statusCode': 404,
                    'body': {
                        'message': error_msg,
                        'operation_id': operation_id,
                        'source_region': source_region,
                        'snapshot_name': snapshot_name
                    }
                }
            
            # Extract snapshot details
            snapshot_arn = snapshot_details.get('DBClusterSnapshotArn')
            snapshot_created = snapshot_details.get('SnapshotCreateTime')
            snapshot_created_str = snapshot_created.isoformat() if snapshot_created else None
            
            # Create state object
            state = {
                'operation_id': operation_id,
                'snapshot_name': snapshot_name,
                'snapshot_arn': snapshot_arn,
                'source_region': source_region,
                'target_region': config.get('target_region'),
                'source_cluster_id': source_cluster_id,
                'target_cluster_id': config.get('target_cluster_id'),
                'snapshot_type': snapshot_details.get('SnapshotType'),
                'snapshot_status': snapshot_details.get('Status'),
                'snapshot_size': snapshot_details.get('AllocatedStorage'),
                'snapshot_encrypted': snapshot_details.get('StorageEncrypted', False),
                'snapshot_created': snapshot_created_str,
                'timestamp': int(time.time()),
                'status': 'found',
                'success': True
            }
            
            # Save state
            save_state(operation_id, state)
            
            # Log audit event
            log_audit_event(
                operation_id=operation_id,
                event_type='snapshot_check',
                status='success',
                details={
                    'snapshot_name': snapshot_name,
                    'snapshot_arn': snapshot_arn,
                    'source_region': source_region,
                    'snapshot_status': snapshot_details.get('Status')
                }
            )
            
            # Update metrics
            duration = time.time() - start_time
            update_metrics(
                operation_id=operation_id,
                metric_name='snapshot_check_duration',
                value=duration,
                unit='Seconds'
            )
            
            # Trigger next step
            trigger_next_step(
                operation_id=operation_id,
                next_step='copy_snapshot',
                event_data=state
            )
            
            return {
                'statusCode': 200,
                'body': {
                    'message': 'Snapshot found successfully',
                    'operation_id': operation_id,
                    'snapshot_name': snapshot_name,
                    'snapshot_arn': snapshot_arn,
                    'source_region': source_region,
                    'target_region': config.get('target_region'),
                    'snapshot_status': snapshot_details.get('Status')
                }
            }
            
        except ClientError as e:
            error_info = handle_aws_error(e, operation_id, 'snapshot_check')
            
            # Save error state
            error_state = {
                'operation_id': operation_id,
                'snapshot_name': snapshot_name,
                'source_region': source_region,
                'error': error_info.get('error', str(e)),
                'error_type': error_info.get('error_type'),
                'timestamp': int(time.time()),
                'status': 'failed',
                'success': False
            }
            save_state(operation_id, error_state)
            
            # Update metrics for duration and failure
            duration = time.time() - start_time
            update_metrics(
                operation_id=operation_id,
                metric_name='snapshot_check_duration',
                value=duration,
                unit='Seconds'
            )
            
            return {
                'statusCode': error_info.get('statusCode', 500),
                'body': {
                    'message': error_info.get('message', 'Failed to check snapshot'),
                    'operation_id': operation_id,
                    'error': error_info.get('error', str(e)),
                    'error_type': error_info.get('error_type')
                }
            }
            
    except Exception as e:
        logger.error(f"Error in snapshot_check: {str(e)}", exc_info=True)
        
        # Create error state
        error_state = {
            'operation_id': operation_id,
            'error': str(e),
            'timestamp': int(time.time()),
            'status': 'failed',
            'success': False
        }
        save_state(operation_id, error_state)
        
        # Log audit event for failure
        log_audit_event(
            operation_id=operation_id,
            event_type='snapshot_check',
            status='failed',
            details={
                'error': str(e)
            }
        )
        
        # Update metrics for failure
        duration = time.time() - start_time
        update_metrics(
            operation_id=operation_id,
            metric_name='snapshot_check_duration',
            value=duration,
            unit='Seconds'
        )
        update_metrics(
            operation_id=operation_id,
            metric_name='snapshot_check_failures',
            value=1,
            unit='Count'
        )
        
        return {
            'statusCode': 500,
            'body': {
                'message': 'Failed to check snapshot',
                'operation_id': operation_id,
                'error': str(e)
            }
        }

def check_snapshot(rds_client: Any, snapshot_name: str, snapshot_type: str, region: str) -> Tuple[bool, Optional[Dict]]:
    """
    Check if a snapshot exists with the given name and type.
    
    Args:
        rds_client: Boto3 RDS client
        snapshot_name: Name of the snapshot to check
        snapshot_type: Type of snapshot (shared, manual, etc)
        region: AWS region to check in
        
    Returns:
        Tuple containing:
            - Boolean indicating if snapshot was found
            - Dictionary of snapshot details if found, None otherwise
    """
    try:
        response = rds_client.describe_db_cluster_snapshots(
            SnapshotType=snapshot_type,
            IncludeShared=True,
            IncludePublic=False
        )
        
        for snapshot in response['DBClusterSnapshots']:
            if snapshot['DBClusterSnapshotIdentifier'] == snapshot_name:
                return True, snapshot
        
        return False, None
    except ClientError as e:
        logger.warning(f"Error checking {snapshot_type} snapshots in {region}: {str(e)}")
        return False, None 