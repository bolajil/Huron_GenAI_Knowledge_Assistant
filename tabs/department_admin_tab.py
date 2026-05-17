"""
Department Administration Tab

Admin interface for managing departments:
- Create new departments
- Configure department settings
- Manage attention profiles
- Configure web crawlers
- View namespace usage

Only accessible to admin users.
"""

import streamlit as st
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

# Import department manager
try:
    from utils.department_manager import (
        DepartmentManager, 
        Department,
        get_department_manager,
        SensitivityLevel,
        AttentionProfile,
        WebCrawlerConfig
    )
    DEPT_MANAGER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Department manager not available: {e}")
    DEPT_MANAGER_AVAILABLE = False


def render_department_admin(user, permissions, auth_middleware, **kwargs):
    """
    Department Administration Tab - Admin Only
    """
    
    # Check admin access
    if isinstance(user, dict):
        username = user.get('username', 'Unknown')
        user_role = user.get('role', 'viewer')
    else:
        username = getattr(user, 'username', 'Unknown')
        user_role = getattr(user, 'role', 'viewer')
        if hasattr(user_role, 'value'):
            user_role = user_role.value
    
    if user_role != 'admin':
        st.error("🔒 This section requires administrator access.")
        st.info("Contact your system administrator for access.")
        return
    
    # Log access
    if auth_middleware:
        auth_middleware.log_user_action("ACCESS_DEPARTMENT_ADMIN")
    
    # Header
    st.header("🏢 Department Administration")
    st.caption(f"Manage organization departments and namespaces | Admin: {username}")
    
    if not DEPT_MANAGER_AVAILABLE:
        st.error("❌ Department manager not available")
        return
    
    # Get manager
    manager = get_department_manager()
    
    # Create tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "📋 Departments", 
        "➕ Create New", 
        "⚙️ Settings",
        "📊 Usage"
    ])
    
    # ==================== DEPARTMENTS LIST ====================
    with tab1:
        render_departments_list(manager)
    
    # ==================== CREATE NEW ====================
    with tab2:
        render_create_department(manager, username)
    
    # ==================== SETTINGS ====================
    with tab3:
        render_department_settings(manager)
    
    # ==================== USAGE ====================
    with tab4:
        render_namespace_usage(manager)


def render_departments_list(manager: DepartmentManager):
    """Render list of all departments"""
    
    st.subheader("📋 Active Departments")
    
    # Controls
    col1, col2 = st.columns([3, 1])
    with col1:
        show_inactive = st.checkbox("Show inactive departments", value=False)
    with col2:
        if st.button("🔄 Refresh"):
            st.rerun()
    
    # Get departments
    departments = manager.list_departments(include_inactive=show_inactive)
    
    if not departments:
        st.info("No departments configured. Create one in the 'Create New' tab.")
        return
    
    # Display as cards
    for dept in departments:
        with st.expander(
            f"{'🟢' if dept.active else '🔴'} **{dept.display_name}** (`{dept.dept_id}`)",
            expanded=False
        ):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown("**Namespace:**")
                st.code(f"vaultmind-huron-{dept.namespace}-general")
                
                st.markdown("**Sensitivity:**")
                sensitivity_colors = {
                    "public": "🟢",
                    "internal": "🔵",
                    "confidential": "🟡",
                    "restricted": "🟠",
                    "hipaa_phi": "🔴",
                }
                st.write(f"{sensitivity_colors.get(dept.sensitivity.value, '⚪')} {dept.sensitivity.value.title()}")
            
            with col2:
                st.markdown("**Document Types:**")
                st.write(", ".join(dept.document_types))
                
                st.markdown("**Dedicated Nodes:**")
                st.write("✅ Yes" if dept.dedicated_nodes else "❌ No")
            
            with col3:
                st.markdown("**Web Crawler:**")
                if dept.web_crawler.enabled:
                    st.write(f"✅ Enabled ({len(dept.web_crawler.seed_urls)} URLs)")
                else:
                    st.write("❌ Disabled")
                
                st.markdown("**Created:**")
                st.write(dept.created_at[:10] if dept.created_at else "Unknown")
            
            # Description
            if dept.description:
                st.markdown("**Description:**")
                st.write(dept.description)
            
            # Actions
            st.markdown("---")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button(f"✏️ Edit", key=f"edit_{dept.dept_id}"):
                    st.session_state[f"editing_{dept.dept_id}"] = True
                    st.rerun()
            
            with col2:
                if dept.active:
                    if st.button(f"🔴 Deactivate", key=f"deactivate_{dept.dept_id}"):
                        manager.update_department(dept.dept_id, active=False)
                        st.success(f"Deactivated {dept.dept_id}")
                        st.rerun()
                else:
                    if st.button(f"🟢 Activate", key=f"activate_{dept.dept_id}"):
                        manager.update_department(dept.dept_id, active=True)
                        st.success(f"Activated {dept.dept_id}")
                        st.rerun()
            
            with col3:
                if st.button(f"🗑️ Delete", key=f"delete_{dept.dept_id}"):
                    if st.session_state.get(f"confirm_delete_{dept.dept_id}"):
                        manager.delete_department(dept.dept_id, soft_delete=False)
                        st.success(f"Deleted {dept.dept_id}")
                        st.rerun()
                    else:
                        st.session_state[f"confirm_delete_{dept.dept_id}"] = True
                        st.warning("Click again to confirm deletion")


