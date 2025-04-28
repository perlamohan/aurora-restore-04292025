# Design Decisions

This document outlines the key design decisions made during the development of the Aurora Restore Pipeline, explaining the rationale behind each choice and the trade-offs considered.

## Serverless Architecture

### Decision
Implement the entire pipeline using serverless components (Lambda, Step Functions, DynamoDB) instead of container-based or EC2-based solutions.

### Rationale
- **Cost Efficiency**: Pay-per-use model reduces costs for intermittent restore operations
- **Operational Overhead**: Eliminates the need to manage and patch servers
- **Scalability**: Automatic scaling handles variable workload demands
- **Development Speed**: Faster development and iteration with managed services

### Trade-offs
- **Cold Start Latency**: Lambda functions may experience cold starts, but acceptable for this use case
- **Execution Duration Limits**: 15-minute Lambda execution limit requires breaking complex operations into multiple functions
- **Debugging Complexity**: Distributed nature can make debugging more challenging

## Step Functions for Orchestration

### Decision
Use AWS Step Functions to orchestrate the pipeline workflow instead of other workflow engines or custom orchestration code.

### Rationale
- **Visual Workflow**: Provides visual representation of workflow for easier understanding
- **State Management**: Built-in state management between steps
- **Error Handling**: Robust error handling with retry capabilities
- **Integration**: Native integration with AWS services
- **Auditability**: Complete execution history for audit and troubleshooting

### Trade-offs
- **Cost**: Per-state transition costs, but offset by reliability benefits
- **Vendor Lock-in**: Tightly coupled to AWS ecosystem
- **Complexity**: State machine definition can become complex for advanced workflows

## DynamoDB for State Storage

### Decision
Use DynamoDB for storing operation state and audit logs instead of relational databases or file-based storage.

### Rationale
- **Scalability**: Automatic scaling to handle any volume of operations
- **Performance**: Consistent single-digit millisecond response times
- **Durability**: Fully managed, highly available storage with cross-region replication options
- **Serverless**: Aligns with serverless architecture principles
- **TTL Support**: Automated cleanup of old records

### Trade-offs
- **Query Limitations**: Less flexible than SQL for complex queries
- **Cost Model**: Pricing based on provisioned capacity or on-demand can be complex to optimize
- **Transaction Limits**: Size limitations for items and transactions

## Modular Lambda Functions

### Decision
Implement multiple single-purpose Lambda functions instead of fewer, more complex functions.

### Rationale
- **Separation of Concerns**: Each function handles a specific task
- **Maintainability**: Smaller, focused functions are easier to understand and maintain
- **Independent Scaling**: Functions can scale independently based on their workload
- **Retry Flexibility**: Granular retry strategies for different operation types
- **Execution Duration**: Working within Lambda's 15-minute execution limit

### Trade-offs
- **Increased Latency**: More function invocations can lead to higher total latency
- **Cross-Function Communication**: Requires standardized state passing
- **Cold Start Multiplication**: More functions mean more potential cold starts

## JSON for Configuration and State

### Decision
Use JSON for configuration files, event passing, and state storage instead of YAML, XML, or binary formats.

### Rationale
- **Ubiquity**: Widely understood and supported format
- **Native AWS Support**: Native format for Lambda events and Step Functions
- **Human Readability**: Relatively easy to read and edit
- **Schema Flexibility**: Easy to extend and evolve

### Trade-offs
- **Verbosity**: More verbose than some alternatives like YAML
- **No Comments**: Standard JSON doesn't support comments
- **Type Safety**: Lacks built-in type validation (mitigated with schema validation)

## Cross-Region Support

### Decision
Implement support for cross-region snapshot operations instead of limiting to single-region.

### Rationale
- **Disaster Recovery**: Supports DR scenarios requiring cross-region restores
- **Environment Parity**: Enables copying production data to non-production environments in different regions
- **Resource Optimization**: Allows for leveraging resources in optimal regions

### Trade-offs
- **Increased Complexity**: More complex error handling and state management
- **Cost**: Cross-region data transfer incurs additional costs
- **Latency**: Cross-region operations take longer to complete

## SNS for Notifications

### Decision
Use Amazon SNS for notifications instead of direct integrations (email, Slack, etc.) or custom notification solutions.

### Rationale
- **Flexibility**: Subscribers can choose preferred notification channels
- **Scalability**: Handles any volume of notifications
- **Reliability**: Managed service with high availability
- **Integration**: Easy integration with other AWS services
- **Fan-out**: Supports multiple subscribers for different purposes

### Trade-offs
- **Limited Formatting**: Basic formatting capabilities compared to custom solutions
- **Delivery Semantics**: At-least-once delivery may result in duplicate notifications
- **Authentication**: Limited authentication options for subscribers

## IAM Role-Based Security

### Decision
Use fine-grained IAM roles for each Lambda function instead of broader permissions.

### Rationale
- **Principle of Least Privilege**: Each function has only the permissions it needs
- **Security**: Reduces blast radius of potential security issues
- **Auditability**: Clearer security boundaries for audit purposes
- **Compliance**: Easier to demonstrate compliance with security standards

### Trade-offs
- **Management Overhead**: More roles to create and maintain
- **Deployment Complexity**: More complex CloudFormation templates or IAC code
- **Permission Boundaries**: Can be challenging to define perfect boundaries

## Next Steps

For more information about how these design decisions are implemented, refer to:
- [Component Diagram](./03_component_diagram.md)
- [Data Flow](./04_data_flow.md)
- [Lambda Functions API Reference](../api_reference/01_lambda_functions.md) 