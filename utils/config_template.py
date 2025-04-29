"""
Configuration Template Generator for Aurora Restore Solution

This module provides utilities for generating configuration templates
and converting between different configuration formats.
"""

import json
import os
import logging
from typing import Dict, Any, List, Optional, Union

# Configure logging
logger = logging.getLogger(__name__)

# Default configuration template
DEFAULT_CONFIG_TEMPLATE = {
    "source_region": "us-east-1",
    "target_region": "us-west-2",
    "source_cluster_id": "your-source-cluster",
    "target_cluster_id": "your-target-cluster",
    "snapshot_prefix": "aurora-snapshot",
    "vpc_config": {
        "vpc_id": "vpc-xxxxxxxx",
        "subnet_ids": [
            "subnet-xxxxxxxx",
            "subnet-yyyyyyyy"
        ],
        "security_group_ids": [
            "sg-xxxxxxxx"
        ]
    },
    "restore_params": {
        "db_subnet_group_name": "your-db-subnet-group",
        "vpc_security_group_ids": [
            "sg-xxxxxxxx"
        ],
        "environment": "dev",
        "deletion_protection": False,
        "port": 5432,
        "availability_zones": [
            "us-west-2a",
            "us-west-2b"
        ],
        "enable_iam_database_authentication": True,
        "storage_encrypted": True
    },
    "master_credentials_secret_id": "aurora-restore/master-db-credentials",
    "app_credentials_secret_id": "aurora-restore/app-db-credentials",
    "sns_topic_arn": "arn:aws:sns:region:account:aurora-restore-notifications",
    "retry_params": {
        "copy_status_retry_delay": 60,
        "restore_status_retry_delay": 60,
        "delete_status_retry_delay": 60,
        "max_copy_attempts": 60,
        "copy_check_interval": 30,
        "max_restore_attempts": 60,
        "restore_check_interval": 30
    },
    "db_params": {
        "db_connection_timeout": 30
    },
    "archive_snapshot": True,
    "state_table_name": "aurora-restore-state",
    "audit_table_name": "aurora-restore-audit",
    "log_level": "INFO"
}

