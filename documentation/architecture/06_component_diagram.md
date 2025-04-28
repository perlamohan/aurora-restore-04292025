# Component Diagram

This document provides component diagrams for the Aurora Restore Pipeline, illustrating the relationships between system components and their interactions.

## System Components Overview

The Aurora Restore Pipeline consists of several interconnected components that work together to automate the restore process:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      Aurora Restore Pipeline                            │
│                                                                         │
│ ┌───────────┐     ┌────────────────┐      ┌─────────────────────────┐   │
│ │           │     │                │      │                         │   │
│ │ API / CLI ├────►│ Step Functions ├─────►│ Lambda Functions        │   │
│ │           │     │ State Machine  │      │                         │   │
│ └───────────┘     └────────────────┘      │ ┌───────────────────┐   │   │
│                            │              │ │ snapshot-check    │   │   │
│                            │              │ └───────────────────┘   │   │
│                            │              │ ┌───────────────────┐   │   │
│                            │              │ │ copy-snapshot     │   │   │
│ ┌───────────┐     ┌────────────────┐      │ └───────────────────┘   │   │
│ │           │     │                │      │ ┌───────────────────┐   │   │
│ │ CloudWatch├─────┤   SNS Topic    │◄─────┤ │ check-copy-status │   │   │
│ │ Alarms    │     │                │      │ └───────────────────┘   │   │
│ └───────────┘     └────────────────┘      │          ...            │   │
│                                           └─────────────────────────┘   │
│                                                       │                 │
│                                                       ▼                 │
│ ┌───────────┐     ┌────────────────┐      ┌─────────────────────────┐   │
│ │           │     │                │      │                         │   │
│ │ CloudWatch├────►│ Logs & Metrics │◄─────┤ AWS Services            │   │
│ │ Dashboard │     │                │      │                         │   │
│ └───────────┘     └────────────────┘      │ ┌───────────────────┐   │   │
│                                           │ │ Amazon RDS/Aurora │   │   │
│                                           │ └───────────────────┘   │   │
│                                           │ ┌───────────────────┐   │   │
│                                           │ │ DynamoDB          │   │   │
│                                           │ └───────────────────┘   │   │
│                                           │ ┌───────────────────┐   │   │
│                                           │ │ Secrets Manager   │   │   │
│                                           │ └───────────────────┘   │   │
│                                           │          ...            │   │
│                                           └─────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Lambda Function Component Details

Each Lambda function in the pipeline serves a specific purpose:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      Lambda Functions                                   │
│                                                                         │
│ ┌───────────────────┐    ┌───────────────────┐    ┌───────────────────┐ │
│ │ snapshot-check    │    │ copy-snapshot     │    │ check-copy-status │ │
│ │                   │    │                   │    │                   │ │
│ │ - Verify snapshot │    │ - Copy snapshot   │    │ - Check copy      │ │
│ │   exists          │    │   across regions  │    │   status          │ │
│ │ - Validate date   │    │ - Handle          │    │   operation       │ │
│ │ - Check encryption│    │   encryption      │    │ - Wait for        │ │
│ │                   │    │                   │    │   completion      │ │
│ └───────────────────┘    └───────────────────┘    └───────────────────┘ │
│                                                                         │
│ ┌───────────────────┐    ┌───────────────────┐    ┌───────────────────┐ │
│ │ restore-snapshot  │    │ check-restore-    │    │ setup-db-users    │ │
│ │                   │    │ status            │    │                   │ │
│ │ - Create new      │    │ - Check restore   │    │ - Create app      │ │
│ │   cluster         │    │   operation       │    │   users           │ │
│ │ - Set params      │    │   status          │    │ - Set permissions │ │
│ │ - Initiate restore│    │ - Verify cluster  │    │ - Handle password │ │
│ │                   │    │   is available    │    │   management      │ │
│ └───────────────────┘    └───────────────────┘    └───────────────────┘ │
│                                                                         │
│ ┌───────────────────┐    ┌───────────────────┐    ┌───────────────────┐ │
│ │ delete-rds        │    │ check-delete-     │    │ archive-snapshot  │ │
│ │                   │    │ status            │    │                   │ │
│ │ - Delete source   │    │ - Check deletion  │    │ - Delete copied   │ │
│ │   cluster         │    │   operation       │    │   snapshot        │ │
│ │ - Handle skip     │    │   status          │    │ - Cleanup         │ │
│ │   option          │    │ - Verify cluster  │    │   resources       │ │
│ │                   │    │   is deleted      │    │                   │ │
│ └───────────────────┘    └───────────────────┘    └───────────────────┘ │
│                                                                         │
│                   ┌───────────────────────────┐                         │
│                   │ sns-notification          │                         │
│                   │                           │                         │
│                   │ - Send success/failure    │                         │
│                   │   notifications           │                         │
│                   │ - Include operation       │                         │
│                   │   details                 │                         │
│                   └───────────────────────────┘                         │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Step Functions State Machine

