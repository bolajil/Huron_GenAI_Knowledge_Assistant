"""
Real Active Directory integration for VaultMind enterprise authentication
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class ActiveDirectoryConnector:
    """Real Active Directory authentication connector"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.ad_config = config.get("active_directory", {})
    
    def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate user against Active Directory"""
        if not self.ad_config.get("configured", False):
            return None
        
        try:
            from ldap3 import Server, Connection, ALL, NTLM, SIMPLE
            from ldap3.core.exceptions import LDAPException
            
            # Build server URL
            protocol = "ldaps" if self.ad_config.get("use_ssl", False) else "ldap"
            server_url = f"{protocol}://{self.ad_config['server']}:{self.ad_config['port']}"
            
            # Create server connection
            server = Server(server_url, get_info=ALL)
            
            # Try to bind with user credentials
            user_dn = f"{username}@{self.ad_config['domain']}"
            
            conn = Connection(
                server,
                user=user_dn,
                password=password,
                authentication=SIMPLE,
                auto_bind=True
            )
            
            # Search for user information
            search_filter = f"({self.ad_config['user_attribute']}={username})"
            conn.search(
                search_base=self.ad_config['base_dn'],
                search_filter=search_filter,
                attributes=['cn', 'mail', 'memberOf', 'displayName']
            )
            
            if not conn.entries:
                conn.unbind()
                return None
            
            user_entry = conn.entries[0]
            
            # Extract user information
            user_info = {
                'username': username,
                'email': str(user_entry.mail) if user_entry.mail else f"{username}@{self.ad_config['domain']}",
                'display_name': str(user_entry.displayName) if user_entry.displayName else username,
                'groups': [str(group) for group in user_entry.memberOf] if user_entry.memberOf else [],
                'auth_method': 'active_directory',
                'authenticated_at': datetime.now().isoformat()
            }
            
            conn.unbind()
            return user_info
            
        except ImportError:
            logger.error("ldap3 library not installed. Run: pip install ldap3")
            return None
        except LDAPException as e:
            logger.error(f"LDAP authentication failed: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"AD authentication error: {str(e)}")
            return None
    
    def get_user_groups(self, username: str) -> list:
        """Get user's AD groups for role mapping"""
        if not self.ad_config.get("configured", False):
            return []
        
        try:
            from ldap3 import Server, Connection, ALL, NTLM
            from app.auth.config_manager import security_config_manager
            
            # Use service account for group lookup
            protocol = "ldaps" if self.ad_config.get("use_ssl", False) else "ldap"
            server_url = f"{protocol}://{self.ad_config['server']}:{self.ad_config['port']}"
            
            server = Server(server_url, get_info=ALL)
            
            # Get service account password
            service_password = security_config_manager.decrypt_credential(
                self.config, "active_directory", "service_password"
            )
            
            if not service_password:
                return []
            
            conn = Connection(
                server,
                user=f"{self.ad_config['domain']}\\{self.ad_config['service_account']}",
                password=service_password,
                authentication=NTLM,
                auto_bind=True
            )
            
            # Search for user
            search_filter = f"({self.ad_config['user_attribute']}={username})"
            conn.search(
                search_base=self.ad_config['base_dn'],
                search_filter=search_filter,
                attributes=[self.ad_config['group_attribute']]
            )
            
            if conn.entries:
                groups = getattr(conn.entries[0], self.ad_config['group_attribute'], [])
                conn.unbind()
                return [str(group) for group in groups]
            
            conn.unbind()
            return []
            
        except Exception as e:
            logger.error(f"Error retrieving user groups: {str(e)}")
            return []
    
    def map_groups_to_role(self, groups: list) -> str:
        """Map AD groups to VaultMind roles"""
        # Define group to role mapping
        role_mappings = {
            'admin': ['Domain Admins', 'VaultMind Admins', 'IT Administrators'],
            'user': ['VaultMind Users', 'Domain Users', 'All Users'],
            'viewer': ['VaultMind Viewers', 'Read Only Users']
        }
        
        # Check for admin role first
        for group in groups:
            for admin_group in role_mappings['admin']:
                if admin_group.lower() in group.lower():
                    return 'admin'
        
        # Check for user role
        for group in groups:
            for user_group in role_mappings['user']:
                if user_group.lower() in group.lower():
                    return 'user'
        
        # Default to viewer
        return 'viewer'

# Global connector instance (will be initialized with config)
ad_connector = None

def get_ad_connector(config: Dict[str, Any]) -> ActiveDirectoryConnector:
    """Get AD connector instance with current config"""
    global ad_connector
    ad_connector = ActiveDirectoryConnector(config)
    return ad_connector
