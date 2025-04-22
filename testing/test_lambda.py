#!/usr/bin/env python3

import json
import boto3
import argparse
from datetime import datetime
import os

def invoke_lambda(function_name, payload, region="us-west-2"):
    """
    Invoke a Lambda function and return its response
    """
    lambda_client = boto3.client('lambda', region_name=region)
    
    try:
        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )
        
        # Parse the response
        status_code = response['StatusCode']
        response_payload = json.loads(response['Payload'].read().decode())
        
        return {
            'status_code': status_code,
            'response': response_payload
        }
    except Exception as e:
        return {
            'status_code': 500,
            'error': str(e)
        }

def save_test_result(function_name, input_payload, output, test_case):
    """
    Save test results to a file
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"test_outputs/{function_name}_{test_case}_{timestamp}.json"
    
    result = {
        'timestamp': timestamp,
        'function_name': function_name,
        'test_case': test_case,
        'input': input_payload,
        'output': output
    }
    
    with open(filename, 'w') as f:
        json.dump(result, f, indent=2)
    
    return filename

def test_snapshot_check():
    """
    Test cases for aurora-restore-snapshot-check
    """
    test_cases = {
        'empty_input': {},
        'with_date': {'date': '2024-03-20'},
        'with_invalid_date': {'date': 'invalid-date'}
    }
    
    for case_name, payload in test_cases.items():
        print(f"\nTesting snapshot check with {case_name}...")
        result = invoke_lambda('aurora-restore-snapshot-check', payload)
        output_file = save_test_result('aurora-restore-snapshot-check', payload, result, case_name)
        print(f"Results saved to {output_file}")

def test_copy_snapshot():
    """
    Test cases for aurora-restore-copy-snapshot
    """
    test_cases = {
        'valid_snapshot': {
            'snapshot_id': 'rds:snapshot-id',
            'source_region': 'us-west-2',
            'target_region': 'us-east-1'
        },
        'invalid_snapshot': {
            'snapshot_id': 'invalid-snapshot',
            'source_region': 'us-west-2',
            'target_region': 'us-east-1'
        }
    }
    
    for case_name, payload in test_cases.items():
        print(f"\nTesting copy snapshot with {case_name}...")
        result = invoke_lambda('aurora-restore-copy-snapshot', payload)
        output_file = save_test_result('aurora-restore-copy-snapshot', payload, result, case_name)
        print(f"Results saved to {output_file}")

def test_check_copy_status():
    """
    Test cases for aurora-restore-check-copy-status
    """
    test_cases = {
        'in_progress': {
            'copy_snapshot_id': 'copy-snapshot-id',
            'status': 'copying'
        },
        'completed': {
            'copy_snapshot_id': 'copy-snapshot-id',
            'status': 'available'
        }
    }
    
    for case_name, payload in test_cases.items():
        print(f"\nTesting check copy status with {case_name}...")
        result = invoke_lambda('aurora-restore-check-copy-status', payload)
        output_file = save_test_result('aurora-restore-check-copy-status', payload, result, case_name)
        print(f"Results saved to {output_file}")

def test_delete_rds():
    """
    Test cases for aurora-restore-delete-rds
    """
    test_cases = {
        'existing_cluster': {
            'cluster_id': 'existing-cluster',
            'region': 'us-west-2'
        },
        'non_existing_cluster': {
            'cluster_id': 'non-existing-cluster',
            'region': 'us-west-2'
        }
    }
    
    for case_name, payload in test_cases.items():
        print(f"\nTesting delete RDS with {case_name}...")
        result = invoke_lambda('aurora-restore-delete-rds', payload)
        output_file = save_test_result('aurora-restore-delete-rds', payload, result, case_name)
        print(f"Results saved to {output_file}")

def test_restore_snapshot():
    """
    Test cases for aurora-restore-restore-snapshot
    """
    test_cases = {
        'valid_restore': {
            'snapshot_id': 'valid-snapshot-id',
            'cluster_id': 'new-cluster-id',
            'region': 'us-west-2'
        },
        'invalid_snapshot': {
            'snapshot_id': 'invalid-snapshot-id',
            'cluster_id': 'new-cluster-id',
            'region': 'us-west-2'
        }
    }
    
    for case_name, payload in test_cases.items():
        print(f"\nTesting restore snapshot with {case_name}...")
        result = invoke_lambda('aurora-restore-restore-snapshot', payload)
        output_file = save_test_result('aurora-restore-restore-snapshot', payload, result, case_name)
        print(f"Results saved to {output_file}")

def test_check_restore_status():
    """
    Test cases for aurora-restore-check-restore-status
    """
    test_cases = {
        'in_progress': {
            'cluster_id': 'new-cluster-id',
            'status': 'creating'
        },
        'completed': {
            'cluster_id': 'new-cluster-id',
            'status': 'available'
        }
    }
    
    for case_name, payload in test_cases.items():
        print(f"\nTesting check restore status with {case_name}...")
        result = invoke_lambda('aurora-restore-check-restore-status', payload)
        output_file = save_test_result('aurora-restore-check-restore-status', payload, result, case_name)
        print(f"Results saved to {output_file}")

def test_setup_db_users():
    """
    Test cases for aurora-restore-setup-db-users
    """
    test_cases = {
        'valid_setup': {
            'cluster_id': 'new-cluster-id',
            'endpoint': 'cluster-endpoint',
            'port': 5432
        },
        'invalid_endpoint': {
            'cluster_id': 'new-cluster-id',
            'endpoint': 'invalid-endpoint',
            'port': 5432
        }
    }
    
    for case_name, payload in test_cases.items():
        print(f"\nTesting setup DB users with {case_name}...")
        result = invoke_lambda('aurora-restore-setup-db-users', payload)
        output_file = save_test_result('aurora-restore-setup-db-users', payload, result, case_name)
        print(f"Results saved to {output_file}")

def test_archive_snapshot():
    """
    Test cases for aurora-restore-archive-snapshot
    """
    test_cases = {
        'valid_archive': {
            'snapshot_id': 'copy-snapshot-id',
            'region': 'us-west-2'
        },
        'invalid_snapshot': {
            'snapshot_id': 'invalid-snapshot-id',
            'region': 'us-west-2'
        }
    }
    
    for case_name, payload in test_cases.items():
        print(f"\nTesting archive snapshot with {case_name}...")
        result = invoke_lambda('aurora-restore-archive-snapshot', payload)
        output_file = save_test_result('aurora-restore-archive-snapshot', payload, result, case_name)
        print(f"Results saved to {output_file}")

def test_sns_notification():
    """
    Test cases for aurora-restore-sns-notification
    """
    test_cases = {
        'success_notification': {
            'status': 'success',
            'cluster_id': 'new-cluster-id',
            'endpoint': 'cluster-endpoint'
        },
        'failure_notification': {
            'status': 'failure',
            'error': 'Test error message'
        }
    }
    
    for case_name, payload in test_cases.items():
        print(f"\nTesting SNS notification with {case_name}...")
        result = invoke_lambda('aurora-restore-sns-notification', payload)
        output_file = save_test_result('aurora-restore-sns-notification', payload, result, case_name)
        print(f"Results saved to {output_file}")

def main():
    parser = argparse.ArgumentParser(description='Test Lambda functions in the Aurora restore pipeline')
    parser.add_argument('function', choices=[
        'snapshot-check',
        'copy-snapshot',
        'check-copy-status',
        'delete-rds',
        'restore-snapshot',
        'check-restore-status',
        'setup-db-users',
        'archive-snapshot',
        'sns-notification',
        'all'
    ], help='Lambda function to test')
    
    args = parser.parse_args()
    
    # Create test_outputs directory if it doesn't exist
    os.makedirs('test_outputs', exist_ok=True)
    
    if args.function == 'all':
        test_snapshot_check()
        test_copy_snapshot()
        test_check_copy_status()
        test_delete_rds()
        test_restore_snapshot()
        test_check_restore_status()
        test_setup_db_users()
        test_archive_snapshot()
        test_sns_notification()
    else:
        function_map = {
            'snapshot-check': test_snapshot_check,
            'copy-snapshot': test_copy_snapshot,
            'check-copy-status': test_check_copy_status,
            'delete-rds': test_delete_rds,
            'restore-snapshot': test_restore_snapshot,
            'check-restore-status': test_check_restore_status,
            'setup-db-users': test_setup_db_users,
            'archive-snapshot': test_archive_snapshot,
            'sns-notification': test_sns_notification
        }
        function_map[args.function]()

if __name__ == '__main__':
    main() 