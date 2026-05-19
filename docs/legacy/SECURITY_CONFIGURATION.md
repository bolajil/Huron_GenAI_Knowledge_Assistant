# VaultMind Security Configuration Guide

## 🔐 Enterprise Security Setup

This guide provides step-by-step instructions for configuring enterprise-grade authentication in VaultMind GenAI Knowledge Assistant.

## 📋 Pre-Configuration Checklist

- [ ] VaultMind application running
- [ ] Admin access credentials
- [ ] Active Directory server details (if using AD)
- [ ] Okta application configuration (if using SSO)
- [ ] SMTP server details (for email MFA)
- [ ] SMS provider credentials (for SMS MFA)
- [ ] SSL certificates installed
- [ ] Master encryption key generated

## 🚀 Initial Setup

### 1. Access Security Setup Dashboard

1. **Login as Administrator**
   - Use your admin credentials to access VaultMind
   - Navigate to **Admin Panel** tab
   - Click on **Security Setup** sub-tab

2. **Security Dashboard Overview**
   - View current authentication status
   - Check provider configuration status
   - Review security metrics

## 🏢 Active Directory Configuration

### 1. Prepare Active Directory

#### Create Service Account
```powershell
# On your AD server, create a dedicated service account
New-ADUser -Name "VaultMind-Service" `
           -UserPrincipalName "vaultmind-service@company.com" `
           -AccountPassword (ConvertTo-SecureString "SecurePassword123!" -AsPlainText -Force) `
           -Enabled $true `
           -PasswordNeverExpires $true `
           -Description "VaultMind GenAI Service Account"

