#!/usr/bin/env python3
"""
Lambda function to set up database users and permissions after restore.
"""

import time
import psycopg2
from typing import Dict, Any
from botocore.exceptions import ClientError

from utils.common import (
    logger,
    get_config,
    log_audit_event,
    update_metrics,
    validate_required_params,
    validate_region,
    get_secret,
    get_operation_id,
    save_state,
    handle_aws_error
)
from utils.function_utils import validate_db_credentials

def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    """
    Set up database users and permissions after restore.
    
    Args:
        event: Lambda event containing:
            - operation_id: Optional operation ID for retry scenarios
            - target_cluster_id: ID of the restored cluster
            - target_region: Target region of the cluster
            - cluster_endpoint: Endpoint of the cluster
            - cluster_port: Port of the cluster
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
                event_type='setup_db_users',
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
                event_type='setup_db_users',
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
        
        # Get cluster details from state
        target_cluster_id = state.get('target_cluster_id') or config.get('target_cluster_id')
        target_region = state.get('target_region') or config.get('target_region')
        cluster_endpoint = state.get('cluster_endpoint')
        cluster_port = state.get('cluster_port')
        
        # Validate required parameters
        required_params = {
            'target_cluster_id': target_cluster_id,
            'target_region': target_region,
            'cluster_endpoint': cluster_endpoint,
            'cluster_port': cluster_port
        }
        
        missing_params = validate_required_params(required_params)
        if missing_params:
            error_msg = f"Missing required parameters: {', '.join(missing_params)}"
            logger.error(error_msg)
            
            # Log audit event for failure
            log_audit_event(
                operation_id=operation_id,
                event_type='setup_db_users',
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
                    'operation_id': operation_id,
                    'success': False
                }
            }
        
        # Validate target region
        if not validate_region(target_region):
            error_msg = f"Invalid region: {target_region}"
            logger.error(error_msg)
            
            # Log audit event for failure
            log_audit_event(
                operation_id=operation_id,
                event_type='setup_db_users',
                status='failed',
                details={
                    'error': error_msg,
                    'target_region': target_region
                }
            )
            
            return {
                'statusCode': 400,
                'body': {
                    'message': error_msg,
                    'operation_id': operation_id,
                    'success': False
                }
            }
        
        # Get database credentials from Secrets Manager
        try:
            # Get master credentials
            master_secret_id = config.get('master_credentials_secret_id')
            if not master_secret_id:
                error_msg = "Missing master_credentials_secret_id in config"
                logger.error(error_msg)
                log_audit_event(
                    operation_id=operation_id,
                    event_type='setup_db_users',
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
            
            logger.info(f"Retrieving master database credentials from secret {master_secret_id}")
            master_credentials = get_secret(master_secret_id)
            validate_db_credentials(master_credentials, is_master=True)
            
            # Get app credentials
            app_secret_id = config.get('app_credentials_secret_id')
            if not app_secret_id:
                error_msg = "Missing app_credentials_secret_id in config"
                logger.error(error_msg)
                log_audit_event(
                    operation_id=operation_id,
                    event_type='setup_db_users',
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
            
            logger.info(f"Retrieving app database credentials from secret {app_secret_id}")
            app_credentials = get_secret(app_secret_id)
            validate_db_credentials(app_credentials, is_master=False)
            
        except ClientError as e:
            error_details = handle_aws_error(e, operation_id, 'setup_db_users')
            
            # Update metrics
            update_metrics(
                operation_id=operation_id,
                metric_name='setup_db_users_failure_count',
                value=1,
                unit='Count'
            )
            
            return {
                'statusCode': error_details.get('statusCode', 500),
                'body': {
                    'message': error_details.get('message', 'Failed to retrieve database credentials'),
                    'operation_id': operation_id,
                    'error': error_details.get('error', str(e)),
                    'success': False
                }
            }
        except ValueError as e:
            error_msg = f"Invalid database credentials: {str(e)}"
            logger.error(error_msg)
            
            # Log audit event for failure
            log_audit_event(
                operation_id=operation_id,
                event_type='setup_db_users',
                status='failed',
                details={
                    'error': error_msg
                }
            )
            
            # Update metrics
            update_metrics(
                operation_id=operation_id,
                metric_name='setup_db_users_failure_count',
                value=1,
                unit='Count'
            )
            
            return {
                'statusCode': 400,
                'body': {
                    'message': error_msg,
                    'operation_id': operation_id,
                    'error': str(e),
                    'success': False
                }
            }
        except Exception as e:
            error_msg = f"Error retrieving database credentials: {str(e)}"
            logger.error(error_msg, exc_info=True)
            
            # Log audit event for failure
            log_audit_event(
                operation_id=operation_id,
                event_type='setup_db_users',
                status='failed',
                details={
                    'error': error_msg
                }
            )
            
            # Update metrics
            update_metrics(
                operation_id=operation_id,
                metric_name='setup_db_users_failure_count',
                value=1,
                unit='Count'
            )
            
            return {
                'statusCode': 500,
                'body': {
                    'message': 'Failed to retrieve database credentials',
                    'operation_id': operation_id,
                    'error': str(e),
                    'success': False
                }
            }
        
        # Connect to the database
        conn = None
        try:
            logger.info(f"Connecting to database at {cluster_endpoint}:{cluster_port}")
            conn = psycopg2.connect(
                host=cluster_endpoint,
                port=cluster_port,
                database=master_credentials['database'],
                user=master_credentials['username'],
                password=master_credentials['password'],
                connect_timeout=30  # Add timeout to avoid hanging indefinitely
            )
            
            with conn.cursor() as cur:
                # Create application user
                logger.info(f"Creating application user {app_credentials['app_username']}")
                cur.execute(f"""
                    DO $$
                    BEGIN
                        IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '{app_credentials['app_username']}') THEN
                            CREATE USER {app_credentials['app_username']} WITH PASSWORD '{app_credentials['app_password']}';
                        ELSE
                            ALTER USER {app_credentials['app_username']} WITH PASSWORD '{app_credentials['app_password']}';
                        END IF;
                    END
                    $$;
                    GRANT CONNECT ON DATABASE {master_credentials['database']} TO {app_credentials['app_username']};
                    GRANT USAGE ON SCHEMA public TO {app_credentials['app_username']};
                    GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {app_credentials['app_username']};
                    GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {app_credentials['app_username']};
                    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {app_credentials['app_username']};
                    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO {app_credentials['app_username']};
                """)
                
                # Create read-only user
                logger.info(f"Creating read-only user {app_credentials['readonly_username']}")
                cur.execute(f"""
                    DO $$
                    BEGIN
                        IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '{app_credentials['readonly_username']}') THEN
                            CREATE USER {app_credentials['readonly_username']} WITH PASSWORD '{app_credentials['readonly_password']}';
                        ELSE
                            ALTER USER {app_credentials['readonly_username']} WITH PASSWORD '{app_credentials['readonly_password']}';
                        END IF;
                    END
                    $$;
                    GRANT CONNECT ON DATABASE {master_credentials['database']} TO {app_credentials['readonly_username']};
                    GRANT USAGE ON SCHEMA public TO {app_credentials['readonly_username']};
                    GRANT SELECT ON ALL TABLES IN SCHEMA public TO {app_credentials['readonly_username']};
                    GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {app_credentials['readonly_username']};
                    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO {app_credentials['readonly_username']};
                    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO {app_credentials['readonly_username']};
                """)
                
                conn.commit()
                
                # Update state
                state_update = {
                    'operation_id': operation_id,
                    'target_cluster_id': target_cluster_id,
                    'target_region': target_region,
                    'cluster_endpoint': cluster_endpoint,
                    'cluster_port': cluster_port,
                    'setup_status': 'completed',
                    'users_created': [
                        app_credentials['app_username'],
                        app_credentials['readonly_username']
                    ],
                    'success': True
                }
                save_state(operation_id, state_update)
                
                # Log audit event
                log_audit_event(
                    operation_id=operation_id,
                    event_type='setup_db_users',
                    status='success',
                    details={
                        'target_cluster_id': target_cluster_id,
                        'target_region': target_region,
                        'cluster_endpoint': cluster_endpoint,
                        'users_created': [
                            app_credentials['app_username'],
                            app_credentials['readonly_username']
                        ],
                        'message': 'Database users setup complete'
                    }
                )
                
                # Update metrics
                duration = time.time() - start_time
                update_metrics(
                    operation_id=operation_id,
                    metric_name='setup_db_users_duration',
                    value=duration,
                    unit='Seconds'
                )
                
                update_metrics(
                    operation_id=operation_id,
                    metric_name='setup_db_users_success_count',
                    value=1,
                    unit='Count'
                )
                
                return {
                    'statusCode': 200,
                    'body': {
                        'message': 'Database users setup complete',
                        'operation_id': operation_id,
                        'target_cluster_id': target_cluster_id,
                        'target_region': target_region,
                        'setup_status': 'completed',
                        'users_created': [
                            app_credentials['app_username'],
                            app_credentials['readonly_username']
                        ],
                        'success': True
                    }
                }
                
        except psycopg2.Error as e:
            error_msg = f"Database error: {str(e)}"
            logger.error(error_msg, exc_info=True)
            
            # Log audit event for failure
            log_audit_event(
                operation_id=operation_id,
                event_type='setup_db_users',
                status='failed',
                details={
                    'error': error_msg,
                    'target_cluster_id': target_cluster_id,
                    'cluster_endpoint': cluster_endpoint
                }
            )
            
            # Update metrics
            update_metrics(
                operation_id=operation_id,
                metric_name='setup_db_users_failure_count',
                value=1,
                unit='Count'
            )
            
            return {
                'statusCode': 500,
                'body': {
                    'message': 'Database error during user setup',
                    'operation_id': operation_id,
                    'error': str(e),
                    'success': False
                }
            }
        finally:
            if conn:
                conn.close()
                
    except Exception as e:
        error_msg = f"Error in setup_db_users: {str(e)}"
        logger.error(error_msg, exc_info=True)
        
        # Log audit event for failure
        log_audit_event(
            operation_id=operation_id,
            event_type='setup_db_users',
            status='failed',
            details={
                'error': error_msg
            }
        )
        
        # Update metrics
        update_metrics(
            operation_id=operation_id,
            metric_name='setup_db_users_failure_count',
            value=1,
            unit='Count'
        )
        
        return {
            'statusCode': 500,
            'body': {
                'message': 'Failed to set up database users',
                'operation_id': operation_id,
                'error': str(e),
                'success': False
            }
        } 