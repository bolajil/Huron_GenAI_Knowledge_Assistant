# Project Cleanup Recommendations

## Files and Folders to Remove

Based on analysis of your VaultMind GenAI Knowledge Assistant project, here are the items that should be removed as they are not relevant to the core functionality:

### 🗑️ **Test/Debug Files to Remove:**
```
test_chunking_fix.py
agent_assistant_console.py
agent_assistant_demo.py
demo_enhanced_research.py
direct_aws_test.py
simple_aws_test.py
simple_dashboard.py
simple_tab_breakdown.py
tab_breakdown_script.py
document_listing.py
fix_import_error.py
fix_user_objects.py
setup_enterprise.py
verify_packages.py
vector_db_fix.py
```

### 🗑️ **Unnecessary Batch Files:**
```
analyze_document.bat
list_available_documents.bat
list_documents.bat
run_query_debug.bat
run_test.bat
start_enhanced_agent.bat
start_vaultmind_9000.bat
start_vaultmind_9999.bat
start_vaultmind_improved.bat
diagnose_query.ps1
```

### 🗑️ **Obsolete Configuration Files:**
```
flowise.yml
package-lock.json
package.json
constraints.txt
cloud_requirements.txt
simple_requirements.txt
```

### 🗑️ **Demo/HTML Files:**
```
vaultmind_agent_demo.html
vaultmind_dashboard.html
vaultmind_tabs.json
```

### 🗑️ **Database/Log Files:**
```
mcp_logs.db
```

### 🗑️ **Miscellaneous Files:**
```
agent_integration_enhancement.md
notification_service.py
schemas.py
query_llm.py
query_llm_streamlit.py
check_vector_db.py
apply_vector_db_fix.py
main.py
```

### 🗑️ **Directories to Remove:**
```
__pycache__/ (all instances)
vaultmind_modular/
vector_store/
vectorstores/
mcp-tracking-UI/
src/
docker/
```

## ✅ **Essential Files to Keep:**

### Core Application Files:
- `genai_dashboard.py` - Main dashboard
- `genai_dashboard_modular.py` - Modular dashboard
- `genai_dashboard_secure.py` - Secure version
- `run_app.py` - Application runner
- `run_enterprise.py` - Enterprise runner

### Essential Batch Files:
- `run_app.bat` - Main app launcher
- `start_vaultmind.bat` - Primary startup script
- `run_vaultmind.bat` - VaultMind runner

### Core Directories:
- `app/` - Core application logic
- `tabs/` - UI tabs
- `utils/` - Utility functions
- `config/` - Configuration files
- `data/` - Data storage
- `tests/` - Essential tests only
- `docs/` - Documentation
- `api/` - API endpoints
- `assets/` - Static assets
- `models/` - AI models
- `scripts/` - Essential scripts
- `template/` - Templates
- `ui/` - UI components

## 🚀 **Cleanup Command:**

Run the cleanup script I created:
```bash
python cleanup_irrelevant_files.py
```

This will safely remove all identified irrelevant files while preserving the core VaultMind functionality.

## 📊 **Expected Results:**

After cleanup, your project will be:
- **Cleaner and more professional**
- **Easier to navigate and maintain**
- **Focused on core VaultMind functionality**
- **Reduced file count by ~50+ files**
- **Smaller repository size**

The cleanup preserves all essential functionality while removing test files, demos, and obsolete components that clutter the project structure.
