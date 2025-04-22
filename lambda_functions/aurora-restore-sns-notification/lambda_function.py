import json
import boto3
from datetime import datetime
from utils.common import get_config, send_notification, log_audit_event, logger

def lambda_handler(event, context):
    """
    Send SNS notification about the restore process completion.
    """
    try:
        config = get_config()
        target_region = event['target_region']
        target_cluster_id = config['target_cluster_id']
        cluster_endpoint = event.get('cluster_endpoint')
        
        # Prepare notification message
        timestamp = datetime.utcnow().isoformat()
        message = {
            'status': 'SUCCESS',
            'timestamp': timestamp,
            'cluster_id': target_cluster_id,
            'region': target_region,
            'endpoint': cluster_endpoint,
            'event': event
        }
        
        # Send notification
        send_notification(
            topic_arn=config['sns_topic_arn'],
            subject=f"Aurora Restore Complete - {target_cluster_id}",
            message=json.dumps(message, indent=2)
        )
        
        # Log notification
        log_audit_event(
            'aurora-restore-audit',
            'sns_notification',
            'SUCCESS',
            {
                'cluster_id': target_cluster_id,
                'timestamp': timestamp
            }
        )
        
        return {
            'status': 'SUCCESS',
            'message': 'Notification sent successfully'
        }
        
    except Exception as e:
        logger.error(f"Error sending notification: {str(e)}")
        log_audit_event(
            'aurora-restore-audit',
            'sns_notification',
            'FAILED',
            {'error': str(e)}
        )
        raise 