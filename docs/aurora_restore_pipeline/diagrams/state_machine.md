# Aurora Restore Pipeline State Machine

```mermaid
stateDiagram-v2
    [*] --> SnapshotCheck
    
    state SnapshotCheck {
        [*] --> CheckSnapshot
        CheckSnapshot --> SnapshotAvailable
        CheckSnapshot --> SnapshotNotFound
        SnapshotAvailable --> [*]
        SnapshotNotFound --> [*]
    }
    
    SnapshotCheck --> CopySnapshot
    SnapshotCheck --> HandleFailure
    
    state CopySnapshot {
        [*] --> InitiateCopy
        InitiateCopy --> CopyInitiated
        CopyInitiated --> [*]
    }
    
    CopySnapshot --> CheckCopyStatus
    CopySnapshot --> HandleFailure
    
    state CheckCopyStatus {
        [*] --> CheckStatus
        CheckStatus --> CopyComplete
        CheckStatus --> CopyInProgress
        CheckStatus --> CopyFailed
        CopyComplete --> [*]
        CopyInProgress --> [*]
        CopyFailed --> [*]
    }
    
    CheckCopyStatus --> IsCopyComplete
    CheckCopyStatus --> HandleFailure
    
    state IsCopyComplete {
        [*] --> Evaluate
        Evaluate --> Yes
        Evaluate --> No
        Yes --> [*]
        No --> [*]
    }
    
    IsCopyComplete --> DeleteRDS
    IsCopyComplete --> WaitForCopy
    IsCopyComplete --> HandleFailure
    
    state WaitForCopy {
        [*] --> Wait
        Wait --> [*]
    }
    
    WaitForCopy --> CheckCopyStatus
    
    state DeleteRDS {
        [*] --> CheckExisting
        CheckExisting --> ClusterExists
        CheckExisting --> NoCluster
        ClusterExists --> DeleteCluster
        DeleteCluster --> ClusterDeleted
        NoCluster --> [*]
        ClusterDeleted --> [*]
    }
    
    DeleteRDS --> RestoreSnapshot
    DeleteRDS --> HandleFailure
    
    state RestoreSnapshot {
        [*] --> InitiateRestore
        InitiateRestore --> RestoreInitiated
        RestoreInitiated --> [*]
    }
    
    RestoreSnapshot --> CheckRestoreStatus
    RestoreSnapshot --> HandleFailure
    
    state CheckRestoreStatus {
        [*] --> CheckStatus
        CheckStatus --> RestoreComplete
        CheckStatus --> RestoreInProgress
        CheckStatus --> RestoreFailed
        RestoreComplete --> [*]
        RestoreInProgress --> [*]
        RestoreFailed --> [*]
    }
    
    CheckRestoreStatus --> IsRestoreComplete
    CheckRestoreStatus --> HandleFailure
    
    state IsRestoreComplete {
        [*] --> Evaluate
        Evaluate --> Yes
        Evaluate --> No
        Yes --> [*]
        No --> [*]
    }
    
    IsRestoreComplete --> SetupDBUsers
    IsRestoreComplete --> WaitForRestore
    IsRestoreComplete --> HandleFailure
    
    state WaitForRestore {
        [*] --> Wait
        Wait --> [*]
    }
    
    WaitForRestore --> CheckRestoreStatus
    
    state SetupDBUsers {
        [*] --> SetupUsers
        SetupUsers --> UsersSetup
        UsersSetup --> [*]
    }
    
    SetupDBUsers --> ArchiveSnapshot
    SetupDBUsers --> HandleFailure
    
    state ArchiveSnapshot {
        [*] --> Archive
        Archive --> SnapshotArchived
        SnapshotArchived --> [*]
    }
    
    ArchiveSnapshot --> SendNotification
    ArchiveSnapshot --> HandleFailure
    
    state SendNotification {
        [*] --> Send
        Send --> NotificationSent
        NotificationSent --> [*]
    }
    
    SendNotification --> [*]
    SendNotification --> HandleFailure
    
    state HandleFailure {
        [*] --> LogError
        LogError --> SendErrorNotification
        SendErrorNotification --> [*]
    }
```

## Diagram Description

This state diagram illustrates the Step Functions state machine of the Aurora Restore Pipeline, showing the states and transitions:

1. **SnapshotCheck**: Validates the source snapshot and checks its availability.
2. **CopySnapshot**: Copies the snapshot from the source region to the target region.
3. **CheckCopyStatus**: Checks the status of the snapshot copy operation.
4. **IsCopyComplete**: Determines if the snapshot copy is complete.
5. **WaitForCopy**: Waits for a specified period before checking the copy status again.
6. **DeleteRDS**: Deletes an existing RDS cluster in the target region (if needed).
7. **RestoreSnapshot**: Restores the Aurora cluster from the snapshot.
8. **CheckRestoreStatus**: Checks the status of the restore operation.
9. **IsRestoreComplete**: Determines if the restore operation is complete.
10. **WaitForRestore**: Waits for a specified period before checking the restore status again.
11. **SetupDBUsers**: Sets up database users and permissions.
12. **ArchiveSnapshot**: Archives the snapshot after successful restore.
13. **SendNotification**: Sends a notification about the completion of the restore operation.
14. **HandleFailure**: Handles failures in the restore process.

The diagram shows the flow of control between states, including:
- The main flow of the restore process
- The retry logic for the snapshot copy and restore operations
- The error handling paths

Each state has its own sub-states, showing the internal logic of the state. 