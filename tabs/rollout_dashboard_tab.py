"""
Department Rollout Dashboard Tab

Track and manage department namespace rollouts across the organization.
"""

import streamlit as st
import logging
import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime
import json
from pathlib import Path

logger = logging.getLogger(__name__)

# Import rollout components
try:
    from rollout.department_rollout import (
        DepartmentRollout, 
        DepartmentRolloutResult,
        RolloutStatus,
        DEPARTMENT_SAMPLE_DOCS,
        DEPARTMENT_TEST_QUERIES
    )
    from utils.department_manager import get_department_manager
    ROLLOUT_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Rollout components not available: {e}")
    ROLLOUT_AVAILABLE = False


def render_rollout_dashboard(user, permissions, auth_middleware, **kwargs):
    """
    Department Rollout Dashboard
    """
    
    # Extract user info
    if isinstance(user, dict):
        username = user.get('username', 'Unknown')
        user_role = user.get('role', 'viewer')
    else:
        username = getattr(user, 'username', 'Unknown')
        user_role = getattr(user, 'role', 'viewer')
        if hasattr(user_role, 'value'):
            user_role = user_role.value
    
    # Admin check
    if user_role != 'admin':
        st.error("🔒 This section requires administrator access.")
        return
    
    # Log access
    if auth_middleware:
        auth_middleware.log_user_action("ACCESS_ROLLOUT_DASHBOARD")
    
    # Header
    st.header("🚀 Department Rollout Dashboard")
    st.caption(f"Manage department namespace rollouts | Admin: {username}")
    
    if not ROLLOUT_AVAILABLE:
        st.error("❌ Rollout components not available")
        return
    
    # Initialize
    dept_manager = get_department_manager()
    departments = dept_manager.list_departments()
    
    # Tabs
    tab1, tab2, tab3 = st.tabs([
        "📊 Overview",
        "🚀 Execute Rollout",
        "📋 Checklist"
    ])
    
    # ==================== OVERVIEW ====================
    with tab1:
        render_overview_section(departments)
    
    # ==================== EXECUTE ====================
    with tab2:
        render_execute_section(departments)
    
    # ==================== CHECKLIST ====================
    with tab3:
        render_checklist_section(departments)


def render_overview_section(departments):
    """Render rollout overview"""
    
    st.subheader("📊 Rollout Status Overview")
    
    # Load status
    status_file = Path("rollout/rollout_status.json")
    status_data = {}
    if status_file.exists():
        with open(status_file) as f:
            status_data = json.load(f)
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    total = len(departments)
    completed = sum(1 for d in status_data.values() if d.get("status") == "completed")
    failed = sum(1 for d in status_data.values() if d.get("status") == "failed")
    pending = total - completed - failed
    
    col1.metric("Total Departments", total)
    col2.metric("✅ Completed", completed)
    col3.metric("⏳ Pending", pending)
    col4.metric("❌ Failed", failed)
    
    # Progress bar
    if total > 0:
        progress = completed / total
        st.progress(progress, text=f"Rollout Progress: {completed}/{total} departments ({progress:.0%})")
    
    # Department table
    st.markdown("---")
    st.markdown("### Department Status")
    
    # Rollout schedule
    schedule = [
        ("hr", "Weeks 10-14", "✅ Pilot Complete"),
        ("finance", "Weeks 13-14", "Dedicated read nodes"),
        ("operations", "Weeks 14-15", "SOP-focused chunking"),
        ("it", "Weeks 15-16", "Technical doc parsing"),
        ("legal", "Weeks 16-17", "Dedicated read nodes, regulatory focus"),
        ("marketing", "Weeks 17-18", "Brand asset handling"),
        ("external", "Weeks 18-19", "Firecrawl configuration"),
        ("clinical", "Weeks 19-20", "⚠️ HIPAA BAA Required"),
    ]
    
    for dept_id, timeline, notes in schedule:
        dept = next((d for d in departments if d.dept_id == dept_id), None)
        if not dept:
            continue
        
        dept_status = status_data.get(dept_id, {})
        status = dept_status.get("status", "pending")
        
        # Status icon
        status_icon = {
            "completed": "✅",
            "in_progress": "🔄",
            "failed": "❌",
            "pending": "⏳",
        }.get(status, "⏳")
        
        col1, col2, col3, col4, col5 = st.columns([2, 1, 2, 2, 1])
        
        col1.write(f"**{dept.display_name}**")
        col2.write(timeline)
        col3.write(notes)
        col4.write(f"{status_icon} {status.title()}")
        
        # Actions
        if status == "completed":
            if col5.button("📄", key=f"view_{dept_id}", help="View report"):
                st.session_state[f"view_report_{dept_id}"] = True
        elif status == "failed":
            if col5.button("🔄", key=f"retry_{dept_id}", help="Retry"):
                st.session_state[f"retry_{dept_id}"] = True
    
    # Detailed view
    for dept_id, _, _ in schedule:
        if st.session_state.get(f"view_report_{dept_id}"):
            with st.expander(f"📄 {dept_id.title()} Rollout Report", expanded=True):
                report = status_data.get(dept_id, {})
                st.json(report)
                if st.button("Close", key=f"close_{dept_id}"):
                    st.session_state[f"view_report_{dept_id}"] = False
                    st.rerun()


