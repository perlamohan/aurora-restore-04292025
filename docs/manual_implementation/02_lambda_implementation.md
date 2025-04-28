# Manual Implementation Guide - Lambda Implementation

## 1. Implement Utility Module

1. **Copy Aurora Utils Implementation**
   - Copy the contents of `aurora_utils.py` from the provided code to `lambda/utils/aurora_utils.py`
   - Verify all imports are available:
```bash
pip install boto3 python-json-logger
```

2. **Test Utility Functions**
```python
# Create test_utils.py
import boto3
from utils.aurora_utils import validate_snapshot_id, validate_region

# Test validation functions
result, error = validate_snapshot_id('rds:my-snapshot-2024')
print(f"Snapshot validation: {result}, {error}")

result, error = validate_region('us-east-1')
print(f"Region validation: {result}, {error}")
```

## 2. Implement Lambda Functions

### Copy Snapshot Function

1. **Create IAM Role**
```bash
# Create role and attach policies
aws iam create-role --role-name aurora-restore-lambda-role --assume-role-policy-document file://trust-policy.json
aws iam attach-role-policy --role-name aurora-restore-lambda-role --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
aws iam attach-role-policy --role-name aurora-restore-lambda-role --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole

# Attach secrets access policy
aws iam put-role-policy \
  --role-name aurora-restore-lambda-role \
  --policy-name aurora-restore-lambda-secrets-policy \
  --policy-document file://lambda-secrets-policy.json
```

2. **Create Lambda Function**
```bash
# Create deployment package
zip -r copy_snapshot.zip lambda/copy_snapshot.py lambda/utils/

# Create function
aws lambda create-function \
  --function-name aurora-restore-copy-snapshot-dev \
  --runtime python3.9 \
  --handler copy_snapshot.lambda_handler \
  --role arn:aws:iam::${AWS_ACCOUNT_ID}:role/aurora-restore-lambda-role \
  --zip-file fileb://copy_snapshot.zip \
  --timeout 300 \
  --memory-size 256 \
  --environment Variables="{ENVIRONMENT=dev,STATE_TABLE_NAME=aurora-restore-state,AUDIT_TABLE_NAME=aurora-restore-audit,MASTER_SECRET_NAME=aurora-restore/dev/master-credentials,APP_SECRET_NAME=aurora-restore/dev/app-credentials}"
```

3. **Test Copy Snapshot Function**
```bash
# Create test event
cat > test_copy_snapshot.json << EOL
{
  "body": {
    "operation_id": "op-test001",
    "snapshot_id": "rds:my-source-snapshot",
    "source_region": "us-east-1",
    "target_region": "us-west-2"
  }
}
EOL

# Invoke function
aws lambda invoke \
  --function-name aurora-restore-copy-snapshot-dev \
  --payload file://test_copy_snapshot.json \
  response.json

# Check response
cat response.json
```

### Check Copy Status Function

1. **Create Function**
```bash
# Create deployment package
zip -r check_copy_status.zip lambda/check_copy_status.py lambda/utils/

# Create function
aws lambda create-function \
  --function-name aurora-restore-check-copy-status-dev \
  --runtime python3.9 \
  --handler check_copy_status.lambda_handler \
  --role arn:aws:iam::${AWS_ACCOUNT_ID}:role/aurora-restore-lambda-role \
  --zip-file fileb://check_copy_status.zip \
  --environment Variables="{ENVIRONMENT=dev,STATE_TABLE_NAME=aurora-restore-state,AUDIT_TABLE_NAME=aurora-restore-audit,MASTER_SECRET_NAME=aurora-restore/dev/master-credentials,APP_SECRET_NAME=aurora-restore/dev/app-credentials}"
```

2. **Test Check Copy Status**
```bash
# Create test event using the operation_id from previous step
cat > test_check_copy_status.json << EOL
{
  "body": {
    "operation_id": "op-test001"
  }
}
EOL

# Invoke function
aws lambda invoke \
  --function-name aurora-restore-check-copy-status-dev \
  --payload file://test_check_copy_status.json \
  response.json
```

### Setup DB Users Function

