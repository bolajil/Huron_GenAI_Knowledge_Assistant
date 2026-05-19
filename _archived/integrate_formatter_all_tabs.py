"""
Script to integrate Universal Response Formatter into all VaultMind tabs
Automatically patches tabs to add beautiful response formatting
"""

import os
import re
from pathlib import Path
from typing import List, Tuple


class TabFormatterIntegrator:
    """Integrates response formatter into VaultMind tabs"""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.tabs_dir = self.project_root / "tabs"
        self.backup_dir = self.project_root / "tabs_backup"
        
    def backup_tabs(self):
        """Backup all tabs before modification"""
        import shutil
        
        if self.backup_dir.exists():
            print(f"⚠️  Backup directory already exists: {self.backup_dir}")
            response = input("Overwrite existing backup? (y/n): ")
            if response.lower() != 'y':
                print("❌ Backup cancelled")
                return False
        
        print(f"📦 Creating backup in {self.backup_dir}...")
        shutil.copytree(self.tabs_dir, self.backup_dir, dirs_exist_ok=True)
        print("✅ Backup created successfully")
        return True
    
    def integrate_query_assistant(self):
        """Integrate formatter into Query Assistant"""
        file_path = self.tabs_dir / "query_assistant.py"
        
        if not file_path.exists():
            print(f"⚠️  File not found: {file_path}")
            return False
        
        print(f"🔧 Integrating formatter into Query Assistant...")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if already integrated
        if 'universal_response_formatter' in content:
            print("ℹ️  Query Assistant already has formatter integration")
            return True
        
        # Add import at top
        import_line = "from utils.universal_response_formatter import format_and_display, add_formatter_settings\n"
        
        # Find import section
        import_match = re.search(r'(import streamlit as st\n)', content)
        if import_match:
            content = content.replace(
                import_match.group(1),
                import_match.group(1) + import_line
            )
        
        # Add settings UI in render function
        render_match = re.search(r'def render[_\w]*\(\):', content)
        if render_match:
            # Find the st.title line after render function
            title_match = re.search(r'(st\.title\([^)]+\)\n)', content[render_match.end():])
            if title_match:
                insert_pos = render_match.end() + title_match.end()
                settings_code = '\n    # Add response formatter settings\n    add_formatter_settings(tab_name="Query Assistant", location="sidebar")\n'
                content = content[:insert_pos] + settings_code + content[insert_pos:]
        
        # Save modified content
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("✅ Query Assistant integration complete")
        return True
    
    def integrate_chat_assistant(self):
        """Integrate formatter into Chat Assistant"""
        file_path = self.tabs_dir / "chat_assistant.py"
        
        if not file_path.exists():
            print(f"⚠️  File not found: {file_path}")
            return False
        
        print(f"🔧 Integrating formatter into Chat Assistant...")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if already integrated
        if 'universal_response_formatter' in content:
            print("ℹ️  Chat Assistant already has formatter integration")
            return True
        
        # Add import
        import_line = "from utils.universal_response_formatter import format_and_display, add_formatter_settings\n"
        import_match = re.search(r'(import streamlit as st\n)', content)
        if import_match:
            content = content.replace(
                import_match.group(1),
                import_match.group(1) + import_line
            )
        
        # Add settings UI
        render_match = re.search(r'def render[_\w]*\(\):', content)
        if render_match:
            title_match = re.search(r'(st\.title\([^)]+\)\n)', content[render_match.end():])
            if title_match:
                insert_pos = render_match.end() + title_match.end()
                settings_code = '\n    # Add response formatter settings\n    add_formatter_settings(tab_name="Chat Assistant", location="expander")\n'
                content = content[:insert_pos] + settings_code + content[insert_pos:]
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("✅ Chat Assistant integration complete")
        return True
    
    def integrate_agent_assistant(self):
        """Integrate formatter into Agent Assistant"""
        file_path = self.tabs_dir / "agent_assistant_enhanced.py"
        
        if not file_path.exists():
            print(f"⚠️  File not found: {file_path}")
            return False
        
        print(f"🔧 Integrating formatter into Agent Assistant...")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if already integrated
        if 'universal_response_formatter' in content:
            print("ℹ️  Agent Assistant already has formatter integration")
            return True
        
        # Add import
        import_line = "from utils.universal_response_formatter import format_and_display, add_formatter_settings\n"
        import_match = re.search(r'(import streamlit as st\n)', content)
        if import_match:
            content = content.replace(
                import_match.group(1),
                import_match.group(1) + import_line
            )
        
        # Add settings UI
        render_match = re.search(r'def render[_\w]*\(\):', content)
        if render_match:
            title_match = re.search(r'(st\.title\([^)]+\)\n)', content[render_match.end():])
            if title_match:
                insert_pos = render_match.end() + title_match.end()
                settings_code = '\n    # Add response formatter settings\n    add_formatter_settings(tab_name="Agent Assistant", location="sidebar")\n'
                content = content[:insert_pos] + settings_code + content[insert_pos:]
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("✅ Agent Assistant integration complete")
        return True
    
    def create_integration_guide(self):
        """Create a guide for manual integration"""
        guide_path = self.project_root / "FORMATTER_INTEGRATION_MANUAL.md"
        
        guide_content = """# Manual Formatter Integration Guide

## For Tabs Not Auto-Integrated

### Step 1: Add Import
```python
from utils.universal_response_formatter import format_and_display, add_formatter_settings
```

### Step 2: Add Settings UI
Add this line after `st.title()` in your render function:
```python
add_formatter_settings(tab_name="Your Tab Name", location="sidebar")
```

### Step 3: Replace Response Display
Find where you display responses (usually `st.markdown(response)`):

**Before:**
```python
st.markdown(response)
```

**After:**
```python
format_and_display(
    raw_response=response,
    query=user_query,
    tab_name="Your Tab Name"
)
```

### Step 4: Add Sources (Optional)
```python
format_and_display(
    raw_response=response,
    query=user_query,
    tab_name="Your Tab Name",
    sources=[
        {'document': 'file.pdf', 'page': 15, 'relevance': 0.95}
    ]
)
```

### Step 5: Add Metadata (Optional)
```python
format_and_display(
    raw_response=response,
    query=user_query,
    tab_name="Your Tab Name",
    metadata={
        'confidence': 0.92,
        'response_time': 1250.5
    }
)
```

## Testing
1. Run your tab
2. Check that formatter settings appear in sidebar/expander
3. Toggle formatting on/off
4. Verify response displays correctly
5. Test with different queries

## Troubleshooting
- If settings don't appear: Check import statement
- If formatting doesn't work: Check `format_and_display` call
- If errors occur: Check console for error messages

See CROSS_TAB_FORMATTER_INTEGRATION.md for complete documentation.
"""
        
        with open(guide_path, 'w', encoding='utf-8') as f:
            f.write(guide_content)
        
        print(f"📝 Created manual integration guide: {guide_path}")
    
    def run_integration(self, tabs: List[str] = None):
        """Run integration for specified tabs"""
        if tabs is None:
            tabs = ['query', 'chat', 'agent']
        
        print("=" * 60)
        print("🚀 VaultMind Response Formatter Integration")
        print("=" * 60)
        print()
        
        # Backup first
        if not self.backup_tabs():
            return False
        
        print()
        
        # Integrate tabs
        results = {}
        
        if 'query' in tabs:
            results['query'] = self.integrate_query_assistant()
        
        if 'chat' in tabs:
            results['chat'] = self.integrate_chat_assistant()
        
        if 'agent' in tabs:
            results['agent'] = self.integrate_agent_assistant()
        
        # Create manual guide
        self.create_integration_guide()
        
        # Summary
        print()
        print("=" * 60)
        print("📊 Integration Summary")
        print("=" * 60)
        
        for tab, success in results.items():
            status = "✅ Success" if success else "❌ Failed"
            print(f"{tab.title()} Assistant: {status}")
        
        print()
        print("📚 Documentation:")
        print("  - CROSS_TAB_FORMATTER_INTEGRATION.md - Complete guide")
        print("  - RESPONSE_WRITER_GUIDE.md - Detailed documentation")
        print("  - RESPONSE_WRITER_QUICK_START.md - Quick start")
        print("  - FORMATTER_INTEGRATION_MANUAL.md - Manual integration")
        
        print()
        print("🧪 Next Steps:")
        print("  1. Test each integrated tab")
        print("  2. Verify formatter settings appear")
        print("  3. Try toggling formatting on/off")
        print("  4. Check response quality")
        print("  5. Manually integrate remaining tabs if needed")
        
        print()
        print("✅ Integration complete!")
        
        return all(results.values())


def main():
    """Main entry point"""
    import sys
    
    # Get project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    print(f"Project root: {project_root}")
    print()
    
    # Create integrator
    integrator = TabFormatterIntegrator(str(project_root))
    
    # Parse arguments
    tabs_to_integrate = ['query', 'chat', 'agent']
    
    if len(sys.argv) > 1:
        if sys.argv[1] == '--all':
            tabs_to_integrate = ['query', 'chat', 'agent']
        elif sys.argv[1] == '--query':
            tabs_to_integrate = ['query']
        elif sys.argv[1] == '--chat':
            tabs_to_integrate = ['chat']
        elif sys.argv[1] == '--agent':
            tabs_to_integrate = ['agent']
        elif sys.argv[1] == '--help':
            print("Usage: python integrate_formatter_all_tabs.py [OPTIONS]")
            print()
            print("Options:")
            print("  --all     Integrate all tabs (default)")
            print("  --query   Integrate Query Assistant only")
            print("  --chat    Integrate Chat Assistant only")
            print("  --agent   Integrate Agent Assistant only")
            print("  --help    Show this help message")
            return
    
    # Run integration
    success = integrator.run_integration(tabs_to_integrate)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
