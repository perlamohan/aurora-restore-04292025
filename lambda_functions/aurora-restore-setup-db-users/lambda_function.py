import json
import boto3
import psycopg2
from utils.common import get_config, log_audit_event, logger

def lambda_handler(event, context):
    """
    Set up database users and permissions after restore.
    """
    try:
        config = get_config()
        target_region = event['target_region']
        cluster_endpoint = event['cluster_endpoint']
        cluster_port = event['cluster_port']
        db_credentials = config['db_credentials']
        
        # Connect to the database
        conn = psycopg2.connect(
            host=cluster_endpoint,
            port=cluster_port,
            database=db_credentials['database'],
            user=db_credentials['master_username'],
            password=db_credentials['master_password']
        )
        
        try:
            with conn.cursor() as cur:
                # Create application user
                cur.execute(f"""
                    CREATE USER {db_credentials['app_username']} WITH PASSWORD '{db_credentials['app_password']}';
                    GRANT CONNECT ON DATABASE {db_credentials['database']} TO {db_credentials['app_username']};
                    GRANT USAGE ON SCHEMA public TO {db_credentials['app_username']};
                    GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {db_credentials['app_username']};
                    GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {db_credentials['app_username']};
                    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {db_credentials['app_username']};
                    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO {db_credentials['app_username']};
                """)
                
                # Create read-only user
                cur.execute(f"""
                    CREATE USER {db_credentials['readonly_username']} WITH PASSWORD '{db_credentials['readonly_password']}';
                    GRANT CONNECT ON DATABASE {db_credentials['database']} TO {db_credentials['readonly_username']};
                    GRANT USAGE ON SCHEMA public TO {db_credentials['readonly_username']};
                    GRANT SELECT ON ALL TABLES IN SCHEMA public TO {db_credentials['readonly_username']};
                    GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {db_credentials['readonly_username']};
                    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO {db_credentials['readonly_username']};
                    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO {db_credentials['readonly_username']};
                """)
                
                conn.commit()
                
                # Log success
                log_audit_event(
                    'aurora-restore-audit',
                    'setup_db_users',
                    'SUCCESS',
                    {
                        'cluster_endpoint': cluster_endpoint,
                        'users_created': [
                            db_credentials['app_username'],
                            db_credentials['readonly_username']
                        ]
                    }
                )
                
        finally:
            conn.close()
        
        # Return event data for next step
        return event
        
    except Exception as e:
        logger.error(f"Error setting up database users: {str(e)}")
        log_audit_event(
            'aurora-restore-audit',
            'setup_db_users',
            'FAILED',
            {'error': str(e)}
        )
        raise 