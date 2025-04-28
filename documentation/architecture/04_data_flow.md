# Data Flow

This document provides a detailed explanation of how data flows between components in the Aurora Restore Pipeline.

## Overview

The Aurora Restore Pipeline involves a complex flow of data across multiple AWS services. Understanding these data flows is crucial for troubleshooting, optimizing, and extending the system.

## Key Data Elements

### Operation ID
A unique identifier generated for each restore operation. This ID is used to track the operation across all components and serves as the primary key in the state database.

### State Object
A JSON object that represents the current state of a restore operation, including:
- Operation parameters (source snapshot, target cluster, etc.)
- Current step status
- Error information (if any)
- Timestamps for tracking duration
- Metadata about the operation

### Audit Events
Structured log entries that capture significant events during the restore process, including:
- Step transitions
- Error conditions
- Operation completion
- Resource creation/deletion

### Metrics
Numerical data points that measure the performance and reliability of the pipeline:
- Operation duration
- Success/failure counts
- Resource usage

## Data Flow Diagrams

### Pipeline Initialization

```
┌─────────────┐      ┌───────────────┐      ┌─────────────────┐
│             │      │               │      │                 │
│  API/CLI    │─────▶│ Step Functions│─────▶│  snapshot-check │
│             │      │               │      │                 │
└─────────────┘      └───────────────┘      └─────────────────┘
                                                     │
                                                     ▼
                                            ┌─────────────────┐
                                            │                 │
                                            │   DynamoDB      │
                                            │                 │
                                            └─────────────────┘
```

1. **API/CLI → Step Functions**: 
   - Input parameters (source snapshot date, target cluster ID, etc.)
   - Operation metadata (initiator, timestamp, etc.)

2. **Step Functions → snapshot-check Lambda**:
   - All input parameters from API/CLI
   - Execution context (execution ID, etc.)

3. **snapshot-check → DynamoDB**:
   - Creates initial state entry with operation_id
   - Records operation parameters
   - Sets initial status

### Snapshot Processing Flow

```
┌──────────────┐     ┌────────────────┐     ┌────────────────┐
│              │     │                │     │                │
│snapshot-check│────▶│ copy-snapshot  │────▶│check-copy-     │
│              │     │                │     │status          │
└──────────────┘     └────────────────┘     └────────────────┘
       │                    │                      │
       │                    │                      │
       ▼                    ▼                      ▼
┌─────────────────────────────────────────────────────────┐
│                                                         │
│                       DynamoDB                          │
│                                                         │
└─────────────────────────────────────────────────────────┘
       │                    │                      │
       │                    │                      │
       ▼                    ▼                      ▼
┌──────────────┐     ┌────────────────┐     ┌────────────────┐
│              │     │                │     │                │
│  RDS API     │────▶│   RDS API      │────▶│   RDS API      │
│  (Source)    │     │   (Target)     │     │   (Target)     │
└──────────────┘     └────────────────┘     └────────────────┘
```

1. **snapshot-check → RDS API (Source)**:
   - Snapshot name or date query
   - Region information

2. **RDS API (Source) → snapshot-check**:
   - Snapshot details (ARN, status, etc.)
   - Error information (if snapshot not found)

3. **snapshot-check → DynamoDB**:
   - Updates state with snapshot information
   - Records audit event for snapshot validation

4. **DynamoDB → copy-snapshot**:
   - Retrieves operation state with snapshot details

5. **copy-snapshot → RDS API (Source & Target)**:
   - Copy snapshot request with source and target information
   - KMS key information for encryption

6. **RDS API → copy-snapshot**:
   - Copy operation identifier
   - Initial status information

7. **copy-snapshot → DynamoDB**:
   - Updates state with copy operation details
   - Records audit event for copy initiation

8. **DynamoDB → check-copy-status**:
   - Retrieves operation state with copy details

9. **check-copy-status → RDS API (Target)**:
   - Status query for copied snapshot

10. **RDS API (Target) → check-copy-status**:
    - Current status of snapshot copy
    - Error information (if copy failed)

11. **check-copy-status → DynamoDB**:
    - Updates state with current status
    - Records audit event for status check

### Restore and Setup Flow

```
┌──────────────┐     ┌────────────────┐     ┌────────────────┐
│              │     │                │     │                │
│restore-      │────▶│check-restore-  │────▶│setup-db-users  │
│snapshot      │     │status          │     │                │
└──────────────┘     └────────────────┘     └────────────────┘
       │                    │                      │
       │                    │                      │
       ▼                    ▼                      ▼
┌─────────────────────────────────────────────────────────┐
│                                                         │
│                       DynamoDB                          │
│                                                         │
└─────────────────────────────────────────────────────────┘
       │                    │                      │
       │                    │                      │
       ▼                    ▼                      ▼
┌──────────────┐     ┌────────────────┐     ┌────────────────┐
│              │     │                │     │                │
│  RDS API     │────▶│   RDS API      │────▶│ Secrets Manager│
│              │     │                │     │                │
└──────────────┘     └────────────────┘     └────────────────┘
                                                   │
                                                   ▼
                                            ┌────────────────┐
                                            │                │
                                            │ Aurora Database│
                                            │                │
                                            └────────────────┘
```

1. **DynamoDB → restore-snapshot**:
   - Retrieves operation state with snapshot details

2. **restore-snapshot → RDS API**:
   - Restore request with snapshot and cluster details
   - Parameter group and subnet group information
   - Security group settings

3. **RDS API → restore-snapshot**:
   - Cluster identifier
   - Initial restore status

4. **restore-snapshot → DynamoDB**:
   - Updates state with restore operation details
   - Records audit event for restore initiation

5. **DynamoDB → check-restore-status**:
   - Retrieves operation state with restore details