1. **Create Function**
```bash
# Create deployment package
zip -r setup_db_users.zip lambda/setup_db_users.py lambda/utils/

# Create function
aws lambda create-function \
  --function-name aurora-restore-setup-db-users-dev \
  --runtime python3.9 \
  --handler setup_db_users.lambda_handler \
  --role arn:aws:iam::${AWS_ACCOUNT_ID}:role/aurora-restore-lambda-role \
  --zip-file fileb://setup_db_users.zip \
  --timeout 300 \
  --memory-size 256 \
  --environment Variables="{ENVIRONMENT=dev,STATE_TABLE_NAME=aurora-restore-state,AUDIT_TABLE_NAME=aurora-restore-audit,MASTER_SECRET_NAME=aurora-restore/dev/master-credentials,APP_SECRET_NAME=aurora-restore/dev/app-credentials}"
```

2. **Test Setup DB Users**
```bash
# Create test event
cat > test_setup_db_users.json << EOL
{
  "body": {
    "operation_id": "op-test001",
    "cluster_id": "target-cluster-id"
  }
}
EOL

# Invoke function
aws lambda invoke \
  --function-name aurora-restore-setup-db-users-dev \
  --payload file://test_setup_db_users.json \
  response.json
```

### Implement Remaining Functions

Follow the same pattern for each remaining function:
1. Create deployment package
2. Create Lambda function with appropriate environment variables
3. Create test event
4. Test function
5. Verify results in DynamoDB and CloudWatch Logs

## 3. Testing Flow

1. **Test Copy Snapshot Flow**
```bash
# 1. Start copy
aws lambda invoke --function-name aurora-restore-copy-snapshot-dev --payload file://test_copy_snapshot.json copy_response.json

# 2. Check copy status (repeat until complete)
aws lambda invoke --function-name aurora-restore-check-copy-status-dev --payload file://test_check_copy_status.json status_response.json
```

2. **Test Delete RDS Flow**
```bash
# Create test event
cat > test_delete_rds.json << EOL
{
  "body": {
    "operation_id": "op-test001",
    "cluster_id": "target-cluster-id"
  }
}
EOL

# Invoke function
aws lambda invoke --function-name aurora-restore-delete-rds-dev --payload file://test_delete_rds.json response.json
```

3. **Test Restore Snapshot Flow**
```bash
# Create test event
cat > test_restore_snapshot.json << EOL
{
  "body": {
    "operation_id": "op-test001",
    "snapshot_id": "rds:my-source-snapshot-copy",
    "target_cluster_id": "new-cluster-id"
  }
}
EOL

# Invoke function
aws lambda invoke --function-name aurora-restore-restore-snapshot-dev --payload file://test_restore_snapshot.json response.json
```

4. **Test Setup DB Users Flow**
```bash
# Create test event
cat > test_setup_db_users.json << EOL
{
  "body": {
    "operation_id": "op-test001",
    "cluster_id": "new-cluster-id"
  }
}
EOL

# Invoke function
aws lambda invoke --function-name aurora-restore-setup-db-users-dev --payload file://test_setup_db_users.json response.json
```

## 4. Monitoring and Verification

1. **Check CloudWatch Logs**
```bash
# Get log group name
aws logs describe-log-groups --query 'logGroups[?contains(logGroupName,`aurora-restore`)].logGroupName'

# Get log streams
aws logs describe-log-streams --log-group-name /aws/lambda/aurora-restore-copy-snapshot-dev

# Get log events
aws logs get-log-events --log-group-name /aws/lambda/aurora-restore-copy-snapshot-dev --log-stream-name "STREAM_NAME"
```

2. **Check DynamoDB State**
```bash
# Query state table
aws dynamodb get-item \
  --table-name aurora-restore-state \
  --key '{"operation_id":{"S":"op-test001"}}'

# Query audit table
aws dynamodb query \
  --table-name aurora-restore-audit \
  --key-condition-expression "operation_id = :id" \
  --expression-attribute-values '{":id":{"S":"op-test001"}}'
```

3. **Verify Secrets Access**
```bash
# Test Lambda access to app credentials
aws lambda invoke \
  --function-name aurora-restore-setup-db-users-dev \
  --payload '{"body":{"operation_id":"test-secrets","cluster_id":"test-cluster"}}' \
  secrets_test.json

# Check response for any permission errors
cat secrets_test.json
```

## Next Steps

After successfully testing each Lambda function individually:
1. Verify all functions work as expected
2. Check error handling by testing failure scenarios
3. Proceed to Step Functions implementation
4. See [03_step_functions_implementation.md](03_step_functions_implementation.md) for next steps 