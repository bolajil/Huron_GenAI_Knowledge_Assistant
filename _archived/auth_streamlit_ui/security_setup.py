"""
Real Security Setup Dashboard for VaultMind Enterprise Authentication
Allows admins to configure Active Directory, Okta SSO, and MFA providers
"""

import streamlit as st
from typing import Dict, Any
from datetime import datetime
import json

from app.auth.config_manager import security_config_manager

class SecuritySetupDashboard:
    """Admin interface for configuring enterprise authentication"""
    
    def __init__(self):
        self.config_manager = security_config_manager
    
    @staticmethod
    @st.cache_data(ttl=120)  # Cache config for 2 minutes
    def _load_config_cached():
        """Load configuration with caching"""
        from app.auth.config_manager import security_config_manager
        return security_config_manager.load_config()

    def render(self):
        """Render the security setup dashboard"""
        st.markdown("# 🛡️ Security Setup Dashboard")
        st.markdown("Configure enterprise authentication providers and security policies")
        
        # Load current configuration with caching
        config = self._load_config_cached()
        
        # Main tabs for different configuration areas
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "🏠 Overview", 
            "🌐 Active Directory", 
            "🔐 Okta SSO", 
            "📱 MFA Setup",
            "⚙️ Security Policies"
        ])
        
        with tab1:
            self._render_overview(config)
        
        with tab2:
            self._render_ad_setup(config)
        
        with tab3:
            self._render_okta_setup(config)
        
        with tab4:
            self._render_mfa_setup(config)
        
        with tab5:
            self._render_security_policies(config)
    
    def render_optimized(self):
        """Render optimized security setup dashboard with lazy loading"""
        st.markdown("# 🛡️ Security Setup Dashboard")
        st.markdown("Configure enterprise authentication providers and security policies")
        
        # Initialize security tab state
        if 'security_active_tab' not in st.session_state:
            st.session_state.security_active_tab = 0
        
        # Load configuration with caching
        config = self._load_config_cached()
        
        # Main tabs for different configuration areas
        tab_names = [
            "🏠 Overview", 
            "🌐 Active Directory", 
            "🔐 Okta SSO", 
            "📱 MFA Setup",
            "⚙️ Security Policies"
        ]
        
        selected_tab = st.selectbox(
            "Select Configuration Section:",
            options=range(len(tab_names)),
            format_func=lambda x: tab_names[x],
            index=st.session_state.security_active_tab,
            key="security_tab_selector"
        )
        
        # Update session state
        if selected_tab != st.session_state.security_active_tab:
            st.session_state.security_active_tab = selected_tab
            st.rerun()
        
        # Render only the selected tab content
        if selected_tab == 0:
            self._render_overview(config)
        elif selected_tab == 1:
            self._render_ad_setup(config)
        elif selected_tab == 2:
            self._render_okta_setup(config)
        elif selected_tab == 3:
            self._render_mfa_setup(config)
        elif selected_tab == 4:
            self._render_security_policies(config)
    
    def _render_overview(self, config: Dict[str, Any]):
        """Render configuration overview"""
        st.markdown("## 📊 Authentication Status")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            local_status = "✅ Enabled" if config["authentication"]["local_enabled"] else "❌ Disabled"
            st.metric("Local Login", local_status)
        
        with col2:
            ad_status = "✅ Configured" if config["active_directory"]["configured"] else "⚠️ Not Configured"
            st.metric("Active Directory", ad_status)
        
        with col3:
            okta_status = "✅ Configured" if config["okta"]["configured"] else "⚠️ Not Configured"
            st.metric("Okta SSO", okta_status)
        
        with col4:
            mfa_status = "✅ Configured" if config["mfa"]["configured"] else "⚠️ Not Configured"
            st.metric("MFA", mfa_status)
        
        st.markdown("---")
        
        # Current authentication methods
        st.markdown("### 🔑 Active Authentication Methods")
        auth_methods = []
        
        if config["authentication"]["local_enabled"]:
            auth_methods.append("🏠 Local Username/Password")
        
        if config["authentication"]["ad_enabled"] and config["active_directory"]["configured"]:
            auth_methods.append("🌐 Active Directory")
        
        if config["authentication"]["okta_enabled"] and config["okta"]["configured"]:
            auth_methods.append("🔐 Okta SSO")
        
        if config["authentication"]["mfa_enabled"] and config["mfa"]["configured"]:
            auth_methods.append("📱 Multi-Factor Authentication")
        
        for method in auth_methods:
            st.write(f"• {method}")
        
        if not auth_methods:
            st.warning("No authentication methods are currently active!")
        
        # Configuration history
        if config.get("last_updated"):
            st.markdown("### 📅 Last Updated")
            st.info(f"Updated: {config['last_updated']} by {config.get('updated_by', 'Unknown')}")
    
    def _render_ad_setup(self, config: Dict[str, Any]):
        """Render Active Directory configuration"""
        st.markdown("## 🌐 Active Directory Configuration")
        
        ad_config = config["active_directory"].copy()
        
        with st.form("ad_config_form"):
            st.markdown("### Server Configuration")
            
            col1, col2 = st.columns(2)
            
            with col1:
                ad_config["server"] = st.text_input(
                    "AD Server URL/IP",
                    value=ad_config["server"],
                    placeholder="dc.company.com or 192.168.1.10",
                    help="Active Directory domain controller address"
                )
                
                ad_config["domain"] = st.text_input(
                    "Domain Name",
                    value=ad_config["domain"],
                    placeholder="COMPANY",
                    help="Windows domain name"
                )
                
                ad_config["port"] = st.number_input(
                    "LDAP Port",
                    value=ad_config["port"],
                    min_value=1,
                    max_value=65535,
                    help="389 for LDAP, 636 for LDAPS"
                )
            
            with col2:
                ad_config["base_dn"] = st.text_input(
                    "Base DN",
                    value=ad_config["base_dn"],
                    placeholder="DC=company,DC=com",
                    help="Base Distinguished Name for user searches"
                )
                
                ad_config["service_account"] = st.text_input(
                    "Service Account",
                    value=ad_config["service_account"],
                    placeholder="svc_vaultmind",
                    help="Service account for LDAP binding"
                )
                
                ad_config["use_ssl"] = st.checkbox(
                    "Use SSL/TLS",
                    value=ad_config["use_ssl"],
                    help="Enable secure LDAP connection"
                )
            
            st.markdown("### Service Account Password")
            service_password = st.text_input(
                "Service Account Password",
                type="password",
                help="Password will be encrypted and stored securely"
            )
            
            st.markdown("### User Mapping")
            col1, col2 = st.columns(2)
            
            with col1:
                ad_config["user_attribute"] = st.selectbox(
                    "Username Attribute",
                    options=["sAMAccountName", "userPrincipalName", "cn"],
                    index=0 if ad_config["user_attribute"] == "sAMAccountName" else 1,
                    help="LDAP attribute to match usernames"
                )
            
            with col2:
                ad_config["group_attribute"] = st.text_input(
                    "Group Attribute",
                    value=ad_config["group_attribute"],
                    help="LDAP attribute containing group memberships"
                )
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.form_submit_button("💾 Save Configuration", type="primary"):
                    if service_password:
                        self.config_manager.encrypt_and_store_credential(
                            config, "active_directory", "service_password", service_password
                        )
                    
                    config["active_directory"].update(ad_config)
                    config["active_directory"]["configured"] = True
                    
                    if self.config_manager.save_config(config):
                        st.success("✅ Active Directory configuration saved!")
                        st.rerun()
            
            with col2:
                if st.form_submit_button("🧪 Test Connection"):
                    if not ad_config["server"] or not ad_config["domain"]:
                        st.error("Please fill in server and domain information")
                    else:
                        config["active_directory"].update(ad_config)
                        if service_password:
                            self.config_manager.encrypt_and_store_credential(
                                config, "active_directory", "service_password", service_password
                            )
                        
                        with st.spinner("Testing AD connection..."):
                            result = self.config_manager.test_ad_connection(config)
                        
                        if result["success"]:
                            st.success(f"✅ {result['message']}")
                            with st.expander("Connection Details"):
                                st.text(result.get("server_info", ""))
                        else:
                            st.error(f"❌ {result['error']}")
            
            with col3:
                if st.form_submit_button("🗑️ Clear Configuration"):
                    config["active_directory"] = self.config_manager.default_config["active_directory"].copy()
                    config["authentication"]["ad_enabled"] = False
                    
                    if self.config_manager.save_config(config):
                        st.success("✅ Active Directory configuration cleared!")
                        st.rerun()
        
        # Enable/Disable AD authentication
        if config["active_directory"]["configured"]:
            st.markdown("### 🔄 Authentication Control")
            
            current_status = config["authentication"]["ad_enabled"]
            new_status = st.toggle(
                "Enable Active Directory Authentication",
                value=current_status,
                help="Allow users to login with AD credentials"
            )
            
            if new_status != current_status:
                config["authentication"]["ad_enabled"] = new_status
                if self.config_manager.save_config(config):
                    status_text = "enabled" if new_status else "disabled"
                    st.success(f"✅ Active Directory authentication {status_text}!")
                    st.rerun()
    
    def _render_okta_setup(self, config: Dict[str, Any]):
        """Render Okta SSO configuration"""
        st.markdown("## 🔐 Okta SSO Configuration")
        
        okta_config = config["okta"].copy()
        
        with st.form("okta_config_form"):
            st.markdown("### Okta Application Settings")
            
            col1, col2 = st.columns(2)
            
            with col1:
                okta_config["domain"] = st.text_input(
                    "Okta Domain",
                    value=okta_config["domain"],
                    placeholder="yourcompany.okta.com",
                    help="Your Okta organization domain"
                )
                
                okta_config["client_id"] = st.text_input(
                    "Client ID",
                    value=okta_config["client_id"],
                    placeholder="0oa1a2b3c4d5e6f7g8h9",
                    help="OAuth2 Client ID from Okta app"
                )
                
                okta_config["authorization_server"] = st.text_input(
                    "Authorization Server",
                    value=okta_config["authorization_server"],
                    placeholder="default",
                    help="Authorization server ID (usually 'default')"
                )
            
            with col2:
                client_secret = st.text_input(
                    "Client Secret",
                    type="password",
                    help="OAuth2 Client Secret (will be encrypted)"
                )
                
                okta_config["redirect_uri"] = st.text_input(
                    "Redirect URI",
                    value=okta_config["redirect_uri"],
                    placeholder="https://yourapp.com/auth/callback",
                    help="OAuth2 redirect URI configured in Okta"
                )
                
                # Scopes selection
                available_scopes = ["openid", "profile", "email", "groups", "offline_access"]
                okta_config["scopes"] = st.multiselect(
                    "OAuth2 Scopes",
                    options=available_scopes,
                    default=okta_config["scopes"],
                    help="OAuth2 scopes to request"
                )
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.form_submit_button("💾 Save Configuration", type="primary"):
                    if client_secret:
                        self.config_manager.encrypt_and_store_credential(
                            config, "okta", "client_secret", client_secret
                        )
                    
                    config["okta"].update(okta_config)
                    config["okta"]["configured"] = True
                    
                    if self.config_manager.save_config(config):
                        st.success("✅ Okta configuration saved!")
                        st.rerun()
            
            with col2:
                if st.form_submit_button("🧪 Test Connection"):
                    if not okta_config["domain"]:
                        st.error("Please enter Okta domain")
                    else:
                        config["okta"].update(okta_config)
                        if client_secret:
                            self.config_manager.encrypt_and_store_credential(
                                config, "okta", "client_secret", client_secret
                            )
                        
                        with st.spinner("Testing Okta connection..."):
                            result = self.config_manager.test_okta_connection(config)
                        
                        if result["success"]:
                            st.success(f"✅ {result['message']}")
                            with st.expander("Connection Details"):
                                st.json({
                                    "issuer": result.get("issuer"),
                                    "authorization_endpoint": result.get("authorization_endpoint")
                                })
                        else:
                            st.error(f"❌ {result['error']}")
            
            with col3:
                if st.form_submit_button("🗑️ Clear Configuration"):
                    config["okta"] = self.config_manager.default_config["okta"].copy()
                    config["authentication"]["okta_enabled"] = False
                    
                    if self.config_manager.save_config(config):
                        st.success("✅ Okta configuration cleared!")
                        st.rerun()
        
        # Enable/Disable Okta authentication
        if config["okta"]["configured"]:
            st.markdown("### 🔄 Authentication Control")
            
            current_status = config["authentication"]["okta_enabled"]
            new_status = st.toggle(
                "Enable Okta SSO Authentication",
                value=current_status,
                help="Allow users to login with Okta SSO"
            )
            
            if new_status != current_status:
                config["authentication"]["okta_enabled"] = new_status
                if self.config_manager.save_config(config):
                    status_text = "enabled" if new_status else "disabled"
                    st.success(f"✅ Okta SSO authentication {status_text}!")
                    st.rerun()
    
    def _render_mfa_setup(self, config: Dict[str, Any]):
        """Render MFA configuration"""
        st.markdown("## 📱 Multi-Factor Authentication Setup")
        
        mfa_config = config["mfa"].copy()
        
        # MFA Provider Selection
        st.markdown("### 🔧 MFA Providers")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            mfa_config["totp_enabled"] = st.checkbox(
                "📱 TOTP (Authenticator Apps)",
                value=mfa_config["totp_enabled"],
                help="Google Authenticator, Authy, Microsoft Authenticator"
            )
        
        with col2:
            mfa_config["email_enabled"] = st.checkbox(
                "📧 Email MFA",
                value=mfa_config["email_enabled"],
                help="Send verification codes via email"
            )
        
        with col3:
            mfa_config["sms_enabled"] = st.checkbox(
                "📱 SMS MFA",
                value=mfa_config["sms_enabled"],
                help="Send verification codes via SMS"
            )
        
        # Email MFA Configuration
        if mfa_config["email_enabled"]:
            with st.expander("📧 Email MFA Configuration", expanded=True):
                with st.form("email_mfa_form"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        mfa_config["email_smtp_server"] = st.text_input(
                            "SMTP Server",
                            value=mfa_config["email_smtp_server"],
                            placeholder="smtp.gmail.com"
                        )
                        
                        mfa_config["email_smtp_port"] = st.number_input(
                            "SMTP Port",
                            value=mfa_config["email_smtp_port"],
                            min_value=1,
                            max_value=65535
                        )
                    
                    with col2:
                        mfa_config["email_username"] = st.text_input(
                            "Email Username",
                            value=mfa_config["email_username"],
                            placeholder="noreply@company.com"
                        )
                        
                        email_password = st.text_input(
                            "Email Password",
                            type="password",
                            help="App password or SMTP password"
                        )
                    
                    test_email = st.text_input(
                        "Test Email Address",
                        placeholder="admin@company.com",
                        help="Email address to test MFA functionality"
                    )
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if st.form_submit_button("💾 Save Email Config"):
                            if email_password:
                                self.config_manager.encrypt_and_store_credential(
                                    config, "mfa", "email_password", email_password
                                )
                            
                            config["mfa"].update(mfa_config)
                            
                            if self.config_manager.save_config(config):
                                st.success("✅ Email MFA configuration saved!")
                    
                    with col2:
                        if st.form_submit_button("🧪 Test Email"):
                            if not test_email:
                                st.error("Please enter test email address")
                            else:
                                config["mfa"].update(mfa_config)
                                if email_password:
                                    self.config_manager.encrypt_and_store_credential(
                                        config, "mfa", "email_password", email_password
                                    )
                                
                                with st.spinner("Sending test email..."):
                                    result = self.config_manager.test_email_mfa(config, test_email)
                                
                                if result["success"]:
                                    st.success(f"✅ {result['message']}")
                                else:
                                    st.error(f"❌ {result['error']}")
        
        # SMS MFA Configuration
        if mfa_config["sms_enabled"]:
            with st.expander("📱 SMS MFA Configuration", expanded=True):
                st.info("SMS MFA requires integration with SMS providers like Twilio or AWS SNS")
                
                with st.form("sms_mfa_form"):
                    mfa_config["sms_provider"] = st.selectbox(
                        "SMS Provider",
                        options=["twilio", "aws_sns", "custom"],
                        help="SMS service provider"
                    )
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        sms_api_key = st.text_input(
                            "API Key/Account SID",
                            type="password",
                            help="SMS provider API key"
                        )
                    
                    with col2:
                        sms_api_secret = st.text_input(
                            "API Secret/Auth Token",
                            type="password",
                            help="SMS provider API secret"
                        )
                    
                    if st.form_submit_button("💾 Save SMS Config"):
                        if sms_api_key:
                            self.config_manager.encrypt_and_store_credential(
                                config, "mfa", "sms_api_key", sms_api_key
                            )
                        if sms_api_secret:
                            self.config_manager.encrypt_and_store_credential(
                                config, "mfa", "sms_api_secret", sms_api_secret
                            )
                        
                        config["mfa"].update(mfa_config)
                        
                        if self.config_manager.save_config(config):
                            st.success("✅ SMS MFA configuration saved!")
        
        # Save MFA configuration and enable/disable
        st.markdown("### 🔄 MFA Control")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("💾 Save MFA Configuration", type="primary"):
                config["mfa"].update(mfa_config)
                config["mfa"]["configured"] = any([
                    mfa_config["totp_enabled"],
                    mfa_config["email_enabled"],
                    mfa_config["sms_enabled"]
                ])
                
                if self.config_manager.save_config(config):
                    st.success("✅ MFA configuration saved!")
                    st.rerun()
        
        with col2:
            if config["mfa"]["configured"]:
                current_status = config["authentication"]["mfa_enabled"]
                new_status = st.toggle(
                    "Enable MFA",
                    value=current_status,
                    help="Require MFA for authentication"
                )
                
                if new_status != current_status:
                    config["authentication"]["mfa_enabled"] = new_status
                    if self.config_manager.save_config(config):
                        status_text = "enabled" if new_status else "disabled"
                        st.success(f"✅ MFA {status_text}!")
                        st.rerun()
    
    def _render_security_policies(self, config: Dict[str, Any]):
        """Render security policy configuration"""
        st.markdown("## ⚙️ Security Policies")
        
        policies = config["security_policies"].copy()
        
        with st.form("security_policies_form"):
            st.markdown("### 🔒 Password Requirements")
            
            col1, col2 = st.columns(2)
            
            with col1:
                policies["password_min_length"] = st.number_input(
                    "Minimum Password Length",
                    value=policies["password_min_length"],
                    min_value=4,
                    max_value=128
                )
                
                policies["password_require_uppercase"] = st.checkbox(
                    "Require Uppercase Letters",
                    value=policies["password_require_uppercase"]
                )
                
                policies["password_require_lowercase"] = st.checkbox(
                    "Require Lowercase Letters",
                    value=policies["password_require_lowercase"]
                )
            
            with col2:
                policies["password_require_numbers"] = st.checkbox(
                    "Require Numbers",
                    value=policies["password_require_numbers"]
                )
                
                policies["password_require_symbols"] = st.checkbox(
                    "Require Special Characters",
                    value=policies["password_require_symbols"]
                )
            
            st.markdown("### 🛡️ Account Security")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                policies["max_login_attempts"] = st.number_input(
                    "Max Login Attempts",
                    value=policies["max_login_attempts"],
                    min_value=1,
                    max_value=20,
                    help="Account lockout after failed attempts"
                )
            
            with col2:
                policies["lockout_duration_minutes"] = st.number_input(
                    "Lockout Duration (minutes)",
                    value=policies["lockout_duration_minutes"],
                    min_value=1,
                    max_value=1440,
                    help="How long accounts stay locked"
                )
            
            with col3:
                policies["session_timeout_minutes"] = st.number_input(
                    "Session Timeout (minutes)",
                    value=policies["session_timeout_minutes"],
                    min_value=5,
                    max_value=1440,
                    help="Automatic session expiration"
                )
            
            st.markdown("### 📱 MFA Requirements")
            
            policies["require_mfa_for_admin"] = st.checkbox(
                "Require MFA for Admin Users",
                value=policies["require_mfa_for_admin"],
                help="Force MFA for users with admin privileges"
            )
            
            if st.form_submit_button("💾 Save Security Policies", type="primary"):
                config["security_policies"].update(policies)
                
                if self.config_manager.save_config(config):
                    st.success("✅ Security policies saved!")
                    st.rerun()

# Global instance
security_setup_dashboard = SecuritySetupDashboard()