The Step Functions state machine orchestrates the entire pipeline:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                   Step Functions State Machine                          │
│                                                                         │
│                         ┌───────────────┐                               │
│                         │ Start         │                               │
│                         └───────┬───────┘                               │
│                                 │                                       │
│                                 ▼                                       │
│                     ┌───────────────────────┐                           │
│                     │ Check Snapshot Exists │                           │
│                     └───────────┬───────────┘                           │
│                                 │                                       │
│                                 ▼                                       │
│                          ┌──────────────┐                               │
│                          │ Success?     │                               │
│                          └──────┬───────┘                               │
│                                 │                                       │
│                    ┌────────────┴────────────┐                          │
│                    │                         │                          │
│                    ▼                         ▼                          │
│          ┌───────────────────┐     ┌──────────────────┐                │
│          │  Copy Snapshot    │     │ Send Failure     │                │
│          │                   │     │ Notification     │                │
│          └─────────┬─────────┘     └──────────────────┘                │
│                    │                                                    │
│                    ▼                                                    │
│         ┌─────────────────────┐                                         │
│         │ Check Copy Status   │                                         │
│         └──────────┬──────────┘                                         │
│                    │                                                    │
│                    ▼                                                    │
│         ┌─────────────────────┐                                         │
│         │ Restore Snapshot    │                                         │
│         └──────────┬──────────┘                                         │
│                    │                                                    │
│                    ▼                                                    │
│         ┌─────────────────────┐                                         │
│         │ Check Restore Status│                                         │
│         └──────────┬──────────┘                                         │
│                    │                                                    │
│                    ▼                                                    │
│         ┌─────────────────────┐                                         │
│         │ Setup DB Users      │                                         │
│         └──────────┬──────────┘                                         │
│                    │                                                    │
│                    ▼                                                    │
│         ┌─────────────────────┐     ┌──────────────────┐                │
│         │ Delete Source RDS?  │─Yes─►  Delete RDS      │                │
│         └──────────┬──────────┘     └────────┬─────────┘                │
│                    │ No                      │                          │
│                    │                         │                          │
│                    │                         ▼                          │
│                    │                ┌──────────────────┐                │
│                    │                │ Check Delete     │                │
│                    │                │ Status           │                │
│                    │                └────────┬─────────┘                │
│                    │                         │                          │
│                    ▼─────────────────────────┘                          │
│         ┌─────────────────────┐                                         │
│         │ Archive Snapshot    │                                         │
│         └──────────┬──────────┘                                         │
│                    │                                                    │
│                    ▼                                                    │
│      ┌────────────────────────────┐                                     │
│      │ Send Success Notification  │                                     │
│      └────────────────────────────┘                                     │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Data Storage Components

