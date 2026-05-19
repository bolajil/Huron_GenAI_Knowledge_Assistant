"""
VaultMind GenAI Knowledge Assistant - Authentication UI Components
Streamlit-based authentication interface with modern design
"""

import streamlit as st
from typing import Optional
from .authentication import auth_manager, User, UserRole
import time

class AuthUI:
    """Authentication UI components for Streamlit"""
    
    @staticmethod
    def init_session_state():
        """Initialize authentication session state"""
        if 'authenticated' not in st.session_state:
            st.session_state.authenticated = False
        if 'user' not in st.session_state:
            st.session_state.user = None
        if 'auth_token' not in st.session_state:
            st.session_state.auth_token = None
    
    @staticmethod
    def login_form() -> bool:
        """Display login form and handle authentication"""
        st.markdown("""
        <div style="
            max-width: 400px;
            margin: 50px auto;
            padding: 30px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 15px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.2);
        ">
            <h2 style="color: white; text-align: center; margin-bottom: 30px;">
                🔐 VaultMind Login
            </h2>
        </div>
        """, unsafe_allow_html=True)
        
        with st.form("login_form", clear_on_submit=False):
            st.markdown("### 🚀 Access Your Knowledge Assistant")
            
            username = st.text_input(
                "👤 Username",
                placeholder="Enter your username",
                help="Use 'admin' for initial setup"
            )
            
            password = st.text_input(
                "🔑 Password",
                type="password",
                placeholder="Enter your password",
                help="Default admin password: VaultMind2025!"
            )
            
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                login_button = st.form_submit_button(
                    "🔓 Login",
                    use_container_width=True,
                    type="primary"
                )
            
            if login_button:
                if username and password:
                    with st.spinner("🔍 Authenticating..."):
                        time.sleep(1)  # UX improvement
                        user = auth_manager.authenticate_user(username, password)
                        
                        if user:
                            # Generate token and set session
                            token = auth_manager.generate_token(user)
                            st.session_state.authenticated = True
                            st.session_state.user = user
                            st.session_state.auth_token = token
                            
                            st.success(f"✅ Welcome back, {user.username}!")
                            st.balloons()
                            time.sleep(1)
                            st.rerun()
                            return True
                        else:
                            st.error("❌ Invalid credentials or account locked")
                            return False
                else:
                    st.warning("⚠️ Please enter both username and password")
                    return False
        
        # Show default credentials info
        with st.expander("ℹ️ Default Credentials"):
            st.info("""
            **Default Admin Account:**
            - Username: `admin`
            - Password: `VaultMind2025!`
            
            **⚠️ Important**: Change default password in production!
            """)
        
        return False
    
    @staticmethod
    def user_registration_form():
        """Display user registration form (admin only)"""
        if not AuthUI.is_admin():
            st.error("❌ Admin access required for user registration")
            return
        
        st.markdown("### 👥 Create New User Account")
        
        with st.form("registration_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                new_username = st.text_input("👤 Username", placeholder="Enter username")
                new_email = st.text_input("📧 Email", placeholder="user@company.com")
            
            with col2:
                new_password = st.text_input("🔑 Password", type="password", placeholder="Secure password")
                new_role = st.selectbox(
                    "🎭 User Role",
                    options=[role.value for role in UserRole],
                    format_func=lambda x: {
                        'admin': '👑 Admin - Full access',
                        'user': '👤 User - Standard access',
                        'viewer': '👁️ Viewer - Read-only access'
                    }[x]
                )
            
            if st.form_submit_button("➕ Create User", type="primary"):
                if new_username and new_email and new_password:
                    if auth_manager.create_user(
                        username=new_username,
                        email=new_email,
                        password=new_password,
                        role=UserRole(new_role)
                    ):
                        st.success(f"✅ User '{new_username}' created successfully!")
                        # Clear cache to refresh user list
                        AuthUI._get_users_paginated.clear()
                        st.rerun()
                    else:
                        st.error("❌ Failed to create user. Username or email may already exist.")
                else:
                    st.warning("⚠️ Please fill in all fields")
    
    @staticmethod
    @st.cache_data(ttl=60)  # Cache user list for 1 minute
    def _get_users_paginated(page=0, per_page=10):
        """Get paginated user list with caching"""
        users = auth_manager.get_all_users()
        total = len(users)
        start_idx = page * per_page
        end_idx = start_idx + per_page
        return users[start_idx:end_idx], total

    @staticmethod
    def user_management_panel():
        """Display user management panel (admin only) - Optimized"""
        if not AuthUI.is_admin():
            st.error("❌ Admin access required for user management")
            return
        
        st.markdown("### 👥 User Management")
        
        # Pagination controls
        if 'user_page' not in st.session_state:
            st.session_state.user_page = 0
        
        per_page = 10
        users, total_users = AuthUI._get_users_paginated(st.session_state.user_page, per_page)
        total_pages = (total_users + per_page - 1) // per_page
        
        # Display pagination info
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.write(f"Page {st.session_state.user_page + 1} of {total_pages} ({total_users} total users)")
        
        if users:
            # Use containers for better performance
            user_container = st.container()
            
            with user_container:
                for user in users:
                    # Handle both dict and object user formats
                    if isinstance(user, dict):
                        username = user.get('username', 'Unknown')
                        email = user.get('email', 'Unknown')
                        role_str = user.get('role', 'viewer')
                        is_active = user.get('is_active', True)
                        created_at = user.get('created_at', 'Unknown')
                        last_login = user.get('last_login', None)
                    else:
                        username = user.username
                        email = user.email
                        role_str = user.role.value
                        is_active = user.is_active
                        created_at = user.created_at.strftime('%Y-%m-%d') if user.created_at else 'Unknown'
                        last_login = user.last_login.strftime('%Y-%m-%d %H:%M') if user.last_login else 'Never'
                    
                    # Get current session user info safely
                    session_user = st.session_state.user
                    if isinstance(session_user, dict):
                        session_username = session_user.get('username', '')
                    else:
                        session_username = session_user.username if session_user else ''
                    
                    with st.expander(f"👤 {username} ({role_str})", expanded=False):
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.write(f"**Email:** {email}")
                            if isinstance(user, dict):
                                st.write(f"**Created:** {created_at}")
                                st.write(f"**Last Login:** {last_login if last_login else 'Never'}")
                            else:
                                st.write(f"**Created:** {created_at}")
                                st.write(f"**Last Login:** {last_login}")
                        
                        with col2:
                            st.write(f"**Status:** {'🟢 Active' if is_active else '🔴 Inactive'}")
                            st.write(f"**Role:** {role_str.title()}")
                        
                        with col3:
                            if username != session_username:  # Can't modify own account
                                new_role = st.selectbox(
                                    "Change Role",
                                    options=[role.value for role in UserRole],
                                    index=[role.value for role in UserRole].index(role_str),
                                    key=f"role_{username}"
                                )
                                
                                if st.button(f"Update Role", key=f"update_{username}"):
                                    if auth_manager.update_user_role(username, UserRole(new_role)):
                                        st.success("✅ Role updated!")
                                        # Clear cache to refresh data
                                        AuthUI._get_users_paginated.clear()
                                        st.rerun()
                                
                                if is_active and st.button(f"🔒 Deactivate", key=f"deactivate_{username}"):
                                    if auth_manager.deactivate_user(username):
                                        st.success("✅ User deactivated!")
                                        # Clear cache to refresh data
                                        AuthUI._get_users_paginated.clear()
                                        st.rerun()
            
            # Pagination controls
            col1, col2, col3, col4, col5 = st.columns(5)
            with col1:
                if st.button("⏮️ First", key="user_first_btn", disabled=st.session_state.user_page == 0):
                    st.session_state.user_page = 0
                    st.rerun()
            with col2:
                if st.button("⬅️ Previous", key="user_prev_btn", disabled=st.session_state.user_page == 0):
                    st.session_state.user_page -= 1
                    st.rerun()
            with col3:
                # Show current page info
                st.write(f"Page {st.session_state.user_page + 1}")
            with col4:
                if st.button("➡️ Next", key="user_next_btn", disabled=st.session_state.user_page >= total_pages - 1):
                    st.session_state.user_page += 1
                    st.rerun()
            with col5:
                if st.button("⏭️ Last", key="user_last_btn", disabled=st.session_state.user_page >= total_pages - 1):
                    st.session_state.user_page = total_pages - 1
                    st.rerun()
        else:
            st.info("No users found")
    
    @staticmethod
    def logout_button():
        """Display logout button"""
        if st.button("🚪 Logout", type="secondary"):
            AuthUI.logout()
    
    @staticmethod
    def logout():
        """Handle user logout"""
        st.session_state.authenticated = False
        st.session_state.user = None
        st.session_state.auth_token = None
        st.success("👋 Logged out successfully!")
        time.sleep(1)
        st.rerun()
    
    @staticmethod
    def user_info_sidebar():
        """Display user info in sidebar"""
        if st.session_state.authenticated and st.session_state.user:
            user = st.session_state.user
            
            st.sidebar.markdown("---")
            st.sidebar.markdown("### 👤 User Info")
            st.sidebar.write(f"**Username:** {user.username}")
            st.sidebar.write(f"**Role:** {user.role.value.title()}")
            st.sidebar.write(f"**Email:** {user.email}")
            
            # Role-based access indicator
            role_colors = {
                UserRole.ADMIN: "🟢",
                UserRole.USER: "🟡", 
                UserRole.VIEWER: "🔵"
            }
            st.sidebar.write(f"**Access Level:** {role_colors.get(user.role, '⚪')} {user.role.value.title()}")
            
            st.sidebar.markdown("---")
            if st.sidebar.button("🚪 Logout", use_container_width=True):
                AuthUI.logout()
    
    @staticmethod
    def require_authentication():
        """Decorator/function to require authentication"""
        AuthUI.init_session_state()
        
        if not st.session_state.authenticated:
            st.markdown("# 🔐 VaultMind Authentication Required")
            st.markdown("Please log in to access the GenAI Knowledge Assistant.")
            return AuthUI.login_form()
        
        return True
    
    @staticmethod
    def require_role(required_role: UserRole) -> bool:
        """Check if current user has required role"""
        if not st.session_state.authenticated or not st.session_state.user:
            return False
        
        user = st.session_state.user
        # Handle both dict and object user formats
        if isinstance(user, dict):
            user_role_str = user.get('role', 'viewer')
            user_role = UserRole(user_role_str) if user_role_str in [r.value for r in UserRole] else UserRole.VIEWER
        else:
            user_role = user.role
        
        # Admin has access to everything
        if user_role == UserRole.ADMIN:
            return True
        
        # Check specific role requirements
        if required_role == UserRole.USER:
            return user_role in [UserRole.ADMIN, UserRole.USER]
        elif required_role == UserRole.VIEWER:
            return user_role in [UserRole.ADMIN, UserRole.USER, UserRole.VIEWER]
        
        return user_role == required_role
    
    @staticmethod
    def is_admin() -> bool:
        """Check if current user is admin"""
        if not (st.session_state.authenticated and st.session_state.user):
            return False
        
        user = st.session_state.user
        # Handle both dict and object user formats
        if isinstance(user, dict):
            user_role_str = user.get('role', 'viewer')
            return user_role_str == 'admin'
        else:
            return user.role == UserRole.ADMIN
    
    @staticmethod
    def access_denied_message(required_role: UserRole):
        """Display access denied message"""
        st.error(f"❌ Access Denied: {required_role.value.title()} role required")
        
        # Handle both dict and object user formats for current role display
        user = st.session_state.user
        if isinstance(user, dict):
            current_role = user.get('role', 'viewer')
        else:
            current_role = user.role.value
        
        st.info(f"Your current role: {current_role.title()}")
    
    @staticmethod
    def admin_panel():
        """Display admin panel"""
        if not AuthUI.is_admin():
            AuthUI.access_denied_message(UserRole.ADMIN)
            return
        
        st.markdown("## 👑 Admin Panel")
        
        admin_tab1, admin_tab2 = st.tabs(["👥 User Management", "➕ Create User"])
        
        with admin_tab1:
            AuthUI.user_management_panel()
        
        with admin_tab2:
            AuthUI.user_registration_form()
    
    @staticmethod
    def admin_panel_optimized():
        """Display optimized admin panel with lazy loading"""
        if not AuthUI.is_admin():
            AuthUI.access_denied_message(UserRole.ADMIN)
            return
        
        st.markdown("## 👑 Admin Panel")
        
        # Initialize tab state
        if 'admin_sub_tab' not in st.session_state:
            st.session_state.admin_sub_tab = 0
        
        admin_tab1, admin_tab2 = st.tabs(["👥 User Management", "➕ Create User"])
        
        # Only render active tab content
        with admin_tab1:
            AuthUI.user_management_panel()
        
        with admin_tab2:
            AuthUI.user_registration_form()

# Global auth UI instance
auth_ui = AuthUI()
