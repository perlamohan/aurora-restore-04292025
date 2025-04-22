#!/bin/bash

# Aurora Restore Pipeline Testing Script
# This script helps test the Lambda functions in sequence

# Set your AWS profile if needed
# export AWS_PROFILE=your-profile

# Set your AWS region
REGION="us-west-2"

# Function to execute a Lambda and capture the output
execute_lambda() {
    local function_name=$1
    local input_file=$2
    local output_file=$3
    
    echo "Executing $function_name with input from $input_file..."
    
    # Execute the Lambda function
    aws lambda invoke \
        --function-name $function_name \
        --region $REGION \
        --payload file://$input_file \
        --cli-binary-format raw-in-base64-out \
        $output_file
    
    # Check if the execution was successful
    if [ $? -eq 0 ]; then
        echo "✅ $function_name executed successfully"
        echo "Output saved to $output_file"
        echo "Output content:"
        cat $output_file
        echo ""
    else
        echo "❌ $function_name execution failed"
        exit 1
    fi
}

# Create a temporary directory for test files
mkdir -p test_outputs

# Step 1: Check if snapshot exists
echo "Step 1: Checking if snapshot exists..."
cat > test_outputs/step1_input.json << EOF
{}
EOF

execute_lambda "aurora-restore-snapshot-check" "test_outputs/step1_input.json" "test_outputs/step1_output.json"

# Step 2: Copy snapshot
echo "Step 2: Copying snapshot..."
cp test_outputs/step1_output.json test_outputs/step2_input.json

execute_lambda "aurora-restore-copy-snapshot" "test_outputs/step2_input.json" "test_outputs/step2_output.json"

# Step 3: Check copy status
echo "Step 3: Checking copy status..."
cp test_outputs/step2_output.json test_outputs/step3_input.json

execute_lambda "aurora-restore-check-copy-status" "test_outputs/step3_input.json" "test_outputs/step3_output.json"

# Step 4: Delete RDS cluster
echo "Step 4: Deleting RDS cluster..."
cp test_outputs/step3_output.json test_outputs/step4_input.json

execute_lambda "aurora-restore-delete-rds" "test_outputs/step4_input.json" "test_outputs/step4_output.json"

# Step 5: Restore snapshot
echo "Step 5: Restoring snapshot..."
cp test_outputs/step4_output.json test_outputs/step5_input.json

execute_lambda "aurora-restore-restore-snapshot" "test_outputs/step5_input.json" "test_outputs/step5_output.json"

# Step 6: Check restore status
echo "Step 6: Checking restore status..."
cp test_outputs/step5_output.json test_outputs/step6_input.json

execute_lambda "aurora-restore-check-restore-status" "test_outputs/step6_input.json" "test_outputs/step6_output.json"

# Step 7: Setup DB users
echo "Step 7: Setting up DB users..."
cp test_outputs/step6_output.json test_outputs/step7_input.json

execute_lambda "aurora-restore-setup-db-users" "test_outputs/step7_input.json" "test_outputs/step7_output.json"

# Step 8: Archive snapshot
echo "Step 8: Archiving snapshot..."
cp test_outputs/step7_output.json test_outputs/step8_input.json

execute_lambda "aurora-restore-archive-snapshot" "test_outputs/step8_input.json" "test_outputs/step8_output.json"

# Step 9: Send notification
echo "Step 9: Sending notification..."
cp test_outputs/step8_output.json test_outputs/step9_input.json

execute_lambda "aurora-restore-sns-notification" "test_outputs/step9_input.json" "test_outputs/step9_output.json"

echo "✅ Pipeline testing completed successfully!"
echo "All test outputs are saved in the test_outputs directory" 