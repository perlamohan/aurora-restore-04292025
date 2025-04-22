import json
import boto3
from utils.common import log_audit_event, logger

def lambda_handler(event, context):
    """
    Copy the snapshot from source account to target account.
    """
    try:
        # Extract snapshot details from event
        snapshot_name = event['snapshot_name']
        snapshot_arn = event['snapshot_arn']
        source_account_id = event['source_account_id']
        target_account_id = event['target_account_id']
        source_region = event['source_region']
        target_region = event['target_region']
        
        # Initialize RDS client in target region
        rds = boto3.client('rds', region_name=target_region)
        
        # Generate target snapshot name
        target_snapshot_name = f"{snapshot_name}-copy"
        
        # Copy snapshot to target account
        response = rds.copy_db_cluster_snapshot(
            SourceDBClusterSnapshotIdentifier=snapshot_arn,
            TargetDBClusterSnapshotIdentifier=target_snapshot_name,
            SourceRegion=source_region,
            KmsKeyId='alias/aws/rds'  # Use default KMS key
        )
        
        # Log the copy initiation
        log_audit_event(
            'aurora-restore-audit',
            'snapshot_copy',
            'INITIATED',
            {
                'source_snapshot': snapshot_name,
                'target_snapshot': target_snapshot_name,
                'source_account': source_account_id,
                'target_account': target_account_id,
                'source_region': source_region,
                'target_region': target_region
            }
        )
        
        # Return details for status check
        return {
            'source_snapshot': snapshot_name,
            'target_snapshot': target_snapshot_name,
            'source_account_id': source_account_id,
            'target_account_id': target_account_id,
            'source_region': source_region,
            'target_region': target_region,
            'copy_status': response['DBClusterSnapshot']['Status']
        }
        
    except Exception as e:
        logger.error(f"Error copying snapshot: {str(e)}")
        log_audit_event(
            'aurora-restore-audit',
            'snapshot_copy',
            'FAILED',
            {'error': str(e)}
        )
        raise 