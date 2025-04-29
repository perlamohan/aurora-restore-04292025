"""
Configuration Manager for Aurora Restore Solution

This module provides a centralized configuration management system that:
1. Loads configuration from multiple sources with priority
2. Validates configuration values
3. Provides type-safe access to configuration
4. Supports environment-specific configuration
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List, Union
from enum import Enum
import boto3
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger(__name__)

class ConfigSource(Enum):
    """Enum for configuration sources in order of priority"""
    EVENT = 1
    STATE = 2
    ENV_VAR = 3
    SSM = 4
    DEFAULT = 5

class ConfigManager:
    """
    Centralized configuration manager for Aurora restore operations.
    
    This class handles loading, validating, and providing access to configuration
    from multiple sources with a defined priority order.
    """
    
    def __init__(self, environment: str = None):
        """
        Initialize the configuration manager.
        
        Args:
            environment: The environment name (dev, test, prod)
        """
        self.environment = environment or os.environ.get('ENVIRONMENT', 'dev')
        self.region = os.environ.get('AWS_REGION', 'us-east-1')
        self.account_id = os.environ.get('AWS_ACCOUNT_ID', '')
        self._config = {}
        self._config_sources = {}
        self._ssm_client = None
        
    @property
    def ssm_client(self):
        """Lazy loading of SSM client"""
        if self._ssm_client is None:
            self._ssm_client = boto3.client('ssm', region_name=self.region)
        return self._ssm_client
    
    def load_config(self, event: Dict[str, Any] = None, state: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Load configuration from all sources with priority.
        
        Args:
            event: Lambda event data
            state: State data from DynamoDB
            
        Returns:
            Dict containing the complete configuration
        """
        # Start with default configuration
        self._config = self._get_default_config()
        self._config_sources = {k: ConfigSource.DEFAULT for k in self._config.keys()}
        
        # Load from SSM Parameter Store
        self._load_from_ssm()
        
        # Load from environment variables
        self._load_from_env_vars()
        
        # Load from state
        if state:
            self._load_from_state(state)
            
        # Load from event (highest priority)
        if event:
            self._load_from_event(event)
            
        # Validate the configuration
        self._validate_config()
        
        return self._config
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration values"""
        return {
            'source_region': '',
            'target_region': '',
            'source_cluster_id': '',
            'target_cluster_id': '',
            'snapshot_prefix': 'aurora-snapshot',
            'vpc_security_group_ids': '',
            'db_subnet_group_name': '',
            'kms_key_id': '',
            'master_credentials_secret_id': 'aurora-restore/master-db-credentials',
            'app_credentials_secret_id': 'aurora-restore/app-db-credentials',
            'copy_status_retry_delay': 60,
            'restore_status_retry_delay': 60,
            'delete_status_retry_delay': 60,
            'max_copy_attempts': 60,
            'copy_check_interval': 30,
            'max_restore_attempts': 60,
            'restore_check_interval': 30,
            'skip_final_snapshot': True,
            'port': 5432,
            'deletion_protection': False,
            'db_connection_timeout': 30,
            'archive_snapshot': True,
            'environment': self.environment,
            'region': self.region,
            'account_id': self.account_id,
            'state_table_name': 'aurora-restore-state',
            'audit_table_name': 'aurora-restore-audit',
            'log_level': 'INFO',
            'sns_topic_arn': f'arn:aws:sns:{self.region}:{self.account_id}:aurora-restore-notifications'
        }
    
    def _load_from_ssm(self) -> None:
        """Load configuration from SSM Parameter Store"""
        try:
            # Try to get the environment-specific config
            ssm_path = f'/aurora-restore/{self.environment}/config'
            response = self.ssm_client.get_parameter(
                Name=ssm_path,
                WithDecryption=True
            )
            
            if response and 'Parameter' in response and 'Value' in response['Parameter']:
                ssm_config = json.loads(response['Parameter']['Value'])
                for key, value in ssm_config.items():
                    self._config[key] = value
                    self._config_sources[key] = ConfigSource.SSM
                logger.info(f"Loaded configuration from SSM: {ssm_path}")
        except ClientError as e:
            if e.response['Error']['Code'] == 'ParameterNotFound':
                logger.warning(f"SSM parameter {ssm_path} not found")
            else:
                logger.error(f"Error loading SSM config: {str(e)}")
        except Exception as e:
            logger.warning(f"Failed to load SSM config: {str(e)}")
    
    def _load_from_env_vars(self) -> None:
        """Load configuration from environment variables"""
        env_var_mapping = {
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
            'STATE_TABLE_NAME': 'state_table_name',
            'AUDIT_TABLE_NAME': 'audit_table_name',
            'LOG_LEVEL': 'log_level',
            'SNS_TOPIC_ARN': 'sns_topic_arn'
        }
        
        for env_var, config_key in env_var_mapping.items():
            if env_var in os.environ:
                value = os.environ[env_var]
                
                # Convert string values to appropriate types
                if config_key in ['copy_status_retry_delay', 'restore_status_retry_delay', 
                                 'delete_status_retry_delay', 'max_copy_attempts', 
                                 'copy_check_interval', 'max_restore_attempts', 
                                 'restore_check_interval', 'port', 'db_connection_timeout']:
                    try:
                        value = int(value)
                    except ValueError:
                        logger.warning(f"Could not convert {env_var} to integer: {value}")
                
                elif config_key in ['skip_final_snapshot', 'deletion_protection', 'archive_snapshot']:
                    value = value.lower() in ['true', '1', 'yes', 'y']
                
                self._config[config_key] = value
                self._config_sources[config_key] = ConfigSource.ENV_VAR
    
    def _load_from_state(self, state: Dict[str, Any]) -> None:
        """Load configuration from state data"""
        for key, value in state.items():
            if key in self._config:
                self._config[key] = value
                self._config_sources[key] = ConfigSource.STATE
    
    def _load_from_event(self, event: Dict[str, Any]) -> None:
        """Load configuration from event data"""
        for key, value in event.items():
            if key in self._config:
                self._config[key] = value
                self._config_sources[key] = ConfigSource.EVENT
    
    def _validate_config(self) -> None:
        """Validate the configuration"""
        # Convert string values to appropriate types if needed
        for key, value in self._config.items():
            if isinstance(value, str):
                if key in ['copy_status_retry_delay', 'restore_status_retry_delay', 
                           'delete_status_retry_delay', 'max_copy_attempts', 
                           'copy_check_interval', 'max_restore_attempts', 
                           'restore_check_interval', 'port', 'db_connection_timeout']:
                    try:
                        self._config[key] = int(value)
                    except ValueError:
                        logger.warning(f"Could not convert {key} to integer: {value}")
                
                elif key in ['skip_final_snapshot', 'deletion_protection', 'archive_snapshot']:
                    self._config[key] = value.lower() in ['true', '1', 'yes', 'y']
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.
        
        Args:
            key: Configuration key
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        return self._config.get(key, default)
    
    def get_source(self, key: str) -> Optional[ConfigSource]:
        """
        Get the source of a configuration value.
        
        Args:
            key: Configuration key
            
        Returns:
            Source of the configuration value
        """
        return self._config_sources.get(key)
    
    def get_all(self) -> Dict[str, Any]:
        """
        Get all configuration values.
        
        Returns:
            Dictionary of all configuration values
        """
        return self._config.copy()
    
    def get_all_with_sources(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all configuration values with their sources.
        
        Returns:
            Dictionary of configuration values with their sources
        """
        result = {}
        for key, value in self._config.items():
            result[key] = {
                'value': value,
                'source': self._config_sources.get(key, ConfigSource.DEFAULT).name
            }
        return result
    
    def to_json(self) -> str:
        """
        Convert configuration to JSON.
        
        Returns:
            JSON string representation of configuration
        """
        return json.dumps(self._config, default=str)
    
    def __str__(self) -> str:
        """String representation of configuration"""
        return self.to_json()
    
    def __repr__(self) -> str:
        """String representation of configuration"""
        return f"ConfigManager(environment='{self.environment}')" 