class ConfigTemplateGenerator:
    """
    Generator for configuration templates.
    
    This class provides utilities for generating configuration templates
    and converting between different configuration formats.
    """
    
    @staticmethod
    def generate_template(output_file: str = None) -> Dict[str, Any]:
        """
        Generate a configuration template.
        
        Args:
            output_file: Optional file path to save the template
            
        Returns:
            Configuration template dictionary
        """
        template = DEFAULT_CONFIG_TEMPLATE.copy()
        
        if output_file:
            with open(output_file, 'w') as f:
                json.dump(template, f, indent=4)
            logger.info(f"Configuration template saved to {output_file}")
        
        return template
    
    @staticmethod
    def generate_env_vars_template(output_file: str = None) -> Dict[str, str]:
        """
        Generate an environment variables template.
        
        Args:
            output_file: Optional file path to save the template
            
        Returns:
            Environment variables dictionary
        """
        template = {
            "SOURCE_REGION": "us-east-1",
            "TARGET_REGION": "us-west-2",
            "SOURCE_CLUSTER_ID": "your-source-cluster",
            "TARGET_CLUSTER_ID": "your-target-cluster",
            "SNAPSHOT_PREFIX": "aurora-snapshot",
            "VPC_SECURITY_GROUP_IDS": "sg-xxxxxxxx,sg-yyyyyyyy",
            "DB_SUBNET_GROUP_NAME": "your-db-subnet-group",
            "KMS_KEY_ID": "arn:aws:kms:region:account:key/your-kms-key-id",
            "MASTER_CREDENTIALS_SECRET_ID": "aurora-restore/master-db-credentials",
            "APP_CREDENTIALS_SECRET_ID": "aurora-restore/app-db-credentials",
            "COPY_STATUS_RETRY_DELAY": "60",
            "RESTORE_STATUS_RETRY_DELAY": "60",
            "DELETE_STATUS_RETRY_DELAY": "60",
            "MAX_COPY_ATTEMPTS": "60",
            "COPY_CHECK_INTERVAL": "30",
            "MAX_RESTORE_ATTEMPTS": "60",
            "RESTORE_CHECK_INTERVAL": "30",
            "SKIP_FINAL_SNAPSHOT": "true",
            "PORT": "5432",
            "DELETION_PROTECTION": "false",
            "DB_CONNECTION_TIMEOUT": "30",
            "ARCHIVE_SNAPSHOT": "true",
            "ENVIRONMENT": "dev",
            "STATE_TABLE_NAME": "aurora-restore-state",
            "AUDIT_TABLE_NAME": "aurora-restore-audit",
            "LOG_LEVEL": "INFO",
            "SNS_TOPIC_ARN": "arn:aws:sns:region:account:aurora-restore-notifications"
        }
        
        if output_file:
            with open(output_file, 'w') as f:
                for key, value in template.items():
                    f.write(f"{key}={value}\n")
            logger.info(f"Environment variables template saved to {output_file}")
        
        return template
    
    @staticmethod
    def generate_ssm_template(output_file: str = None) -> Dict[str, Any]:
        """
        Generate an SSM Parameter Store template.
        
        Args:
            output_file: Optional file path to save the template
            
        Returns:
            SSM Parameter Store template dictionary
        """
        template = {
            "/aurora-restore/dev/config": {
                "source_region": "us-east-1",
                "target_region": "us-west-2",
                "source_cluster_id": "your-source-cluster",
                "target_cluster_id": "your-target-cluster",
                "snapshot_prefix": "aurora-snapshot",
                "vpc_security_group_ids": "sg-xxxxxxxx,sg-yyyyyyyy",
                "db_subnet_group_name": "your-db-subnet-group",
                "kms_key_id": "arn:aws:kms:region:account:key/your-kms-key-id",
                "master_credentials_secret_id": "aurora-restore/master-db-credentials",
                "app_credentials_secret_id": "aurora-restore/app-db-credentials",
                "copy_status_retry_delay": 60,
                "restore_status_retry_delay": 60,
                "delete_status_retry_delay": 60,
                "max_copy_attempts": 60,
                "copy_check_interval": 30,
                "max_restore_attempts": 60,
                "restore_check_interval": 30,
                "skip_final_snapshot": True,
                "port": 5432,
                "deletion_protection": False,
                "db_connection_timeout": 30,
                "archive_snapshot": True,
                "environment": "dev",
                "state_table_name": "aurora-restore-state",
                "audit_table_name": "aurora-restore-audit",
                "log_level": "INFO",
                "sns_topic_arn": "arn:aws:sns:region:account:aurora-restore-notifications"
            }
        }
        
        if output_file:
            with open(output_file, 'w') as f:
                json.dump(template, f, indent=4)
            logger.info(f"SSM Parameter Store template saved to {output_file}")
        
        return template
    
    @staticmethod
    def convert_config_to_env_vars(config: Dict[str, Any]) -> Dict[str, str]:
        """
        Convert a configuration dictionary to environment variables.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            Environment variables dictionary
        """
        env_vars = {}
        
        # Map configuration keys to environment variable names
        key_mapping = {
            'source_region': 'SOURCE_REGION',
            'target_region': 'TARGET_REGION',
            'source_cluster_id': 'SOURCE_CLUSTER_ID',
            'target_cluster_id': 'TARGET_CLUSTER_ID',
            'snapshot_prefix': 'SNAPSHOT_PREFIX',
            'vpc_security_group_ids': 'VPC_SECURITY_GROUP_IDS',
            'db_subnet_group_name': 'DB_SUBNET_GROUP_NAME',
            'kms_key_id': 'KMS_KEY_ID',
            'master_credentials_secret_id': 'MASTER_CREDENTIALS_SECRET_ID',
            'app_credentials_secret_id': 'APP_CREDENTIALS_SECRET_ID',
            'copy_status_retry_delay': 'COPY_STATUS_RETRY_DELAY',
            'restore_status_retry_delay': 'RESTORE_STATUS_RETRY_DELAY',
            'delete_status_retry_delay': 'DELETE_STATUS_RETRY_DELAY',
            'max_copy_attempts': 'MAX_COPY_ATTEMPTS',
            'copy_check_interval': 'COPY_CHECK_INTERVAL',
            'max_restore_attempts': 'MAX_RESTORE_ATTEMPTS',
            'restore_check_interval': 'RESTORE_CHECK_INTERVAL',
            'skip_final_snapshot': 'SKIP_FINAL_SNAPSHOT',
            'port': 'PORT',
            'deletion_protection': 'DELETION_PROTECTION',
            'db_connection_timeout': 'DB_CONNECTION_TIMEOUT',
            'archive_snapshot': 'ARCHIVE_SNAPSHOT',
            'environment': 'ENVIRONMENT',
            'state_table_name': 'STATE_TABLE_NAME',
            'audit_table_name': 'AUDIT_TABLE_NAME',
            'log_level': 'LOG_LEVEL',
            'sns_topic_arn': 'SNS_TOPIC_ARN'
        }
        
        for key, value in config.items():
            if key in key_mapping:
                env_vars[key_mapping[key]] = str(value)
        
        return env_vars
    
    @staticmethod
    def convert_env_vars_to_config(env_vars: Dict[str, str]) -> Dict[str, Any]:
        """
        Convert environment variables to a configuration dictionary.
        
        Args:
            env_vars: Environment variables dictionary
            
        Returns:
            Configuration dictionary
        """
        config = {}
        
        # Map environment variable names to configuration keys
        key_mapping = {
            'SOURCE_REGION': 'source_region',
            'TARGET_REGION': 'target_region',
            'SOURCE_CLUSTER_ID': 'source_cluster_id',
            'TARGET_CLUSTER_ID': 'target_cluster_id',
            'SNAPSHOT_PREFIX': 'snapshot_prefix',
            'VPC_SECURITY_GROUP_IDS': 'vpc_security_group_ids',
            'DB_SUBNET_GROUP_NAME': 'db_subnet_group_name',
            'KMS_KEY_ID': 'kms_key_id',
            'MASTER_CREDENTIALS_SECRET_ID': 'master_credentials_secret_id',
            'APP_CREDENTIALS_SECRET_ID': 'app_credentials_secret_id',
            'COPY_STATUS_RETRY_DELAY': 'copy_status_retry_delay',
            'RESTORE_STATUS_RETRY_DELAY': 'restore_status_retry_delay',
            'DELETE_STATUS_RETRY_DELAY': 'delete_status_retry_delay',
            'MAX_COPY_ATTEMPTS': 'max_copy_attempts',
            'COPY_CHECK_INTERVAL': 'copy_check_interval',
            'MAX_RESTORE_ATTEMPTS': 'max_restore_attempts',
            'RESTORE_CHECK_INTERVAL': 'restore_check_interval',
            'SKIP_FINAL_SNAPSHOT': 'skip_final_snapshot',
            'PORT': 'port',
            'DELETION_PROTECTION': 'deletion_protection',
            'DB_CONNECTION_TIMEOUT': 'db_connection_timeout',
            'ARCHIVE_SNAPSHOT': 'archive_snapshot',
            'ENVIRONMENT': 'environment',
            'STATE_TABLE_NAME': 'state_table_name',
            'AUDIT_TABLE_NAME': 'audit_table_name',
            'LOG_LEVEL': 'log_level',
            'SNS_TOPIC_ARN': 'sns_topic_arn'
        }
        
        for key, value in env_vars.items():
            if key in key_mapping:
                config_key = key_mapping[key]
                
                # Convert string values to appropriate types
                if config_key in ['copy_status_retry_delay', 'restore_status_retry_delay', 
                                 'delete_status_retry_delay', 'max_copy_attempts', 
                                 'copy_check_interval', 'max_restore_attempts', 
                                 'restore_check_interval', 'port', 'db_connection_timeout']:
                    try:
                        config[config_key] = int(value)
                    except ValueError:
                        config[config_key] = value
                
                elif config_key in ['skip_final_snapshot', 'deletion_protection', 'archive_snapshot']:
                    config[config_key] = value.lower() in ['true', '1', 'yes', 'y']
                
                else:
                    config[config_key] = value
        
        return config 