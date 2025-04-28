# Manual Implementation Guide - Production Deployment

## 1. Production Environment Setup

1. **Create Production Resources**
```bash
# Set production environment
export ENVIRONMENT=prod
export AWS_REGION=us-east-1  # or your preferred region

# Create DynamoDB tables with higher capacity
aws dynamodb create-table \
  --table-name aurora-restore-state-prod \
  --attribute-definitions AttributeName=operation_id,AttributeType=S \
  --key-schema AttributeName=operation_id,KeyType=HASH \
  --provisioned-throughput ReadCapacityUnits=10,WriteCapacityUnits=10

aws dynamodb create-table \
  --table-name aurora-restore-audit-prod \
  --attribute-definitions \
    AttributeName=operation_id,AttributeType=S \
    AttributeName=timestamp,AttributeType=N \
  --key-schema \
    AttributeName=operation_id,KeyType=HASH \
    AttributeName=timestamp,KeyType=RANGE \
  --provisioned-throughput ReadCapacityUnits=10,WriteCapacityUnits=10

# Create SNS topic with subscriptions
aws sns create-topic --name aurora-restore-notifications-prod
aws sns subscribe \
  --topic-arn $SNS_TOPIC_ARN \
  --protocol email \
  --notification-endpoint your-team@company.com
```

2. **Create Production Secrets**
```bash
# Create secrets with stricter permissions
aws secretsmanager create-secret \
  --name aurora-restore/prod/db-credentials \
  --secret-string '{"username":"admin","password":"PROD_PASSWORD"}' \
  --tags Key=Environment,Value=prod

aws secretsmanager create-secret \
  --name aurora-restore/prod/kms-key \
  --secret-string '{"key_id":"PROD_KMS_KEY_ID"}' \
  --tags Key=Environment,Value=prod
```

## 2. Production Lambda Deployment

1. **Update Lambda Configuration**
```bash
# Set production variables
export LAMBDA_MEMORY=512
export LAMBDA_TIMEOUT=300
export LOG_RETENTION=30

# Function deployment script
deploy_lambda() {
  local function_name=$1
  local handler=$2
  
  # Create deployment package
  zip -r ${function_name}.zip lambda/${handler}.py lambda/utils/
  
  # Create or update function
  aws lambda create-function \
    --function-name aurora-restore-${function_name}-prod \
    --runtime python3.9 \
    --handler ${handler}.lambda_handler \
    --role arn:aws:iam::${AWS_ACCOUNT_ID}:role/aurora-restore-lambda-role-prod \
    --zip-file fileb://${function_name}.zip \
    --timeout $LAMBDA_TIMEOUT \
    --memory-size $LAMBDA_MEMORY \
    --environment Variables="{ENVIRONMENT=prod,STATE_TABLE_NAME=aurora-restore-state-prod,AUDIT_TABLE_NAME=aurora-restore-audit-prod}" \
    --tags Environment=prod,Application=aurora-restore,Function=${function_name} \
    || aws lambda update-function-code \
       --function-name aurora-restore-${function_name}-prod \
       --zip-file fileb://${function_name}.zip
}

# Deploy all functions
deploy_lambda "snapshot-check" "snapshot_check"
deploy_lambda "copy-snapshot" "copy_snapshot"
deploy_lambda "check-copy-status" "check_copy_status"
deploy_lambda "delete-rds" "delete_rds"
deploy_lambda "restore-snapshot" "restore_snapshot"
deploy_lambda "check-restore-status" "check_restore_status"
deploy_lambda "setup-db-users" "setup_db_users"
deploy_lambda "archive-snapshot" "archive_snapshot"
deploy_lambda "sns-notification" "sns_notification"
```

2. **Configure CloudWatch Alarms**
```bash
# Create alarms for Lambda errors
aws cloudwatch put-metric-alarm \
  --alarm-name aurora-restore-lambda-errors-prod \
  --alarm-description "Alert on Lambda errors in Aurora Restore pipeline" \
  --metric-name Errors \
  --namespace AWS/Lambda \
  --statistic Sum \
  --period 300 \
  --threshold 1 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1 \
  --dimensions Name=FunctionName,Value=aurora-restore-*-prod \
  --alarm-actions $SNS_TOPIC_ARN

# Create alarm for DynamoDB throttles
aws cloudwatch put-metric-alarm \
  --alarm-name aurora-restore-dynamodb-throttles-prod \
  --alarm-description "Alert on DynamoDB throttles" \
  --metric-name ThrottledRequests \
  --namespace AWS/DynamoDB \
  --statistic Sum \
  --period 300 \
  --threshold 1 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1 \
  --dimensions Name=TableName,Value=aurora-restore-state-prod \
  --alarm-actions $SNS_TOPIC_ARN
```

