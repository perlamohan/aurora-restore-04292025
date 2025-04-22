import json
import boto3
from utils.common import log_audit_event, logger

def lambda_handler(event, context):
    """
    Archive the snapshot after successful restore.
    """
    try:
        target_region = event['target_region']
        target_snapshot = event['target_snapshot']
        
        # Initialize RDS client in target region
        rds = boto3.client('rds', region_name=target_region)
        
        # Delete the copied snapshot
        rds.delete_db_cluster_snapshot(
            DBClusterSnapshotIdentifier=target_snapshot
        )
        
        # Log archiving
        log_audit_event(
            'aurora-restore-audit',
            'archive_snapshot',
            'SUCCESS',
            {
                'snapshot': target_snapshot,
                'region': target_region
            }
        )
        
        # Return event data for next step
        return event
        
    except Exception as e:
        logger.error(f"Error archiving snapshot: {str(e)}")
        log_audit_event(
            'aurora-restore-audit',
            'archive_snapshot',
            'FAILED',
            {'error': str(e)}
        )
        raise 