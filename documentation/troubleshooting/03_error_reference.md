# Aurora Restore Pipeline Error Reference

This document provides a reference for error codes and messages you might encounter when using the Aurora Restore Pipeline, along with their meaning and potential solutions.

## Error Code Format

Errors in the Aurora Restore Pipeline follow this format:

```
ARP-<component>-<error_type>-<error_code>
```

Where:
- `ARP` stands for Aurora Restore Pipeline
- `<component>` indicates which component generated the error
- `<error_type>` describes the category of error
- `<error_code>` is a specific identifier for the error

## Common Error Codes

### Snapshot Check Errors

| Error Code | Description | Potential Solutions |
|------------|-------------|-------------------|
| ARP-SNAP-CHECK-001 | Snapshot not found | Verify the snapshot name and ensure it exists in the source region. Check if the naming format matches the expected format. |
| ARP-SNAP-CHECK-002 | Snapshot not available | Ensure the snapshot status is "available" and not "creating" or "failed". Wait for the snapshot to become available or check if it has failed. |
| ARP-SNAP-CHECK-003 | Insufficient permissions to access snapshot | Verify IAM permissions to describe and share snapshots. Check if the snapshot is shared with your account. |
| ARP-SNAP-CHECK-004 | Invalid date format | Ensure the date in the snapshot name is in the correct format (YYYY-MM-DD). Check if the snapshot prefix is correctly configured. |
| ARP-SNAP-CHECK-005 | Missing source region | Ensure the source region is specified in the input parameters. Verify that the region is valid. |

### Snapshot Copy Errors

| Error Code | Description | Potential Solutions |
|------------|-------------|-------------------|
| ARP-SNAP-COPY-001 | Failed to start snapshot copy | Check if the source snapshot exists and is available. Verify permissions to copy snapshots across regions. |
| ARP-SNAP-COPY-002 | Target region not supported | Ensure the target region is a valid AWS region where Aurora is available. Verify that the target region is different from the source region. |
| ARP-SNAP-COPY-003 | Target snapshot already exists | Check if a snapshot with the same name already exists in the target region. Use a different name or delete the existing snapshot. |
| ARP-SNAP-COPY-004 | KMS key access denied | Verify that the KMS key is accessible in the target region. Check if the Lambda function has permission to use the KMS key. |
| ARP-SNAP-COPY-005 | Snapshot copying failed | Check CloudWatch logs for specific error messages. Verify that there is sufficient quota for DB cluster snapshots in the target region. |

### Snapshot Copy Status Errors

| Error Code | Description | Potential Solutions |
|------------|-------------|-------------------|
| ARP-COPY-STATUS-001 | Snapshot copy not found | Verify that the copy operation was started successfully. Check if the target snapshot name is correct. |
| ARP-COPY-STATUS-002 | Snapshot copy failed | Check CloudWatch logs for specific error messages. Verify permissions to copy snapshots across regions. |
| ARP-COPY-STATUS-003 | Snapshot copy timeout | Increase the timeout value for the check copy status Lambda function. Consider using a smaller snapshot or pre-copying snapshots. |
| ARP-COPY-STATUS-004 | Failed to check snapshot copy status | Verify permissions to describe snapshots in the target region. Check CloudWatch logs for specific error messages. |
| ARP-COPY-STATUS-005 | Invalid snapshot copy state | Check if the snapshot copy is in an unexpected state. Verify that the snapshot is not being modified by another process. |

### Cluster Deletion Errors

| Error Code | Description | Potential Solutions |
|------------|-------------|-------------------|
| ARP-DELETE-001 | Cluster not found | Check if the cluster exists in the target region. Verify that the cluster name is correct. |
| ARP-DELETE-002 | Deletion protection enabled | Disable deletion protection for the cluster. Verify permissions to modify the cluster. |
| ARP-DELETE-003 | Failed to delete cluster | Check CloudWatch logs for specific error messages. Verify permissions to delete clusters. |
| ARP-DELETE-004 | Instances still attached to cluster | Wait for instances to be deleted or manually delete them. Verify that all instances in the cluster are deleted before deleting the cluster. |
| ARP-DELETE-005 | Cluster in use by other resources | Check if the cluster is referenced by other resources (e.g., snapshots being created). Wait for dependent operations to complete. |

### Deletion Status Errors