The pipeline uses various storage mechanisms:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      Data Storage Components                            │
│                                                                         │
│ ┌───────────────────────────────────────────────────────────────────┐   │
│ │                          DynamoDB                                 │   │
│ │                                                                   │   │
│ │ ┌───────────────────┐    ┌───────────────────┐                    │   │
│ │ │ AuroraRestoreState│    │ AuroraRestoreAudit│                    │   │
│ │ │                   │    │                   │                    │   │
│ │ │ - operation_id (PK)    │ - operation_id    │                    │   │
│ │ │ - state           │    │ - timestamp (PK)  │                    │   │
│ │ │ - status          │    │ - event_type      │                    │   │
│ │ │ - parameters      │    │ - event_details   │                    │   │
│ │ │ - last_updated    │    │ - status          │                    │   │
│ │ └───────────────────┘    └───────────────────┘                    │   │
│ └───────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│ ┌───────────────────────────────────────────────────────────────────┐   │
│ │                        Secrets Manager                            │   │
│ │                                                                   │   │
│ │ ┌───────────────────┐    ┌───────────────────┐                    │   │
│ │ │ AdminCredentials  │    │ AppCredentials    │                    │   │
│ │ │                   │    │                   │                    │   │
│ │ │ - username        │    │ - app_username    │                    │   │
│ │ │ - password        │    │ - app_password    │                    │   │
│ │ │ - host            │    │ - readonly_user   │                    │   │
│ │ │ - port            │    │ - readonly_pwd    │                    │   │
│ │ └───────────────────┘    └───────────────────┘                    │   │
│ └───────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│ ┌───────────────────────────────────────────────────────────────────┐   │
│ │                       CloudWatch Logs                             │   │
│ │                                                                   │   │
│ │ ┌───────────────────┐    ┌───────────────────┐                    │   │
│ │ │ Lambda Logs       │    │ State Machine Logs│                    │   │
│ │ │                   │    │                   │                    │   │
│ │ │ - /aws/lambda/    │    │ - /aws/states/    │                    │   │
│ │ │   aurora-restore- │    │   aurora-restore  │                    │   │
│ │ │   *               │    │                   │                    │   │
│ │ └───────────────────┘    └───────────────────┘                    │   │
│ └───────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Network Architecture

The network architecture highlights VPC configuration for the pipeline components:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      Network Architecture                               │
│                                                                         │
│ ┌───────────────────────────────────────────────────────────────────┐   │
│ │                            VPC                                    │   │
│ │                                                                   │   │
│ │ ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐     │   │
│ │ │  Private Subnet │  │  Private Subnet │  │  Private Subnet │     │   │
│ │ │  (AZ-a)         │  │  (AZ-b)         │  │  (AZ-c)         │     │   │
│ │ │                 │  │                 │  │                 │     │   │
│ │ │  ┌───────────┐  │  │  ┌───────────┐  │  │  ┌───────────┐  │     │   │
│ │ │  │ Lambda    │  │  │  │ Aurora DB │  │  │  │ Lambda    │  │     │   │
│ │ │  │ Functions │  │  │  │ Cluster   │  │  │  │ Functions │  │     │   │
│ │ │  └───────────┘  │  │  └───────────┘  │  │  └───────────┘  │     │   │
│ │ └─────────────────┘  └─────────────────┘  └─────────────────┘     │   │
│ │                                                                   │   │
│ │ ┌─────────────────────────────────────────────────────────────┐   │   │
│ │ │                    Security Groups                          │   │   │
│ │ │                                                             │   │   │
│ │ │  ┌───────────────┐      ┌───────────────┐                   │   │   │
│ │ │  │ Lambda SG     │      │ Aurora SG     │                   │   │   │
│ │ │  │               │      │               │                   │   │   │
│ │ │  │ - Outbound to │      │ - Inbound from│                   │   │   │
│ │ │  │   Aurora SG   │◄────►│   Lambda SG   │                   │   │   │
│ │ │  │   (port 5432) │      │   (port 5432) │                   │   │   │
│ │ │  └───────────────┘      └───────────────┘                   │   │   │
│ │ └─────────────────────────────────────────────────────────────┘   │   │
│ │                                                                   │   │
│ │ ┌─────────────────────────────────────────────────────────────┐   │   │
│ │ │                    VPC Endpoints                            │   │   │
│ │ │                                                             │   │   │
│ │ │  ┌────────────┐  ┌────────────┐  ┌────────────┐             │   │   │
│ │ │  │ DynamoDB   │  │ S3         │  │ Secrets    │             │   │   │
│ │ │  │ Endpoint   │  │ Endpoint   │  │ Manager    │             │   │   │
│ │ │  │            │  │            │  │ Endpoint   │             │   │   │
│ │ │  └────────────┘  └────────────┘  └────────────┘             │   │   │
│ │ └─────────────────────────────────────────────────────────────┘   │   │
│ └───────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Component Dependencies

