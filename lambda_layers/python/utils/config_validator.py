"""
Configuration Validator for Aurora Restore Solution

This module provides validation for configuration values using JSON Schema.
It ensures that all configuration values are of the correct type and within acceptable ranges.
"""

import json
import logging
from typing import Dict, Any, List, Optional, Union
from jsonschema import validate, ValidationError

# Configure logging
logger = logging.getLogger(__name__)

# Configuration schema
CONFIG_SCHEMA = {
    "type": "object",
    "properties": {
        "source_region": {"type": "string"},
        "target_region": {"type": "string"},
        "source_cluster_id": {"type": "string"},
        "target_cluster_id": {"type": "string"},
        "snapshot_prefix": {"type": "string"},
        "vpc_security_group_ids": {"type": "string"},
        "db_subnet_group_name": {"type": "string"},
        "kms_key_id": {"type": "string"},
        "master_credentials_secret_id": {"type": "string"},
        "app_credentials_secret_id": {"type": "string"},
        "copy_status_retry_delay": {"type": "integer", "minimum": 1},
        "restore_status_retry_delay": {"type": "integer", "minimum": 1},
        "delete_status_retry_delay": {"type": "integer", "minimum": 1},
        "max_copy_attempts": {"type": "integer", "minimum": 1},
        "copy_check_interval": {"type": "integer", "minimum": 1},
        "max_restore_attempts": {"type": "integer", "minimum": 1},
        "restore_check_interval": {"type": "integer", "minimum": 1},
        "skip_final_snapshot": {"type": "boolean"},
        "port": {"type": "integer", "minimum": 1, "maximum": 65535},
        "deletion_protection": {"type": "boolean"},
        "db_connection_timeout": {"type": "integer", "minimum": 1},
        "archive_snapshot": {"type": "boolean"},
        "environment": {"type": "string", "enum": ["dev", "test", "prod"]},
        "region": {"type": "string"},
        "account_id": {"type": "string"},
        "state_table_name": {"type": "string"},
        "audit_table_name": {"type": "string"},
        "log_level": {"type": "string", "enum": ["DEBUG", "INFO", "WARNING", "ERROR"]},
        "sns_topic_arn": {"type": "string"}
    },
    "required": [
        "source_region",
        "target_region",
        "source_cluster_id",
        "target_cluster_id",
        "state_table_name",
        "audit_table_name"
    ]
}

# Function-specific required fields
FUNCTION_REQUIRED_FIELDS = {
    "aurora-restore-snapshot-check": [
        "source_region",
        "source_cluster_id",
        "snapshot_prefix"
    ],
    "aurora-restore-copy-snapshot": [
        "source_region",
        "target_region",
        "kms_key_id"
    ],
    "aurora-restore-check-copy-status": [
        "source_region",
        "target_region",
        "max_copy_attempts",
        "copy_check_interval"
    ],
    "aurora-restore-delete-rds": [
        "target_region",
        "target_cluster_id",
        "skip_final_snapshot"
    ],
    "aurora-restore-restore-snapshot": [
        "target_region",
        "target_cluster_id",
        "db_subnet_group_name",
        "vpc_security_group_ids",
        "kms_key_id",
        "port",
        "deletion_protection"
    ],
    "aurora-restore-check-restore-status": [
        "target_region",
        "target_cluster_id",
        "max_restore_attempts",
        "restore_check_interval"
    ],
    "aurora-restore-setup-db-users": [
        "target_region",
        "target_cluster_id",
        "master_credentials_secret_id",
        "app_credentials_secret_id",
        "db_connection_timeout"
    ],
    "aurora-restore-archive-snapshot": [
        "target_region",
        "archive_snapshot"
    ],
    "aurora-restore-sns-notification": [
        "target_region",
        "sns_topic_arn"
    ]
}

class ConfigValidator:
    """
    Validator for configuration values.
    
    This class validates configuration values against a JSON Schema and
    ensures that all required fields for a specific function are present.
    """
    
    @staticmethod
    def validate_config(config: Dict[str, Any]) -> List[str]:
        """
        Validate configuration against the schema.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            List of validation errors, empty if valid
        """
        errors = []
        try:
            validate(instance=config, schema=CONFIG_SCHEMA)
        except ValidationError as e:
            errors.append(f"Schema validation error: {str(e)}")
        
        return errors
    
    @staticmethod
    def validate_function_config(config: Dict[str, Any], function_name: str) -> List[str]:
        """
        Validate configuration for a specific function.
        
        Args:
            config: Configuration dictionary
            function_name: Name of the Lambda function
            
        Returns:
            List of validation errors, empty if valid
        """
        errors = ConfigValidator.validate_config(config)
        
        # Check for function-specific required fields
        if function_name in FUNCTION_REQUIRED_FIELDS:
            for field in FUNCTION_REQUIRED_FIELDS[function_name]:
                if field not in config or not config[field]:
                    errors.append(f"Missing required field for {function_name}: {field}")
        
        return errors
    
    @staticmethod
    def validate_and_log(config: Dict[str, Any], function_name: str) -> bool:
        """
        Validate configuration and log errors.
        
        Args:
            config: Configuration dictionary
            function_name: Name of the Lambda function
            
        Returns:
            True if valid, False otherwise
        """
        errors = ConfigValidator.validate_function_config(config, function_name)
        
        if errors:
            for error in errors:
                logger.error(f"Configuration validation error for {function_name}: {error}")
            return False
        
        logger.info(f"Configuration validation successful for {function_name}")
        return True 