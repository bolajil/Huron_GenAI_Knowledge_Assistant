"""
Configuration manager for enterprise authentication settings
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import logging

from app.utils.encryption import credential_manager

logger = logging.getLogger(__name__)

class SecurityConfigManager:
    """Manages enterprise authentication configuration"""
    
    def __init__(self):
        self.config_dir = Path(__file__).parent.parent.parent / "config"
        self.config_file = self.config_dir / "security_config.json"
        self.config_dir.mkdir(exist_ok=True)
        
        # Initialize default configuration
        self.default_config = {
            "authentication": {
                "local_enabled": True,
                "ad_enabled": False,
                "okta_enabled": False,
                "mfa_enabled": False
            },
            "active_directory": {
                "configured": False,
                "server": "",
                "domain": "",
                "base_dn": "",
                "service_account": "",
                "service_password_encrypted": "",
                "port": 389,
                "use_ssl": False,
                "user_attribute": "sAMAccountName",
                "group_attribute": "memberOf"
            },
            "okta": {
                "configured": False,
                "domain": "",
                "client_id": "",
                "client_secret_encrypted": "",
                "authorization_server": "",
                "redirect_uri": "",
                "scopes": ["openid", "profile", "email", "groups"]
            },
            "mfa": {
                "configured": False,
                "totp_enabled": False,
                "email_enabled": False,
                "sms_enabled": False,
                "email_smtp_server": "",
                "email_smtp_port": 587,
                "email_username": "",
                "email_password_encrypted": "",
                "sms_provider": "",
                "sms_api_key_encrypted": "",
                "sms_api_secret_encrypted": ""
            },
            "security_policies": {
                "password_min_length": 8,
                "password_require_uppercase": True,
                "password_require_lowercase": True,
                "password_require_numbers": True,
                "password_require_symbols": False,
                "max_login_attempts": 5,
                "lockout_duration_minutes": 30,
                "session_timeout_minutes": 480,
                "require_mfa_for_admin": True
            },
            "last_updated": None,
            "updated_by": None
        }
    
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file"""
        if not self.config_file.exists():
            return self.default_config.copy()
        
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
            
            # Merge with defaults to ensure all keys exist
            merged_config = self.default_config.copy()
            self._deep_merge(merged_config, config)
            return merged_config
        except Exception as e:
            logger.error(f"Error loading security configuration: {str(e)}")
            return self.default_config.copy()
    
    def save_config(self, config: Dict[str, Any], updated_by: str = "admin") -> bool:
        """Save configuration to file"""
        try:
            config["last_updated"] = datetime.now().isoformat()
            config["updated_by"] = updated_by
            
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
            
            return True
        except Exception as e:
            logger.error(f"Error saving security configuration: {str(e)}")
            return False
    
    def _deep_merge(self, target: Dict, source: Dict):
        """Deep merge source dict into target dict"""
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._deep_merge(target[key], value)
            else:
                target[key] = value
    
    def encrypt_and_store_credential(self, config: Dict[str, Any], 
                                   section: str, field: str, value: str):
        """Encrypt and store a credential"""
        encrypted_value = credential_manager.encrypt_string(value)
        config[section][f"{field}_encrypted"] = encrypted_value
    
    def decrypt_credential(self, config: Dict[str, Any], 
                          section: str, field: str) -> Optional[str]:
        """Decrypt a stored credential"""
        encrypted_field = f"{field}_encrypted"
        if encrypted_field in config[section]:
            try:
                return credential_manager.decrypt_string(config[section][encrypted_field])
            except Exception:
                return None
        return None
    
    def test_ad_connection(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Test Active Directory connection"""
        try:
            from ldap3 import Server, Connection, ALL, NTLM
            
            ad_config = config["active_directory"]
            server_url = f"{'ldaps' if ad_config['use_ssl'] else 'ldap'}://{ad_config['server']}:{ad_config['port']}"
            
            server = Server(server_url, get_info=ALL)
            
            # Get decrypted password
            password = self.decrypt_credential(config, "active_directory", "service_password")
            if not password:
                return {"success": False, "error": "Service password not configured"}
            
            # Test connection
            conn = Connection(
                server,
                user=f"{ad_config['domain']}\\{ad_config['service_account']}",
                password=password,
                authentication=NTLM,
                auto_bind=True
            )
            
            # Test search
            conn.search(
                search_base=ad_config['base_dn'],
                search_filter='(objectClass=user)',
                size_limit=1
            )
            
            conn.unbind()
            
            return {
                "success": True,
                "message": "Successfully connected to Active Directory",
                "server_info": str(server.info)
            }
            
        except ImportError:
            return {"success": False, "error": "ldap3 library not installed. Run: pip install ldap3"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def test_okta_connection(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Test Okta connection"""
        try:
            import requests
            
            okta_config = config["okta"]
            
            # Get decrypted client secret
            client_secret = self.decrypt_credential(config, "okta", "client_secret")
            if not client_secret:
                return {"success": False, "error": "Client secret not configured"}
            
            # Test Okta well-known endpoint
            well_known_url = f"https://{okta_config['domain']}/.well-known/openid_configuration"
            
            response = requests.get(well_known_url, timeout=10)
            response.raise_for_status()
            
            well_known = response.json()
            
            return {
                "success": True,
                "message": "Successfully connected to Okta",
                "issuer": well_known.get("issuer"),
                "authorization_endpoint": well_known.get("authorization_endpoint")
            }
            
        except ImportError:
            return {"success": False, "error": "requests library not available"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def test_email_mfa(self, config: Dict[str, Any], test_email: str) -> Dict[str, Any]:
        """Test email MFA configuration"""
        try:
            import smtplib
            from email.mime.text import MimeText
            
            mfa_config = config["mfa"]
            
            # Get decrypted password
            password = self.decrypt_credential(config, "mfa", "email_password")
            if not password:
                return {"success": False, "error": "Email password not configured"}
            
            # Test SMTP connection
            server = smtplib.SMTP(mfa_config["email_smtp_server"], mfa_config["email_smtp_port"])
            server.starttls()
            server.login(mfa_config["email_username"], password)
            
            # Send test email
            msg = MimeText("VaultMind MFA test email - configuration successful!")
            msg['Subject'] = "VaultMind MFA Test"
            msg['From'] = mfa_config["email_username"]
            msg['To'] = test_email
            
            server.send_message(msg)
            server.quit()
            
            return {
                "success": True,
                "message": f"Test email sent successfully to {test_email}"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}

# Global instance
security_config_manager = SecurityConfigManager()