| Error Code | Description | Potential Solutions |
|------------|-------------|-------------------|
| ARP-DELETE-STATUS-001 | Failed to check deletion status | Verify permissions to describe clusters in the target region. Check CloudWatch logs for specific error messages. |
| ARP-DELETE-STATUS-002 | Deletion timeout | Increase the timeout value for the check deletion status Lambda function. Check if the cluster has a large number of resources attached. |
| ARP-DELETE-STATUS-003 | Deletion failed | Check CloudWatch logs for specific error messages. Verify permissions to delete clusters. |
| ARP-DELETE-STATUS-004 | Unexpected deletion state | Check if the cluster is in an unexpected state. Verify that the cluster is not being modified by another process. |
| ARP-DELETE-STATUS-005 | Failed to find deletion status | Check if the cluster name is correct. Verify that the cluster exists in the target region. |

### Restore Errors

| Error Code | Description | Potential Solutions |
|------------|-------------|-------------------|
| ARP-RESTORE-001 | Snapshot not found in target region | Verify that the snapshot copy completed successfully. Check if the target snapshot name is correct. |
| ARP-RESTORE-002 | Failed to start restore | Check CloudWatch logs for specific error messages. Verify permissions to restore clusters from snapshots. |
| ARP-RESTORE-003 | Invalid subnet group | Ensure the subnet group exists in the target region. Verify that the subnet group is valid for the target region. |
| ARP-RESTORE-004 | Invalid security group | Ensure the security group exists in the target region. Verify that the security group is valid for the target VPC. |
| ARP-RESTORE-005 | Invalid parameter group | Ensure the parameter group exists in the target region. Verify that the parameter group is compatible with the engine version. |
| ARP-RESTORE-006 | Invalid instance class | Ensure the instance class is supported in the target region. Verify that the instance class is compatible with the engine version. |
| ARP-RESTORE-007 | Restore quota exceeded | Check if you have reached the quota for DB clusters in the target region. Request a quota increase or delete unused resources. |
| ARP-RESTORE-008 | VPC not found | Ensure the VPC exists in the target region. Verify that the VPC is valid and has the required resources (subnets, security groups). |

### Restore Status Errors

| Error Code | Description | Potential Solutions |
|------------|-------------|-------------------|
| ARP-RESTORE-STATUS-001 | Failed to check restore status | Verify permissions to describe clusters in the target region. Check CloudWatch logs for specific error messages. |
| ARP-RESTORE-STATUS-002 | Restore timeout | Increase the timeout value for the check restore status Lambda function. Consider using a smaller snapshot or a larger instance class. |
| ARP-RESTORE-STATUS-003 | Restore failed | Check CloudWatch logs for specific error messages. Verify permissions to restore clusters from snapshots. |
| ARP-RESTORE-STATUS-004 | Unexpected restore state | Check if the cluster is in an unexpected state. Verify that the cluster is not being modified by another process. |
| ARP-RESTORE-STATUS-005 | Failed to find restore status | Check if the cluster name is correct. Verify that the cluster was created in the target region. |

### Database User Setup Errors

| Error Code | Description | Potential Solutions |
|------------|-------------|-------------------|
| ARP-DBUSER-001 | Failed to connect to database | Verify that the security group allows connections from the Lambda function. Check if the database is available and accepting connections. |
| ARP-DBUSER-002 | Invalid master credentials | Ensure the master username and password are correct in Secrets Manager. Verify that the secrets are accessible to the Lambda function. |
| ARP-DBUSER-003 | Failed to create users | Check CloudWatch logs for specific error messages. Verify that the master user has sufficient privileges to create users. |
| ARP-DBUSER-004 | Failed to retrieve user credentials | Verify that the user credentials are correctly stored in Secrets Manager. Check if the Lambda function has permission to access the secrets. |
| ARP-DBUSER-005 | User already exists | Check if the user already exists in the database. Modify the Lambda function to handle existing users gracefully. |

### Snapshot Archive Errors

| Error Code | Description | Potential Solutions |
|------------|-------------|-------------------|
| ARP-ARCHIVE-001 | Failed to delete snapshot | Verify permissions to delete snapshots in the target region. Check CloudWatch logs for specific error messages. |
| ARP-ARCHIVE-002 | Snapshot not found | Check if the snapshot exists in the target region. Verify that the snapshot name is correct. |
| ARP-ARCHIVE-003 | Snapshot in use | Check if the snapshot is being used by another process. Wait for dependent operations to complete. |
| ARP-ARCHIVE-004 | Failed to archive snapshot | Check CloudWatch logs for specific error messages. Verify permissions to archive snapshots. |
| ARP-ARCHIVE-005 | Archive location not accessible | Verify permissions to access the archive location. Check if the archive location is valid and exists. |