The following diagram illustrates component dependencies:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     Component Dependencies                              │
│                                                                         │
│    ┌───────────┐                                                        │
│    │ CloudWatch│                                                        │
│    │ Events    │                                                        │
│    └─────┬─────┘                                                        │
│          │                                                              │
│          │ triggers                                                     │
│          ▼                                                              │
│ ┌─────────────────┐     configures      ┌───────────────────┐          │
│ │ Step Functions  │─────────────────────► Lambda Functions  │          │
│ │ State Machine   │                     │                   │          │
│ └───────┬─────────┘                     └─────────┬─────────┘          │
│         │                                         │                     │
│         │ uses                                    │ use                 │
│         ▼                                         ▼                     │
│ ┌─────────────────┐                     ┌─────────────────────┐        │
│ │ IAM Roles &     │                     │ Common Utilities    │        │
│ │ Policies        │                     │                     │        │
│ └─────────────────┘                     │ - aurora_utils.py   │        │
│                                         │ - common.py         │        │
│                                         │ - metrics.py        │        │
│                                         └─────────┬───────────┘        │
│                                                   │                     │
│                                                   │ interact with       │
│                                                   ▼                     │
│ ┌─────────────────┐  read/write  ┌───────────────────────────────────┐ │
│ │ Lambda Functions│◄────────────►│ AWS Services                      │ │
│ └─────────────────┘              │                                   │ │
│                                   │ - RDS/Aurora                     │ │
│                                   │ - DynamoDB                       │ │
│                                   │ - Secrets Manager                │ │
│                                   │ - CloudWatch                     │ │
│                                   │ - SNS                            │ │
│                                   └───────────────────────────────────┘ │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Code Structure

The codebase is organized as follows:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Code Structure                                   │
│                                                                         │
│ project_root/                                                           │
│ │                                                                       │
│ ├── lambda_functions/                                                   │
│ │   ├── aurora-restore-snapshot-check/                                  │
│ │   │   └── lambda_function.py                                          │
│ │   ├── aurora-restore-copy-snapshot/                                   │
│ │   │   └── lambda_function.py                                          │
│ │   ├── aurora-restore-check-copy-status/                               │
│ │   │   └── lambda_function.py                                          │
│ │   ├── (other lambda functions...)                                     │
│ │                                                                       │
│ ├── utils/                                                              │
│ │   ├── aurora_utils.py                                                 │
│ │   ├── common.py                                                       │
│ │   └── metrics.py                                                      │
│ │                                                                       │
│ ├── infrastructure/                                                     │
│ │   ├── aurora-restore-pipeline.yaml                                    │
│ │   └── parameters.json                                                 │
│ │                                                                       │
│ ├── scripts/                                                            │
│ │   ├── build_lambda_packages.sh                                        │
│ │   └── deploy.sh                                                       │
│ │                                                                       │
│ ├── tests/                                                              │
│ │   ├── unit/                                                           │
│ │   └── integration/                                                    │
│ │                                                                       │
│ └── documentation/                                                      │
│     ├── architecture/                                                   │
│     ├── implementation_guide/                                           │
│     └── troubleshooting/                                                │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Next Steps

For more detailed information about specific components and their implementation, refer to:
- [Data Flow Documentation](./04_data_flow.md)
- [Security Documentation](./05_security.md)
- [Implementation Guide](../implementation_guide/01_prerequisites.md) 