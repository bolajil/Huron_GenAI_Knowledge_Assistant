# Model Context Protocol (MCP) System

## Overview

The Model Context Protocol (MCP) system provides comprehensive monitoring and management capabilities for AI model interactions within the VaultMind GenAI Knowledge Assistant. It tracks operations, tool usage, and system metrics to provide insights into how the system is being used.

## Key Components

### 1. MCP Logger (`mcp/logger.py`)

The core component that logs operations, tools usage, and metrics to a SQLite database. Key features:

- Operation logging with timestamps, user information, and status
- Tool registration and usage tracking
- System metrics collection and analysis
- Dashboard data aggregation

### 2. MCP Dashboard (`tabs/mcp_dashboard.py`)

An administrative interface that provides visualizations and controls for the MCP system:

- Real-time metrics on system usage
- Operation logs with filtering and search
- Tool management interface
- System configuration options
- Security monitoring

### 3. MCP Client (`mcp/mcp_client.py`)

A client library for interacting with MCP tools:

- Tool execution with logging
- Tool listing and discovery
- Smart query routing

### 4. MCP Integration (`mcp/integration.py`)

Integration with the authentication middleware to capture user actions across the system.

## Database Schema

The MCP system uses a SQLite database (`mcp_logs.db`) with the following tables:

1. **mcp_operations**: Logs all operations performed in the system
   - Timestamp, operation name, username, user role, status, duration, details

2. **mcp_tools**: Information about available tools and their usage
   - Name, description, category, last used, usage count, status

3. **mcp_metrics**: System-wide metrics
   - Timestamp, metric name, metric value, details

## Usage

### Logging Operations

```python
from mcp.logger import mcp_logger

# Log an operation
mcp_logger.log_operation(
    operation="SEARCH_DOCUMENTS",
    username="admin",
    user_role="admin",
    status="success",
    duration=2.5,
    details={"query": "cloud security", "results": 5},
    tool_name="document_search"
)
```

### Accessing the Dashboard

The MCP Dashboard is available to users with the `can_view_mcp` permission, typically administrators. It provides real-time insights into system operation.

## Integration Points

The MCP system integrates with:

1. **Authentication Middleware**: Captures user logins, logouts, and permission checks
2. **Search System**: Tracks document searches and retrieval operations
3. **Agent System**: Monitors agent execution and tool usage
4. **Content Management**: Tracks document ingestion and processing

## Future Enhancements

1. **Real-time Alerts**: Configurable alerts for system events
2. **Export Capabilities**: Enhanced export of logs and metrics
3. **Advanced Analytics**: More comprehensive metrics and visualizations
4. **Custom Tool Management**: Interface for adding and configuring tools