## 3. Production Step Functions Deployment

1. **Create Production State Machine**
```bash
# Update state machine with production config
aws stepfunctions create-state-machine \
  --name aurora-restore-pipeline-prod \
  --role-arn arn:aws:iam::${AWS_ACCOUNT_ID}:role/aurora-restore-step-functions-role-prod \
  --definition file://state-machine.json \
  --tags Key=Environment,Value=prod,Key=Application,Value=aurora-restore
```

2. **Configure Step Functions Monitoring**
```bash
# Create alarm for failed executions
aws cloudwatch put-metric-alarm \
  --alarm-name aurora-restore-pipeline-failures-prod \
  --alarm-description "Alert on Step Functions execution failures" \
  --metric-name ExecutionsFailed \
  --namespace AWS/States \
  --statistic Sum \
  --period 300 \
  --threshold 1 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1 \
  --dimensions Name=StateMachineArn,Value=$STATE_MACHINE_ARN \
  --alarm-actions $SNS_TOPIC_ARN
```

## 4. Production Testing

1. **Validate Production Setup**
```bash
# Test each Lambda function
for func in snapshot-check copy-snapshot check-copy-status delete-rds restore-snapshot check-restore-status setup-db-users archive-snapshot sns-notification; do
  aws lambda invoke \
    --function-name aurora-restore-${func}-prod \
    --payload '{"body":{"operation_id":"test-prod-001"}}' \
    response.json
done

# Test Step Functions execution
aws stepfunctions start-execution \
  --state-machine-arn $PROD_STATE_MACHINE_ARN \
  --input file://test-input.json
```

2. **Verify Monitoring**
```bash
# Check CloudWatch dashboards
aws cloudwatch get-dashboard \
  --dashboard-name aurora-restore-prod

# Verify SNS notifications
aws sns publish \
  --topic-arn $SNS_TOPIC_ARN \
  --message "Test notification from Aurora Restore Pipeline"
```

## 5. Production Runbook

1. **Common Operations**
```bash
# Check pipeline status
aws stepfunctions list-executions \
  --state-machine-arn $PROD_STATE_MACHINE_ARN \
  --status-filter RUNNING

# Stop execution
aws stepfunctions stop-execution \
  --execution-arn $EXECUTION_ARN

# Retry failed execution
aws stepfunctions start-execution \
  --state-machine-arn $PROD_STATE_MACHINE_ARN \
  --input file://failed-execution-input.json
```

2. **Troubleshooting Guide**
   - Check CloudWatch Logs for Lambda errors
   - Verify DynamoDB state and audit trail
   - Check SNS notifications
   - Review Step Functions execution history
   - Validate IAM permissions
   - Check network connectivity
   - Verify secrets and configuration

3. **Backup and Recovery**
   - DynamoDB tables have point-in-time recovery enabled
   - Lambda code is versioned in S3
   - State machine definition is version controlled
   - Secrets are backed up in Secrets Manager

4. **Maintenance Procedures**
   - Regular review of CloudWatch metrics
   - Periodic testing of error scenarios
   - Update dependencies and runtime versions
   - Review and rotate secrets
   - Monitor costs and optimize resources

## 6. Security Considerations

1. **Access Control**
   - Use IAM roles with least privilege
   - Implement network security groups
   - Enable AWS CloudTrail
   - Monitor API calls and access patterns

2. **Data Protection**
   - Encrypt data at rest and in transit
   - Use KMS for key management
   - Implement backup and retention policies
   - Follow compliance requirements

3. **Monitoring and Auditing**
   - Enable VPC Flow Logs
   - Monitor security groups
   - Track configuration changes
   - Review access logs

## Next Steps

1. Set up CI/CD pipeline for automated deployments
2. Implement additional monitoring and alerting
3. Create disaster recovery procedures
4. Document operational procedures
5. Train team members on maintenance and troubleshooting 