#!/usr/bin/env python3
"""
Lambda function to check the status of a cluster deletion operation.
"""

import time
from typing import Dict, Any, Optional, List, Tuple

from utils.base_handler import BaseHandler
from utils.common import logger
from utils.validation import validate_required_params, validate_region
from utils.aws_utils import get_client, handle_aws_error
from utils.state_utils import trigger_next_step

class CheckDeleteStatusHandler(BaseHandler):
    """Handler for checking RDS cluster deletion status."""
    
    def __init__(self):
        """Initialize the check delete status handler."""
        super().__init__('check_delete_status')
        self.rds_client = None
    
    def validate_config(self) -> None:
        """
        Validate required configuration parameters.
        
        Raises:
            ValueError: If required parameters are missing or invalid
        """
        required_params = {
            'target_cluster_id': self.config.get('target_cluster_id'),
            'target_region': self.config.get('target_region')
        }
        
        missing_params = validate_required_params(required_params)
        if missing_params:
            raise ValueError(f"Missing required parameters: {', '.join(missing_params)}")
        
        if not validate_region(self.config['target_region']):
            raise ValueError(f"Invalid target region: {self.config['target_region']}")
    
    def get_cluster_details(self, event: Dict[str, Any]) -> Tuple[str, str]:
        """
        Get cluster details from event or state.
        
        Args:
            event: Lambda event
            
        Returns:
            Tuple[str, str]: Target cluster ID and region
            
        Raises:
            ValueError: If cluster details are missing
        """
        state = self.load_state()
        
        target_cluster_id = (
            state.get('target_cluster_id') or 
            event.get('target_cluster_id') or 
            self.config.get('target_cluster_id')
        )
        
        target_region = (
            state.get('target_region') or 
            event.get('target_region') or 
            self.config.get('target_region')
        )
        
        if not target_cluster_id:
            raise ValueError("Target cluster ID is required")
        
        if not target_region:
            raise ValueError("Target region is required")
        
        return target_cluster_id, target_region
    
    def initialize_rds_client(self, region: str) -> None:
        """
        Initialize RDS client for target region.
        
        Args:
            region: AWS region
            
        Raises:
            Exception: If client initialization fails
        """
        try:
            self.rds_client = get_client('rds', region_name=region)
        except Exception as e:
            raise Exception(f"Failed to create RDS client for region {region}: {str(e)}")
    
    def check_cluster_status(self, cluster_id: str) -> Optional[Dict[str, Any]]:
        """
        Check the status of the cluster.
        
        Args:
            cluster_id: ID of the cluster to check
            
        Returns:
            Optional[Dict[str, Any]]: Cluster details if found, None if deleted
            
        Raises:
            Exception: If check fails
        """
        try:
            logger.info(f"Checking status of cluster {cluster_id}")
            response = self.rds_client.describe_db_clusters(DBClusterIdentifier=cluster_id)
            if response['DBClusters']:
                cluster = response['DBClusters'][0]
                status = cluster['Status']
                logger.info(f"Cluster {cluster_id} status: {status}")
                return cluster
            return None
        except Exception as e:
            if 'DBClusterNotFoundFault' in str(e):
                logger.info(f"Cluster {cluster_id} has been deleted")
                return None
            handle_aws_error(e, self.operation_id, self.step_name)
            raise
    
    def handle_cluster_deleted(self, cluster_id: str, region: str) -> Dict[str, Any]:
        """
        Handle case where cluster has been deleted.
        
        Args:
            cluster_id: ID of the cluster
            region: AWS region
            
        Returns:
            Dict[str, Any]: Response
        """
        # Update state
        state = {
            'target_cluster_id': cluster_id,
            'target_region': region,
            'status': 'deleted',
            'success': True
        }
        
        self.save_state(state)
        
        # Trigger next step - restore snapshot
        trigger_next_step(
            self.operation_id,
            'restore_snapshot',
            state
        )
        
        return {
            'message': 'Cluster deletion complete',
            'cluster_id': cluster_id,
            'region': region,
            'next_step': 'restore_snapshot'
        }
    
    def handle_cluster_deleting(self, cluster_id: str, region: str, status: str) -> Dict[str, Any]:
        """
        Handle case where cluster is still being deleted.
        
        Args:
            cluster_id: ID of the cluster
            region: AWS region
            status: Current status of the cluster
            
        Returns:
            Dict[str, Any]: Response
        """
        # Update state
        state = {
            'target_cluster_id': cluster_id,
            'target_region': region,
            'status': status,
            'success': True
        }
        
        self.save_state(state)
        
        return {
            'message': 'Cluster deletion in progress',
            'cluster_id': cluster_id,
            'region': region,
            'status': status
        }
    
    def process(self, event: Dict[str, Any], context: Any) -> Dict[str, Any]:
        """
        Process the cluster deletion status check request.
        
        Args:
            event: Lambda event
            context: Lambda context
            
        Returns:
            dict: Processing result
        """
        start_time = time.time()
        
        # Validate configuration
        self.validate_config()
        
        # Get cluster details
        target_cluster_id, target_region = self.get_cluster_details(event)
        
        # Initialize RDS client
        self.initialize_rds_client(target_region)
        
        try:
            # Check cluster status
            cluster = self.check_cluster_status(target_cluster_id)
            
            if not cluster:
                # Cluster has been deleted
                result = self.handle_cluster_deleted(target_cluster_id, target_region)
                
                # Update metrics
                duration = time.time() - start_time
                self.update_metrics('check_delete_status_duration', duration, 'Seconds')
                
                return result
            
            # Cluster is still being deleted
            status = cluster['Status']
            result = self.handle_cluster_deleting(target_cluster_id, target_region, status)
            
            # Update metrics
            duration = time.time() - start_time
            self.update_metrics('check_delete_status_duration', duration, 'Seconds')
            
            return result
            
        except Exception as e:
            # Update metrics for failure
            duration = time.time() - start_time
            self.update_metrics('check_delete_status_duration', duration, 'Seconds')
            self.update_metrics('check_delete_status_failures', 1, 'Count')
            
            raise

# Initialize handler
handler = CheckDeleteStatusHandler()

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for checking RDS cluster deletion status.
    
    Args:
        event: Lambda event
        context: Lambda context
        
    Returns:
        dict: Response
    """
    return handler.execute(event, context) 