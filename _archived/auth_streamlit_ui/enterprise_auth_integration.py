"""
Enterprise Authentication Integration for VaultMind
Integrates all authentication methods and configurations
"""

import streamlit as st
from typing import Optional, Dict, Any
from datetime import datetime
import re

class EnterpriseAuthIntegration:
    """Main enterprise authentication integration class"""
    
    def __init__(self):
        self.config = None
        self.load_config()
    
    def load_config(self):
        """Load security configuration"""
        try:
            from app.auth.config_manager import security_config_manager
            self.config = security_config_manager.load_config()
        except Exception as e:
            st.error(f"Failed to load security configuration: {self._safe_err(e)}")
            self.config = {}
    
    def authenticate_user(self, username: str, password: str, auth_method: str = "auto") -> Optional[Dict[str, Any]]:
        """Authenticate user using specified method or auto-detect"""
        
        if auth_method == "auto":
            auth_method = self._detect_auth_method(username)
        
        try:
            if auth_method == "local":
                return self._authenticate_local(username, password)
            elif auth_method == "active_directory":
                return self._authenticate_ad(username, password)
            elif auth_method == "okta":
                return self._authenticate_okta(username, password)
            else:
                st.error("❌ Unsupported authentication method")
                return None
                
        except Exception as e:
            st.error(f"❌ Authentication error: {self._safe_err(e)}")
            return None
    
    def _detect_auth_method(self, username: str) -> str:
        """Auto-detect authentication method based on username format"""
        if "@" in username:
            domain = username.split("@")[1].lower()
            
            # Check if domain matches configured AD domain
            ad_config = self.config.get("active_directory", {})
            if ad_config.get("configured", False) and domain == ad_config.get("domain", "").lower():
                return "active_directory"
            
            # Check if domain matches configured Okta domain
            okta_config = self.config.get("okta", {})
            if okta_config.get("configured", False) and domain in okta_config.get("allowed_domains", []):
                return "okta"
        
        # Default to local authentication
        return "local"
    
    def _authenticate_local(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate against local user database"""
        try:
            from app.auth.auth_manager import auth_manager
            
            user = auth_manager.authenticate_user(username, password)
            if user:
                return {
                    'username': user.get('username', username),
                    'email': user.get('email', f"{username}@local"),
                    'display_name': user.get('display_name', username),
                    'role': user.get('role', 'user'),
                    'auth_method': 'local',
                    'authenticated_at': datetime.now().isoformat()
                }
            return None
            
        except Exception as e:
            st.error(f"Local authentication error: {self._safe_err(e)}")
            return None
    
    def _authenticate_ad(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate against Active Directory"""
        try:
            from app.auth.ad_connector import get_ad_connector
            
            ad_connector = get_ad_connector(self.config)
            user_data = ad_connector.authenticate_user(username, password)
            
            if user_data:
                # Map AD groups to role
                role = ad_connector.map_groups_to_role(user_data.get('groups', []))
                user_data['role'] = role
                return user_data
            
            return None
            
        except Exception as e:
            st.error(f"AD authentication error: {self._safe_err(e)}")
            return None
    
    def _authenticate_okta(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate against Okta (OAuth flow would be handled separately)"""
        # Note: Okta typically uses OAuth flow, not username/password
        # This is a placeholder for direct authentication scenarios
        st.info("🔐 Okta authentication requires OAuth flow. Please use SSO login.")
        return None
    
    def requires_mfa(self, user_data: Dict[str, Any]) -> bool:
        """Check if MFA is required for user"""
        mfa_config = self.config.get('mfa', {})
        
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
    
    def initiate_mfa(self, user_data: Dict[str, Any]) -> bool:
        """Initiate MFA verification process"""
        try:
            from app.auth.mfa_providers import get_mfa_providers
            
            mfa_providers = get_mfa_providers(self.config)
            mfa_config = self.config.get('mfa', {})
            
            # Store user data for MFA completion
            st.session_state.mfa_pending = True
            st.session_state.mfa_user_data = user_data
            st.session_state.mfa_config = self.config
            
            return True
            
        except Exception as e:
            st.error(f"MFA initiation error: {self._safe_err(e)}")
            return False
    
    def verify_mfa(self, code: str, method: str, username: str) -> bool:
        """Verify MFA code"""
        try:
            from app.auth.mfa_providers import get_mfa_providers
            
            mfa_providers = get_mfa_providers(self.config)
            
            if method == "authenticator":
                # Get user's TOTP secret
                secret = self._get_user_totp_secret(username)
                if secret:
                    return mfa_providers.verify_totp_code(secret, code)
            
            elif method in ["email", "sms"]:
                # Verify stored verification code
                return mfa_providers.verify_stored_code(username, code, method)
            
            return False
            
        except Exception as e:
            st.error(f"MFA verification error: {self._safe_err(e)}")
            return False
    
    def _get_user_totp_secret(self, username: str) -> str:
        """Get user's TOTP secret from storage"""
        # In production, retrieve from encrypted user database
        return st.session_state.get(f"totp_secret_{username}", "")
    
    def complete_authentication(self, user_data: Dict[str, Any]) -> bool:
        """Complete authentication and set session"""
        try:
            # Set session state
            st.session_state.authenticated = True
            st.session_state.user = user_data
            
            # Clear MFA session if present
            if 'mfa_pending' in st.session_state:
                del st.session_state.mfa_pending
            if 'mfa_user_data' in st.session_state:
                del st.session_state.mfa_user_data
            
            # Log successful authentication
            self._log_auth_event("login_success", user_data['username'], user_data['auth_method'])
            
            return True
            
        except Exception as e:
            st.error(f"Authentication completion error: {self._safe_err(e)}")
            return False
    
    def _log_auth_event(self, event_type: str, username: str, method: str):
        """Log authentication event"""
        try:
            # In production, log to secure audit system
            event = {
                'timestamp': datetime.now().isoformat(),
                'event_type': event_type,
                'username': username,
                'auth_method': method,
                'ip_address': self._get_client_ip(),
                'user_agent': self._get_user_agent()
            }
            
            # Store in session for demo (in production, use proper logging)
            if 'auth_events' not in st.session_state:
                st.session_state.auth_events = []
            
            st.session_state.auth_events.append(event)
            
        except Exception:
            pass  # Don't fail authentication due to logging errors
    
    def _get_client_ip(self) -> str:
        """Get client IP address"""
        # In production, extract from request headers
        return "127.0.0.1"
    
    def _get_user_agent(self) -> str:
        """Get user agent string"""
        # In production, extract from request headers
        return "Streamlit Browser"
    
    def _safe_err(self, e: object) -> str:
        """Return an ASCII-safe, control-char stripped error message for Windows consoles."""
        try:
            msg = str(e)
        except Exception:
            msg = ""
        # Strip control chars
        msg = re.sub(r"[\x00-\x1f]+", " ", msg)
        # Encode to ASCII, drop unsupported (emoji, etc.)
        try:
            return msg.encode('ascii', 'ignore').decode('ascii')
        except Exception:
            return "error"
    def logout_user(self):
        """Logout current user and clear session"""
        try:
            # Log logout event
            if st.session_state.get('authenticated', False):
                user = st.session_state.get('user', {})
                self._log_auth_event("logout", user.get('username', 'unknown'), user.get('auth_method', 'unknown'))
            
            # Clear all authentication session data
            auth_keys = [
                'authenticated', 'user', 'mfa_pending', 'mfa_user_data', 'mfa_config',
                'oauth_state', 'temp_username'
            ]
            
            for key in auth_keys:
                if key in st.session_state:
                    del st.session_state[key]
            st.success("✅ Successfully logged out")
            st.rerun()
            
        except Exception as e:
            st.error(f"Logout error: {self._safe_err(e)}")
    
# Global instance and accessor
enterprise_auth = EnterpriseAuthIntegration()

def get_enterprise_auth() -> EnterpriseAuthIntegration:
    """Get enterprise authentication instance"""
    return enterprise_auth
