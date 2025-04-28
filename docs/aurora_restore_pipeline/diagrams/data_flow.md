# Aurora Restore Pipeline Data Flow

```mermaid
sequenceDiagram
    participant User
    participant SF as Step Functions
    participant SC as SnapshotCheckFunction
    participant CS as CopySnapshotFunction
    participant CCS as CheckCopyStatusFunction
    participant DR as DeleteRDSFunction
    participant RS as RestoreSnapshotFunction
    participant CRS as CheckRestoreStatusFunction
    participant SDU as SetupDBUsersFunction
    participant AS as ArchiveSnapshotFunction
    participant SN as SNSNotificationFunction
    participant ST as State Table
    participant AT as Audit Table
    participant SNS as SNS Topic
    participant RDS1 as Source RDS
    participant RDS2 as Target RDS
    
    User->>SF: Invoke State Machine
    SF->>SC: Execute SnapshotCheckFunction
    
    SC->>RDS1: Check Snapshot Availability
    RDS1-->>SC: Snapshot Status
    SC->>ST: Save State
    SC->>AT: Log Audit Event
    SC-->>SF: Snapshot Check Result
    
    SF->>CS: Execute CopySnapshotFunction
    CS->>RDS1: Copy Snapshot
    RDS1-->>CS: Copy Initiated
    CS->>ST: Save State
    CS->>AT: Log Audit Event
    CS-->>SF: Copy Initiated
    
    SF->>CCS: Execute CheckCopyStatusFunction
    CCS->>RDS1: Check Copy Status
    RDS1-->>CCS: Copy Status
    CCS->>ST: Save State
    CCS->>AT: Log Audit Event
    CCS-->>SF: Copy Status
    
    alt Copy Not Complete
        SF->>CCS: Execute CheckCopyStatusFunction (Retry)
    else Copy Complete
        SF->>DR: Execute DeleteRDSFunction
        DR->>RDS2: Delete Existing Cluster
        RDS2-->>DR: Delete Status
        DR->>ST: Save State
        DR->>AT: Log Audit Event
        DR-->>SF: Delete Status
        
        SF->>RS: Execute RestoreSnapshotFunction
        RS->>RDS2: Restore from Snapshot
        RDS2-->>RS: Restore Initiated
        RS->>ST: Save State
        RS->>AT: Log Audit Event
        RS-->>SF: Restore Initiated
        
        SF->>CRS: Execute CheckRestoreStatusFunction
        CRS->>RDS2: Check Restore Status
        RDS2-->>CRS: Restore Status
        CRS->>ST: Save State
        CRS->>AT: Log Audit Event
        CRS-->>SF: Restore Status
        
        alt Restore Not Complete
            SF->>CRS: Execute CheckRestoreStatusFunction (Retry)
        else Restore Complete
            SF->>SDU: Execute SetupDBUsersFunction
            SDU->>RDS2: Setup DB Users
            RDS2-->>SDU: Setup Status
            SDU->>ST: Save State
            SDU->>AT: Log Audit Event
            SDU-->>SF: Setup Status
            
            SF->>AS: Execute ArchiveSnapshotFunction
            AS->>RDS1: Archive Snapshot
            RDS1-->>AS: Archive Status
            AS->>ST: Save State
            AS->>AT: Log Audit Event
            AS-->>SF: Archive Status
            
            SF->>SN: Execute SNSNotificationFunction
            SN->>SNS: Send Notification
            SNS-->>SN: Notification Sent
            SN->>ST: Save State
            SN->>AT: Log Audit Event
            SN-->>SF: Notification Sent
        end
    end
```

## Diagram Description

This sequence diagram illustrates the data flow of the Aurora Restore Pipeline, showing the interactions between different components:

1. **User**: Initiates the restore process by invoking the Step Functions state machine.
2. **Step Functions**: Orchestrates the entire restore process, coordinating the execution of Lambda functions.
3. **Lambda Functions**: Execute individual steps of the restore process.
4. **DynamoDB Tables**: Store state and audit information.
5. **SNS Topic**: Sends notifications about the restore process.
6. **RDS**: Contains the source and target Aurora clusters.

The diagram shows the flow of data and control between components, including:
- Checking the availability of the source snapshot
- Copying the snapshot from the source region to the target region
- Checking the status of the snapshot copy operation
- Deleting an existing RDS cluster in the target region (if needed)
- Restoring the Aurora cluster from the snapshot
- Checking the status of the restore operation
- Setting up database users and permissions
- Archiving the snapshot after successful restore
- Sending notifications about the completion of the restore operation

The diagram also shows the retry logic for the snapshot copy and restore operations. 