# Aurora Restore Configuration Management

This directory contains utilities for managing configuration for the Aurora restore solution. The configuration management system is designed to be flexible, maintainable, and secure, with support for multiple configuration sources and formats.

## Components

### Configuration Manager (`config_manager.py`)

The `ConfigManager` class provides a centralized way to manage configuration from multiple sources:

- Event data (from Lambda invocations)
- State data (from DynamoDB)
- Environment variables
- SSM Parameter Store
- Default values

The manager follows a priority order for configuration sources and provides methods to access configuration values.

### Configuration Validator (`config_validator.py`)

The `ConfigValidator` class ensures that configuration values are valid according to a JSON Schema. It provides:

- Schema validation for all configuration values
- Function-specific validation for Lambda functions
- Detailed error messages for invalid configurations

### Configuration Template Generator (`config_template.py`)

The `ConfigTemplateGenerator` class helps users generate and manage configuration templates:

- Generate templates in JSON, environment variables, or SSM Parameter Store format
- Convert between different configuration formats
- Provide default values for all configuration parameters

### Configuration CLI (`config_cli.py`)

The CLI tool provides a command-line interface for managing configuration:

- Generate configuration templates
- Validate configuration files
- Convert between configuration formats
- Deploy configuration to SSM Parameter Store

## Usage

### Generating Configuration Templates

```bash
# Generate a JSON template
python config_cli.py generate-template --format json --output config.json

# Generate an environment variables template
python config_cli.py generate-template --format env --output .env

# Generate an SSM Parameter Store template
python config_cli.py generate-template --format ssm --output ssm_config.json
```

### Validating Configuration

```bash
# Validate a configuration file
python config_cli.py validate --config config.json

# Validate configuration for a specific Lambda function
python config_cli.py validate --config config.json --function aurora-restore-snapshot-check
```

### Converting Configuration Formats

```bash
# Convert from JSON to environment variables
python config_cli.py convert --input config.json --output .env --from-format json --to-format env

# Convert from environment variables to SSM Parameter Store
python config_cli.py convert --input .env --output ssm_config.json --from-format env --to-format ssm
```

### Deploying Configuration

```bash
# Deploy configuration to SSM Parameter Store
python config_cli.py deploy --config config.json --environment dev
```

## Configuration Schema

The configuration schema defines the structure and validation rules for all configuration values. The schema includes:

- Required fields for each Lambda function
- Type validation for all fields
- Range validation for numeric fields
- Pattern validation for string fields

## Best Practices

1. **Use SSM Parameter Store for Production**: Store production configuration in SSM Parameter Store for security and centralized management.

2. **Validate Configuration**: Always validate configuration before deployment to catch errors early.

3. **Use Environment-Specific Configuration**: Maintain separate configuration files for different environments (dev, test, prod).

4. **Secure Sensitive Values**: Use AWS Secrets Manager for sensitive values like credentials and API keys.

5. **Version Control Configuration**: Keep configuration templates in version control, but exclude environment-specific values.

6. **Document Configuration**: Maintain documentation for all configuration parameters and their purpose.

## Integration with Lambda Functions

Lambda functions can use the configuration management system by:

1. Importing the `ConfigManager` class
2. Creating a `ConfigManager` instance
3. Accessing configuration values through the manager

Example:

```python
from utils.config_manager import ConfigManager

def lambda_handler(event, context):
    # Create a configuration manager
    config_manager = ConfigManager(event, context)
    
    # Access configuration values
    source_region = config_manager.get('source_region')
    target_region = config_manager.get('target_region')
    
    # Use configuration values
    print(f"Restoring from {source_region} to {target_region}")
```

## Troubleshooting

### Common Issues

1. **Invalid Configuration**: Use the validator to check for invalid configuration values.

2. **Missing Configuration**: Ensure all required configuration values are provided.

3. **SSM Parameter Store Access**: Verify IAM permissions for accessing SSM Parameter Store.

4. **Environment Variables**: Check that environment variables are correctly set in Lambda functions.

### Getting Help

For issues with configuration management:

1. Check the error messages from the validator
2. Review the configuration schema
3. Verify the configuration format
4. Check AWS CloudWatch Logs for detailed error messages 