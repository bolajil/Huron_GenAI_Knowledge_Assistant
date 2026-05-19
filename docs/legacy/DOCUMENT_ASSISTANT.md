# VaultMIND Document Assistant

This tool provides advanced document management capabilities, including document analysis, improvement, and knowledge extraction.

## Key Features

### Document Operations
- **Document Analysis**: Review and analyze document structure, content, and organization
- **Document Improvement**: Enhance document structure, formatting, and content clarity
- **Document Visualization**: See what's in your indexed documents
- **Document Creation**: Create new documents based on your requirements

### Knowledge Operations
- **Document-based Knowledge**: Extract information from indexed documents
- **General Knowledge**: Get information from the agent's built-in knowledge
- **Combined Knowledge**: Leverage both document and general knowledge sources

## Usage Guide

### Working with Indexed Documents

#### Analyzing Documents
To analyze a document in the index:
```
analyze_document.bat AWS
```

This will show you information about the document's structure, content, and key components.

#### Improving Documents
To improve a document, use the Agent Assistant tab and specify:
```
Category: Document Operations
Operation: Document Improvement
Task: Improve AWS document
```

#### Listing Available Documents
To see what documents are available in the index:
```
list_documents.bat
```

### Tips for Best Results

1. Be specific about which document you want to work with
2. For document operations, select "Use Indexed Documents" as the knowledge source
3. For general knowledge, select "Use General Knowledge" as the source
4. You can combine document analysis with general knowledge for comprehensive results

## Troubleshooting

If the agent can't find a document:
1. Use `list_documents.bat` to see exactly what documents are available
2. Try variations of the document name (e.g., "AWS", "AWS_index", "aws documentation")
3. Check that the document is properly indexed in the knowledge base

## Developer Notes

The agent's document capabilities are implemented in the following files:
- `tabs/agent_assistant_enhanced.py`: Main agent assistant implementation
- `analyze_document.py`: Tool for document analysis
- `list_documents.py`: Tool to list available documents
