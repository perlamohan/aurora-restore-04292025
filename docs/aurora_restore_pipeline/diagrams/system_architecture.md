# Aurora Restore Pipeline System Architecture

```mermaid
graph TD
    subgraph "AWS Cloud"
        subgraph "Step Functions"
            SF[State Machine]
        end
        
        subgraph "Lambda Functions"
            SC[SnapshotCheckFunction]
            CS[CopySnapshotFunction]
            CCS[CheckCopyStatusFunction]
            DR[DeleteRDSFunction]
            RS[RestoreSnapshotFunction]
            CRS[CheckRestoreStatusFunction]
            SDU[SetupDBUsersFunction]
            AS[ArchiveSnapshotFunction]
            SN[SNSNotificationFunction]
        end
        
        subgraph "DynamoDB"
            ST[State Table]
            AT[Audit Table]
        end
        
        subgraph "SNS"
            SNS[SNS Topic]
        end
        
        subgraph "CloudWatch"
            CW[CloudWatch Logs]
            CWA[CloudWatch Alarms]
        end
        
        subgraph "Secrets Manager"
            SM[Secrets]
        end
        
        subgraph "KMS"
            KMS[KMS Keys]
        end
        
        subgraph "RDS"
            RDS1[Source Aurora Cluster]
            RDS2[Target Aurora Cluster]
        end
    end
    
    User[User] --> SF
    
    SF --> SC
    SC --> CS
    CS --> CCS
    CCS --> DR
    DR --> RS
    RS --> CRS
    CRS --> SDU
    SDU --> AS
    AS --> SN
    
    SC --> ST
    CS --> ST
    CCS --> ST
    DR --> ST
    RS --> ST
    CRS --> ST
    SDU --> ST
    AS --> ST
    SN --> ST
    
    SC --> AT
    CS --> AT
    CCS --> AT
    DR --> AT
    RS --> AT
    CRS --> AT
    SDU --> AT
    AS --> AT
    SN --> AT
    
    SC --> CW
    CS --> CW
    CCS --> CW
    DR --> CW
    RS --> CW
    CRS --> CW
    SDU --> CW
    AS --> CW
    SN --> CW
    
    SC --> CWA
    CS --> CWA
    CCS --> CWA
    DR --> CWA
    RS --> CWA
    CRS --> CWA
    SDU --> CWA
    AS --> CWA
    SN --> CWA
    
    SC --> SM
    CS --> SM
    CCS --> SM
    DR --> SM
    RS --> SM
    CRS --> SM
    SDU --> SM
    AS --> SM
    SN --> SM
    
    SC --> KMS
    CS --> KMS
    CCS --> KMS
    DR --> KMS
    RS --> KMS
    CRS --> KMS
    SDU --> KMS
    AS --> KMS
    SN --> KMS
    
    SC --> RDS1
    CS --> RDS1
    CCS --> RDS1
    DR --> RDS2
    RS --> RDS2
    CRS --> RDS2
    SDU --> RDS2
    AS --> RDS2
    SN --> RDS2
    
    SN --> SNS
```

## Diagram Description

This diagram illustrates the architecture of the Aurora Restore Pipeline, showing the relationships between different AWS services and components:

1. **User**: Initiates the restore process by invoking the Step Functions state machine.
2. **Step Functions**: Orchestrates the entire restore process, coordinating the execution of Lambda functions.
3. **Lambda Functions**: Execute individual steps of the restore process.
4. **DynamoDB**: Stores state and audit information.
5. **SNS**: Sends notifications about the restore process.
6. **CloudWatch**: Stores logs and monitors the health of the pipeline.
7. **Secrets Manager**: Stores sensitive configuration.
8. **KMS**: Encrypts sensitive data.
9. **RDS**: Contains the source and target Aurora clusters.

The arrows indicate the flow of data and control between components. 