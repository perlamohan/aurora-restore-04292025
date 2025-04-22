import json
import boto3
import logging
from datetime import datetime
from botocore.exceptions import ClientError
from pythonjsonlogger import jsonlogger

# Configure JSON logging
logger = logging.getLogger()
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter()
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)
logger.setLevel(logging.INFO)

# Initialize AWS clients
ssm = boto3.client('ssm')
secrets = boto3.client('secretsmanager')
dynamodb = boto3.resource('dynamodb')
sns = boto3.client('sns')

def get_ssm_parameter(param_name: str) -> str:
    """Retrieve parameter from SSM Parameter Store."""
    try:
        response = ssm.get_parameter(Name=param_name, WithDecryption=True)
        return response['Parameter']['Value']
    except ClientError as e:
        logger.error(f"Error retrieving SSM parameter {param_name}: {str(e)}")
        raise

def get_secret(secret_name: str) -> dict:
    """Retrieve secret from Secrets Manager."""
    try:
        response = secrets.get_secret_value(SecretId=secret_name)
        return json.loads(response['SecretString'])
    except ClientError as e:
        logger.error(f"Error retrieving secret {secret_name}: {str(e)}")
        raise

def log_audit_event(table_name: str, event_type: str, status: str, details: dict):
    """Log audit event to DynamoDB."""
    table = dynamodb.Table(table_name)
    timestamp = datetime.utcnow().isoformat()
    
    item = {
        'event_id': f"{event_type}_{timestamp}",
        'event_type': event_type,
        'status': status,
        'timestamp': timestamp,
        'details': json.dumps(details)
    }
    
    try:
        table.put_item(Item=item)
        logger.info(f"Logged audit event: {event_type} - {status}")
    except ClientError as e:
        logger.error(f"Error logging audit event: {str(e)}")
        raise

def send_notification(topic_arn: str, subject: str, message: str):
    """Send notification via SNS."""
    try:
        sns.publish(
            TopicArn=topic_arn,
            Subject=subject,
            Message=message
        )
        logger.info(f"Sent notification: {subject}")
    except ClientError as e:
        logger.error(f"Error sending notification: {str(e)}")
        raise

def get_config():
    """Retrieve all required configuration parameters."""
    return {
        'source_account_id': get_ssm_parameter('/aurora-restore/source-account-id'),
        'target_account_id': get_ssm_parameter('/aurora-restore/target-account-id'),
        'source_region': get_ssm_parameter('/aurora-restore/source-region'),
        'target_region': get_ssm_parameter('/aurora-restore/target-region'),
        'source_cluster_id': get_ssm_parameter('/aurora-restore/source-cluster-id'),
        'target_cluster_id': get_ssm_parameter('/aurora-restore/target-cluster-id'),
        'snapshot_prefix': get_ssm_parameter('/aurora-restore/snapshot-prefix'),
        'db_credentials': get_secret('/aurora-restore/db-credentials')
    } 