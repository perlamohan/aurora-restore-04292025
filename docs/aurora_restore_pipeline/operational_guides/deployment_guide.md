# Aurora Restore Pipeline Deployment Guide

This document provides detailed instructions for deploying the Aurora Restore Pipeline.

## Prerequisites

Before deploying the Aurora Restore Pipeline, ensure that you have completed the prerequisites outlined in the [Prerequisites Guide](prerequisites.md).

## Deployment Options

The Aurora Restore Pipeline can be deployed using the following methods:

1. **AWS CloudFormation**: Deploy the pipeline using a CloudFormation template.
2. **AWS SAM**: Deploy the pipeline using the AWS Serverless Application Model (SAM).
3. **Manual Deployment**: Deploy the pipeline components manually using the AWS Management Console or AWS CLI.

## Deployment Using AWS CloudFormation

### Step 1: Prepare the CloudFormation Template

1. Download the CloudFormation template from the repository.
2. Review the template and make any necessary modifications.

### Step 2: Deploy the CloudFormation Stack

1. Navigate to the AWS CloudFormation console.
2. Click on "Create stack" and select "With new resources (standard)".
3. Upload the CloudFormation template or specify the S3 URL of the template.
4. Click on "Next".
5. Enter a stack name and specify the following parameters:
   - `Environment`: The environment (e.g., dev, test, prod).
   - `Region`: The AWS region where the pipeline will be deployed.
   - `DynamoDBTableName`: The name of the DynamoDB table for storing state and audit information.
   - `SNSTopicName`: The name of the SNS topic for sending notifications.
   - `KMSKeyAlias`: The alias of the KMS key for encrypting sensitive data.
   - `VPCId`: The ID of the VPC where the Lambda functions will be deployed.
   - `SubnetIds`: The IDs of the subnets where the Lambda functions will be deployed.
   - `SecurityGroupIds`: The IDs of the security groups to be associated with the Lambda functions.
6. Click on "Next".
7. Configure the stack options (tags, permissions, etc.) and click on "Next".
8. Review the stack details and click on "Create stack".

### Step 3: Verify the Deployment

1. Wait for the stack creation to complete.
2. Check the "Outputs" tab of the stack to verify that all resources have been created successfully.
3. Test the deployment by invoking the Step Functions state machine with a test input.

## Deployment Using AWS SAM

### Step 1: Prepare the SAM Template

1. Download the SAM template from the repository.
2. Review the template and make any necessary modifications.

### Step 2: Build the SAM Application

1. Open a terminal and navigate to the directory containing the SAM template.
2. Run the following command to build the SAM application:

```bash
sam build
```

### Step 3: Deploy the SAM Application

1. Run the following command to deploy the SAM application:

```bash
sam deploy --guided
```

2. Follow the prompts to configure the deployment:
   - Enter a stack name.
   - Specify the AWS region.
   - Confirm the changes before deployment.
   - Allow SAM CLI to create IAM roles.
   - Save the arguments to a configuration file.

3. After the guided deployment, you can use the following command for subsequent deployments:

```bash
sam deploy
```

### Step 4: Verify the Deployment

1. Check the CloudFormation console to verify that the stack has been created successfully.
2. Test the deployment by invoking the Step Functions state machine with a test input.

## Manual Deployment

If you prefer to deploy the pipeline components manually, follow these steps:

### Step 1: Create the DynamoDB Tables

1. Navigate to the AWS DynamoDB console.
2. Create the State Table:
   - Click on "Create table".
   - Enter the table name (e.g., `aurora-restore-state`).
   - Set the primary key to `operation_id` (String).
   - Configure the table settings and click on "Create".

3. Create the Audit Table:
   - Click on "Create table".
   - Enter the table name (e.g., `aurora-restore-audit`).
   - Set the primary key to `operation_id` (String).
   - Set the sort key to `timestamp` (String).
   - Configure the table settings and click on "Create".

### Step 2: Create the SNS Topic

1. Navigate to the AWS SNS console.
2. Click on "Create topic".
3. Enter the topic name (e.g., `aurora-restore-notifications`).
4. Click on "Create topic".

### Step 3: Create the KMS Key

1. Navigate to the AWS KMS console.
2. Click on "Create key".
3. Configure the key settings and click on "Create key".

### Step 4: Create the IAM Roles

1. Navigate to the AWS IAM console.
2. Create the Step Functions role:
   - Click on "Roles" and then "Create role".
   - Select "AWS Service" and "Step Functions" as the use case.
   - Attach the necessary policies and click on "Next: Tags".
   - Add tags and click on "Next: Review".
   - Enter the role name (e.g., `aurora-restore-step-functions-role`) and click on "Create role".

3. Create the Lambda role:
   - Click on "Roles" and then "Create role".
   - Select "AWS Service" and "Lambda" as the use case.
   - Attach the necessary policies and click on "Next: Tags".
   - Add tags and click on "Next: Review".
   - Enter the role name (e.g., `aurora-restore-lambda-role`) and click on "Create role".

### Step 5: Create the Lambda Functions

1. Navigate to the AWS Lambda console.
2. Create each Lambda function:
   - Click on "Create function".
   - Enter the function name (e.g., `aurora-restore-snapshot-check`).
   - Select the runtime (Python 3.8).
   - Select the architecture (x86_64).
   - Click on "Create function".
   - Upload the function code.
   - Configure the function settings (memory, timeout, VPC, environment variables, etc.).
   - Click on "Save".

3. Repeat the above steps for each Lambda function:
   - `aurora-restore-copy-snapshot`
   - `aurora-restore-check-copy-status`
   - `aurora-restore-delete-rds`
   - `aurora-restore-restore-snapshot`
   - `aurora-restore-check-restore-status`
   - `aurora-restore-setup-db-users`
   - `aurora-restore-archive-snapshot`
   - `aurora-restore-sns-notification`

### Step 6: Create the Step Functions State Machine

1. Navigate to the AWS Step Functions console.
2. Click on "Create state machine".
3. Enter the state machine definition (ASL JSON).
4. Configure the state machine settings (timeout, retry strategy, etc.).
5. Select the IAM role for the state machine.
6. Click on "Create state machine".

### Step 7: Create the CloudWatch Alarms

1. Navigate to the AWS CloudWatch console.
2. Create the Step Functions execution failures alarm:
   - Click on "Alarms" and then "Create alarm".
   - Select the metric (ExecutionsFailed) and configure the alarm settings.
   - Click on "Create alarm".

3. Create the Lambda function errors alarm:
   - Click on "Alarms" and then "Create alarm".
   - Select the metric (Errors) and configure the alarm settings.
   - Click on "Create alarm".

### Step 8: Verify the Deployment

1. Test the deployment by invoking the Step Functions state machine with a test input.
2. Monitor the CloudWatch Logs and DynamoDB tables to verify that the pipeline is working correctly.

## Post-Deployment Configuration

After deploying the Aurora Restore Pipeline, you need to configure the following:

1. **Secrets**: Create the required secrets in AWS Secrets Manager.
2. **Environment Variables**: Configure the environment variables for each Lambda function.
3. **IAM Roles and Policies**: Review and update the IAM roles and policies as needed.
4. **CloudWatch Alarms**: Configure the CloudWatch alarms as needed.

For detailed instructions on configuring these components, refer to the [Configuration Guide](configuration_guide.md).

## Conclusion

This deployment guide provides detailed instructions for deploying the Aurora Restore Pipeline. By following these instructions, you can successfully deploy the pipeline to your AWS environment. 