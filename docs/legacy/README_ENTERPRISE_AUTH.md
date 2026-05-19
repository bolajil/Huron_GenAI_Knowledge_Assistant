# VaultMind Enterprise Authentication System

## Overview

VaultMind GenAI Knowledge Assistant now features a complete enterprise-grade authentication system with real backend integrations for Active Directory, Okta SSO, and Multi-Factor Authentication. This system removes all dummy data and placeholder implementations, providing production-ready security suitable for large corporations and government organizations.

## 🔐 Authentication Methods

### 1. Local Authentication
- **Username/Password** - Traditional local user database
- **Fallback Support** - Always available when enterprise auth fails
- **Role Management** - Admin, User, Viewer roles with permissions

### 2. Active Directory Integration
- **Real LDAP Authentication** - Connects to corporate AD servers
- **Group Mapping** - Automatic role assignment based on AD groups
- **SSL/TLS Support** - Secure LDAPS connections
- **Service Account** - Uses dedicated service account for group lookups

### 3. Okta SSO Integration
- **OAuth2 Flow** - Standard enterprise SSO implementation
- **SAML Support** - Compatible with Okta SAML configurations
- **Group Synchronization** - Maps Okta groups to VaultMind roles
- **Token Management** - Secure access token handling

## 🛡️ Multi-Factor Authentication

### TOTP (Time-based One-Time Password)
- **Authenticator Apps** - Google Authenticator, Authy, Microsoft Authenticator
- **QR Code Setup** - Easy enrollment process
- **Secret Storage** - Encrypted TOTP secrets per user

### Email Verification
- **SMTP Integration** - Real email delivery via configured SMTP server
- **Code Expiration** - 5-minute expiration for security
- **Template Support** - Customizable email templates

### SMS Verification
- **Twilio Integration** - Professional SMS delivery
- **AWS SNS Support** - Alternative SMS provider
- **International Support** - Global phone number support

## 🔧 Configuration Management

### Security Setup Dashboard
Access via **Admin Panel → Security Setup**

#### Active Directory Configuration
```
Server: your-ad-server.company.com
Port: 636 (LDAPS) or 389 (LDAP)
Domain: company.com
Base DN: DC=company,DC=com
Service Account: vaultmind-service@company.com
User Attribute: sAMAccountName
Group Attribute: memberOf
```

#### Okta SSO Configuration
```
Domain: your-company.okta.com
Client ID: [Your Okta App Client ID]
Client Secret: [Encrypted - Set via UI]
Authorization Server: default
Redirect URI: https://your-vaultmind.com/auth/callback
Scopes: openid, profile, email, groups
```

#### MFA Provider Setup
```
TOTP: Enabled by default
Email SMTP: Configure server, port, credentials
SMS Provider: Choose Twilio or AWS SNS
Enforcement: Configure per role (Admin/User/Viewer)
```

## 🚀 Deployment Instructions

### 1. Environment Variables
```bash
# Master encryption key
VAULTMIND_MASTER_KEY=your-secure-master-key

# OpenAI API (if using AI features)
OPENAI_API_KEY=your-openai-key

# Optional: Database connection
DATABASE_URL=postgresql://user:pass@host:port/db
```

### 2. Dependencies Installation
```bash
# Core enterprise auth dependencies
pip install ldap3 cryptography requests pyotp

# Optional MFA providers
pip install twilio boto3

# Email support
pip install smtplib email
```

### 3. Initial Setup
1. **Run VaultMind** - Start the application
2. **Login as Admin** - Use default admin credentials
3. **Access Security Setup** - Admin Panel → Security Setup
4. **Configure Providers** - Set up AD, Okta, and MFA as needed
5. **Test Connections** - Use built-in connection testing
6. **Enable MFA** - Configure enforcement policies

### 4. User Onboarding
1. **AD Users** - Automatic on first login
2. **Okta Users** - SSO redirect handles enrollment
3. **Local Users** - Manual creation via Admin Panel
4. **MFA Setup** - Users guided through setup on first MFA-required login

## 🔒 Security Features

### Encryption
- **Credential Storage** - All secrets encrypted with Fernet
- **Key Derivation** - PBKDF2 with salt for master key
- **Session Security** - Encrypted session tokens

### Account Protection
- **Failed Attempt Lockout** - Configurable attempts and duration
- **Session Timeout** - Automatic logout after inactivity
- **IP Tracking** - Real IP address logging
- **Audit Trail** - Complete authentication event logging

### Compliance
- **SOC2 Ready** - Audit logging and access controls
- **GDPR Compatible** - User data protection and privacy
- **HIPAA Considerations** - Healthcare data security features
- **FedRAMP Alignment** - Government security standards

## 📊 Monitoring & Analytics

### Authentication Events
- Login attempts (success/failure)
- MFA verification events
- Account lockouts
- Session management
- Configuration changes

### Security Dashboard
- Real-time authentication metrics
- Failed login monitoring
- Active session tracking
- Security alert management

## 🛠️ Troubleshooting

### Common Issues

#### Active Directory Connection Failed
1. Check server hostname and port
2. Verify SSL certificate if using LDAPS
3. Test service account credentials
4. Confirm firewall allows LDAP traffic

#### Okta SSO Not Working
1. Verify Okta app configuration
2. Check redirect URI matches exactly
3. Confirm client ID and secret
4. Test authorization server endpoint

#### MFA Code Not Received
1. **Email**: Check SMTP server settings and credentials
2. **SMS**: Verify provider API keys and phone number format
3. **TOTP**: Ensure time synchronization between server and device

#### User Cannot Access Features
1. Check role assignment in AD/Okta groups
2. Verify group mapping configuration
3. Review permission settings in Admin Panel

### Support Contacts
- **Technical Issues**: Contact your IT administrator
- **Access Problems**: Submit request via Admin Panel
- **Security Concerns**: Report immediately to security team

## 📈 Performance Optimization

### Caching
- **Group Lookups** - Cache AD group memberships
- **Session Data** - Efficient session storage
- **Configuration** - Cache auth provider settings

### Scaling
- **Load Balancing** - Multiple VaultMind instances
- **Database** - External database for user data
- **Redis** - Session and cache storage

## 🔄 Backup & Recovery

### Configuration Backup
- Export security configurations
- Backup encryption keys securely
- Document provider settings

### User Data
- Regular user database backups
- MFA secret recovery procedures
- Session data cleanup policies

## 📋 Compliance Checklist

- [ ] Master encryption key securely stored
- [ ] All provider credentials encrypted
- [ ] Audit logging enabled
- [ ] Failed attempt monitoring active
- [ ] Session timeout configured
- [ ] MFA enforcement policies set
- [ ] Regular security reviews scheduled
- [ ] Backup procedures tested
- [ ] Incident response plan ready
- [ ] User training completed

## 🆕 Version History

### v2.0 - Enterprise Authentication
- Real Active Directory integration
- Okta SSO implementation
- Multi-Factor Authentication
- Secure credential storage
- Configuration management UI
- Audit logging and monitoring

### v1.0 - Basic Authentication
- Local user management
- Simple role-based access
- Basic session handling

---

**VaultMind Enterprise Authentication System** - Production-ready security for enterprise deployment.
