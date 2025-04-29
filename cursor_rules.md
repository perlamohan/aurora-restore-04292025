# Aurora Restore Lambda Functions Sequence

This document outlines the sequence and rules for the Aurora restore Lambda functions.

## Function Sequence

The Aurora restore process follows this sequence of Lambda functions:

1. `aurora-restore-snapshot-check` - Checks for the existence of daily snapshots in the source account
2. `aurora-restore-copy-snapshot` - Copies the snapshot to the target region
3. `aurora-restore-check-copy-status` - Checks the status of the snapshot copy operation
4. `aurora-restore-delete-rds` - Deletes the existing RDS cluster in the target region
5. `aurora-restore-check-delete-status` - Checks the status of the cluster deletion
6. `aurora-restore-restore-snapshot` - Restores the cluster from the snapshot
7. `aurora-restore-check-restore-status` - Checks the status of the restore operation
8. `aurora-restore-setup-db-users` - Sets up database users and permissions
9. `aurora-restore-archive-snapshot` - Archives the snapshot after successful restore
10. `aurora-restore-sns-notification` - Sends SNS notification about the restore process completion

## Utility Modules

The Lambda functions utilize the following utility modules:

1. `base_handler.py` - Base handler class providing common functionality for all Lambda functions
2. `common.py` - Common utilities for logging, metrics, and configuration
3. `state_utils.py` - Utilities for state management and transitions
4. `function_utils.py` - Function-specific utilities
5. `aws_utils.py` - AWS service interaction utilities
6. `validation.py` - Input validation utilities

## Coding Standards

All Lambda functions should adhere to the following standards:

1. **Class-based Structure**:
   - Each Lambda function should have a handler class inheriting from `BaseHandler`
   - Organize code into logical methods with clear responsibilities
   - Improve code reusability and maintainability

2. **Error Handling**:
   - Centralize error handling through the base handler
   - Use consistent error reporting and logging
   - Implement proper exception handling with specific error types

3. **State Management**:
   - Use improved state handling with dedicated methods
   - Ensure clear state transitions and updates
   - Implement proper state validation and error checking

4. **Code Organization**:
   - Split functionality into smaller, focused methods
   - Add comprehensive docstrings and type hints
   - Improve code readability and maintainability

5. **Metrics and Logging**:
   - Use consistent metrics tracking
   - Implement improved logging with context
   - Ensure proper performance monitoring

6. **AWS Integration**:
   - Improve AWS client initialization
   - Implement better error handling for AWS operations
   - Ensure cleaner AWS service interactions

7. **Documentation**:
   - Add comprehensive docstrings
   - Provide clear method and class documentation
   - Include improved code comments

## Best Practices

1. **Modularity**: Keep functions small and focused on a single responsibility
2. **Error Handling**: Implement proper error handling and recovery mechanisms
3. **Logging**: Use structured logging with appropriate context
4. **Metrics**: Track performance metrics and error rates
5. **State Management**: Maintain clear state transitions and validation
6. **Security**: Follow security best practices for AWS resource access
7. **Testing**: Implement unit tests for critical functionality 