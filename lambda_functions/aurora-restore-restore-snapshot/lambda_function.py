import json
import boto3
from utils.common import get_config, log_audit_event, logger

def lambda_handler(event, context):
    """
    Restore the snapshot to create a new RDS cluster.
    """
    try:
        config = get_config()
        target_region = event['target_region']
        target_cluster_id = config['target_cluster_id']
        snapshot_arn = event['snapshot_arn']
        
        # Initialize RDS client in target region
        rds = boto3.client('rds', region_name=target_region)
        
        # Get the source cluster configuration
        source_response = rds.describe_db_clusters(
            DBClusterIdentifier=config['source_cluster_id']
        )
        source_cluster = source_response['DBClusters'][0]
        
        # Prepare restore parameters
        restore_params = {
            'DBClusterIdentifier': target_cluster_id,
            'SnapshotIdentifier': snapshot_arn,
            'Engine': source_cluster['Engine'],
            'EngineVersion': source_cluster['EngineVersion'],
            'DBSubnetGroupName': source_cluster['DBSubnetGroupName'],
            'VpcSecurityGroupIds': source_cluster['VpcSecurityGroupIds'],
            'Port': source_cluster['Port'],
            'DatabaseName': source_cluster.get('DatabaseName'),
            'EnableIAMDatabaseAuthentication': source_cluster.get('EnableIAMDatabaseAuthentication', False),
            'EnableCloudwatchLogsExports': source_cluster.get('EnableCloudwatchLogsExports', []),
            'KmsKeyId': 'alias/aws/rds'  # Use default KMS key
        }
        
        # Restore the cluster
        response = rds.restore_db_cluster_from_snapshot(**restore_params)
        
        # Log restore initiation
        log_audit_event(
            'aurora-restore-audit',
            'restore_snapshot',
            'INITIATED',
            {
                'cluster_id': target_cluster_id,
                'snapshot_arn': snapshot_arn,
                'region': target_region
            }
        )
        
        # Return event data for next step
        return {
            **event,
            'restore_status': response['DBCluster']['Status']
        }
        
    except Exception as e:
        logger.error(f"Error restoring snapshot: {str(e)}")
        log_audit_event(
            'aurora-restore-audit',
            'restore_snapshot',
            'FAILED',
            {'error': str(e)}
        )
        raise 