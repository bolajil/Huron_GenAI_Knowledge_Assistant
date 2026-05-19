"""
Real MFA providers for VaultMind enterprise authentication
"""

import logging
import secrets
import time
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import hashlib
import hmac
import base64

logger = logging.getLogger(__name__)

# In-memory storage for MFA codes (in production, use Redis or database)
_mfa_code_storage: Dict[str, Dict[str, Any]] = {}

class MFAProviders:
    """Real MFA provider implementations"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.mfa_config = config.get("mfa", {})
    
    def generate_totp_secret(self, username: str) -> str:
        """Generate TOTP secret for user"""
        # Create a unique secret based on username and system key
        system_key = "vaultmind_totp_2024"  # In production, use secure random key
        combined = f"{username}:{system_key}:{secrets.token_hex(16)}"
        secret = base64.b32encode(combined.encode()).decode()[:32]
        return secret
    
    def generate_totp_qr_code(self, username: str, secret: str) -> str:
        """Generate QR code for TOTP setup"""
        try:
            import qrcode
            from io import BytesIO
            
            # TOTP URI format
            issuer = "VaultMind"
            totp_uri = f"otpauth://totp/{issuer}:{username}?secret={secret}&issuer={issuer}"
            
            # Generate QR code
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(totp_uri)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Convert to base64 for display
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            img_str = base64.b64encode(buffer.getvalue()).decode()
            
            return f"data:image/png;base64,{img_str}"
            
        except ImportError:
            return ""
        except Exception as e:
            logger.error(f"Error generating QR code: {str(e)}")
            return ""
    
    def verify_totp_code(self, secret: str, code: str, window: int = 1) -> bool:
        """Verify TOTP code"""
        try:
            import pyotp
            
            totp = pyotp.TOTP(secret)
            return totp.verify(code, valid_window=window)
            
        except ImportError:
            # Fallback implementation without pyotp
            return self._verify_totp_fallback(secret, code, window)
        except Exception:
            return False
    
    def _verify_totp_fallback(self, secret: str, code: str, window: int = 1) -> bool:
        """Fallback TOTP verification without pyotp"""
        try:
            # Simple time-based verification
            current_time = int(time.time() // 30)
            
            for i in range(-window, window + 1):
                time_step = current_time + i
                expected_code = self._generate_totp_code(secret, time_step)
                if expected_code == code:
                    return True
            
            return False
            
        except Exception:
            return False
    
    def _generate_totp_code(self, secret: str, time_step: int) -> str:
        """Generate TOTP code for given time step"""
        try:
            # Convert secret from base32
            key = base64.b32decode(secret.upper() + '=' * (8 - len(secret) % 8))
            
            # Convert time step to bytes
            time_bytes = time_step.to_bytes(8, byteorder='big')
            
            # Generate HMAC
            hmac_digest = hmac.new(key, time_bytes, hashlib.sha1).digest()
            
            # Dynamic truncation
            offset = hmac_digest[-1] & 0xf
            code = (
                (hmac_digest[offset] & 0x7f) << 24 |
                (hmac_digest[offset + 1] & 0xff) << 16 |
                (hmac_digest[offset + 2] & 0xff) << 8 |
                (hmac_digest[offset + 3] & 0xff)
            )
            
            # Return 6-digit code
            return str(code % 1000000).zfill(6)
            
        except Exception:
            return "000000"
    
    def send_email_code(self, email: str, code: str) -> bool:
        """Send MFA code via email"""
        if not self.mfa_config.get("email_enabled", False):
            return False
        
        try:
            import smtplib
            from email.mime.text import MimeText
            from email.mime.multipart import MimeMultipart
            from app.auth.config_manager import security_config_manager
            
            # Get email configuration
            smtp_server = self.mfa_config.get("email_smtp_server")
            smtp_port = self.mfa_config.get("email_smtp_port", 587)
            username = self.mfa_config.get("email_username")
            
            # Get decrypted password
            password = security_config_manager.decrypt_credential(
                self.config, "mfa", "email_password"
            )
            
            if not all([smtp_server, username, password]):
                return False
            
            # Create email message
            msg = MimeMultipart()
            msg['From'] = username
            msg['To'] = email
            msg['Subject'] = "VaultMind Security Code"
            
            body = f"""
            Your VaultMind security code is: {code}
            
            This code will expire in 5 minutes.
            
            If you did not request this code, please contact your administrator.
            
            Best regards,
            VaultMind Security Team
            """
            
            msg.attach(MimeText(body, 'plain'))
            
            # Send email
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(username, password)
            server.send_message(msg)
            server.quit()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {str(e)}")
            return False
    
    def send_sms_code(self, phone: str, code: str) -> bool:
        """Send MFA code via SMS"""
        if not self.mfa_config.get("sms_enabled", False):
            return False
        
        provider = self.mfa_config.get("sms_provider", "")
        
        if provider == "twilio":
            return self._send_twilio_sms(phone, code)
        elif provider == "aws_sns":
            return self._send_aws_sns_sms(phone, code)
        else:
            logger.error("SMS provider not configured")
            return False
    
    def _send_twilio_sms(self, phone: str, code: str) -> bool:
        """Send SMS via Twilio"""
        try:
            from twilio.rest import Client
            from app.auth.config_manager import security_config_manager
            
            # Get Twilio credentials
            account_sid = security_config_manager.decrypt_credential(
                self.config, "mfa", "sms_api_key"
            )
            auth_token = security_config_manager.decrypt_credential(
                self.config, "mfa", "sms_api_secret"
            )
            
            if not all([account_sid, auth_token]):
                return False
            
            client = Client(account_sid, auth_token)
            
            message = client.messages.create(
                body=f"Your VaultMind security code is: {code}",
                from_='+1234567890',  # Configure Twilio phone number
                to=phone
            )
            
            return message.sid is not None
            
        except ImportError:
            logger.error("Twilio library not installed. Run: pip install twilio")
            return False
        except Exception as e:
            logger.error(f"Failed to send SMS via Twilio: {str(e)}")
            return False
    
    def _send_aws_sns_sms(self, phone: str, code: str) -> bool:
        """Send SMS via AWS SNS"""
        try:
            import boto3
            from app.auth.config_manager import security_config_manager
            
            # Get AWS credentials
            access_key = security_config_manager.decrypt_credential(
                self.config, "mfa", "sms_api_key"
            )
            secret_key = security_config_manager.decrypt_credential(
                self.config, "mfa", "sms_api_secret"
            )
            
            if not all([access_key, secret_key]):
                return False
            
            sns = boto3.client(
                'sns',
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                region_name='us-east-1'  # Configure region
            )
            
            response = sns.publish(
                PhoneNumber=phone,
                Message=f"Your VaultMind security code is: {code}"
            )
            
            return response['ResponseMetadata']['HTTPStatusCode'] == 200
            
        except ImportError:
            logger.error("boto3 library not installed. Run: pip install boto3")
            return False
        except Exception as e:
            logger.error(f"Failed to send SMS via AWS SNS: {str(e)}")
            return False
    
    def generate_verification_code(self) -> str:
        """Generate 6-digit verification code"""
        return str(secrets.randbelow(1000000)).zfill(6)
    
    def store_verification_code(self, username: str, code: str, method: str):
        """Store verification code with expiration"""
        expiry = datetime.now() + timedelta(minutes=5)
        
        _mfa_code_storage[f"mfa_code_{username}_{method}"] = {
            "code": code,
            "expires_at": expiry.isoformat(),
            "attempts": 0
        }
    
    def verify_stored_code(self, username: str, code: str, method: str) -> bool:
        """Verify stored verification code"""
        key = f"mfa_code_{username}_{method}"
        stored_data = _mfa_code_storage.get(key)
        
        if not stored_data:
            return False
        
        # Check expiration
        expires_at = datetime.fromisoformat(stored_data["expires_at"])
        if datetime.now() > expires_at:
            # Clean up expired code
            if key in _mfa_code_storage:
                del _mfa_code_storage[key]
            return False
        
        # Check attempts
        if stored_data["attempts"] >= 3:
            return False
        
        # Verify code
        if stored_data["code"] == code:
            # Clean up used code
            if key in _mfa_code_storage:
                del _mfa_code_storage[key]
            return True
        else:
            # Increment attempts
            _mfa_code_storage[key]["attempts"] += 1
            return False
    
    def cleanup_expired_codes(self):
        """Clean up expired verification codes"""
        current_time = datetime.now()
        keys_to_delete = []
        
        for key in list(_mfa_code_storage.keys()):
            if key.startswith("mfa_code_"):
                stored_data = _mfa_code_storage[key]
                if isinstance(stored_data, dict) and "expires_at" in stored_data:
                    expires_at = datetime.fromisoformat(stored_data["expires_at"])
                    if current_time > expires_at:
                        keys_to_delete.append(key)
        
        for key in keys_to_delete:
            del _mfa_code_storage[key]

# Global MFA providers instance
mfa_providers = None

def get_mfa_providers(config: Dict[str, Any]) -> MFAProviders:
    """Get MFA providers instance with current config"""
    global mfa_providers
    mfa_providers = MFAProviders(config)
    return mfa_providers
