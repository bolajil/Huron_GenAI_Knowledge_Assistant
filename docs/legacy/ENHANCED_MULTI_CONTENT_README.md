# Enhanced Multi-Content Dashboard

## Overview
The Enhanced Multi-Content Dashboard provides advanced content management capabilities with PowerBI integration and comprehensive Excel support, built on top of the enterprise permission system.

## Features

### 🔐 Enterprise Security Integration
- **Permission-based access control** using the enterprise permission system
- **Role-based tab visibility** - users only see features they have access to
- **Resource request integration** - users can request additional permissions
- **Audit logging** for all user actions

### 📊 PowerBI Integration
- **Embedded PowerBI reports** with iframe support
- **Connection configuration** for Azure AD authentication
- **Multiple authentication methods**: Service Principal, User Auth, Managed Identity
- **Report management** with workspace integration
- **Custom report embedding** with dynamic parameters

### 📈 Excel Analytics & Viewer
- **Full Excel file processing** with openpyxl engine
- **Multi-sheet support** with tab navigation
- **Advanced data viewing modes**:
  - Table View with pagination
  - Summary Statistics
  - Data Types analysis
  - Missing Values analysis
- **Interactive chart generation**:
  - Line Charts, Bar Charts, Scatter Plots
  - Histograms, Box Plots
  - Dynamic column selection
- **Data profiling capabilities** (extensible)

### 🔍 Multi-Source Search
- **Unified search interface** across multiple content types
- **Source selection**: Documents, Excel files, Web search, PowerBI reports
- **Search type options**: Semantic, Keyword, Hybrid
- **Configurable result formats**: Summary, Detailed, Raw Data
- **Search engine integration**: Google, Bing, DuckDuckGo

### 📋 Content Management
- **Content overview dashboard** with metrics
- **Bulk operations** for admins and power users
- **Content refresh and cleanup tools**
- **Backup and reporting capabilities**

### ⚙️ Integrations Hub
- **Available connectors**: PowerBI, Excel Online, SharePoint, OneDrive, Google Sheets, Tableau
- **Connection status monitoring**
- **Configuration management**
- **Connection testing tools**
- **Custom integration support**

## Permission Requirements

### Feature Access Matrix
| Feature | Viewer | User | Power User | Admin |
|---------|--------|------|------------|-------|
| Excel Analytics | ✅ | ✅ | ✅ | ✅ |
| PowerBI Reports | ❌ | ❌ | ✅ | ✅ |
| Multi-Source Search | ❌ | ✅ | ✅ | ✅ |
| Content Management | ❌ | ❌ | ✅ | ✅ |
| Integrations Config | ❌ | ❌ | ❌ | ✅ |

### Enterprise Permissions Required
- `multi_source_search` (READ) - Access to enhanced search
- `enhanced_research` (READ) - Multi-source search tab
- `analytics_dashboard` (READ) - PowerBI reports tab
- `integrations` (WRITE) - Integration configuration (Admin only)

## Installation & Setup

### 1. Install Dependencies
```bash
pip install -r requirements-multicontent.txt
```

### 2. Required Dependencies
- `plotly>=5.17.0` - Interactive charts and visualizations
- `openpyxl>=3.1.2` - Excel file processing
- `xlrd>=2.0.1` - Legacy Excel support
- `pandas>=2.0.0` - Data manipulation
- `numpy>=1.24.0` - Numerical operations
- `streamlit-components-v1>=0.0.1` - Custom components

### 3. PowerBI Configuration
1. **Azure AD App Registration**:
   - Register app in Azure AD
   - Configure API permissions for PowerBI
   - Generate client secret

2. **PowerBI Workspace Setup**:
   - Create dedicated workspace
   - Configure security settings
   - Note workspace GUID

3. **Authentication Setup**:
   - Configure in Security Setup tab (Admin only)
   - Test connection before use

## Usage Guide

### Excel File Analysis
1. **Upload Excel File**: Use the file uploader in Excel Analytics tab
2. **Select Sheet**: Choose from available sheets
3. **Choose View Mode**: Table, Statistics, Data Types, or Missing Values
4. **Generate Charts**: Select columns and chart type for visualization
5. **Advanced Operations**: Access pivot tables, profiling, and export features

### PowerBI Integration
1. **Admin Configuration**: Set up PowerBI connection in admin settings
2. **Browse Reports**: View available reports in gallery
3. **Custom Embedding**: Use Report ID and Workspace ID for custom reports
4. **Interactive Dashboards**: Full PowerBI functionality within VaultMind

### Multi-Source Search
1. **Enter Query**: Type search terms or questions
2. **Select Sources**: Choose document collections, Excel files, web sources
3. **Configure Options**: Set result limits, search type, and format
4. **Review Results**: Analyze findings across all sources

## Technical Architecture

### File Structure
```
tabs/
├── multi_content_enhanced.py     # Main enhanced dashboard
├── multi_content_dashboard.py    # Original dashboard (fallback)
└── __init__.py                   # Module imports

requirements-multicontent.txt      # Additional dependencies
```

### Integration Points
- **Enterprise Permissions**: `app.auth.enterprise_permissions`
- **Resource Requests**: `app.auth.resource_request_manager`
- **Authentication**: `app.middleware.auth_middleware`
- **Main Dashboard**: `genai_dashboard_modular.py`

### Error Handling
- **Graceful fallback** to original multi-content dashboard if enhanced version fails
- **Permission-based error messages** with guidance for access requests
- **Comprehensive logging** for debugging and audit trails

## Security Considerations

### Data Protection
- **File upload validation** for Excel files
- **Secure PowerBI embedding** with proper authentication
- **Session-based access control** with enterprise permissions
- **Audit logging** for all user actions

### Access Control
- **Role-based feature access** with granular permissions
- **Resource request workflow** for additional access
- **Admin-only configuration** for sensitive integrations
- **Permission inheritance** from enterprise system

## Troubleshooting

### Common Issues
1. **PowerBI Not Loading**: Check Azure AD configuration and network connectivity
2. **Excel Upload Fails**: Verify file format (xlsx/xls) and size limits
3. **Permission Denied**: Request access through User Permissions tab
4. **Charts Not Generating**: Ensure numeric columns are available

### Debug Mode
Enable detailed logging by setting `logging.basicConfig(level=logging.DEBUG)` in the main dashboard.

### Fallback Behavior
If enhanced features fail, the system automatically falls back to the original multi-content dashboard with a warning message.

## Future Enhancements

### Planned Features
- **Real-time PowerBI refresh** with webhook integration
- **Advanced Excel operations**: Pivot tables, data cleaning, transformations
- **AI-powered insights** for uploaded Excel data
- **Custom connector framework** for additional integrations
- **Collaborative features** for shared analysis

### API Extensions
- **REST API endpoints** for programmatic access
- **Webhook support** for external integrations
- **Bulk upload capabilities** for large datasets
- **Export functionality** in multiple formats

## Support & Maintenance

### Monitoring
- **Performance metrics** tracked in MCP dashboard
- **Usage analytics** available in admin panel
- **Error tracking** with detailed logs
- **User activity auditing** through enterprise system

### Updates
- **Modular architecture** allows independent feature updates
- **Backward compatibility** maintained with fallback systems
- **Configuration-driven** feature toggles
- **Enterprise-grade** deployment support

---

For technical support or feature requests, contact the VaultMind development team or submit a request through the Tool Requests tab.
