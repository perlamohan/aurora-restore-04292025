#!/bin/bash

# Exit on error
set -e

# Default values
ENVIRONMENT="dev"
REGION="us-east-1"
STACK_PREFIX="aurora-restore"
OUTPUT_DIR="package_output"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --environment)
      ENVIRONMENT="$2"
      shift 2
      ;;
    --region)
      REGION="$2"
      shift 2
      ;;
    --stack-prefix)
      STACK_PREFIX="$2"
      shift 2
      ;;
    --output-dir)
      OUTPUT_DIR="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

echo "Building Lambda packages for Aurora Restore Pipeline..."

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Create S3 bucket for deployment artifacts if it doesn't exist
BUCKET_NAME="${STACK_PREFIX}-${ENVIRONMENT}-artifacts-${REGION}"
if ! aws s3api head-bucket --bucket "$BUCKET_NAME" 2>/dev/null; then
    echo "Creating S3 bucket for deployment artifacts: $BUCKET_NAME"
    aws s3api create-bucket \
        --bucket "$BUCKET_NAME" \
        --region "$REGION" \
        --create-bucket-configuration LocationConstraint="$REGION"
fi

# Function to package a Lambda function
package_lambda() {
    FUNCTION_NAME=$1
    HANDLER_FILE=$2
    
    echo "Packaging $FUNCTION_NAME..."
    
    # Get the Lambda function directory
    FUNCTION_DIR="lambda_functions/$FUNCTION_NAME"
    
    if [ ! -d "$FUNCTION_DIR" ]; then
        echo "Error: Directory $FUNCTION_DIR not found!"
        exit 1
    fi
    
    # Create a temporary directory for packaging
    TEMP_DIR=$(mktemp -d)
    
    # Copy the Lambda function file and the utils directory
    cp "$FUNCTION_DIR/lambda_function.py" "$TEMP_DIR/$HANDLER_FILE"
    cp -r utils "$TEMP_DIR/"
    
    # Add requirements.txt if it exists
    if [ -f "requirements.txt" ]; then
        cp requirements.txt "$TEMP_DIR/"
        
        # Install dependencies
        cd "$TEMP_DIR"
        pip install -r requirements.txt -t .
        cd - > /dev/null
    fi
    
    # Create the zip package
    cd "$TEMP_DIR"
    zip -r "$FUNCTION_NAME.zip" *
    cd - > /dev/null
    
    # Move the zip to the output directory
    mv "$TEMP_DIR/$FUNCTION_NAME.zip" "$OUTPUT_DIR/"
    
    # Upload to S3
    aws s3 cp "$OUTPUT_DIR/$FUNCTION_NAME.zip" "s3://$BUCKET_NAME/aurora-restore/$HANDLER_FILE.zip"
    
    # Clean up
    rm -rf "$TEMP_DIR"
    
    echo "Package for $FUNCTION_NAME uploaded to s3://$BUCKET_NAME/aurora-restore/$HANDLER_FILE.zip"
}

# Package all Lambda functions
package_lambda "aurora-restore-snapshot-check" "snapshot_check"
package_lambda "aurora-restore-copy-snapshot" "copy_snapshot"
package_lambda "aurora-restore-check-copy-status" "check_copy_status"
package_lambda "aurora-restore-delete-rds" "delete_rds"
package_lambda "aurora-restore-check-delete-status" "check_delete_status"
package_lambda "aurora-restore-restore-snapshot" "restore_snapshot"
package_lambda "aurora-restore-check-restore-status" "check_restore_status"
package_lambda "aurora-restore-setup-db-users" "setup_db_users"
package_lambda "aurora-restore-archive-snapshot" "archive_snapshot"
package_lambda "aurora-restore-sns-notification" "sns_notification"

echo "All Lambda packages built and uploaded to S3 bucket: $BUCKET_NAME"
echo "Package files are also available in the $OUTPUT_DIR directory." 