#!/usr/bin/env python3
"""
Lambda function to restore a DB cluster from a snapshot.
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
    Restore a DB cluster from a snapshot.
    
    Args:
        event: Lambda event containing:
            - operation_id: Optional operation ID for retry scenarios
            - target_snapshot_name: Name of the snapshot to restore from
            - target_cluster_id: ID of the cluster to restore to
            - target_region: AWS region where the snapshot exists and cluster will be created
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
        
        # Load previous state
        state = load_state(operation_id)
        if not state:
            error_msg = f"No previous state found for operation {operation_id}"
            logger.error(error_msg)
            log_audit_event(
                operation_id=operation_id,
                event_type='restore_snapshot',
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
                event_type='restore_snapshot',
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
        
        # Get parameters from state or config
        target_snapshot_name = state.get('target_snapshot_name') or config.get('target_snapshot_name')
        target_cluster_id = state.get('target_cluster_id') or config.get('target_cluster_id')
        target_region = state.get('target_region') or config.get('target_region')
        
        # Validate required parameters
        required_params = {
            'target_snapshot_name': target_snapshot_name,
            'target_cluster_id': target_cluster_id,
            'target_region': target_region
        }
        
        missing_params = validate_required_params(required_params)
        if missing_params:
            error_msg = f"Missing required parameters: {', '.join(missing_params)}"
            logger.error(error_msg)
            log_audit_event(
                operation_id=operation_id,
                event_type='restore_snapshot',
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
                event_type='restore_snapshot',
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
                event_type='restore_snapshot',
                status='failed',
                details={'error': error_msg, 'target_region': target_region}
            )
            
            # Update metrics
            update_metrics(
                operation_id=operation_id,
                metric_name='restore_snapshot_failures',
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
        
        # Check if cluster already exists
        try:
            logger.info(f"Checking if cluster {target_cluster_id} already exists")
            existing_clusters = rds_client.describe_db_clusters(
                DBClusterIdentifier=target_cluster_id
            )
            
            if existing_clusters.get('DBClusters'):
                cluster_status = existing_clusters['DBClusters'][0]['Status']
                logger.info(f"Cluster {target_cluster_id} already exists with status {cluster_status}")
                
                # Update state
                state_update = {
                    'operation_id': operation_id,
                    'target_snapshot_name': target_snapshot_name,
                    'target_cluster_id': target_cluster_id,
                    'target_region': target_region,
                    'restore_status': 'already_exists',
                    'cluster_status': cluster_status,
                    'success': True
                }
                save_state(operation_id, state_update)
                
                # Log audit event
                log_audit_event(
                    operation_id=operation_id,
                    event_type='restore_snapshot',
                    status='success',
                    details={
                        'target_snapshot_name': target_snapshot_name,
                        'target_cluster_id': target_cluster_id,
                        'target_region': target_region,
                        'restore_status': 'already_exists',
                        'cluster_status': cluster_status,
                        'message': 'Cluster already exists, no action needed'
                    }
                )
                
                # Update metrics
                duration = time.time() - start_time
                update_metrics(
                    operation_id=operation_id,
                    metric_name='restore_snapshot_duration',
                    value=duration,
                    unit='Seconds'
                )
                
                return {
                    'statusCode': 200,
                    'body': {
                        'message': f"Cluster {target_cluster_id} already exists with status {cluster_status}",
                        'operation_id': operation_id,
                        'target_snapshot_name': target_snapshot_name,
                        'target_cluster_id': target_cluster_id,
                        'target_region': target_region,
                        'restore_status': 'already_exists',
                        'cluster_status': cluster_status,
                        'success': True
                    }
                }
                
        except ClientError as e:
            if e.response['Error']['Code'] != 'DBClusterNotFoundFault':
                error_details = handle_aws_error(e, operation_id, 'restore_snapshot')
                
                # Update metrics
                update_metrics(
                    operation_id=operation_id,
                    metric_name='restore_snapshot_failures',
                    value=1,
                    unit='Count'
                )
                
                return {
                    'statusCode': error_details.get('statusCode', 500),
                    'body': {
                        'message': error_details.get('message', 'Failed to check if cluster exists'),
                        'operation_id': operation_id,
                        'error': error_details.get('error', str(e)),
                        'success': False
                    }
                }
        
        # Get DB snapshot details to get parameters for restore
        try:
            logger.info(f"Getting details for snapshot {target_snapshot_name}")
            snapshot_response = rds_client.describe_db_cluster_snapshots(
                DBClusterSnapshotIdentifier=target_snapshot_name
            )
            
            if not snapshot_response.get('DBClusterSnapshots'):
                error_msg = f"Snapshot {target_snapshot_name} not found in region {target_region}"
                logger.error(error_msg)
                log_audit_event(
                    operation_id=operation_id,
                    event_type='restore_snapshot',
                    status='failed',
                    details={
                        'error': error_msg,
                        'target_snapshot_name': target_snapshot_name,
                        'target_region': target_region
                    }
                )
                
                # Update metrics
                update_metrics(
                    operation_id=operation_id,
                    metric_name='restore_snapshot_failures',
                    value=1,
                    unit='Count'
                )
                
                return {
                    'statusCode': 404,
                    'body': {
                        'message': error_msg,
                        'operation_id': operation_id,
                        'success': False
                    }
                }
            
            snapshot = snapshot_response['DBClusterSnapshots'][0]
            
            # Ensure snapshot is available
            if snapshot['Status'] != 'available':
                error_msg = f"Snapshot {target_snapshot_name} is not available (status: {snapshot['Status']})"
                logger.error(error_msg)
                log_audit_event(
                    operation_id=operation_id,
                    event_type='restore_snapshot',
                    status='failed',
                    details={
                        'error': error_msg,
                        'target_snapshot_name': target_snapshot_name,
                        'snapshot_status': snapshot['Status']
                    }
                )
                
                # Update metrics
                update_metrics(
                    operation_id=operation_id,
                    metric_name='restore_snapshot_failures',
                    value=1,
                    unit='Count'
                )
                
                return {
                    'statusCode': 400,
                    'body': {
                        'message': error_msg,
                        'operation_id': operation_id,
                        'snapshot_status': snapshot['Status'],
                        'success': False
                    }
                }
                
            # Get VPC and subnet group details from snapshot
            source_vpc = snapshot.get('VpcId')
            db_subnet_group = snapshot.get('DBSubnetGroup')
            
            # Additional restore parameters from config
            restore_params = config.get('restore_params', {})
            
            # Prepare restore parameters
            params = {
                'DBClusterIdentifier': target_cluster_id,
                'SnapshotIdentifier': target_snapshot_name,
                'Engine': snapshot.get('Engine', 'aurora-postgresql'),
                'DBSubnetGroupName': restore_params.get('db_subnet_group_name', db_subnet_group),
                'VpcSecurityGroupIds': restore_params.get('vpc_security_group_ids', []),
                'Tags': [
                    {
                        'Key': 'Name',
                        'Value': target_cluster_id
                    },
                    {
                        'Key': 'Environment',
                        'Value': restore_params.get('environment', 'dev')
                    },
                    {
                        'Key': 'CreatedBy',
                        'Value': 'aurora-restore-pipeline'
                    },
                    {
                        'Key': 'OperationId',
                        'Value': operation_id
                    }
                ],
                'CopyTagsToSnapshot': True,
                'DeletionProtection': restore_params.get('deletion_protection', False)
            }
            
            # Add optional parameters if specified in config
            if 'port' in restore_params:
                params['Port'] = restore_params['port']
                
            if 'availability_zones' in restore_params:
                params['AvailabilityZones'] = restore_params['availability_zones']
                
            if 'enable_iam_database_authentication' in restore_params:
                params['EnableIAMDatabaseAuthentication'] = restore_params['enable_iam_database_authentication']
                
            if 'storage_encrypted' in restore_params:
                params['StorageEncrypted'] = restore_params['storage_encrypted']
                
            if 'kms_key_id' in restore_params:
                params['KmsKeyId'] = restore_params['kms_key_id']
                
            # Restore from snapshot
            try:
                logger.info(f"Restoring cluster {target_cluster_id} from snapshot {target_snapshot_name}")
                response = rds_client.restore_db_cluster_from_snapshot(**params)
                
                # Extract cluster details
                cluster = response['DBCluster']
                
                # Update state
                state_update = {
                    'operation_id': operation_id,
                    'target_snapshot_name': target_snapshot_name,
                    'target_cluster_id': target_cluster_id,
                    'target_region': target_region,
                    'restore_status': 'in_progress',
                    'cluster_status': cluster['Status'],
                    'cluster_arn': cluster['DBClusterArn'],
                    'vpc_id': cluster['VpcId'],
                    'db_subnet_group': cluster['DBSubnetGroup'],
                    'success': True
                }
                save_state(operation_id, state_update)
                
                # Log audit event
                log_audit_event(
                    operation_id=operation_id,
                    event_type='restore_snapshot',
                    status='success',
                    details={
                        'target_snapshot_name': target_snapshot_name,
                        'target_cluster_id': target_cluster_id,
                        'target_region': target_region,
                        'restore_status': 'in_progress',
                        'cluster_arn': cluster['DBClusterArn'],
                        'cluster_status': cluster['Status'],
                        'message': 'Cluster restore initiated successfully'
                    }
                )
                
                # Update metrics
                duration = time.time() - start_time
                update_metrics(
                    operation_id=operation_id,
                    metric_name='restore_snapshot_duration',
                    value=duration,
                    unit='Seconds'
                )
                
                return {
                    'statusCode': 200,
                    'body': {
                        'message': f"Initiated restore of {target_cluster_id} from snapshot {target_snapshot_name}",
                        'operation_id': operation_id,
                        'target_snapshot_name': target_snapshot_name,
                        'target_cluster_id': target_cluster_id,
                        'target_region': target_region,
                        'restore_status': 'in_progress',
                        'cluster_status': cluster['Status'],
                        'success': True
                    }
                }
            
            except ClientError as e:
                error_details = handle_aws_error(e, operation_id, 'restore_snapshot')
                
                # Update metrics
                update_metrics(
                    operation_id=operation_id,
                    metric_name='restore_snapshot_failures',
                    value=1,
                    unit='Count'
                )
                
                return {
                    'statusCode': error_details.get('statusCode', 500),
                    'body': {
                        'message': error_details.get('message', 'Failed to restore snapshot'),
                        'operation_id': operation_id,
                        'error': error_details.get('error', str(e)),
                        'success': False
                    }
                }
                
        except ClientError as e:
            error_details = handle_aws_error(e, operation_id, 'restore_snapshot')
            
            # Update metrics
            update_metrics(
                operation_id=operation_id,
                metric_name='restore_snapshot_failures',
                value=1,
                unit='Count'
            )
            
            return {
                'statusCode': error_details.get('statusCode', 500),
                'body': {
                    'message': error_details.get('message', 'Failed to get snapshot details'),
                    'operation_id': operation_id,
                    'error': error_details.get('error', str(e)),
                    'success': False
                }
            }
            
    except Exception as e:
        error_msg = f"Error in restore_snapshot: {str(e)}"
        logger.error(error_msg, exc_info=True)
        
        # Log audit event for failure
        log_audit_event(
            operation_id=operation_id,
            event_type='restore_snapshot',
            status='failed',
            details={
                'error': error_msg
            }
        )
        
        # Update metrics
        update_metrics(
            operation_id=operation_id,
            metric_name='restore_snapshot_failures',
            value=1,
            unit='Count'
        )
        
        return {
            'statusCode': 500,
            'body': {
                'message': 'Failed to restore snapshot',
                'operation_id': operation_id,
                'error': str(e),
                'success': False
            }
        } 