import json
import boto3
from utils.common import log_audit_event, logger

def lambda_handler(event, context):
    """
    Check the status of the snapshot copy operation.
    """
    try:
        # Extract snapshot details from event
        target_snapshot = event['target_snapshot']
        target_region = event['target_region']
        
        # Initialize RDS client in target region
        rds = boto3.client('rds', region_name=target_region)
        
        # Check snapshot status
        response = rds.describe_db_cluster_snapshots(
            DBClusterSnapshotIdentifier=target_snapshot
        )
        
        if not response['DBClusterSnapshots']:
            error_msg = f"Snapshot {target_snapshot} not found"
            logger.error(error_msg)
            log_audit_event(
                'aurora-restore-audit',
                'copy_status_check',
                'FAILED',
                {'error': error_msg}
            )
            raise Exception(error_msg)
        
        snapshot = response['DBClusterSnapshots'][0]
        status = snapshot['Status']
        
        # Log status check
        log_audit_event(
            'aurora-restore-audit',
            'copy_status_check',
            'CHECKED',
            {
                'snapshot': target_snapshot,
                'status': status
            }
        )
        
        # Return status and event data for next step
        return {
            **event,
            'copy_status': status,
            'snapshot_arn': snapshot['DBClusterSnapshotArn']
        }
        
    except Exception as e:
        logger.error(f"Error checking copy status: {str(e)}")
        log_audit_event(
            'aurora-restore-audit',
            'copy_status_check',
            'FAILED',
            {'error': str(e)}
        )
        raise 