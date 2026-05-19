"""
VaultMind Enterprise UI Components
Enhanced user interface for enterprise permission management and resource requests
"""

import streamlit as st
from typing import Dict, List, Optional
from datetime import datetime, timedelta

from .enterprise_permissions import enterprise_permissions, PermissionLevel, FeatureCategory
from .resource_request_manager import resource_request_manager
from .authentication import UserRole

class EnterpriseUI:
    """Enterprise UI components for permission management"""
    
    @staticmethod
    def render_user_dashboard(user_id: str, username: str, role: str):
        """Render user dashboard with permissions and request options"""
        st.markdown("## 🎯 My Access & Permissions")
        
        # Get user's current permissions
        custom_permissions = resource_request_manager.get_user_custom_permissions(user_id)
        user_permissions = enterprise_permissions.get_user_permissions(role, custom_permissions)
        
        # Display current access
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("### 🔑 Current Access")
            EnterpriseUI._display_user_permissions(user_permissions)
        
        with col2:
            st.markdown("### 📊 Quick Stats")
            active_permissions = sum(1 for level in user_permissions.values() if level != PermissionLevel.NONE)
            st.metric("Active Features", active_permissions)
            
            # Show pending requests
            user_requests = resource_request_manager.get_user_requests(user_id)
            pending_count = sum(1 for req in user_requests if req.status == 'pending')
            st.metric("Pending Requests", pending_count)
        
        st.markdown("---")
        
        # Request additional access
        if role != 'admin':  # Admins don't need to request access
            EnterpriseUI._render_request_access_section(user_id, username, role, user_permissions)
        
        # Show request history
        EnterpriseUI._render_request_history(user_id)
    
    @staticmethod
    def _display_user_permissions(permissions: Dict[str, PermissionLevel]):
        """Display user's current permissions organized by category"""
        # Group permissions by category
        categorized = {}
        for feature_id, level in permissions.items():
            if level != PermissionLevel.NONE and feature_id in enterprise_permissions.features:
                feature = enterprise_permissions.features[feature_id]
                category = feature.category.value
                if category not in categorized:
                    categorized[category] = []
                categorized[category].append((feature, level))
        
        # Display by category
        for category, features in categorized.items():
            with st.expander(f"📁 {category.replace('_', ' ').title()}", expanded=True):
                for feature, level in features:
                    level_icon = {
                        PermissionLevel.READ: "👁️",
                        PermissionLevel.WRITE: "✏️",
                        PermissionLevel.ADMIN: "👑"
                    }.get(level, "❓")
                    
                    col1, col2, col3 = st.columns([3, 1, 1])
                    with col1:
                        st.write(f"**{feature.name}**")
                        st.caption(feature.description)
                    with col2:
                        st.write(f"{level_icon} {level.value.title()}")
                    with col3:
                        if feature.cost_tier != "free":
                            # Streamlit's st.badge may be missing or have different signatures across versions
                            try:
                                st.badge(feature.cost_tier.title())
                            except Exception:
                                # Fallback for older versions without badge or differing signatures
                                st.caption(f"Tier: {feature.cost_tier.title()}")
    
    @staticmethod
    def _render_request_access_section(user_id: str, username: str, role: str, current_permissions: Dict[str, PermissionLevel]):
        """Render section for requesting additional access"""
        st.markdown("### 🚀 Request Additional Access")
        
        # Get requestable features
        requestable_features = enterprise_permissions.get_requestable_features_for_user(role, current_permissions)
        
        if not requestable_features:
            st.info("You currently have access to all features available for your role.")
            return
        
        with st.form("request_access_form"):
            # Feature selection
            feature_options = {f.id: f"{f.name} - {f.description}" for f in requestable_features}
            selected_feature_id = st.selectbox(
                "Select Feature",
                options=list(feature_options.keys()),
                format_func=lambda x: feature_options[x]
            )
            
            if selected_feature_id:
                selected_feature = enterprise_permissions.features[selected_feature_id]
                
                # Show feature details
                col1, col2 = st.columns(2)
                with col1:
                    st.info(f"**Category:** {selected_feature.category.value.replace('_', ' ').title()}")
                with col2:
                    if selected_feature.cost_tier != "free":
                        st.warning(f"**Tier:** {selected_feature.cost_tier.title()}")
                
                # Permission level selection
                current_level = current_permissions.get(selected_feature_id, PermissionLevel.NONE)
                available_levels = [
                    level for level in selected_feature.available_levels 
                    if level != PermissionLevel.NONE and (
                        current_level == PermissionLevel.NONE or 
                        enterprise_permissions._is_higher_level(level, current_level)
                    )
                ]
                
                if available_levels:
                    requested_level = st.selectbox(
                        "Requested Access Level",
                        options=available_levels,
                        format_func=lambda x: f"{x.value.title()} Access"
                    )
                    
                    # Justification
                    justification = st.text_area(
                        "Business Justification",
                        placeholder="Please explain why you need this access and how it will benefit your work...",
                        help="Provide a clear business case for why you need this access"
                    )
                    
                    # Show approval requirement
                    if selected_feature.requires_approval:
                        st.warning("⚠️ This feature requires admin approval")
                    
                    # Submit button
                    if st.form_submit_button("📤 Submit Request", type="primary"):
                        if justification.strip():
                            request_id = resource_request_manager.create_request(
                                user_id, username, selected_feature_id, requested_level, justification
                            )
                            st.success(f"✅ Request submitted successfully! Request ID: {request_id}")
                            st.rerun()
                        else:
                            st.error("Please provide a business justification for your request")
    
    @staticmethod
    def _render_request_history(user_id: str):
        """Render user's request history"""
        st.markdown("### 📋 My Request History")
        
        requests = resource_request_manager.get_user_requests(user_id)
        
        if not requests:
            st.info("No requests found")
            return
        
        for request in requests:
            feature = enterprise_permissions.features.get(request.feature_id)
            if not feature:
                continue
            
            status_colors = {
                'pending': 'warning',
                'approved': 'success',
                'rejected': 'error'
            }
            
            with st.expander(f"{feature.name} - {request.requested_level.value.title()} Access"):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.write(f"**Feature:** {feature.name}")
                    st.write(f"**Requested Level:** {request.requested_level.value.title()}")
                    st.write(f"**Justification:** {request.justification}")
                    
                    if request.admin_notes:
                        st.write(f"**Admin Notes:** {request.admin_notes}")
                
                with col2:
                    st.write(f"**Status:** {request.status.title()}")
                    st.write(f"**Requested:** {request.requested_at.strftime('%Y-%m-%d %H:%M')}")
                    
                    if request.reviewed_at:
                        st.write(f"**Reviewed:** {request.reviewed_at.strftime('%Y-%m-%d %H:%M')}")
                        st.write(f"**Reviewed By:** {request.reviewed_by}")
    
    @staticmethod
    def render_admin_permission_management():
        """Render admin interface for managing permissions and requests"""
        st.markdown("## 👑 Enterprise Permission Management")
        
        tab1, tab2, tab3, tab4 = st.tabs([
            "📋 Pending Requests",
            "👥 User Permissions", 
            "📊 Analytics",
            "⚙️ Feature Management"
        ])
        
        with tab1:
            EnterpriseUI._render_pending_requests()
        
        with tab2:
            EnterpriseUI._render_user_permission_management()
        
        with tab3:
            EnterpriseUI._render_permission_analytics()
        
        with tab4:
            EnterpriseUI._render_feature_management()
    
    @staticmethod
    def _render_pending_requests():
        """Render pending resource requests for admin review"""
        st.markdown("### 📋 Pending Access Requests")
        
        pending_requests = resource_request_manager.get_pending_requests()
        
        if not pending_requests:
            st.info("No pending requests")
            return
        
        for request in pending_requests:
            feature = enterprise_permissions.features.get(request.feature_id)
            if not feature:
                continue
            
            with st.expander(f"👤 {request.username} - {feature.name}", expanded=False):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.write(f"**User:** {request.username}")
                    st.write(f"**Feature:** {feature.name}")
                    st.write(f"**Category:** {feature.category.value.replace('_', ' ').title()}")
                    st.write(f"**Requested Level:** {request.requested_level.value.title()}")
                    st.write(f"**Cost Tier:** {feature.cost_tier.title()}")
                    st.write(f"**Requested:** {request.requested_at.strftime('%Y-%m-%d %H:%M')}")
                    
                    st.markdown("**Business Justification:**")
                    st.write(request.justification)
                
                with col2:
                    st.markdown("**Admin Actions**")
                    
                    admin_notes = st.text_area(
                        "Admin Notes",
                        key=f"notes_{request.id}",
                        placeholder="Optional notes for the user..."
                    )
                    
                    # Approval with optional expiry
                    col_approve, col_reject = st.columns(2)
                    
                    with col_approve:
                        if st.button("✅ Approve", key=f"approve_{request.id}", type="primary"):
                            admin_user = st.session_state.user
                            admin_username = admin_user.get('username') if isinstance(admin_user, dict) else admin_user.username
                            
                            if resource_request_manager.approve_request(request.id, admin_username, admin_notes):
                                st.success("Request approved!")
                                st.rerun()
                            else:
                                st.error("Failed to approve request")
                    
                    with col_reject:
                        if st.button("❌ Reject", key=f"reject_{request.id}"):
                            admin_user = st.session_state.user
                            admin_username = admin_user.get('username') if isinstance(admin_user, dict) else admin_user.username
                            
                            if resource_request_manager.reject_request(request.id, admin_username, admin_notes):
                                st.success("Request rejected!")
                                st.rerun()
                            else:
                                st.error("Failed to reject request")
    
    @staticmethod
    def _render_user_permission_management():
        """Render interface for managing individual user permissions"""
        st.markdown("### 👥 User Permission Management")
        
        # This would integrate with your existing user management system
        st.info("This section would show all users with options to view/modify their custom permissions")
        
        # Placeholder for user selection and permission editing
        st.markdown("**Features to implement:**")
        st.write("- User search and selection")
        st.write("- View current permissions")
        st.write("- Grant/revoke custom permissions")
        st.write("- Set permission expiry dates")
        st.write("- Bulk permission operations")
    
    @staticmethod
    def _render_permission_analytics():
        """Render analytics dashboard for permissions"""
        st.markdown("### 📊 Permission Analytics")
        
        stats = resource_request_manager.get_request_statistics()
        
        # Request statistics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            total_requests = sum(stats.get('by_status', {}).values())
            st.metric("Total Requests", total_requests)
        
        with col2:
            pending_requests = stats.get('by_status', {}).get('pending', 0)
            st.metric("Pending Requests", pending_requests)
        
        with col3:
            recent_requests = stats.get('requests_last_7_days', 0)
            st.metric("Requests (7 days)", recent_requests)
        
        # Most requested features
        if stats.get('most_requested'):
            st.markdown("#### 🔥 Most Requested Features")
            for feature_id, count in stats['most_requested']:
                feature = enterprise_permissions.features.get(feature_id)
                if feature:
                    st.write(f"**{feature.name}:** {count} requests")
    
    @staticmethod
    def _render_feature_management():
        """Render interface for managing features and their settings"""
        st.markdown("### ⚙️ Feature Management")
        
        # Feature overview
        st.markdown("#### 📋 Available Features")
        
        # Group features by category
        by_category = {}
        for feature in enterprise_permissions.features.values():
            category = feature.category.value
            if category not in by_category:
                by_category[category] = []
            by_category[category].append(feature)
        
        for category, features in by_category.items():
            with st.expander(f"📁 {category.replace('_', ' ').title()}", expanded=False):
                for feature in features:
                    col1, col2, col3 = st.columns([2, 1, 1])
                    
                    with col1:
                        st.write(f"**{feature.name}**")
                        st.caption(feature.description)
                    
                    with col2:
                        st.write(f"Tier: {feature.cost_tier.title()}")
                        if feature.requires_approval:
                            st.write("⚠️ Requires Approval")
                    
                    with col3:
                        levels_str = ", ".join([level.value.title() for level in feature.available_levels])
                        st.write(f"Levels: {levels_str}")

                    # Management controls per feature
                    with st.expander(f"Manage: {feature.name}", expanded=False):
                        pol_col, role_col = st.columns([1, 1])
                        with pol_col:
                            st.markdown("**Policy**")
                            req_key = f"req_{feature.id}"
                            def_lvl_key = f"deflvl_{feature.id}"
                            tier_key = f"tier_{feature.id}"
                            requires_approval = st.checkbox("Requires Approval", value=feature.requires_approval, key=req_key)
                            default_level_val = feature.default_level.value if hasattr(feature.default_level, 'value') else str(feature.default_level)
                            level_options = [lvl.value for lvl in feature.available_levels]
                            if default_level_val not in level_options:
                                level_options = [default_level_val] + [lv for lv in level_options if lv != default_level_val]
                            selected_default_level = st.selectbox(
                                "Default Level",
                                options=level_options,
                                index=0,
                                key=def_lvl_key
                            )
                            selected_tier = st.selectbox(
                                "Cost Tier",
                                options=["free", "standard", "premium", "enterprise"],
                                index=["free", "standard", "premium", "enterprise"].index(feature.cost_tier) if feature.cost_tier in ["free","standard","premium","enterprise"] else 0,
                                key=tier_key
                            )
                            if st.button("Save Policy", key=f"save_pol_{feature.id}"):
                                ok = enterprise_permissions.update_feature_policy(
                                    feature_id=feature.id,
                                    requires_approval=requires_approval,
                                    default_level=selected_default_level,
                                    cost_tier=selected_tier,
                                )
                                if ok:
                                    st.success("Policy saved.")
                                else:
                                    st.error("Failed to save policy.")
                        with role_col:
                            st.markdown("**Role Template Overrides**")
                            roles = ["viewer", "user", "power_user", "admin"]
                            current_templates = enterprise_permissions.role_templates
                            # Build selectors
                            selectors = {}
                            for r in roles:
                                cur_lvl = current_templates.get(r, {}).get(feature.id, None)
                                cur_val = cur_lvl.value if cur_lvl else "none"
                                role_key = f"role_{feature.id}_{r}"
                                selectors[r] = st.selectbox(
                                    f"{r.title()}",
                                    options=[lvl.value for lvl in feature.available_levels],
                                    index=max(0, [lvl.value for lvl in feature.available_levels].index(cur_val) if cur_val in [lvl.value for lvl in feature.available_levels] else 0),
                                    key=role_key
                                )
                            if st.button("Save Role Levels", key=f"save_roles_{feature.id}"):
                                all_ok = True
                                for r, val in selectors.items():
                                    ok = enterprise_permissions.update_role_template(r, feature.id, val)
                                    all_ok = all_ok and ok
                                if all_ok:
                                    st.success("Role template overrides saved.")
                                else:
                                    st.error("Failed to save one or more role overrides.")

# Global instance
enterprise_ui = EnterpriseUI()