6. **check-restore-status → RDS API**:
   - Status query for restored cluster

7. **RDS API → check-restore-status**:
   - Current status of cluster restore
   - Endpoint information (when available)
   - Error information (if restore failed)

8. **check-restore-status → DynamoDB**:
   - Updates state with current status and endpoint
   - Records audit event for status check

9. **DynamoDB → setup-db-users**:
   - Retrieves operation state with cluster endpoint

10. **setup-db-users → Secrets Manager**:
    - Retrieves admin credentials
    - Retrieves application user templates

11. **setup-db-users → Aurora Database**:
    - SQL commands to create users and set permissions
    - SQL commands to validate setup

12. **setup-db-users → DynamoDB**:
    - Updates state with user setup status
    - Records audit event for user creation

### Cleanup and Notification Flow

```
┌──────────────┐     ┌────────────────┐     ┌────────────────┐
│              │     │                │     │                │
│archive-      │────▶│sns-notification│────▶│CloudWatch      │
│snapshot      │     │                │     │                │
└──────────────┘     └────────────────┘     └────────────────┘
       │                    │                      
       │                    │                      
       ▼                    ▼                      
┌─────────────────────────────────────────────────────────┐
│                                                         │
│                       DynamoDB                          │
│                                                         │
└─────────────────────────────────────────────────────────┘
       │                                           
       │                                           
       ▼                                           
┌──────────────┐                           ┌────────────────┐
│              │                           │                │
│  RDS API     │                           │ SNS Topic      │
│              │                           │                │
└──────────────┘                           └────────────────┘
                                                  │
                                                  ▼
                                           ┌────────────────┐
                                           │                │
                                           │ Email/SMS      │
                                           │                │
                                           └────────────────┘
```

1. **DynamoDB → archive-snapshot**:
   - Retrieves operation state with snapshot details

2. **archive-snapshot → RDS API**:
   - Delete or archive request for temporary snapshots

3. **RDS API → archive-snapshot**:
   - Operation status

4. **archive-snapshot → DynamoDB**:
   - Updates state with archive status
   - Records audit event for snapshot cleanup

5. **DynamoDB → sns-notification**:
   - Retrieves complete operation state

6. **sns-notification → SNS Topic**:
   - Notification message with operation details
   - Success/failure status
   - Cluster endpoint information

7. **SNS Topic → Email/SMS**:
   - Formatted notification message to subscribers

8. **sns-notification → DynamoDB**:
   - Updates state with notification status
   - Records final audit event for operation completion

## Data Schema Examples

### State Object Schema

```json
{
  "operation_id": "restore-20230615-123456",
  "status": "RESTORE_IN_PROGRESS",
  "start_time": "2023-06-15T12:34:56Z",
  "last_updated_time": "2023-06-15T13:00:00Z",
  "parameters": {
    "source_snapshot_date": "2023-06-14",
    "source_region": "us-east-1",
    "target_region": "us-west-2",
    "target_cluster_id": "aurora-restored-cluster",
    "db_instance_class": "db.r5.large",
    "vpc_security_group_ids": ["sg-12345678"],
    "db_subnet_group_name": "default-vpc-subnet-group"
  },
  "snapshot_details": {
    "source_snapshot_id": "rds:aurora-prod-2023-06-14-00-00",
    "snapshot_arn": "arn:aws:rds:us-east-1:123456789012:cluster-snapshot:aurora-prod-2023-06-14-00-00",
    "snapshot_status": "available",
    "target_snapshot_id": "rds:aurora-prod-2023-06-14-00-00-copy"
  },
  "restore_details": {
    "cluster_id": "aurora-restored-cluster",
    "cluster_status": "creating",
    "writer_endpoint": null,
    "reader_endpoint": null
  },
  "error": null,
  "next_step": "CHECK_RESTORE_STATUS"
}
```

### Audit Event Schema

```json
{
  "operation_id": "restore-20230615-123456",
  "timestamp": "2023-06-15T13:00:00Z",
  "event_type": "RESTORE_STARTED",
  "details": {
    "source_snapshot_id": "rds:aurora-prod-2023-06-14-00-00-copy",
    "target_cluster_id": "aurora-restored-cluster",
    "parameters": {
      "db_instance_class": "db.r5.large",
      "vpc_security_group_ids": ["sg-12345678"],
      "db_subnet_group_name": "default-vpc-subnet-group"
    }
  },
  "status": "SUCCESS",
  "error": null
}
```

### Metrics Schema

```json
{
  "operation_id": "restore-20230615-123456",
  "timestamp": "2023-06-15T14:30:00Z",
  "metrics": {
    "snapshot_validation_duration_seconds": 5.2,
    "snapshot_copy_duration_seconds": 600.4,
    "restore_duration_seconds": 1800.7,
    "total_duration_seconds": 2406.3,
    "error_count": 0
  }
}
```

## Data Persistence and Retention

1. **State Data**:
   - Stored in DynamoDB with operation_id as the partition key
   - Retained for 90 days by default
   - Can be archived to S3 for longer-term storage

2. **Audit Events**:
   - Stored in DynamoDB with operation_id as the partition key and timestamp as the sort key
   - Retained for 365 days by default
   - Can be exported to S3 for compliance and long-term retention

3. **CloudWatch Logs**:
   - Lambda function logs retained for 30 days
   - Log groups include operation_id in log events for correlation

4. **Step Functions Execution History**:
   - Retained for 90 days
   - Includes state transitions and Lambda function inputs/outputs

## Next Steps

For more detailed information about the implementation of data flows, refer to:
- [API Reference](../api_reference/01_lambda_functions.md)
- [Implementation Guide](../implementation_guide/01_prerequisites.md)
- [Troubleshooting Guide](../troubleshooting/01_common_issues.md) 