def render_create_department(manager: DepartmentManager, username: str):
    """Render department creation form"""
    
    st.subheader("➕ Create New Department")
    
    with st.form("create_department_form"):
        # Basic info
        col1, col2 = st.columns(2)
        
        with col1:
            dept_id = st.text_input(
                "Department ID*",
                placeholder="e.g., compliance",
                help="Unique identifier (lowercase, alphanumeric, underscores allowed)"
            )
            
            display_name = st.text_input(
                "Display Name*",
                placeholder="e.g., Compliance & Risk"
            )
        
        with col2:
            sensitivity = st.selectbox(
                "Sensitivity Level*",
                options=["internal", "public", "confidential", "restricted", "hipaa_phi"],
                index=0,
                help="Determines access controls and handling requirements"
            )
            
            dedicated_nodes = st.checkbox(
                "Dedicated Pinecone Nodes",
                value=False,
                help="Enable for high-traffic departments (Finance, Legal, Clinical)"
            )
        
        description = st.text_area(
            "Description",
            placeholder="Brief description of department purpose and content"
        )
        
        # Document types
        st.markdown("**Document Types**")
        doc_types = st.multiselect(
            "Select supported document types",
            options=["general", "legal", "financial", "technical", "hr", "clinical", "external"],
            default=["general"]
        )
        
        # Web crawler config
        st.markdown("**Web Crawler Configuration** (optional)")
        col1, col2 = st.columns(2)
        
        with col1:
            enable_crawler = st.checkbox("Enable web crawler", value=False)
        
        with col2:
            crawler_schedule = st.selectbox(
                "Crawl schedule",
                options=["weekly", "daily", "monthly"],
                index=0,
                disabled=not enable_crawler
            )
        
        seed_urls = st.text_area(
            "Seed URLs (one per line)",
            placeholder="https://example.com/docs\nhttps://example.com/wiki",
            disabled=not enable_crawler
        )
        
        # Submit
        submitted = st.form_submit_button("🚀 Create Department", type="primary")
        
        if submitted:
            # Validation
            if not dept_id or not display_name:
                st.error("Department ID and Display Name are required")
            elif not dept_id.replace("_", "").replace("-", "").isalnum():
                st.error("Department ID must be alphanumeric (underscores and hyphens allowed)")
            elif dept_id in manager.get_department_ids(include_inactive=True):
                st.error(f"Department '{dept_id}' already exists")
            else:
                try:
                    # Parse seed URLs
                    urls = []
                    if enable_crawler and seed_urls:
                        urls = [u.strip() for u in seed_urls.split("\n") if u.strip()]
                    
                    # Create department
                    dept = manager.create_department(
                        dept_id=dept_id.lower().strip(),
                        display_name=display_name,
                        sensitivity=sensitivity,
                        description=description,
                        document_types=doc_types,
                        dedicated_nodes=dedicated_nodes,
                        seed_urls=urls if enable_crawler else None,
                        created_by=username,
                    )
                    
                    st.success(f"✅ Created department: **{dept.display_name}**")
                    st.info(f"Namespace: `vaultmind-huron-{dept.namespace}-general`")
                    
                    # Show next steps
                    st.markdown("### Next Steps")
                    st.markdown(f"""
                    1. **Configure attention profile** in Settings tab
                    2. **Upload documents** to the {display_name} namespace
                    3. **Test queries** to verify retrieval
                    """)
                    
                except Exception as e:
                    st.error(f"Failed to create department: {e}")


