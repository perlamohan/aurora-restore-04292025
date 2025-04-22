import json
import boto3
from utils.common import get_config, log_audit_event, logger

def lambda_handler(event, context):
    """
    Check the status of the cluster restore operation.
    """
    try:
        config = get_config()
        target_region = event['target_region']
        target_cluster_id = config['target_cluster_id']
        
        # Initialize RDS client in target region
        rds = boto3.client('rds', region_name=target_region)
        
        # Check cluster status
        response = rds.describe_db_clusters(
            DBClusterIdentifier=target_cluster_id
        )
        
        if not response['DBClusters']:
            error_msg = f"Cluster {target_cluster_id} not found"
            logger.error(error_msg)
            log_audit_event(
                'aurora-restore-audit',
                'restore_status_check',
                'FAILED',
                {'error': error_msg}
            )
            raise Exception(error_msg)
        
        cluster = response['DBClusters'][0]
        status = cluster['Status']
        
        # Log status check
        log_audit_event(
            'aurora-restore-audit',
            'restore_status_check',
            'CHECKED',
            {
                'cluster_id': target_cluster_id,
                'status': status
            }
        )
        
        # Return status and event data for next step
        return {
            **event,
            'restore_status': status,
            'cluster_endpoint': cluster.get('Endpoint'),
            'cluster_port': cluster.get('Port')
        }
        
    except Exception as e:
        logger.error(f"Error checking restore status: {str(e)}")
        log_audit_event(
            'aurora-restore-audit',
            'restore_status_check',
            'FAILED',
            {'error': str(e)}
        )
        raise 