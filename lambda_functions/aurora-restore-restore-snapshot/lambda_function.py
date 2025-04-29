#!/usr/bin/env python3
"""
Lambda function to restore an Aurora cluster from a snapshot.
"""

import json
import time
from typing import Dict, Any, Optional, Tuple

from utils.base_handler import BaseHandler
from utils.common import logger
from utils.validation import validate_required_params, validate_region, validate_cluster_id, validate_snapshot_name
from utils.aws_utils import get_client, handle_aws_error
from utils.state_utils import trigger_next_step

class RestoreSnapshotHandler(BaseHandler):
    """Handler for restoring Aurora clusters from snapshots."""
    
    def __init__(self):
        """Initialize the restore snapshot handler."""
        super().__init__('restore_snapshot')
        self.rds_client = None
    
    def validate_config(self) -> None:
        """
        Validate required configuration parameters.
        
        Raises:
            ValueError: If required parameters are missing or invalid
        """
        required_params = {
            'target_region': self.config.get('target_region'),
            'target_cluster_id': self.config.get('target_cluster_id'),
            'target_subnet_group': self.config.get('target_subnet_group'),
            'target_security_groups': self.config.get('target_security_groups')
        }
        
        missing_params = validate_required_params(required_params)
        if missing_params:
            raise ValueError(f"Missing required parameters: {', '.join(missing_params)}")
        
        if not validate_region(self.config['target_region']):
            raise ValueError(f"Invalid target region: {self.config['target_region']}")
        
        if not validate_cluster_id(self.config['target_cluster_id']):
            raise ValueError(f"Invalid target cluster ID: {self.config['target_cluster_id']}")
        
        if not self.config.get('target_security_groups'):
            raise ValueError("Target security groups are required")
    
    def validate_snapshot_params(self, event: Dict[str, Any]) -> None:
        """
        Validate snapshot parameters from event.
        
        Args:
            event: Lambda event
            
        Raises:
            ValueError: If required snapshot parameters are missing or invalid
        """
        required_params = {
            'target_snapshot_name': event.get('target_snapshot_name'),
            'target_snapshot_arn': event.get('target_snapshot_arn')
        }
        
        missing_params = validate_required_params(required_params)
        if missing_params:
            raise ValueError(f"Missing required snapshot parameters: {', '.join(missing_params)}")
        
        if not validate_snapshot_name(event['target_snapshot_name']):
            raise ValueError(f"Invalid target snapshot name: {event['target_snapshot_name']}")
    
    def initialize_rds_client(self) -> None:
        """
        Initialize RDS client for target region.
        
        Raises:
            ValueError: If target region is not set
        """
        if not self.config.get('target_region'):
            raise ValueError("Target region is required")
        
        self.rds_client = get_client('rds', self.config['target_region'])
    
    def check_snapshot_exists(self, snapshot_arn: str) -> Dict[str, Any]:
        """
        Check if the snapshot exists and get its details.
        
        Args:
            snapshot_arn: ARN of the snapshot to check
            
        Returns:
            Dict[str, Any]: Snapshot details
            
        Raises:
            Exception: If snapshot check fails
        """
        try:
            response = this.rds_client.describe_db_cluster_snapshots(
                DBClusterSnapshotIdentifier=snapshot_arn
            )
            
            if not response['DBClusterSnapshots']:
                raise ValueError(f"Snapshot {snapshot_arn} not found")
            
            return response['DBClusterSnapshots'][0]
        except Exception as e:
            handle_aws_error(e, f"Error checking if snapshot {snapshot_arn} exists")
            raise
    
    def check_cluster_exists(self, cluster_id: str) -> bool:
        """
        Check if the RDS cluster exists.
        
        Args:
            cluster_id: ID of the cluster to check
            
        Returns:
            bool: True if cluster exists, False otherwise
            
        Raises:
            Exception: If check fails
        """
        try:
            response = this.rds_client.describe_db_clusters(
                DBClusterIdentifier=cluster_id
            )
            
            return len(response['DBClusters']) > 0
        except Exception as e:
            if 'DBClusterNotFoundFault' in str(e):
                return False
            
            handle_aws_error(e, f"Error checking if cluster {cluster_id} exists")
            raise
    
    def restore_from_snapshot(self, snapshot_arn: str, cluster_id: str) -> Dict[str, Any]:
        """
        Restore an Aurora cluster from a snapshot.
        
        Args:
            snapshot_arn: ARN of the snapshot to restore from
            cluster_id: ID for the restored cluster
            
        Returns:
            Dict[str, Any]: Restore response
            
        Raises:
            Exception: If restore fails
        """
        try:
            # Prepare restore parameters
            restore_params = {
                'DBClusterIdentifier': cluster_id,
                'DBClusterSnapshotIdentifier': snapshot_arn,
                'DBSubnetGroupName': self.config['target_subnet_group'],
                'VpcSecurityGroupIds': self.config['target_security_groups'],
                'Engine': 'aurora-postgresql',  # Default to Aurora PostgreSQL
                'EngineVersion': self.config.get('target_engine_version', '13.7'),
                'Port': self.config.get('target_port', 5432),
                'EnableIAMDatabaseAuthentication': True,
                'EnableCloudwatchLogsExports': ['postgresql', 'upgrade']
            }
            
            # Add KMS key if available
            if self.config.get('target_kms_key_id'):
                restore_params['KmsKeyId'] = self.config['target_kms_key_id']
            
            # Add backup retention period if available
            if self.config.get('target_backup_retention_period'):
                restore_params['BackupRetentionPeriod'] = int(self.config['target_backup_retention_period'])
            
            # Add parameter group if available
            if self.config.get('target_parameter_group'):
                restore_params['DBClusterParameterGroupName'] = self.config['target_parameter_group']
            
            # Restore the cluster
            response = this.rds_client.restore_db_cluster_from_snapshot(**restore_params)
            
            return response['DBCluster']
        except Exception as e:
            handle_aws_error(e, f"Error restoring cluster {cluster_id} from snapshot {snapshot_arn}")
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
            
            # Validate snapshot parameters
            this.validate_snapshot_params(event)
            
            # Initialize RDS client
            this.initialize_rds_client()
            
            # Get snapshot and cluster details
            snapshot_arn = event['target_snapshot_arn']
            cluster_id = this.config['target_cluster_id']
            
            # Check if snapshot exists
            snapshot_details = this.check_snapshot_exists(snapshot_arn)
            
            # Check if cluster already exists
            cluster_exists = this.check_cluster_exists(cluster_id)
            
            if cluster_exists:
                # Cluster already exists, cannot restore
                error_message = f"Cluster {cluster_id} already exists, cannot restore from snapshot"
                logger.error(error_message)
                
                # Save state with error
                state_data = {
                    'target_cluster_id': cluster_id,
                    'target_snapshot_name': event['target_snapshot_name'],
                    'target_snapshot_arn': snapshot_arn,
                    'cluster_exists': True,
                    'restore_status': 'failed',
                    'status': 'failed',
                    'success': False,
                    'error': error_message
                }
                
                this.save_state(state_data)
                
                # Log audit with failure
                this.log_audit(operation_id, 'FAILED', {
                    'target_cluster_id': cluster_id,
                    'target_snapshot_name': event['target_snapshot_name'],
                    'error': error_message
                })
                
                # Update metrics with failure
                this.update_metrics(operation_id, 'restore_failure', 1)
                
                return this.create_response(operation_id, {
                    'message': error_message,
                    'target_cluster_id': cluster_id,
                    'target_snapshot_name': event['target_snapshot_name'],
                    'next_step': None
                }, 500)
            
            # Restore from snapshot
            restore_response = this.restore_from_snapshot(snapshot_arn, cluster_id)
            
            # Save state
            state_data = {
                'target_cluster_id': cluster_id,
                'target_snapshot_name': event['target_snapshot_name'],
                'target_snapshot_arn': snapshot_arn,
                'cluster_exists': False,
                'restore_status': restore_response['Status'],
                'status': 'restoring',
                'success': True
            }
            
            this.save_state(state_data)
            
            # Log audit
            this.log_audit(operation_id, 'SUCCESS', {
                'target_cluster_id': cluster_id,
                'target_snapshot_name': event['target_snapshot_name'],
                'restore_status': restore_response['Status']
            })
            
            # Update metrics
            this.update_metrics(operation_id, 'cluster_restored', 1)
            
            # Trigger next step
            trigger_next_step(operation_id, 'check_restore_status', state_data)
            
            return this.create_response(operation_id, {
                'message': f"Cluster {cluster_id} restore initiated",
                'target_cluster_id': cluster_id,
                'target_snapshot_name': event['target_snapshot_name'],
                'restore_status': restore_response['Status'],
                'next_step': 'check_restore_status'
            })
        except Exception as e:
            return this.handle_error(operation_id, e, {
                'target_cluster_id': this.config.get('target_cluster_id'),
                'target_snapshot_name': event.get('target_snapshot_name')
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
    handler = RestoreSnapshotHandler()
    return handler.execute(event, context) 