def render_execute_section(departments):
    """Render rollout execution controls"""
    
    st.subheader("🚀 Execute Department Rollout")
    
    # Department selector
    dept_options = [d.dept_id for d in departments]
    
    col1, col2 = st.columns(2)
    
    with col1:
        selected_dept = st.selectbox(
            "Select Department",
            options=dept_options,
            format_func=lambda x: next((d.display_name for d in departments if d.dept_id == x), x)
        )
    
    with col2:
        # Show department info
        dept = next((d for d in departments if d.dept_id == selected_dept), None)
        if dept:
            st.info(f"""
            **{dept.display_name}**
            - Sensitivity: {dept.sensitivity.value.title()}
            - Namespace: `vaultmind-huron-{dept.namespace}-general`
            """)
    
    # Pre-rollout checks
    st.markdown("---")
    st.markdown("### Pre-Rollout Checklist")
    
    checks = {
        "dept_exists": ("Department configured", True),
        "sample_docs": ("Sample documents available", selected_dept in DEPARTMENT_SAMPLE_DOCS),
        "test_queries": ("Test queries defined", selected_dept in DEPARTMENT_TEST_QUERIES),
    }
    
    # Special checks
    if selected_dept == "clinical":
        checks["hipaa_baa"] = ("HIPAA BAA in place", False)
        st.warning("⚠️ Clinical department requires HIPAA BAA before rollout")
    
    all_passed = True
    for check_id, (label, passed) in checks.items():
        icon = "✅" if passed else "❌"
        st.write(f"{icon} {label}")
        if not passed:
            all_passed = False
    
    # Execute button
    st.markdown("---")
    
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        run_single = st.button(
            f"🚀 Roll Out {selected_dept.title()}",
            type="primary",
            disabled=not all_passed
        )
    
    with col2:
        run_all = st.button(
            "🚀 Roll Out All Pending",
            disabled=False
        )
    
    # Execute rollout
    if run_single:
        with st.spinner(f"Rolling out {selected_dept}..."):
            try:
                rollout = DepartmentRollout()
                result = asyncio.run(rollout.rollout_department(selected_dept))
                
                if result.status == RolloutStatus.COMPLETED:
                    st.success(f"✅ {selected_dept.title()} rollout completed!")
                    st.metric("Documents Ingested", result.documents_ingested)
                    st.metric("Test Queries Passed", f"{result.test_queries_passed}/{result.test_queries_total}")
                else:
                    st.error(f"❌ Rollout failed: {', '.join(result.errors)}")
                
                st.rerun()
                
            except Exception as e:
                st.error(f"Rollout error: {e}")
    
    elif run_all:
        with st.spinner("Rolling out all pending departments..."):
            try:
                rollout = DepartmentRollout()
                # Exclude clinical (HIPAA)
                results = asyncio.run(rollout.rollout_all(exclude=["clinical"]))
                
                completed = sum(1 for r in results.values() if r.status == RolloutStatus.COMPLETED)
                failed = sum(1 for r in results.values() if r.status == RolloutStatus.FAILED)
                
                st.success(f"Rollout complete: {completed} succeeded, {failed} failed")
                st.rerun()
                
            except Exception as e:
                st.error(f"Rollout error: {e}")


def render_checklist_section(departments):
    """Render per-department checklist"""
    
    st.subheader("📋 Department Rollout Checklist")
    
    # Department selector
    dept_options = [d.dept_id for d in departments]
    selected_dept = st.selectbox(
        "Select Department",
        options=dept_options,
        format_func=lambda x: next((d.display_name for d in departments if d.dept_id == x), x),
        key="checklist_dept"
    )
    
    # Checklist items
    st.markdown("---")
    
    checklist_key = f"checklist_{selected_dept}"
    if checklist_key not in st.session_state:
        st.session_state[checklist_key] = {
            "docs_ingested": False,
            "attention_profile": False,
            "sso_mapping": False,
            "acceptance_test": False,
            "isolation_test": False,
            "admin_trained": False,
        }
    
    checklist = st.session_state[checklist_key]
    
    # Checklist items
    items = [
        ("docs_ingested", "📄 Ingest all department documents"),
        ("attention_profile", "⚙️ Configure attention profile"),
        ("sso_mapping", "🔐 Wire SSO group mapping"),
        ("acceptance_test", "✅ Run 50-query acceptance test"),
        ("isolation_test", "🔒 Test cross-dept isolation (3 other depts)"),
        ("admin_trained", "👤 Train department admin"),
    ]
    
    completed = 0
    for item_id, label in items:
        col1, col2 = st.columns([4, 1])
        with col1:
            checked = st.checkbox(label, value=checklist[item_id], key=f"{checklist_key}_{item_id}")
            checklist[item_id] = checked
            if checked:
                completed += 1
    
    # Progress
    st.markdown("---")
    progress = completed / len(items)
    st.progress(progress, text=f"Checklist Progress: {completed}/{len(items)} ({progress:.0%})")
    
    # Save checklist
    st.session_state[checklist_key] = checklist
    
    # Sign-off
    if completed == len(items):
        st.success("✅ All checklist items complete!")
        if st.button("📝 Sign Off Department", type="primary"):
            st.balloons()
            st.success(f"🎉 {selected_dept.title()} signed off and ready for production!")
    
    # Sample documents preview
    st.markdown("---")
    st.markdown("### 📁 Sample Documents")
    
    sample_docs = DEPARTMENT_SAMPLE_DOCS.get(selected_dept, [])
    if sample_docs:
        for doc in sample_docs:
            with st.expander(f"📄 {doc['title']}"):
                st.markdown(doc["content"][:500] + "..." if len(doc["content"]) > 500 else doc["content"])
    else:
        st.info("No sample documents defined for this department")
    
    # Test queries
    st.markdown("### 🧪 Acceptance Test Queries")
    
    test_queries = DEPARTMENT_TEST_QUERIES.get(selected_dept, [])
    if test_queries:
        for i, test in enumerate(test_queries, 1):
            st.write(f"**{i}.** {test['query']}")
            st.caption(f"Expected: {', '.join(test['expected'])}")
    else:
        st.info("No test queries defined for this department")


# Alias
render_department_rollout = render_rollout_dashboard
