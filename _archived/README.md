# Archived Files

This directory contains files that were archived during the Huron Enterprise transformation.

## Why Archived?

These files are **not currently imported** by the main dashboard (`genai_dashboard_modular.py`) or `tabs/__init__.py`. They represent:
- Duplicate/variant implementations
- Superseded versions
- Backup files

## Contents

### `/tabs/` - Archived Tab Variants

| File | Reason Archived |
|------|-----------------|
| `chat_assistant.py` | Superseded by `chat_assistant_enhanced.py` |
| `chat_assistant_enterprise.py` | Not imported; enterprise UI can be merged later |
| `chat_assistant_fixed.py` | Bug-fix version, changes merged into enhanced |
| `chat_assistant_modern.py` | UI variant, not imported |
| `chat_assistant_professional.py` | UI variant, not imported |
| `chat_assistant_ultimate.py` | UI variant, not imported |
| `agent_assistant.py` | Superseded by `agent_assistant_enhanced.py` |
| `agent_assistant_mock.py` | Empty file |
| `agent_assistant_simple.py` | Empty file |
| `document_ingestion.py` | Superseded by `document_ingestion_fixed.py` |
| `enhanced_research_updated.py` | Not imported |
| `agent_assistant_enhanced.py.fixed` | Backup file |
| `query_assistant.py.new` | Empty/backup |
| `query_assistant_backup.py` | Empty/backup |
| `query_assistant_simple.py` | Empty file |
| `mcp_dashboard.py.bak_*` | Backup file |

## Restoring Files

If you need to restore a file:

```bash
# Copy back to tabs/
cp _archived/tabs/chat_assistant_enterprise.py tabs/

# Update tabs/__init__.py to import it
```

## Active Tab Files

The following files in `tabs/` ARE actively imported and should NOT be archived:

- `chat_assistant_enhanced.py` ← Chat Assistant
- `agent_assistant_enhanced.py` ← Agent Assistant
- `agent_assistant_hybrid.py` ← Agent Hybrid (LangGraph)
- `query_assistant.py` ← Query Assistant
- `document_ingestion_fixed.py` ← Document Ingestion
- `enhanced_research.py` ← Enhanced Research
- `mcp_dashboard.py` ← MCP Dashboard
- `multi_content_enhanced.py` ← Multi-Content
- `admin_panel.py` ← Admin Panel
- `tool_requests.py` ← Tool Requests
- `user_permissions_tab.py` ← Permissions
- And others...

---

*Archived on: May 2026*  
*Project: VaultMind → Huron Enterprise*
