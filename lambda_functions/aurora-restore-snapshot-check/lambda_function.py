import json
import boto3
from datetime import datetime, timedelta
from utils.common import get_config, log_audit_event, logger

def lambda_handler(event, context):
    """
    Check if the daily snapshot exists in the source account.
    """
    try:
        config = get_config()
        rds = boto3.client('rds', region_name=config['source_region'])
        
        # Calculate yesterday's date for snapshot name
        yesterday = (datetime.utcnow() - timedelta(days=1)).strftime('%Y-%m-%d')
        snapshot_name = f"{config['snapshot_prefix']}-{yesterday}"
        
        # Check if snapshot exists
        response = rds.describe_db_cluster_snapshots(
            DBClusterIdentifier=config['source_cluster_id'],
            SnapshotType='automated',
            IncludeShared=True,
            IncludePublic=False
        )
        
        snapshot_found = False
        snapshot_arn = None
        
        for snapshot in response['DBClusterSnapshots']:
            if snapshot['DBClusterSnapshotIdentifier'] == snapshot_name:
                snapshot_found = True
                snapshot_arn = snapshot['DBClusterSnapshotArn']
                break
        
        if not snapshot_found:
            error_msg = f"Snapshot {snapshot_name} not found"
            logger.error(error_msg)
            log_audit_event(
                'aurora-restore-audit',
                'snapshot_check',
                'FAILED',
                {'error': error_msg}
            )
            raise Exception(error_msg)
        
        # Log success
        log_audit_event(
            'aurora-restore-audit',
            'snapshot_check',
            'SUCCESS',
            {
                'snapshot_name': snapshot_name,
                'snapshot_arn': snapshot_arn
            }
        )
        
        # Return snapshot details for next step
        return {
            'snapshot_name': snapshot_name,
            'snapshot_arn': snapshot_arn,
            'source_account_id': config['source_account_id'],
            'target_account_id': config['target_account_id'],
            'source_region': config['source_region'],
            'target_region': config['target_region']
        }
        
    except Exception as e:
        logger.error(f"Error in snapshot check: {str(e)}")
        log_audit_event(
            'aurora-restore-audit',
            'snapshot_check',
            'FAILED',
            {'error': str(e)}
        )
        raise 