def render_department_settings(manager: DepartmentManager):
    """Render department settings editor"""
    
    st.subheader("⚙️ Department Settings")
    
    departments = manager.list_departments(include_inactive=True)
    
    if not departments:
        st.info("No departments to configure")
        return
    
    # Department selector
    dept_options = {d.display_name: d.dept_id for d in departments}
    selected_name = st.selectbox(
        "Select Department",
        options=list(dept_options.keys())
    )
    
    if not selected_name:
        return
    
    dept_id = dept_options[selected_name]
    dept = manager.get_department(dept_id)
    
    if not dept:
        st.error("Department not found")
        return
    
    # Settings tabs
    settings_tab1, settings_tab2, settings_tab3 = st.tabs([
        "🎯 Attention Profile",
        "🌐 Web Crawler",
        "📝 General"
    ])
    
    # Attention Profile
    with settings_tab1:
        st.markdown("**RAG Retrieval Settings**")
        st.caption("Configure how this department's content is prioritized in searches")
        
        with st.form("attention_profile_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                retrieval_weight = st.slider(
                    "Retrieval Weight",
                    min_value=0.1,
                    max_value=2.0,
                    value=dept.attention_profile.retrieval_weight,
                    step=0.1,
                    help="Higher = prioritize this dept's content"
                )
                
                rerank_boost = st.slider(
                    "Rerank Boost",
                    min_value=0.5,
                    max_value=2.0,
                    value=dept.attention_profile.rerank_boost,
                    step=0.1,
                    help="Multiplier applied during cross-encoder reranking"
                )
            
            with col2:
                context_window = st.number_input(
                    "Context Window (tokens)",
                    min_value=1024,
                    max_value=16384,
                    value=dept.attention_profile.context_window,
                    step=512
                )
                
                max_chunks = st.number_input(
                    "Max Chunks",
                    min_value=3,
                    max_value=20,
                    value=dept.attention_profile.max_chunks
                )
            
            prefer_recent = st.checkbox(
                "Prefer recent documents",
                value=dept.attention_profile.prefer_recent
            )
            
            cross_dept = st.checkbox(
                "Allow cross-department queries",
                value=dept.attention_profile.cross_dept_allowed,
                help="Allow users to search other departments (based on permissions)"
            )
            
            if st.form_submit_button("💾 Save Attention Profile"):
                dept.attention_profile.retrieval_weight = retrieval_weight
                dept.attention_profile.rerank_boost = rerank_boost
                dept.attention_profile.context_window = context_window
                dept.attention_profile.max_chunks = max_chunks
                dept.attention_profile.prefer_recent = prefer_recent
                dept.attention_profile.cross_dept_allowed = cross_dept
                
                manager._save_registry()
                st.success("Attention profile saved!")
    
    # Web Crawler
    with settings_tab2:
        st.markdown("**Web Crawler Configuration**")
        
        with st.form("crawler_config_form"):
            enabled = st.checkbox(
                "Enable crawler",
                value=dept.web_crawler.enabled
            )
            
            col1, col2 = st.columns(2)
            with col1:
                max_pages = st.number_input(
                    "Max pages per crawl",
                    min_value=10,
                    max_value=1000,
                    value=dept.web_crawler.max_pages
                )
                
                max_depth = st.number_input(
                    "Max crawl depth",
                    min_value=1,
                    max_value=5,
                    value=dept.web_crawler.max_depth
                )
            
            with col2:
                schedule = st.selectbox(
                    "Schedule",
                    options=["daily", "weekly", "monthly"],
                    index=["daily", "weekly", "monthly"].index(dept.web_crawler.schedule)
                )
                
                ttl_days = st.number_input(
                    "Content TTL (days)",
                    min_value=30,
                    max_value=365,
                    value=dept.web_crawler.ttl_days
                )
            
            seed_urls = st.text_area(
                "Seed URLs (one per line)",
                value="\n".join(dept.web_crawler.seed_urls)
            )
            
            if st.form_submit_button("💾 Save Crawler Config"):
                dept.web_crawler.enabled = enabled
                dept.web_crawler.max_pages = max_pages
                dept.web_crawler.max_depth = max_depth
                dept.web_crawler.schedule = schedule
                dept.web_crawler.ttl_days = ttl_days
                dept.web_crawler.seed_urls = [
                    u.strip() for u in seed_urls.split("\n") if u.strip()
                ]
                
                manager._save_registry()
                st.success("Crawler config saved!")
    
    # General
    with settings_tab3:
        st.markdown("**General Settings**")
        
        with st.form("general_settings_form"):
            new_display_name = st.text_input(
                "Display Name",
                value=dept.display_name
            )
            
            new_description = st.text_area(
                "Description",
                value=dept.description
            )
            
            new_sensitivity = st.selectbox(
                "Sensitivity Level",
                options=["public", "internal", "confidential", "restricted", "hipaa_phi"],
                index=["public", "internal", "confidential", "restricted", "hipaa_phi"].index(dept.sensitivity.value)
            )
            
            new_doc_types = st.multiselect(
                "Document Types",
                options=["general", "legal", "financial", "technical", "hr", "clinical", "external"],
                default=dept.document_types
            )
            
            if st.form_submit_button("💾 Save General Settings"):
                manager.update_department(
                    dept_id,
                    display_name=new_display_name,
                    description=new_description,
                    sensitivity=new_sensitivity,
                    document_types=new_doc_types
                )
                st.success("Settings saved!")


def render_namespace_usage(manager: DepartmentManager):
    """Render namespace usage statistics"""
    
    st.subheader("📊 Namespace Usage")
    
    departments = manager.list_departments()
    
    if not departments:
        st.info("No departments configured")
        return
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    col1.metric("Total Departments", len(departments))
    col2.metric("Active", sum(1 for d in departments if d.active))
    col3.metric("With Crawler", sum(1 for d in departments if d.web_crawler.enabled))
    col4.metric("HIPAA/Restricted", sum(1 for d in departments if d.sensitivity.value in ["hipaa_phi", "restricted"]))
    
    # Namespace table
    st.markdown("### Namespace Details")
    
    data = []
    for dept in departments:
        namespace = f"vaultmind-huron-{dept.namespace}-general"
        data.append({
            "Department": dept.display_name,
            "Namespace": namespace,
            "Sensitivity": dept.sensitivity.value.title(),
            "Dedicated": "✅" if dept.dedicated_nodes else "❌",
            "Active": "🟢" if dept.active else "🔴",
        })
    
    st.dataframe(data, use_container_width=True)
    
    # Export button
    if st.button("📥 Export Configuration"):
        config = manager.export_config()
        st.json(config)


# Alias for compatibility
render_admin_departments = render_department_admin