### Notification Errors

| Error Code | Description | Potential Solutions |
|------------|-------------|-------------------|
| ARP-NOTIFY-001 | SNS topic not found | Ensure the SNS topic exists in the target region. Verify that the topic ARN is correct. |
| ARP-NOTIFY-002 | Failed to publish notification | Verify permissions to publish to the SNS topic. Check CloudWatch logs for specific error messages. |
| ARP-NOTIFY-003 | Invalid notification format | Check if the notification message is correctly formatted. Verify that the message does not exceed the SNS message size limit. |
| ARP-NOTIFY-004 | Missing required parameters | Ensure that all required parameters are specified in the notification. Verify that the parameters are correctly formatted. |
| ARP-NOTIFY-005 | Failed to construct notification message | Check CloudWatch logs for specific error messages. Verify that the message construction logic is correct. |

### General Errors

| Error Code | Description | Potential Solutions |
|------------|-------------|-------------------|
| ARP-GENERAL-001 | Missing required parameter | Ensure that all required parameters are specified in the input. Verify that the parameters are correctly formatted. |
| ARP-GENERAL-002 | Invalid parameter value | Check if the parameter values are valid. Verify that the parameters are correctly formatted. |
| ARP-GENERAL-003 | Failed to load configuration | Verify that the configuration is correctly stored. Check if the Lambda function has permission to access the configuration. |
| ARP-GENERAL-004 | Failed to load state | Verify that the state is correctly stored in DynamoDB. Check if the Lambda function has permission to access the state table. |
| ARP-GENERAL-005 | Failed to save state | Verify that the Lambda function has permission to write to the state table. Check CloudWatch logs for specific error messages. |
| ARP-GENERAL-006 | Timeout during operation | Increase the timeout value for the Lambda function. Optimize the code to reduce execution time. |
| ARP-GENERAL-007 | AWS API rate limit exceeded | Implement exponential backoff for AWS API calls. Reduce the frequency of API calls. |
| ARP-GENERAL-008 | Failed to assume IAM role | Verify that the IAM role exists and is correctly configured. Check if the Lambda function has permission to assume the role. |
| ARP-GENERAL-009 | Failed to access DynamoDB | Verify that the DynamoDB table exists and is accessible. Check if the Lambda function has permission to access the table. |
| ARP-GENERAL-010 | Internal error | Check CloudWatch logs for specific error messages. Contact the Aurora Restore Pipeline development team for assistance. |

## AWS Service Error Codes

### Amazon RDS Error Codes

| Error Code | Description | Potential Solutions |
|------------|-------------|-------------------|
| DBClusterNotFoundFault | The specified DB cluster does not exist | Verify that the cluster name is correct. Check if the cluster exists in the specified region. |
| DBClusterSnapshotNotFoundFault | The specified DB cluster snapshot does not exist | Verify that the snapshot name is correct. Check if the snapshot exists in the specified region. |
| DBClusterSnapshotAlreadyExistsFault | A DB cluster snapshot with the same name already exists | Use a different name or delete the existing snapshot. |
| DBClusterAlreadyExistsFault | A DB cluster with the same name already exists | Use a different name or delete the existing cluster. |
| DBSubnetGroupNotFoundFault | The specified DB subnet group does not exist | Ensure the subnet group exists in the target region. Create the subnet group if it doesn't exist. |
| InvalidDBClusterStateFault | The DB cluster is not in a valid state for the operation | Check the current state of the cluster. Wait for the cluster to reach a valid state or resolve the underlying issue. |
| InvalidDBClusterSnapshotStateFault | The DB cluster snapshot is not in a valid state for the operation | Check the current state of the snapshot. Wait for the snapshot to reach a valid state or resolve the underlying issue. |
| StorageQuotaExceededFault | The request would exceed the user's storage quota | Delete unused DB clusters or snapshots. Request a quota increase. |
| DBClusterParameterGroupNotFoundFault | The specified DB cluster parameter group does not exist | Ensure the parameter group exists in the target region. Create the parameter group if it doesn't exist. |
| InvalidVPCNetworkStateFault | The VPC network is not in a valid state for the operation | Check the current state of the VPC. Ensure the VPC is correctly configured with subnets and routing. |
| KMSKeyNotAccessibleFault | The specified KMS key is not accessible | Verify that the KMS key exists and is accessible. Check if the Lambda function has permission to use the key. |

### Amazon EC2 Error Codes