# Grant necessary permissions
Add-ADGroupMember -Identity "Domain Users" -Members "VaultMind-Service"
```

#### Configure LDAPS (Recommended)
```bash
# Ensure LDAPS is enabled on your AD server
# Port 636 should be open and SSL certificate installed
```

### 2. Configure in VaultMind

1. **Access AD Configuration**
   - Go to Security Setup → Active Directory
   - Click "Configure Active Directory"

2. **Server Settings**
   ```
   Server: your-ad-server.company.com
   Port: 636 (LDAPS) or 389 (LDAP)
   Use SSL: ✓ (recommended)
   Domain: company.com
   ```

3. **Authentication Settings**
   ```
   Base DN: DC=company,DC=com
   User Attribute: sAMAccountName
   Group Attribute: memberOf
   ```

4. **Service Account**
   ```
   Service Account: vaultmind-service@company.com
   Password: [Enter securely - will be encrypted]
   ```

5. **Group Mapping**
   ```
   Admin Groups: Domain Admins, VaultMind Admins
   User Groups: VaultMind Users, Domain Users
   Viewer Groups: VaultMind Viewers, Read Only Users
   ```

6. **Test Connection**
   - Click "Test AD Connection"
   - Verify successful authentication
   - Test user lookup functionality

## 🔐 Okta SSO Configuration

### 1. Prepare Okta Application

#### Create Okta App Integration
1. **Login to Okta Admin Console**
2. **Create New App Integration**
   - Sign-in method: OIDC - OpenID Connect
   - Application type: Web Application

3. **App Integration Settings**
   ```
   App integration name: VaultMind GenAI
   Grant types: Authorization Code, Refresh Token
   Sign-in redirect URIs: https://your-vaultmind.com/auth/callback
   Sign-out redirect URIs: https://your-vaultmind.com/logout
   Controlled access: Allow everyone in your organization to access
   ```

4. **Note Configuration Details**
   - Client ID: [Copy this value]
   - Client Secret: [Copy this value]
   - Okta Domain: your-company.okta.com

### 2. Configure in VaultMind

1. **Access Okta Configuration**
   - Go to Security Setup → Okta SSO
   - Click "Configure Okta SSO"

2. **Basic Settings**
   ```
   Okta Domain: your-company.okta.com
   Client ID: [From Okta app configuration]
   Client Secret: [From Okta app - will be encrypted]
   ```

3. **OAuth Settings**
   ```
   Authorization Server: default
   Redirect URI: https://your-vaultmind.com/auth/callback
   Scopes: openid, profile, email, groups
   ```

4. **Group Mapping**
   ```
   Admin Groups: VaultMind_Admins, Administrators
   User Groups: VaultMind_Users, Everyone
   Viewer Groups: VaultMind_Viewers, ReadOnly
   ```

5. **Test Connection**
   - Click "Test Okta Connection"
   - Verify OAuth flow works
   - Test user information retrieval

## 📱 Multi-Factor Authentication Setup

### 1. TOTP (Authenticator Apps)

1. **Enable TOTP**
   - Go to Security Setup → MFA Configuration
   - Enable "TOTP Authentication"
   - Configure settings:
     ```
     Code Length: 6 digits
     Time Window: 30 seconds
     Allowed Drift: ±1 window
     ```

2. **User Enrollment**
   - Users will see QR code on first MFA-required login
   - Support Google Authenticator, Authy, Microsoft Authenticator
   - Backup codes generated automatically

### 2. Email MFA

1. **Configure SMTP Server**
   ```
   SMTP Server: smtp.gmail.com
   Port: 587
   Security: TLS
   Username: noreply@your-company.com
   Password: [App password - will be encrypted]
   ```

2. **Email Settings**
   ```
   From Address: noreply@your-company.com
   From Name: VaultMind Security
   Subject: VaultMind Security Code
   Code Expiration: 5 minutes
   ```

3. **Test Email Delivery**
   - Click "Send Test Email"
   - Verify email delivery and formatting

### 3. SMS MFA

#### Option A: Twilio Configuration
1. **Twilio Account Setup**
   - Create Twilio account
   - Purchase phone number
   - Get Account SID and Auth Token

2. **Configure in VaultMind**
   ```
   Provider: Twilio
   Account SID: [From Twilio console]
   Auth Token: [From Twilio console - will be encrypted]
   From Number: +1234567890
   ```

#### Option B: AWS SNS Configuration
1. **AWS Setup**
   - Create AWS account
   - Enable SNS service
   - Create IAM user with SNS permissions

2. **Configure in VaultMind**
   ```
   Provider: AWS SNS
   Access Key ID: [From AWS IAM]
   Secret Access Key: [From AWS IAM - will be encrypted]
   Region: us-east-1
   ```

3. **Test SMS Delivery**
   - Click "Send Test SMS"
   - Verify SMS delivery to test number

## ⚙️ Security Policies Configuration

### 1. Password Policies

```
Minimum Length: 12 characters
Require Uppercase: ✓
Require Lowercase: ✓
Require Numbers: ✓
Require Special Characters: ✓
Password History: 5 passwords
Maximum Age: 90 days
```

### 2. Session Management

```
Session Timeout: 8 hours
Idle Timeout: 30 minutes
Remember Me Duration: 30 days
Concurrent Sessions: 3 per user
```

### 3. Account Lockout

```
Failed Attempts Threshold: 5 attempts
Lockout Duration: 30 minutes
Progressive Delays: ✓
Admin Override: ✓
```

### 4. MFA Enforcement

```
Admin Users: Required
Regular Users: Optional (configurable)
Viewer Users: Optional
Trusted Devices: 30 days
```

## 🔍 Testing Authentication Flow

### 1. Local Authentication Test
1. Create test user account
2. Login with username/password
3. Verify role assignment
4. Test MFA flow (if enabled)

### 2. Active Directory Test
1. Use existing AD user account
2. Login with domain credentials
3. Verify group mapping to roles
4. Test MFA integration

### 3. Okta SSO Test
1. Access VaultMind login page
2. Click "Login with Okta"
3. Complete OAuth flow
4. Verify user information sync

## 📊 Monitoring & Auditing

### 1. Authentication Logs
- Login attempts (success/failure)
- MFA verification events
- Account lockouts
- Configuration changes

### 2. Security Metrics
- Authentication success rates
- Failed login patterns
- MFA adoption rates
- Session duration analytics

### 3. Alert Configuration
- Multiple failed logins
- Unusual login patterns
- Configuration changes
- System errors

## 🛠️ Troubleshooting

### Common Issues

#### Active Directory Connection Failed
**Symptoms:** "AD authentication error" messages
**Solutions:**
1. Verify server hostname and port
2. Check SSL certificate validity
3. Test service account credentials
4. Confirm firewall allows LDAP traffic
5. Validate Base DN format

#### Okta SSO Not Working
**Symptoms:** OAuth flow fails or user info not retrieved
**Solutions:**
1. Verify Okta app configuration
2. Check redirect URI matches exactly
3. Confirm client ID and secret
4. Test authorization server endpoint
5. Review group assignments in Okta

#### MFA Codes Not Received
**Email MFA Issues:**
1. Check SMTP server settings
2. Verify email credentials
3. Test with different email provider
4. Check spam/junk folders

**SMS MFA Issues:**
1. Verify provider API credentials
2. Check phone number format (+1234567890)
3. Test with different phone number
4. Review provider account balance

#### User Access Issues
**Symptoms:** User cannot access certain features
**Solutions:**
1. Check role assignment in AD/Okta groups
2. Verify group mapping configuration
3. Review permission settings
4. Test with different user account

### Debug Mode
Enable debug logging for detailed troubleshooting:
```python
# In .env file
DEBUG=True
LOG_LEVEL=DEBUG
```

## 🔒 Security Best Practices

### 1. Credential Management
- Use strong, unique passwords
- Rotate service account passwords regularly
- Store secrets in encrypted configuration
- Use environment variables for sensitive data

### 2. Network Security
- Enable HTTPS/SSL for all connections
- Use LDAPS instead of plain LDAP
- Implement firewall rules
- Monitor network traffic

### 3. Access Control
- Follow principle of least privilege
- Regular access reviews
- Disable unused accounts
- Monitor privileged access

### 4. Monitoring
- Enable comprehensive logging
- Set up security alerts
- Regular security assessments
- Incident response procedures

## 📅 Maintenance Schedule

### Daily
- Review authentication logs
- Monitor failed login attempts
- Check system health

### Weekly
- Review user access patterns
- Update security configurations
- Test backup procedures

### Monthly
- Security configuration audit
- User access review
- Update dependencies
- Performance optimization

### Quarterly
- Full security assessment
- Disaster recovery testing
- Policy review and updates
- Training updates

---

**Security Configuration Complete** - Your VaultMind installation now has enterprise-grade authentication with comprehensive security controls.
