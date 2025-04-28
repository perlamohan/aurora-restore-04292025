#!/bin/bash

# Exit on error
set -e

# Configuration
STACK_NAME="aurora-restore-pipeline"
REGION="us-east-1"  # Change this to your desired region
TEMPLATE_FILE="template.yaml"
PACKAGE_DIR="lambda_packages"
S3_BUCKET_NAME="${STACK_NAME}-deployment-${RANDOM}"

# Create S3 bucket for deployment packages
echo "Creating S3 bucket for deployment packages..."
aws s3api create-bucket \
    --bucket $S3_BUCKET_NAME \
    --region $REGION \
    --create-bucket-configuration LocationConstraint=$REGION

# Create package directory if it doesn't exist
mkdir -p $PACKAGE_DIR

# Install dependencies and create deployment packages for each Lambda function
for func_dir in lambda_functions/*/; do
    if [ -d "$func_dir" ]; then
        func_name=$(basename "$func_dir")
        echo "Processing $func_name..."
        
        # Create function-specific package directory
        mkdir -p "${PACKAGE_DIR}/${func_name}"
        
        # Install dependencies if requirements.txt exists
        if [ -f "${func_dir}requirements.txt" ]; then
            echo "Installing dependencies for $func_name..."
            pip install -r "${func_dir}requirements.txt" -t "${PACKAGE_DIR}/${func_name}"
        fi
        
        # Copy Lambda function code
        cp "${func_dir}lambda_function.py" "${PACKAGE_DIR}/${func_name}/"
        
        # Copy utils
        cp -r utils "${PACKAGE_DIR}/${func_name}/"
        
        # Create deployment package
        cd "${PACKAGE_DIR}/${func_name}"
        zip -r "../${func_name}.zip" .
        cd ../..
        
        # Upload to S3
        aws s3 cp "${PACKAGE_DIR}/${func_name}.zip" "s3://${S3_BUCKET_NAME}/${func_name}.zip"
    fi
done

# Deploy CloudFormation stack
echo "Deploying CloudFormation stack..."
aws cloudformation deploy \
    --template-file $TEMPLATE_FILE \
    --stack-name $STACK_NAME \
    --parameter-overrides \
        DeploymentBucket=$S3_BUCKET_NAME \
        Environment=dev \
    --capabilities CAPABILITY_IAM \
    --region $REGION

# Clean up
echo "Cleaning up..."
rm -rf $PACKAGE_DIR

echo "Deployment complete!"
echo "Please ensure you have:"
echo "1. Created the necessary VPC, subnets, and security groups"
echo "2. Stored database credentials in Secrets Manager"
echo "3. Updated any environment-specific configurations" 