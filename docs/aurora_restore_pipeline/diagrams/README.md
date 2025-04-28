# Aurora Restore Pipeline Diagrams

This directory contains diagrams that illustrate the architecture, data flow, and state machine of the Aurora Restore Pipeline.

## Diagrams

1. [System Architecture](system_architecture.md) - Illustrates the architecture of the Aurora Restore Pipeline, showing the relationships between different AWS services and components.

2. [Data Flow](data_flow.md) - Illustrates the data flow of the Aurora Restore Pipeline, showing the interactions between different components.

3. [State Machine](state_machine.md) - Illustrates the Step Functions state machine of the Aurora Restore Pipeline, showing the states and transitions.

## Diagram Formats

The diagrams are created using Mermaid, a JavaScript-based diagramming and charting tool that renders Markdown-inspired text definitions to create and modify diagrams dynamically.

## Viewing the Diagrams

To view the diagrams, you can use any Markdown viewer that supports Mermaid, such as:
- GitHub
- GitLab
- VS Code with the Mermaid extension
- Mermaid Live Editor (https://mermaid.live/)

## Generating Images

To generate images from the Mermaid diagrams, you can use the Mermaid CLI or the Mermaid Live Editor.

### Using Mermaid CLI

1. Install the Mermaid CLI:
   ```
   npm install -g @mermaid-js/mermaid-cli
   ```

2. Generate an image from a Mermaid diagram:
   ```
   mmdc -i system_architecture.md -o system_architecture.png
   ```

### Using Mermaid Live Editor

1. Copy the Mermaid code from the diagram file.
2. Paste the code into the Mermaid Live Editor (https://mermaid.live/).
3. Export the diagram as an image. 