# Component Diagram

This document provides a detailed overview of the Aurora Restore Pipeline components and their interactions.

## System Components

The Aurora Restore Pipeline consists of several interconnected AWS services that work together to automate the database restore process:

```
┌────────────────────────────────────────────────────────────────────────┐
│                          Aurora Restore Pipeline                        │
│                                                                         │
│  ┌──────────────┐     ┌─────────────────┐     ┌─────────────────────┐  │
│  │              │     │                 │     │                     │  │
│  │  AWS Step    │──┬─▶│  AWS Lambda     │────▶│  Amazon RDS/Aurora  │  │
│  │  Functions   │  │  │  Functions      │     │                     │  │
│  │              │  │  │                 │     └─────────────────────┘  │
│  └──────────────┘  │  └─────────────────┘               ▲              │
│         ▲          │           │                        │              │
│         │          │           ▼                        │              │
│  ┌──────────────┐  │  ┌─────────────────┐     ┌─────────────────────┐  │
│  │              │  │  │                 │     │                     │  │
│  │  API Gateway │──┘  │  Amazon         │     │  AWS Secrets        │  │
│  │  / CLI       │     │  DynamoDB       │     │  Manager            │  │
│  │              │     │                 │     │                     │  │
│  └──────────────┘     └─────────────────┘     └─────────────────────┘  │
│                               │                                         │
│                               ▼                                         │
│                      ┌─────────────────┐     ┌─────────────────────┐   │
│                      │                 │     │                     │   │
│                      │  Amazon         │────▶│  CloudWatch         │   │
│                      │  SNS            │     │  Logs/Metrics       │   │
│                      │                 │     │                     │   │
│                      └─────────────────┘     └─────────────────────┘   │
│                                                                         │
└────────────────────────────────────────────────────────────────────────┘
```

## Component Descriptions

### AWS Step Functions

The Step Functions state machine orchestrates the entire pipeline workflow, coordinating the execution of Lambda functions in the correct sequence and handling errors and retries.

**Key Responsibilities:**
- Defining and managing the workflow for the snapshot validation, copy, restore, and cleanup process
- Tracking state transitions between steps
- Handling errors and retry logic
- Providing visual representation of workflow progress
- Storing execution history for troubleshooting

**Interactions:**
- Invokes Lambda functions in the correct sequence
- Receives status updates from Lambda functions
- Handles conditional logic for workflow branching

### AWS Lambda Functions

A collection of specialized Lambda functions that perform specific tasks within the pipeline. Each function is designed to handle a single responsibility.

**Key Lambda Functions:**
1. **snapshot-check**: Validates the existence and status of source snapshots
2. **copy-snapshot**: Copies snapshots between regions when needed
3. **check-copy-status**: Monitors the progress of snapshot copy operations
4. **restore-snapshot**: Initiates the restore process for a validated snapshot
5. **check-restore-status**: Monitors the progress of the restore operation
6. **setup-db-users**: Configures database users and permissions
7. **delete-rds**: Cleans up existing clusters before restore (if needed)
8. **check-delete-status**: Monitors the progress of cluster deletion
9. **archive-snapshot**: Archives or deletes snapshots after restore
10. **sns-notification**: Sends notifications about pipeline completion

**Interactions:**
- Interact with RDS/Aurora to manage snapshots and clusters
- Read from and write to DynamoDB for state persistence
- Access Secrets Manager for database credentials
- Send notifications via SNS
- Log information to CloudWatch

### Amazon RDS/Aurora

The target database service that hosts the restored database clusters.

**Key Responsibilities:**
- Storing database snapshots
- Creating new database clusters from snapshots
- Managing database connections and security

**Interactions:**
- Receives snapshot copy and restore commands from Lambda functions
- Provides status updates on operations to Lambda functions

### Amazon DynamoDB

Stores operation state, configuration, and audit logs for the pipeline.

**Key Tables:**
1. **AuroraRestoreState**: Stores the state of each restore operation
2. **AuroraRestoreAudit**: Records audit events for compliance and troubleshooting
3. **AuroraRestoreConfig**: Stores configuration for the pipeline

**Interactions:**
- Receives state updates from Lambda functions
- Provides state information to Lambda functions
- Stores audit logs for compliance and troubleshooting

### AWS Secrets Manager

Securely stores and manages sensitive information such as database credentials.

**Key Secrets:**
- Database administrator credentials
- Application user credentials
- Read-only user credentials

**Interactions:**
- Provides secure access to credentials for Lambda functions

### Amazon SNS

Handles notifications about pipeline events and completion status.

**Key Topics:**
- Restore completion notifications
- Error notifications
- Operation status updates

**Interactions:**
- Receives notification requests from Lambda functions
- Distributes notifications to subscribers
- Integrates with CloudWatch for alarming

### CloudWatch Logs/Metrics

Captures logs and performance metrics from all components of the pipeline.

**Key Metrics:**
- Operation duration metrics
- Success/failure counts
- Error rates by operation type

**Interactions:**
- Receives logs from Lambda functions
- Collects metrics from all components
- Provides monitoring dashboards and alarms

### API Gateway / CLI

Entry points for triggering restore operations.

**Key Responsibilities:**
- Providing RESTful API for triggering restores
- Validating input parameters
- Initiating Step Functions executions

**Interactions:**
- Receives restore requests from users
- Invokes Step Functions state machine with appropriate parameters

## Interaction Flows

### Primary Flow: Successful Restore

1. User initiates restore via API Gateway or CLI
2. Step Functions workflow begins and invokes snapshot-check Lambda
3. snapshot-check validates snapshot existence
4. If cross-region, copy-snapshot and check-copy-status are executed
5. restore-snapshot initiates restore process
6. check-restore-status monitors progress until complete
7. setup-db-users configures database access
8. sns-notification sends completion notification
9. DynamoDB stores state updates throughout the process
10. CloudWatch logs each step for auditing

### Alternate Flow: Cluster Deletion Required

1. User initiates restore via API Gateway or CLI
2. Step Functions workflow begins and invokes snapshot-check Lambda
3. If target cluster exists, delete-rds is invoked
4. check-delete-status monitors deletion progress
5. Once deletion completes, normal restore flow continues

### Error Flow: Snapshot Not Found

1. User initiates restore via API Gateway or CLI
2. Step Functions workflow begins and invokes snapshot-check Lambda
3. snapshot-check fails to find valid snapshot
4. Step Functions transitions to error handling state
5. sns-notification sends error notification
6. DynamoDB records error state
7. CloudWatch logs error details

## Next Steps

For more detailed information about the data flow between components, refer to:
- [Data Flow](./04_data_flow.md)
- [API Reference](../api_reference/01_lambda_functions.md)
- [Implementation Guide](../implementation_guide/01_prerequisites.md) 