"""
Configuration CLI for Aurora Restore Solution

This module provides a command-line interface for managing configuration
for the Aurora restore solution.
"""

import argparse
import json
import os
import sys
import logging
from typing import Dict, Any, List, Optional, Union

from utils.config_manager import ConfigManager
from utils.config_validator import ConfigValidator
from utils.config_template import ConfigTemplateGenerator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def setup_parser():
    """Set up command-line argument parser"""
    parser = argparse.ArgumentParser(
        description='Aurora Restore Configuration CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Generate template command
    template_parser = subparsers.add_parser('generate-template', help='Generate configuration template')
    template_parser.add_argument('--output', '-o', help='Output file path')
    template_parser.add_argument('--format', '-f', choices=['json', 'env', 'ssm'], default='json',
                                help='Template format (default: json)')
    
    # Validate config command
    validate_parser = subparsers.add_parser('validate', help='Validate configuration')
    validate_parser.add_argument('--config', '-c', required=True, help='Configuration file path')
    validate_parser.add_argument('--function', '-f', help='Lambda function name')
    
    # Convert config command
    convert_parser = subparsers.add_parser('convert', help='Convert configuration format')
    convert_parser.add_argument('--input', '-i', required=True, help='Input file path')
    convert_parser.add_argument('--output', '-o', required=True, help='Output file path')
    convert_parser.add_argument('--from-format', '-f', choices=['json', 'env', 'ssm'], required=True,
                               help='Input format')
    convert_parser.add_argument('--to-format', '-t', choices=['json', 'env', 'ssm'], required=True,
                               help='Output format')
    
    # Deploy config command
    deploy_parser = subparsers.add_parser('deploy', help='Deploy configuration to SSM Parameter Store')
    deploy_parser.add_argument('--config', '-c', required=True, help='Configuration file path')
    deploy_parser.add_argument('--environment', '-e', default='dev', help='Environment name (default: dev)')
    
    return parser

def generate_template(args):
    """Generate configuration template"""
    if args.format == 'json':
        ConfigTemplateGenerator.generate_template(args.output)
    elif args.format == 'env':
        ConfigTemplateGenerator.generate_env_vars_template(args.output)
    elif args.format == 'ssm':
        ConfigTemplateGenerator.generate_ssm_template(args.output)
    
    logger.info(f"Template generated in {args.format} format")

def validate_config(args):
    """Validate configuration"""
    try:
        with open(args.config, 'r') as f:
            config = json.load(f)
        
        if args.function:
            is_valid = ConfigValidator.validate_and_log(config, args.function)
        else:
            errors = ConfigValidator.validate_config(config)
            is_valid = len(errors) == 0
            if not is_valid:
                for error in errors:
                    logger.error(error)
        
        if is_valid:
            logger.info("Configuration is valid")
        else:
            logger.error("Configuration is invalid")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Error validating configuration: {str(e)}")
        sys.exit(1)

def convert_config(args):
    """Convert configuration format"""
    try:
        # Load input configuration
        if args.from_format == 'json':
            with open(args.input, 'r') as f:
                config = json.load(f)
        elif args.from_format == 'env':
            config = {}
            with open(args.input, 'r') as f:
                for line in f:
                    if '=' in line:
                        key, value = line.strip().split('=', 1)
                        config[key] = value
            config = ConfigTemplateGenerator.convert_env_vars_to_config(config)
        elif args.from_format == 'ssm':
            with open(args.input, 'r') as f:
                ssm_config = json.load(f)
            # Extract the first environment's config
            config = next(iter(ssm_config.values()))
        
        # Convert to output format
        if args.to_format == 'json':
            with open(args.output, 'w') as f:
                json.dump(config, f, indent=4)
        elif args.to_format == 'env':
            env_vars = ConfigTemplateGenerator.convert_config_to_env_vars(config)
            with open(args.output, 'w') as f:
                for key, value in env_vars.items():
                    f.write(f"{key}={value}\n")
        elif args.to_format == 'ssm':
            ssm_config = {f"/aurora-restore/{config.get('environment', 'dev')}/config": config}
            with open(args.output, 'w') as f:
                json.dump(ssm_config, f, indent=4)
        
        logger.info(f"Configuration converted from {args.from_format} to {args.to_format}")
    except Exception as e:
        logger.error(f"Error converting configuration: {str(e)}")
        sys.exit(1)

def deploy_config(args):
    """Deploy configuration to SSM Parameter Store"""
    try:
        with open(args.config, 'r') as f:
            config = json.load(f)
        
        # Validate configuration
        errors = ConfigValidator.validate_config(config)
        if errors:
            for error in errors:
                logger.error(error)
            logger.error("Configuration is invalid")
            sys.exit(1)
        
        # Create SSM client
        import boto3
        ssm_client = boto3.client('ssm')
        
        # Deploy to SSM Parameter Store
        ssm_path = f"/aurora-restore/{args.environment}/config"
        ssm_client.put_parameter(
            Name=ssm_path,
            Value=json.dumps(config),
            Type='String',
            Overwrite=True,
            Tags=[
                {'Key': 'Environment', 'Value': args.environment},
                {'Key': 'Project', 'Value': 'AuroraRestore'},
                {'Key': 'Service', 'Value': 'Configuration'}
            ]
        )
        
        logger.info(f"Configuration deployed to SSM Parameter Store: {ssm_path}")
    except Exception as e:
        logger.error(f"Error deploying configuration: {str(e)}")
        sys.exit(1)

def main():
    """Main entry point"""
    parser = setup_parser()
    args = parser.parse_args()
    
    if args.command == 'generate-template':
        generate_template(args)
    elif args.command == 'validate':
        validate_config(args)
    elif args.command == 'convert':
        convert_config(args)
    elif args.command == 'deploy':
        deploy_config(args)
    else:
        parser.print_help()

if __name__ == '__main__':
    main() 