"""
VaultMind GenAI Knowledge Assistant - Simplified Enterprise Authentication
Production-ready authentication without external dependencies
"""

import streamlit as st
import hashlib
import secrets
import json
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import os
import sys
from pathlib import Path

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.auth.authentication import AuthenticationManager, UserRole

# Initialize auth manager
auth_manager = AuthenticationManager()

class EnterpriseAuth:
    """Simplified Enterprise Authentication System"""
    
    def __init__(self):
        self.session_timeout_minutes = 480  # 8 hours
        self.max_login_attempts = 5
        self.lockout_duration_minutes = 30
        
    def render_login_page(self) -> bool:
        """Render enterprise login page with real authentication options"""
        # Load current security configuration
        from app.auth.config_manager import security_config_manager
        config = security_config_manager.load_config()
        
        # Check if MFA setup is pending
        if st.session_state.get('mfa_setup_pending', False):
            from app.auth.mfa_setup import render_mfa_setup_page
            render_mfa_setup_page()
            return False # Prevent login form from rendering
        
        # Check if MFA verification is pending
        if st.session_state.get('mfa_pending', False):
            return self._render_mfa_verification(config)
        
        # Main login form
        st.markdown("""
        <div style="text-align: center; padding: 2rem;">
            <h1>🧠 VaultMind GenAI Knowledge Assistant</h1>
            <h3>🔐 Enterprise Secure Login</h3>
            <p style="color: #666;">Production-grade authentication with enterprise security</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Show available authentication methods
        self._show_auth_methods(config)
        
        st.markdown("---")
        
        # Authentication method selection
        auth_methods = self._get_available_auth_methods(config)
        
        if len(auth_methods) > 1:
            selected_method = st.selectbox(
                "Choose Authentication Method:",
                options=list(auth_methods.keys()),
                format_func=lambda x: auth_methods[x]
            )
        else:
            selected_method = list(auth_methods.keys())[0] if auth_methods else "local"
        
        # Render appropriate login form
        if selected_method == "local":
            return self._render_local_login(config)
        elif selected_method == "active_directory":
            return self._render_ad_login(config)
        elif selected_method == "okta":
            return self._render_okta_login(config)
        
        return False
    
    def _get_available_auth_methods(self, config: dict) -> dict:
        """Get available authentication methods based on configuration"""
        methods = {"local": "🔑 Local Login"}
        
        if config.get("active_directory", {}).get("configured", False):
            methods["active_directory"] = "🏢 Active Directory"
        
        if config.get("okta", {}).get("configured", False):
            methods["okta"] = "🔐 Okta SSO"
        
        return methods
    
    def _show_auth_methods(self, config: dict):
        """Show available authentication methods status"""
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if config.get("active_directory", {}).get("configured", False):
                st.success("🏢 Active Directory Ready")
            else:
                st.info("🏢 AD Not Configured")
        
        with col2:
            if config.get("okta", {}).get("configured", False):
                st.success("🔐 Okta SSO: Ready")
            else:
                st.info("🔐 Okta SSO: Not Configured")
        
        with col3:
            if config.get("mfa", {}).get("enabled", False):
                st.success("📱 MFA: Enabled")
            else:
                st.info("📱 MFA: Disabled")
    
    def _render_local_login(self, config: dict) -> bool:
        """Render local login form"""
        with st.form("local_login"):
            st.markdown("### 🔑 Local Authentication")
            
            username = st.text_input(
                "👤 Username or Email",
                placeholder="Enter your username or email address"
            )
            
            password = st.text_input(
                "🔒 Password",
                type="password",
                placeholder="Enter your password"
            )
            
            col1, col2 = st.columns(2)
            with col1:
                remember_me = st.checkbox("🔄 Remember me")
            with col2:
                trust_device = st.checkbox("📱 Trust device")
            
            login_button = st.form_submit_button(
                "🔓 Login",
                type="primary",
                use_container_width=True
            )
            
            if login_button:
                return self._process_local_login(username, password, remember_me, trust_device, config)
        
        return False
    
    def _render_ad_login(self, config: dict) -> bool:
        """Render Active Directory login form"""
        from app.auth.ad_connector import get_ad_connector
        
        with st.form("ad_login"):
            st.markdown("### 🏢 Active Directory Authentication")
            
            username = st.text_input(
                "👤 Domain Username",
                placeholder="username (without domain)",
                help=f"Domain: {config.get('active_directory', {}).get('domain', 'Not configured')}"
            )
            
            password = st.text_input(
                "🔒 Password",
                type="password",
                placeholder="Enter your domain password"
            )
            
            login_button = st.form_submit_button(
                "🔓 Login with AD",
                type="primary",
                use_container_width=True
            )
            
            if login_button:
                return self._process_ad_login(username, password, config)
        
        return False
    
    def _render_okta_login(self, config: dict) -> bool:
        """Render Okta SSO login"""
        from app.auth.okta_connector import get_okta_connector
        
        st.markdown("### 🔐 Okta Single Sign-On")
        
        # Check for OAuth callback
        query_params = st.query_params
        if 'code' in query_params and 'state' in query_params:
            return self._handle_okta_callback(query_params['code'], query_params['state'], config)
        
        # Show SSO login button
        okta_connector = get_okta_connector(config)
        return okta_connector.initiate_sso_login()
    
    def _authenticate_local_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate user against local database"""
        try:
            user = auth_manager.authenticate_user(username, password)
            if user:
                return {
                    'username': user.username,
                    'email': user.email,
                    'role': user.role.value,
                    'last_login': user.last_login,
                    'is_active': user.is_active
                }
            return None
        except Exception as e:
            import logging as _logging, json as _json
            safe_msg = _json.dumps({"error": str(e)}, ensure_ascii=True)
            _logging.getLogger(__name__).warning("Local authentication error: %s", safe_msg)
            return None
    
    def _process_local_login(self, username: str, password: str, remember_me: bool, trust_device: bool, config: dict) -> bool:
        """Process login with enterprise security"""
        if not username or not password:
            st.error("❌ Please enter both username and password")
            return False
        
        # Check account lockout
        if self._is_account_locked(username):
            st.error("🔒 Account temporarily locked due to multiple failed attempts")
            return False
        
        try:
            # Real authentication against local user database
            user_data = self._authenticate_local_user(username, password)
            
            if user_data:
                # Check if MFA is required
                if self._requires_mfa(user_data, config):
                    return self._handle_mfa_flow(user_data, config)
                
                # Complete login
                return self._complete_login(user_data)
            else:
                self._record_failed_attempt(username)
                st.error("❌ Invalid credentials")
                return False
                
        except Exception as e:
            st.error(f"❌ Local authentication error: {str(e)}")
            return False
    
    def _process_ad_login(self, username: str, password: str, config: dict) -> bool:
        """Process Active Directory login"""
        if not username or not password:
            st.error("❌ Please enter both username and password")
            return False
        
        # Check account lockout
        if self._is_account_locked(username):
            remaining = self._get_lockout_remaining(username)
            st.error(f"🔒 Account locked. Try again in {remaining} minutes.")
            return False
        
        try:
            from app.auth.ad_connector import get_ad_connector
            
            ad_connector = get_ad_connector(config)
            user_data = ad_connector.authenticate_user(username, password)
            
            if user_data:
                # Map AD groups to role
                role = ad_connector.map_groups_to_role(user_data.get('groups', []))
                user_data['role'] = role
                
                # Check MFA requirement
                if self._requires_mfa(user_data, config):
                    return self._handle_mfa_flow(user_data, config)
                
                # Complete login
                return self._complete_login(user_data)
            else:
                self._record_failed_attempt(username)
                st.error("❌ Invalid Active Directory credentials")
                return False
                
        except Exception as e:
            st.error(f"❌ AD authentication error: {str(e)}")
            return False
    
    def _handle_okta_callback(self, code: str, state: str, config: dict) -> bool:
        """Handle Okta OAuth callback"""
        try:
            from app.auth.okta_connector import get_okta_connector
            
            okta_connector = get_okta_connector(config)
            user_data = okta_connector.handle_callback(code, state)
            
            if user_data:
                # Map Okta groups to role
                role = okta_connector.map_groups_to_role(user_data.get('groups', []))
                user_data['role'] = role
                
                # Check MFA requirement
                if self._requires_mfa(user_data, config):
                    return self._handle_mfa_flow(user_data, config)
                
                # Complete login
                return self._complete_login(user_data)
            else:
                st.error("❌ Okta authentication failed")
                return False
                
        except Exception as e:
            st.error(f"❌ Okta callback error: {str(e)}")
            return False
    
    def _requires_mfa(self, user_data: dict, config: dict) -> bool:
        """Check if MFA is required for user"""
        mfa_config = config.get('mfa', {})
        
        if not mfa_config.get('enabled', False):
            return False
        
        # Check if MFA is enforced for user's role
        role = user_data.get('role', 'viewer')
        enforcement = mfa_config.get('enforcement', {})
        
        if role == 'admin' and enforcement.get('admin_required', True):
            return True
        elif role == 'user' and enforcement.get('user_required', False):
            return True
        elif role == 'viewer' and enforcement.get('viewer_required', False):
            return True
        
        return False
    
    def _handle_mfa_flow(self, user_data: dict, config: dict) -> bool:
        """Handles the MFA flow by checking if setup is needed or just verification."""
        username = user_data.get('username')
        secret = self._get_user_totp_secret(username)

        if not secret:
            # User needs to set up MFA
            st.session_state.mfa_setup_pending = True
            st.session_state.user = user_data  # mfa_setup page expects 'user'
            st.rerun()
            return False
        else:
            # User has a secret, proceed with verification
            return self._initiate_mfa(user_data, config)

    def _initiate_mfa(self, user_data: dict, config: dict) -> bool:
        """Initiate MFA verification process"""
        st.session_state.mfa_pending = True
        st.session_state.mfa_user_data = user_data
        st.session_state.mfa_config = config
        st.rerun()
        return False
    
    def _render_mfa_verification(self, config: dict) -> bool:
        """Render MFA verification form with real providers"""
        from app.auth.mfa_providers import get_mfa_providers
        
        user_data = st.session_state.get('mfa_user_data', {})
        mfa_providers = get_mfa_providers(config)
        mfa_config = config.get('mfa', {})
        
        st.markdown("### 📱 Multi-Factor Authentication Required")
        st.info("Additional verification required for enhanced security")
        
        # Available MFA methods based on configuration
        available_methods = []
        if mfa_config.get('totp_enabled', True):
            available_methods.append("📱 Authenticator App")
        if mfa_config.get('email_enabled', False):
            available_methods.append("📧 Email Code")
        if mfa_config.get('sms_enabled', False):
            available_methods.append("📱 SMS Code")
        
        if not available_methods:
            st.error("❌ No MFA methods configured")
            return False
        
        mfa_method = st.radio(
            "Choose verification method:",
            available_methods,
            horizontal=True
        )
        
        # Send code for email/SMS methods
        username = user_data.get('username', '')
        method_key = mfa_method.split()[1].lower()  # Extract method name
        
        if mfa_method == "📧 Email Code":
            if st.button("📧 Send Email Code"):
                code = mfa_providers.generate_verification_code()
                email = user_data.get('email', f"{username}@company.com")
                if mfa_providers.send_email_code(email, code):
                    mfa_providers.store_verification_code(username, code, 'email')
                    st.success(f"📧 Verification code sent to {email}")
                else:
                    st.error("❌ Failed to send email code")
        
        elif mfa_method == "📱 SMS Code":
            if st.button("📱 Send SMS Code"):
                code = mfa_providers.generate_verification_code()
                phone = user_data.get('phone', '+1234567890')  # Would be from user profile
                if mfa_providers.send_sms_code(phone, code):
                    mfa_providers.store_verification_code(username, code, 'sms')
                    st.success(f"📱 Verification code sent to {phone}")
                else:
                    st.error("❌ Failed to send SMS code")
        
        with st.form("mfa_verification"):
            if mfa_method == "📱 Authenticator App":
                st.info("📱 Enter the 6-digit code from your authenticator app")
                code = st.text_input(
                    "Authentication Code",
                    placeholder="000000",
                    max_chars=6,
                    help="Google Authenticator, Authy, or Microsoft Authenticator"
                )
            col1, col2 = st.columns(2)
            with col1:
                verify_button = st.form_submit_button("✅ Verify Code", type="primary")
            with col2:
                cancel_button = st.form_submit_button("❌ Cancel")
            
            if cancel_button:
                # Clear MFA session
                st.session_state.mfa_pending = False
                if 'mfa_user_data' in st.session_state:
                    del st.session_state.mfa_user_data
                st.rerun()
                return False
            
            if verify_button and code:
                return self._verify_mfa_code(code, method_key, username, mfa_providers, user_data)
        
        return False
    
    def _verify_mfa_code(self, code: str, method: str, username: str, mfa_providers, user_data: dict) -> bool:
        """Verify MFA code using appropriate method"""
        try:
            if method == "authenticator":
                if self._verify_totp_code(username, code):
                    return self._complete_mfa_login(user_data)
            
            elif method in ["email", "sms"]:
                # Verify stored verification code
                if mfa_providers.verify_stored_code(username, code, method):
                    return self._complete_mfa_login(user_data)
            
            st.error("❌ Invalid verification code")
            return False
            
        except Exception as e:
            st.error(f"❌ MFA verification error: {str(e)}")
            return False
    
    def _complete_mfa_login(self, user_data: dict) -> bool:
        """Complete login after successful MFA verification"""
        # Clear MFA session
        st.session_state.mfa_pending = False
        if 'mfa_user_data' in st.session_state:
            del st.session_state.mfa_user_data
        
        # Complete login
        return self._complete_login(user_data)
    
    def _complete_login(self, user_data: dict) -> bool:
        """Complete the login process"""
        try:
            # Set session state
            st.session_state.authenticated = True
            st.session_state.user = user_data
            
            # Create secure session
            self._create_secure_session(user_data['username'], False, False)
            self._log_security_event("login_success", user_data['username'])
            
            st.success("✅ Authentication successful!")
            st.balloons()
            return True
            
        except Exception as e:
            st.error(f"❌ Login completion error: {str(e)}")
            return False
    
    def _get_user_totp_secret(self, username: str) -> str:
        """Get user's TOTP secret from storage"""
        # In a real application, this MUST be stored securely in a database.
        # Using session_state is for demonstration purposes only and is NOT secure.
        return st.session_state.get(f"totp_secret_{username}", "")
    
    
    def _verify_totp_code(self, username: str, code: str) -> bool:
        """Verify TOTP code from authenticator app"""
        # Get user's TOTP secret from secure storage
        user_secret = self._get_user_totp_secret(username)
        if not user_secret:
            return False
        
        import pyotp
        totp = pyotp.TOTP(user_secret)
        return totp.verify(code, valid_window=1)
    
    def _verify_email_code(self, username: str, code: str) -> bool:
        """Verify email-based MFA code"""
        # Get stored email code from secure cache/database
        stored_code = self._get_stored_email_code(username)
        if not stored_code:
            return False
        
        # Check if code matches and hasn't expired
        return stored_code.get('code') == code and not self._is_code_expired(stored_code.get('timestamp'))
    
    def _verify_sms_code(self, username: str, code: str) -> bool:
        """Verify SMS-based MFA code"""
        # Get stored SMS code from secure cache/database
        stored_code = self._get_stored_sms_code(username)
        if not stored_code:
            return False
        
        # Check if code matches and hasn't expired
        return stored_code.get('code') == code and not self._is_code_expired(stored_code.get('timestamp'))
    
    def _get_lockout_remaining(self, username: str) -> int:
        """Get remaining lockout time in minutes"""
        lockout_time = st.session_state.get(f'lockout_time_{username}')
        if lockout_time:
            lockout_datetime = datetime.fromisoformat(lockout_time)
            remaining = (lockout_datetime - datetime.now()).total_seconds() / 60
            return max(0, int(remaining))
        return 0
    
    def _get_stored_email_code(self, username: str) -> dict:
        """Get stored email verification code"""
        # In production, retrieve from secure cache (Redis) or database
        return None
    
    def _get_stored_sms_code(self, username: str) -> dict:
        """Get stored SMS verification code"""
        # In production, retrieve from secure cache (Redis) or database
        return None
    
    def _is_code_expired(self, timestamp: str) -> bool:
        """Check if verification code has expired"""
        if not timestamp:
            return True
        
        from datetime import datetime
        code_time = datetime.fromisoformat(timestamp)
        expiry_minutes = 5  # Codes expire after 5 minutes
        
        return (datetime.now() - code_time).total_seconds() > (expiry_minutes * 60)
    
    def _reset_failed_attempts(self, username: str):
        """Reset failed login attempts after successful login"""
        if f'failed_attempts_{username}' in st.session_state:
            del st.session_state[f'failed_attempts_{username}']
        if f'lockout_time_{username}' in st.session_state:
            del st.session_state[f'lockout_time_{username}']
    
    def _is_account_locked(self, username: str) -> bool:
        """Check if account is locked due to failed attempts"""
        # Get failed attempts from session state or secure storage
        failed_attempts = st.session_state.get(f'failed_attempts_{username}', 0)
        lockout_time = st.session_state.get(f'lockout_time_{username}')
        
        if lockout_time:
            # Check if lockout period has expired
            lockout_datetime = datetime.fromisoformat(lockout_time)
            if datetime.now() < lockout_datetime:
                return True
            else:
                # Lockout expired, reset counters
                if f'failed_attempts_{username}' in st.session_state:
                    del st.session_state[f'failed_attempts_{username}']
                if f'lockout_time_{username}' in st.session_state:
                    del st.session_state[f'lockout_time_{username}']
        
        return failed_attempts >= self.max_login_attempts
    
    def _record_failed_attempt(self, username: str):
        """Record failed login attempt and implement lockout"""
        # Increment failed attempt counter
        failed_attempts = st.session_state.get(f'failed_attempts_{username}', 0) + 1
        st.session_state[f'failed_attempts_{username}'] = failed_attempts
        
        # If max attempts reached, set lockout time
        if failed_attempts >= self.max_login_attempts:
            lockout_until = datetime.now() + timedelta(minutes=self.lockout_duration_minutes)
            st.session_state[f'lockout_time_{username}'] = lockout_until.isoformat()
            
            self._log_security_event("account_locked", username, 
                                   f"Account locked for {self.lockout_duration_minutes} minutes")
        
        self._log_security_event("failed_attempt", username, 
                               f"Failed attempt #{failed_attempts}")
    
    def _reset_failed_attempts(self, username: str):
        """Reset failed attempt counter on successful login"""
        if f'failed_attempts_{username}' in st.session_state:
            del st.session_state[f'failed_attempts_{username}']
        if f'lockout_time_{username}' in st.session_state:
            del st.session_state[f'lockout_time_{username}']
    
    def _create_secure_session(self, username: str, remember_me: bool, trust_device: bool):
        """Create secure session"""
        session_data = {
            'username': username,
            'login_time': datetime.now().isoformat(),
            'remember_me': remember_me,
            'trust_device': trust_device,
            'session_id': secrets.token_urlsafe(32),
            'ip_address': self._get_client_ip(),
            'expires_at': (datetime.now() + timedelta(minutes=self.session_timeout_minutes)).isoformat()
        }
        
        # Store session data
        st.session_state.secure_session = session_data
        st.session_state.session_timeout = datetime.now() + timedelta(minutes=self.session_timeout_minutes)
    
    def _log_security_event(self, event_type: str, username: str, details: str = None):
        """Log security events for audit trail"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'username': username,
            'event_type': event_type,
            'ip_address': self._get_client_ip(),
            'details': details or {}
        }
        
        # Use logger to avoid Windows console encoding issues
        try:
            import logging as _logging, json as _json
            msg = _json.dumps(log_entry, ensure_ascii=True)  # ASCII-safe
            _logging.getLogger(__name__).info("[AUDIT] %s", msg)
        except Exception:
            # Last resort: swallow logging errors to not break auth flow
            pass
    
    def _get_client_ip(self) -> str:
        """Get client IP address from request headers"""
        try:
            # Try to get real client IP from Streamlit context
            import streamlit.web.server.websocket_headers as ws_headers
            headers = ws_headers.get_websocket_headers()
            
            # Check for forwarded IP headers (common in production)
            forwarded_ips = [
                headers.get('X-Forwarded-For'),
                headers.get('X-Real-IP'),
                headers.get('CF-Connecting-IP'),  # Cloudflare
                headers.get('X-Client-IP')
            ]
            
            for ip in forwarded_ips:
                if ip:
                    # Take first IP if comma-separated list
                    return ip.split(',')[0].strip()
            
            # Fallback to remote address
            return headers.get('Remote-Addr', 'unknown')
        except:
            # If unable to get real IP, return unknown instead of dummy data
            return 'unknown'
    
    def logout(self):
        """Secure logout with session cleanup"""
        # Log logout event before clearing session
        if hasattr(st.session_state, 'user') and st.session_state.user:
            self._log_security_event("logout_success", st.session_state.user.username)
        
        # Clear all session state
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        
        st.success("🔐 Logged out successfully")
        st.info("Your session has been securely terminated")
    
    def render_security_dashboard(self):
        """Render security monitoring dashboard for admins"""
        st.markdown("### 🛡️ Enterprise Security Dashboard")
        
        # Get real metrics from session state and system
        active_sessions = self._count_active_sessions()
        failed_logins = self._count_failed_logins_24h()
        locked_accounts = self._count_locked_accounts()
        mfa_enabled_percent = self._calculate_mfa_adoption()
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("🔐 Active Sessions", str(active_sessions))
        
        with col2:
            st.metric("🚨 Failed Logins (24h)", str(failed_logins))
        
        with col3:
            st.metric("🔒 Locked Accounts", str(locked_accounts))
        
        with col4:
            st.metric("📱 MFA Enabled", f"{mfa_enabled_percent}%")
        
        # Recent security events from real audit log
        st.markdown("#### 📊 Recent Security Events")
        security_events = self._get_recent_security_events()
        
        if security_events:
            import pandas as pd
            st.dataframe(pd.DataFrame(security_events), use_container_width=True)
        else:
            st.info("No recent security events to display")
    
    def _count_active_sessions(self) -> int:
        """Count currently active sessions"""
        # In production, query session storage (Redis/database)
        # For now, count from session state
        active_count = 0
        if hasattr(st.session_state, 'authenticated') and st.session_state.authenticated:
            active_count = 1
        return active_count
    
    def _count_failed_logins_24h(self) -> int:
        """Count failed login attempts in last 24 hours"""
        # In production, query audit logs for failed attempts in last 24h
        # For now, count from session state
        failed_count = 0
        for key in st.session_state.keys():
            if key.startswith('failed_attempts_'):
                failed_count += st.session_state[key]
        return failed_count
    
    def _count_locked_accounts(self) -> int:
        """Count currently locked accounts"""
        # Count accounts with active lockout times
        locked_count = 0
        current_time = datetime.now()
        
        for key in st.session_state.keys():
            if key.startswith('lockout_time_'):
                lockout_time = st.session_state[key]
                if lockout_time and datetime.fromisoformat(lockout_time) > current_time:
                    locked_count += 1
        
        return locked_count
    
    def _calculate_mfa_adoption(self) -> int:
        """Calculate MFA adoption percentage"""
        # In production, query user database for MFA setup status
        # For now, return based on current user
        if hasattr(st.session_state, 'user') and st.session_state.user:
            if self._requires_mfa(st.session_state.user):
                return 100  # Admin users require MFA
        return 0
    
    def _get_recent_security_events(self) -> list:
        """Get recent security events from audit log"""
        # In production, query audit log database
        # For now, return events from current session if any
        events = []
        
        # Add current session info if authenticated
        if hasattr(st.session_state, 'user') and st.session_state.user:
            current_time = datetime.now().strftime("%H:%M")
            events.append({
                "Time": current_time,
                "Event": "Active Session",
                "User": st.session_state.user.username,
                "IP": self._get_client_ip(),
                "Status": "✅"
            })
        
        # Add failed attempts if any
        for key in st.session_state.keys():
            if key.startswith('failed_attempts_'):
                username = key.replace('failed_attempts_', '')
                attempts = st.session_state[key]
                if attempts > 0:
                    events.append({
                        "Time": datetime.now().strftime("%H:%M"),
                        "Event": f"Failed Attempts ({attempts})",
                        "User": username,
                        "IP": self._get_client_ip(),
                        "Status": "❌"
                    })
        
        return events

# Global enterprise auth instance
enterprise_auth = EnterpriseAuth()
