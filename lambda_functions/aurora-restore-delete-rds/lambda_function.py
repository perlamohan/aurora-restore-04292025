import json
import boto3
from utils.common import get_config, log_audit_event, logger

def lambda_handler(event, context):
    """
    Delete the existing RDS cluster in the target account.
    """
    try:
        config = get_config()
        target_region = event['target_region']
        target_cluster_id = config['target_cluster_id']
        
        # Initialize RDS client in target region
        rds = boto3.client('rds', region_name=target_region)
        
        # Check if cluster exists
        try:
            response = rds.describe_db_clusters(
                DBClusterIdentifier=target_cluster_id
            )
            cluster_exists = len(response['DBClusters']) > 0
        except rds.exceptions.DBClusterNotFoundFault:
            cluster_exists = False
        
        if not cluster_exists:
            logger.info(f"Cluster {target_cluster_id} does not exist, skipping deletion")
            log_audit_event(
                'aurora-restore-audit',
                'delete_rds',
                'SKIPPED',
                {'reason': 'Cluster does not exist'}
            )
            return event
        
        # Delete the cluster
        rds.delete_db_cluster(
            DBClusterIdentifier=target_cluster_id,
            SkipFinalSnapshot=True  # Skip final snapshot as we're restoring from a backup
        )
        
        # Log deletion initiation
        log_audit_event(
            'aurora-restore-audit',
            'delete_rds',
            'INITIATED',
            {
                'cluster_id': target_cluster_id,
                'region': target_region
            }
        )
        
        # Return event data for next step
        return event
        
    except Exception as e:
        logger.error(f"Error deleting RDS cluster: {str(e)}")
        log_audit_event(
            'aurora-restore-audit',
            'delete_rds',
            'FAILED',
            {'error': str(e)}
        )
        raise 