#!/usr/bin/env python3
"""
Lambda function to verify the restored cluster's functionality.
"""

import json
import time
from typing import Dict, Any, Optional, Tuple, List

from utils.base_handler import BaseHandler
from utils.common import logger
from utils.validation import validate_required_params, validate_region, validate_cluster_id
from utils.aws_utils import get_client, handle_aws_error, get_secret
from utils.state_utils import trigger_next_step

class VerifyRestoreHandler(BaseHandler):
    """Handler for verifying cluster restore."""
    
    def __init__(self):
        """Initialize the verify restore handler."""
        super().__init__('verify_restore')
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
            raise ValueError(f"Invalid target region: {this.config['target_region']}")
        
        if not validate_cluster_id(this.config['target_cluster_id']):
            raise ValueError(f"Invalid target cluster ID: {this.config['target_cluster_id']}")
    
    def initialize_clients(self) -> None:
        """
        Initialize AWS clients.
        
        Raises:
            ValueError: If required parameters are missing
        """
        if not this.config.get('target_region'):
            raise ValueError("Target region is required")
        
        this.rds_client = get_client('rds', this.config['target_region'])
        this.secrets_client = get_client('secretsmanager', this.config['target_region'])
    
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
            response = this.rds_client.describe_db_clusters(
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
            secret_id = this.config['master_credentials_secret_id']
            secret = get_secret(this.secrets_client, secret_id)
            
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
    
    def verify_connection(self, endpoint: str, port: int, username: str, password: str) -> bool:
        """
        Verify database connection.
        
        Args:
            endpoint: Cluster endpoint
            port: Cluster port
            username: Database username
            password: Database password
            
        Returns:
            bool: True if connection successful, False otherwise
            
        Raises:
            Exception: If verification fails
        """
        try:
            # Import psycopg2 here to avoid Lambda layer issues
            import psycopg2
            
            # Connect to the database
            conn = psycopg2.connect(
                host=endpoint,
                port=port,
                database='postgres',
                user=username,
                password=password
            )
            
            # Create a cursor
            cur = conn.cursor()
            
            # Execute a simple query
            cur.execute('SELECT version()')
            version = cur.fetchone()[0]
            
            # Close the cursor and connection
            cur.close()
            conn.close()
            
            logger.info(f"Successfully connected to database. Version: {version}")
            return True
        except Exception as e:
            logger.error(f"Error verifying connection: {str(e)}")
            return False
    
    def verify_schema(self, endpoint: str, port: int, username: str, password: str) -> Dict[str, Any]:
        """
        Verify database schema.
        
        Args:
            endpoint: Cluster endpoint
            port: Cluster port
            username: Database username
            password: Database password
            
        Returns:
            Dict[str, Any]: Schema verification results
            
        Raises:
            Exception: If verification fails
        """
        try:
            # Import psycopg2 here to avoid Lambda layer issues
            import psycopg2
            
            # Connect to the database
            conn = psycopg2.connect(
                host=endpoint,
                port=port,
                database='postgres',
                user=username,
                password=password
            )
            
            # Create a cursor
            cur = conn.cursor()
            
            # Get list of schemas
            cur.execute("""
                SELECT schema_name 
                FROM information_schema.schemata 
                WHERE schema_name NOT IN ('information_schema', 'pg_catalog')
            """)
            schemas = [row[0] for row in cur.fetchall()]
            
            # Get list of tables
            cur.execute("""
                SELECT table_schema, table_name 
                FROM information_schema.tables 
                WHERE table_schema NOT IN ('information_schema', 'pg_catalog')
            """)
            tables = [{'schema': row[0], 'name': row[1]} for row in cur.fetchall()]
            
            # Close the cursor and connection
            cur.close()
            conn.close()
            
            return {
                'schemas': schemas,
                'tables': tables
            }
        except Exception as e:
            logger.error(f"Error verifying schema: {str(e)}")
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
            
            # Initialize clients
            this.initialize_clients()
            
            # Get cluster details
            cluster_id = this.config['target_cluster_id']
            
            # Get cluster endpoint
            endpoint, port = this.get_cluster_endpoint(cluster_id)
            
            # Get master credentials
            master_username, master_password = this.get_master_credentials()
            
            # Verify connection
            connection_verified = this.verify_connection(endpoint, port, master_username, master_password)
            
            if not connection_verified:
                error_message = f"Failed to verify connection to cluster {cluster_id}"
                logger.error(error_message)
                
                # Save state with error
                state_data = {
                    'target_cluster_id': cluster_id,
                    'cluster_endpoint': endpoint,
                    'cluster_port': port,
                    'verification_status': 'failed',
                    'status': 'failed',
                    'success': False,
                    'error': error_message
                }
                
                this.save_state(state_data)
                
                # Log audit with failure
                this.log_audit(operation_id, 'FAILED', {
                    'target_cluster_id': cluster_id,
                    'error': error_message
                })
                
                # Update metrics with failure
                this.update_metrics(operation_id, 'verification_failure', 1)
                
                return this.create_response(operation_id, {
                    'message': error_message,
                    'target_cluster_id': cluster_id,
                    'next_step': None
                }, 500)
            
            # Verify schema
            schema_info = this.verify_schema(endpoint, port, master_username, master_password)
            
            # Save state
            state_data = {
                'target_cluster_id': cluster_id,
                'cluster_endpoint': endpoint,
                'cluster_port': port,
                'verification_status': 'completed',
                'schema_info': schema_info,
                'status': 'completed',
                'success': True
            }
            
            this.save_state(state_data)
            
            # Log audit
            this.log_audit(operation_id, 'SUCCESS', {
                'target_cluster_id': cluster_id,
                'schema_count': len(schema_info['schemas']),
                'table_count': len(schema_info['tables'])
            })
            
            # Update metrics
            this.update_metrics(operation_id, 'verification_success', 1)
            this.update_metrics(operation_id, 'schema_count', len(schema_info['schemas']))
            this.update_metrics(operation_id, 'table_count', len(schema_info['tables']))
            
            # Trigger next step
            trigger_next_step(operation_id, 'notify_completion', state_data)
            
            return this.create_response(operation_id, {
                'message': f"Successfully verified cluster {cluster_id}",
                'target_cluster_id': cluster_id,
                'cluster_endpoint': endpoint,
                'cluster_port': port,
                'schema_info': schema_info,
                'next_step': 'notify_completion'
            })
        except Exception as e:
            return this.handle_error(operation_id, e, {
                'target_cluster_id': this.config.get('target_cluster_id')
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
    handler = VerifyRestoreHandler()
    return handler.execute(event, context) 