| Error Code | Description | Potential Solutions |
|------------|-------------|-------------------|
| InvalidSubnetID | The specified subnet ID is invalid | Verify that the subnet ID is correct. Check if the subnet exists in the target region. |
| InvalidSecurityGroupID | The specified security group ID is invalid | Verify that the security group ID is correct. Check if the security group exists in the target region. |
| SecurityGroupNotFoundFault | The specified security group does not exist | Verify that the security group exists in the target region. Create the security group if it doesn't exist. |
| VPCNotFoundFault | The specified VPC does not exist | Verify that the VPC exists in the target region. Check if the VPC ID is correct. |
| SubnetNotFoundFault | The specified subnet does not exist | Verify that the subnet exists in the target region. Check if the subnet ID is correct. |

### AWS IAM Error Codes

| Error Code | Description | Potential Solutions |
|------------|-------------|-------------------|
| AccessDenied | Access to the requested resource is denied | Verify that the IAM role has sufficient permissions. Check if the resource policy allows access from the IAM role. |
| InvalidClientTokenId | The security token included in the request is invalid | Verify that the AWS credentials are valid. Check if the IAM role exists and is correctly configured. |
| MalformedPolicyDocument | The policy document is malformed | Verify that the policy document is correctly formatted. Check for syntax errors in the policy. |
| NoSuchEntity | The requested entity does not exist | Verify that the IAM role or policy exists. Create the IAM role or policy if it doesn't exist. |
| UnauthorizedOperation | The client is not authorized to perform the operation | Verify that the IAM role has sufficient permissions. Check if the resource policy allows the operation. |

### AWS Step Functions Error Codes

| Error Code | Description | Potential Solutions |
|------------|-------------|-------------------|
| ExecutionAlreadyExists | The execution already exists | Use a different execution name or wait for the existing execution to complete. |
| ExecutionDoesNotExist | The execution does not exist | Verify that the execution ARN is correct. Check if the execution exists in the specified state machine. |
| ExecutionLimitExceeded | The maximum number of executions has been reached | Wait for existing executions to complete. Request a quota increase for concurrent executions. |
| InvalidArn | The ARN is invalid | Verify that the ARN is correctly formatted. Check if the ARN exists. |
| InvalidExecutionInput | The execution input is invalid | Verify that the input is correctly formatted JSON. Check if the input size exceeds the limit. |
| StateMachineDoesNotExist | The state machine does not exist | Verify that the state machine ARN is correct. Check if the state machine exists. |
| StateMachineDeleting | The state machine is being deleted | Wait for the state machine to be recreated. Use a different state machine. |

### AWS DynamoDB Error Codes

| Error Code | Description | Potential Solutions |
|------------|-------------|-------------------|
| ConditionalCheckFailedException | The condition specified in the conditional write was not met | Verify that the condition is correct. Check if the item being updated meets the condition. |
| ItemCollectionSizeLimitExceededException | The size of an item collection exceeds the maximum size limit | Redesign the table to avoid large item collections. Use a different partition key. |
| ProvisionedThroughputExceededException | The request rate exceeds the provisioned throughput | Implement exponential backoff for DynamoDB API calls. Increase the provisioned throughput. |
| ResourceNotFoundException | The specified table does not exist | Verify that the table exists in the specified region. Create the table if it doesn't exist. |
| TableAlreadyExistsException | The table you're trying to create already exists | Use a different table name or use the existing table. |
| LimitExceededException | The operation exceeds the current limits | Reduce the number of operations. Request a quota increase. |

### AWS Secrets Manager Error Codes

| Error Code | Description | Potential Solutions |
|------------|-------------|-------------------|
| ResourceNotFoundException | The specified secret does not exist | Verify that the secret exists in the specified region. Create the secret if it doesn't exist. |
| InvalidParameterException | The parameter value is invalid | Verify that the parameter values are correct. Check if the secret name is valid. |
| InvalidRequestException | The request is malformed | Verify that the request is correctly formatted. Check if the request contains all required parameters. |
| DecryptionFailure | The protected secret text cannot be decrypted | Verify that the KMS key used to encrypt the secret is accessible. Check if the Lambda function has permission to use the key. |

## Next Steps

If you encounter an error not listed in this document, consider the following:

1. Review the [Common Issues and Solutions](./01_common_issues.md) for more general troubleshooting.
2. Consult the [Debugging Guide](./02_debugging_guide.md) for detailed debugging steps.
3. Check CloudWatch Logs for specific error messages and stack traces.
4. Contact the Aurora Restore Pipeline development team for assistance. 