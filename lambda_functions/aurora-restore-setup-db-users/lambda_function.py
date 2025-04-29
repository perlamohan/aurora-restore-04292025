#!/usr/bin/env python3
"""
Lambda function to set up database users after a cluster restore.
"""

import json
import time
from typing import Dict, Any, Optional, Tuple, List

from utils.base_handler import BaseHandler
from utils.common import logger
from utils.validation import validate_required_params, validate_region, validate_cluster_id
from utils.aws_utils import get_client, handle_aws_error, get_secret
from utils.state_utils import trigger_next_step

class SetupDbUsersHandler(BaseHandler):
    """Handler for setting up database users."""
    
    def __init__(self):
        """Initialize the setup DB users handler."""
        super().__init__('setup_db_users')
        self.rds_client = None
        self.secrets_client = None
    
    def validate_config(self) -> None:
        """
        Validate required configuration parameters.
        
        Raises:
            ValueError: If required parameters are missing or invalid
        """
        required_params = {
            'target_region': self.config.get('target_region'),
            'target_cluster_id': self.config.get('target_cluster_id'),
            'master_credentials_secret_id': self.config.get('master_credentials_secret_id')
        }
        
        missing_params = validate_required_params(required_params)
        if missing_params:
            raise ValueError(f"Missing required parameters: {', '.join(missing_params)}")
        
        if not validate_region(self.config['target_region']):
            raise ValueError(f"Invalid target region: {self.config['target_region']}")
        
        if not validate_cluster_id(self.config['target_cluster_id']):
            raise ValueError(f"Invalid target cluster ID: {self.config['target_cluster_id']}")
    
    def initialize_clients(self) -> None:
        """
        Initialize AWS clients.
        
        Raises:
            ValueError: If required parameters are missing
        """
        if not self.config.get('target_region'):
            raise ValueError("Target region is required")
        
        self.rds_client = get_client('rds', self.config['target_region'])
        self.secrets_client = get_client('secretsmanager', self.config['target_region'])
    
    def get_cluster_endpoint(self, cluster_id: str) -> Tuple[str, int]:
        """
        Get the cluster endpoint and port.
        
        Args:
            cluster_id: ID of the cluster
            
        Returns:
            Tuple[str, int]: Cluster endpoint and port
            
        Raises:
            Exception: If endpoint retrieval fails
        """
        try:
            response = self.rds_client.describe_db_clusters(
                DBClusterIdentifier=cluster_id
            )
            
            if not response['DBClusters']:
                raise ValueError(f"Cluster {cluster_id} not found")
            
            cluster = response['DBClusters'][0]
            endpoint = cluster['Endpoint']
            port = cluster['Port']
            
            return endpoint, port
        except Exception as e:
            handle_aws_error(e, f"Error getting endpoint for cluster {cluster_id}")
            raise
    
    def get_master_credentials(self) -> Tuple[str, str]:
        """
        Get master database credentials from Secrets Manager.
        
        Returns:
            Tuple[str, str]: Master username and password
            
        Raises:
            Exception: If credentials retrieval fails
        """
        try:
            secret_id = self.config['master_credentials_secret_id']
            secret = get_secret(self.secrets_client, secret_id)
            
            if not secret:
                raise ValueError(f"Secret {secret_id} not found")
            
            username = secret.get('username')
            password = secret.get('password')
            
            if not username or not password:
                raise ValueError(f"Invalid credentials in secret {secret_id}")
            
            return username, password
        except Exception as e:
            handle_aws_error(e, "Error getting master credentials")
            raise
    
    def setup_users(self, endpoint: str, port: int, master_username: str, master_password: str) -> List[Dict[str, str]]:
        """
        Set up database users.
        
        Args:
            endpoint: Cluster endpoint
            port: Cluster port
            master_username: Master database username
            master_password: Master database password
            
        Returns:
            List[Dict[str, str]]: List of created users
            
        Raises:
            Exception: If user setup fails
        """
        try:
            # Import psycopg2 here to avoid Lambda layer issues
            import psycopg2
            
            # Connect to the database
            conn = psycopg2.connect(
                host=endpoint,
                port=port,
                database='postgres',
                user=master_username,
                password=master_password
            )
            
            # Create a cursor
            cur = conn.cursor()
            
            # Get list of users to create from config
            users = self.config.get('db_users', [])
            created_users = []
            
            for user in users:
                username = user.get('username')
                password = user.get('password')
                privileges = user.get('privileges', [])
                
                if not username or not password:
                    logger.warning(f"Skipping user setup: missing username or password")
                    continue
                
                # Create user
                cur.execute(f"CREATE USER {username} WITH PASSWORD '{password}'")
                
                # Grant privileges
                for privilege in privileges:
                    cur.execute(f"GRANT {privilege} TO {username}")
                
                created_users.append({
                    'username': username,
                    'privileges': privileges
                })
            
            # Commit the transaction
            conn.commit()
            
            # Close the cursor and connection
            cur.close()
            conn.close()
            
            return created_users
        except Exception as e:
            logger.error(f"Error setting up users: {str(e)}")
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
            operation_id = self.get_operation_id(event)
            
            # Validate configuration
            self.validate_config()
            
            # Initialize clients
            self.initialize_clients()
            
            # Get cluster details
            cluster_id = self.config['target_cluster_id']
            
            # Get cluster endpoint
            endpoint, port = self.get_cluster_endpoint(cluster_id)
            
            # Get master credentials
            master_username, master_password = self.get_master_credentials()
            
            # Set up users
            created_users = self.setup_users(endpoint, port, master_username, master_password)
            
            # Save state
            state_data = {
                'target_cluster_id': cluster_id,
                'cluster_endpoint': endpoint,
                'cluster_port': port,
                'users_created': created_users,
                'status': 'completed',
                'success': True
            }
            
            self.save_state(state_data)
            
            # Log audit
            self.log_audit(operation_id, 'SUCCESS', {
                'target_cluster_id': cluster_id,
                'users_created': len(created_users)
            })
            
            # Update metrics
            self.update_metrics(operation_id, 'users_created', len(created_users))
            
            # Trigger next step
            trigger_next_step(operation_id, 'verify_restore', state_data)
            
            return self.create_response(operation_id, {
                'message': f"Successfully set up {len(created_users)} users for cluster {cluster_id}",
                'target_cluster_id': cluster_id,
                'cluster_endpoint': endpoint,
                'cluster_port': port,
                'users_created': created_users,
                'next_step': 'verify_restore'
            })
        except Exception as e:
            return self.handle_error(operation_id, e, {
                'target_cluster_id': self.config.get('target_cluster_id')
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
    handler = SetupDbUsersHandler()
    return handler.execute(event, context) 