# 📱 VaultMind Push Notification Setup Guide
## Complete Guide to Mobile & Desktop Notifications

---

## 🎯 Overview

VaultMind now supports push notifications to your phone and other devices through multiple channels:

- 📱 **Mobile Push** (Firebase, OneSignal, Pushover)
- 📧 **Email** (SMTP)
- 💬 **SMS** (Twilio)
- 🤖 **Telegram** Bot
- 💼 **Slack** Webhooks
- 🏢 **Microsoft Teams** Webhooks

---

## 🚀 Quick Start (Easiest Option: Pushover)

### Why Pushover?
- ✅ Easiest to set up (5 minutes)
- ✅ Works on iOS and Android
- ✅ No coding required
- ✅ One-time $5 purchase (no subscription)
- ✅ Perfect for personal use

### Setup Steps

#### 1. Install Pushover App
- **iOS:** https://apps.apple.com/us/app/pushover-notifications/id506088175
- **Android:** https://play.google.com/store/apps/details?id=net.superblock.pushover

#### 2. Create Pushover Account
- Go to https://pushover.net
- Sign up for free account
- Note your **User Key** from dashboard

#### 3. Create Application
- Go to https://pushover.net/apps/build
- Create new application named "VaultMind"
- Note your **API Token**

#### 4. Configure VaultMind
```bash
# Edit config/notifications.env
PUSHOVER_ENABLED=true
PUSHOVER_USER_KEY=your_user_key_here
PUSHOVER_API_TOKEN=your_api_token_here
```

#### 5. Test Notification
```python
from utils.notification_manager import send_push_notification

send_push_notification(
    title="VaultMind Test",
    message="Push notifications are working! 🎉"
)
```

**Done!** You'll receive notifications on your phone. ✅

---

## 📱 Mobile Push Options Comparison

| Service | Cost | Setup Difficulty | Platforms | Best For |
|---------|------|------------------|-----------|----------|
| **Pushover** | $5 one-time | ⭐ Easy | iOS, Android | Personal use |
| **Firebase (FCM)** | Free | ⭐⭐⭐ Hard | iOS, Android | Production apps |
| **OneSignal** | Free | ⭐⭐ Medium | iOS, Android, Web | Multi-platform |

---

## 🔥 Option 1: Firebase Cloud Messaging (FCM)

### Best For
- Production mobile apps
- Large user base
- Free unlimited notifications

### Setup Steps

#### 1. Create Firebase Project
1. Go to https://console.firebase.google.com
2. Click "Add project"
3. Name it "VaultMind"
4. Follow setup wizard

#### 2. Get Server Key
1. In Firebase Console, go to Project Settings
2. Click "Cloud Messaging" tab
3. Copy "Server key"

#### 3. Configure VaultMind
```bash
# config/notifications.env
FCM_ENABLED=true
FCM_SERVER_KEY=your_firebase_server_key
```

#### 4. Get Device Tokens
You need to implement FCM in your mobile app to get device tokens.

**Android Example:**
```java
FirebaseMessaging.getInstance().getToken()
    .addOnCompleteListener(task -> {
        if (task.isSuccessful()) {
            String token = task.getResult();
            // Send this token to VaultMind backend
        }
    });
```

**iOS Example:**
```swift
Messaging.messaging().token { token, error in
    if let token = token {
        // Send this token to VaultMind backend
    }
}
```

#### 5. Send Notification
```python
from utils.notification_manager import notification_manager

notification_manager.send_notification(
    title="Query Complete",
    message="Your search returned 15 results",
    device_tokens=["device_token_1", "device_token_2"],
    channels=['fcm']
)
```

---

## 🎯 Option 2: OneSignal

### Best For
- Web + mobile notifications
- Easy setup
- Free tier available

### Setup Steps

#### 1. Create OneSignal Account
1. Go to https://onesignal.com
2. Sign up for free account
3. Create new app

#### 2. Get Credentials
1. Go to Settings > Keys & IDs
2. Copy "OneSignal App ID"
3. Copy "REST API Key"

#### 3. Configure VaultMind
```bash
# config/notifications.env
ONESIGNAL_ENABLED=true
ONESIGNAL_APP_ID=your_app_id
ONESIGNAL_API_KEY=your_api_key
```

#### 4. Add OneSignal SDK to Your App
Follow OneSignal documentation for your platform:
- **Web:** https://documentation.onesignal.com/docs/web-push-quickstart
- **iOS:** https://documentation.onesignal.com/docs/ios-sdk-setup
- **Android:** https://documentation.onesignal.com/docs/android-sdk-setup

#### 5. Send Notification
```python
notification_manager.send_notification(
    title="Document Processed",
    message="Your PDF has been indexed",
    device_tokens=["player_id_1", "player_id_2"],
    channels=['onesignal']
)
```

---

## 💬 SMS Notifications (Twilio)

### Setup Steps

#### 1. Create Twilio Account
1. Go to https://www.twilio.com
2. Sign up (free trial includes $15 credit)
3. Get a phone number

#### 2. Get Credentials
1. Go to Console Dashboard
2. Copy "Account SID"
3. Copy "Auth Token"
4. Note your Twilio phone number

#### 3. Install Twilio SDK
```bash
pip install twilio
```

#### 4. Configure VaultMind
```bash
# config/notifications.env
TWILIO_ENABLED=true
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_FROM_NUMBER=+1234567890
```

#### 5. Send SMS
```python
from utils.notification_manager import send_sms_notification

send_sms_notification(
    phone_number="+1234567890",
    message="Your VaultMind query is complete!"
)
```

---

## 📧 Email Notifications

### Setup with Gmail

#### 1. Enable App Passwords
1. Go to Google Account settings
2. Security > 2-Step Verification
3. App passwords > Generate
4. Copy the 16-character password

#### 2. Configure VaultMind
```bash
# config/notifications.env
EMAIL_NOTIFICATIONS_ENABLED=true
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_16_char_app_password
FROM_EMAIL=noreply@vaultmind.ai
```

#### 3. Send Email
```python
from utils.notification_manager import send_email_notification

send_email_notification(
    email="user@example.com",
    title="Query Complete",
    message="Your search returned 15 results with 95% confidence."
)
```

---

## 🤖 Telegram Bot Notifications

### Setup Steps

#### 1. Create Telegram Bot
1. Open Telegram app
2. Search for "@BotFather"
3. Send `/newbot` command
4. Follow instructions
5. Copy your bot token

#### 2. Get Your Chat ID
1. Send a message to your bot
2. Visit: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
3. Find your "chat_id" in the response

#### 3. Configure VaultMind
```bash
# config/notifications.env
TELEGRAM_ENABLED=true
TELEGRAM_BOT_TOKEN=your_bot_token
```

#### 4. Send Notification
```python
notification_manager.send_notification(
    title="VaultMind Alert",
    message="Your document has been processed!",
    telegram_chat_id="your_chat_id",
    channels=['telegram']
)
```

---

## 💼 Slack Notifications

### Setup Steps

#### 1. Create Slack Webhook
1. Go to https://api.slack.com/apps
2. Create new app
3. Enable "Incoming Webhooks"
4. Add webhook to workspace
5. Copy webhook URL

#### 2. Configure VaultMind
```bash
# config/notifications.env
SLACK_ENABLED=true
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

#### 3. Send Notification
```python
notification_manager.send_notification(
    title="Query Complete",
    message="Search returned 15 results",
    channels=['slack']
)
```

---

## 🏢 Microsoft Teams Notifications

### Setup Steps

#### 1. Create Teams Webhook
1. Open Microsoft Teams
2. Go to channel > Connectors
3. Add "Incoming Webhook"
4. Name it "VaultMind"
5. Copy webhook URL

#### 2. Configure VaultMind
```bash
# config/notifications.env
TEAMS_ENABLED=true
TEAMS_WEBHOOK_URL=https://outlook.office.com/webhook/YOUR/WEBHOOK/URL
```

#### 3. Send Notification
```python
notification_manager.send_notification(
    title="Document Processed",
    message="PDF indexed successfully",
    channels=['teams']
)
```

---

## 🔧 Integration with VaultMind

### 1. Update Query Assistant

```python
# tabs/query_assistant.py

from utils.notification_manager import notification_manager, NotificationType

def handle_query(query, index, user_info):
    # Perform search
    results = search_documents(query, index)
    
    # Send notification
    if user_info.get('device_tokens'):
        notification_manager.notify_query_complete(
            user_id=user_info['user_id'],
            query=query,
            results_count=len(results),
            device_tokens=user_info['device_tokens'],
            phone_number=user_info.get('phone_number'),
            email=user_info.get('email')
        )
    
    return results
```

### 2. Update Document Ingestion

```python
# tabs/document_ingestion.py

from utils.notification_manager import notification_manager

def process_document(file, index_name, user_info):
    # Process document
    chunks = ingest_document(file, index_name)
    
    # Send notification
    notification_manager.notify_document_processed(
        user_id=user_info['user_id'],
        document_name=file.name,
        chunks_count=len(chunks),
        device_tokens=user_info.get('device_tokens'),
        email=user_info.get('email')
    )
    
    return chunks
```

### 3. Add User Notification Preferences

```python
# app/auth/user_preferences.py

class UserPreferences:
    def __init__(self, user_id):
        self.user_id = user_id
        self.preferences = self.load_preferences()
    
    def get_notification_settings(self):
        return {
            'device_tokens': self.preferences.get('device_tokens', []),
            'phone_number': self.preferences.get('phone_number'),
            'email': self.preferences.get('email'),
            'enabled_channels': self.preferences.get('channels', ['pushover', 'email']),
            'notify_on_query': self.preferences.get('notify_on_query', True),
            'notify_on_document': self.preferences.get('notify_on_document', True)
        }
```

### 4. Add Settings UI (Streamlit)

```python
# tabs/user_settings.py

import streamlit as st
from utils.notification_manager import notification_manager

def render_notification_settings():
    st.header("📱 Notification Settings")
    
    # Enable/disable notifications
    enable_notifications = st.checkbox(
        "Enable Push Notifications",
        value=True
    )
    
    if enable_notifications:
        # Select channels
        st.subheader("Notification Channels")
        
        col1, col2 = st.columns(2)
        
        with col1:
            enable_push = st.checkbox("📱 Mobile Push", value=True)
            enable_email = st.checkbox("📧 Email", value=True)
            enable_sms = st.checkbox("💬 SMS", value=False)
        
        with col2:
            enable_telegram = st.checkbox("🤖 Telegram", value=False)
            enable_slack = st.checkbox("💼 Slack", value=False)
            enable_teams = st.checkbox("🏢 Teams", value=False)
        
        # Contact information
        st.subheader("Contact Information")
        
        email = st.text_input("Email Address", value="user@example.com")
        phone = st.text_input("Phone Number", value="+1234567890")
        telegram_id = st.text_input("Telegram Chat ID", value="")
        
        # Notification preferences
        st.subheader("Notify Me When")
        
        notify_query = st.checkbox("Query is complete", value=True)
        notify_document = st.checkbox("Document is processed", value=True)
        notify_mention = st.checkbox("Someone mentions me", value=True)
        notify_system = st.checkbox("System alerts", value=True)
        
        # Test notification
        if st.button("🧪 Send Test Notification"):
            result = notification_manager.send_notification(
                title="Test Notification",
                message="If you see this, notifications are working! 🎉",
                email=email if enable_email else None,
                phone_number=phone if enable_sms else None,
                telegram_chat_id=telegram_id if enable_telegram else None
            )
            
            st.success(f"Test notification sent! Results: {result}")
        
        # Save settings
        if st.button("💾 Save Settings", type="primary"):
            # Save to database
            st.success("Notification settings saved!")
```

---

## 📊 Notification Examples

### Query Complete
```python
notification_manager.notify_query_complete(
    user_id="user123",
    query="What are the governance powers?",
    results_count=15,
    device_tokens=["token1"],
    email="user@example.com"
)
```

### Document Processed
```python
notification_manager.notify_document_processed(
    user_id="user123",
    document_name="bylaws.pdf",
    chunks_count=186,
    device_tokens=["token1"],
    phone_number="+1234567890"
)
```

### System Alert
```python
notification_manager.notify_system_alert(
    title="System Maintenance",
    message="VaultMind will be offline for 30 minutes starting at 2 AM.",
    priority=NotificationPriority.HIGH,
    email="admin@company.com"
)
```

### Custom Notification
```python
notification_manager.send_notification(
    title="Custom Alert",
    message="Something important happened!",
    notification_type=NotificationType.INFO,
    priority=NotificationPriority.URGENT,
    device_tokens=["token1", "token2"],
    email="user@example.com",
    phone_number="+1234567890",
    data={"custom_field": "custom_value"}
)
```

---

## 🔒 Security Best Practices

### 1. Protect API Keys
```bash
# Never commit notifications.env to git
echo "config/notifications.env" >> .gitignore
```

### 2. Use Environment Variables
```python
import os
from dotenv import load_dotenv

load_dotenv('config/notifications.env')
```

### 3. Validate Phone Numbers
```python
import phonenumbers

def validate_phone(phone_number):
    try:
        parsed = phonenumbers.parse(phone_number, None)
        return phonenumbers.is_valid_number(parsed)
    except:
        return False
```

### 4. Rate Limiting
```python
from functools import lru_cache
from datetime import datetime, timedelta

class RateLimiter:
    def __init__(self, max_per_hour=10):
        self.max_per_hour = max_per_hour
        self.notifications = {}
    
    def can_send(self, user_id):
        now = datetime.now()
        hour_ago = now - timedelta(hours=1)
        
        # Clean old entries
        self.notifications[user_id] = [
            ts for ts in self.notifications.get(user_id, [])
            if ts > hour_ago
        ]
        
        # Check limit
        if len(self.notifications.get(user_id, [])) >= self.max_per_hour:
            return False
        
        # Add current notification
        if user_id not in self.notifications:
            self.notifications[user_id] = []
        self.notifications[user_id].append(now)
        
        return True
```

---

## 🧪 Testing

### Test Script
```python
# test_notifications.py

from utils.notification_manager import notification_manager, NotificationType, NotificationPriority

def test_all_channels():
    """Test all configured notification channels"""
    
    test_config = {
        'title': 'VaultMind Test',
        'message': 'Testing notification system 🧪',
        'notification_type': NotificationType.INFO,
        'priority': NotificationPriority.NORMAL
    }
    
    # Test mobile push
    if notification_manager.config['pushover']['enabled']:
        print("Testing Pushover...")
        result = notification_manager.send_notification(
            **test_config,
            channels=['pushover']
        )
        print(f"Pushover: {'✅ Success' if result.get('pushover') else '❌ Failed'}")
    
    # Test email
    if notification_manager.config['email']['enabled']:
        print("Testing Email...")
        result = notification_manager.send_notification(
            **test_config,
            email="test@example.com",
            channels=['email']
        )
        print(f"Email: {'✅ Success' if result.get('email') else '❌ Failed'}")
    
    # Test SMS
    if notification_manager.config['twilio']['enabled']:
        print("Testing SMS...")
        result = notification_manager.send_notification(
            **test_config,
            phone_number="+1234567890",
            channels=['twilio']
        )
        print(f"SMS: {'✅ Success' if result.get('twilio') else '❌ Failed'}")
    
    # Test Telegram
    if notification_manager.config['telegram']['enabled']:
        print("Testing Telegram...")
        result = notification_manager.send_notification(
            **test_config,
            telegram_chat_id="your_chat_id",
            channels=['telegram']
        )
        print(f"Telegram: {'✅ Success' if result.get('telegram') else '❌ Failed'}")

if __name__ == '__main__':
    test_all_channels()
```

Run test:
```bash
python test_notifications.py
```

---

## 📱 Mobile App Integration

### React Native Example
```javascript
// Install: npm install @react-native-firebase/messaging

import messaging from '@react-native-firebase/messaging';

// Request permission
async function requestUserPermission() {
  const authStatus = await messaging().requestPermission();
  const enabled =
    authStatus === messaging.AuthorizationStatus.AUTHORIZED ||
    authStatus === messaging.AuthorizationStatus.PROVISIONAL;

  if (enabled) {
    console.log('Authorization status:', authStatus);
    getFCMToken();
  }
}

// Get FCM token
async function getFCMToken() {
  const token = await messaging().getToken();
  console.log('FCM Token:', token);
  
  // Send token to VaultMind backend
  await fetch('https://your-vaultmind-api.com/api/register-device', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${userToken}`
    },
    body: JSON.stringify({
      device_token: token,
      platform: Platform.OS
    })
  });
}

// Handle foreground notifications
messaging().onMessage(async remoteMessage => {
  console.log('Notification received:', remoteMessage);
  // Show local notification
});
```

---

## 🎯 Best Practices

### 1. User Preferences
- Let users choose which notifications they want
- Allow channel selection (push, email, SMS)
- Respect quiet hours

### 2. Notification Content
- Keep titles short (< 50 characters)
- Make messages actionable
- Include relevant context
- Use appropriate priority levels

### 3. Frequency
- Don't spam users
- Batch related notifications
- Implement rate limiting
- Allow snooze/mute options

### 4. Testing
- Test on real devices
- Test all channels
- Verify delivery
- Monitor failure rates

---

## 🐛 Troubleshooting

### Pushover Not Working
```
Problem: No notifications received
Solution:
1. Check API token and user key
2. Verify app is installed on phone
3. Check phone notification settings
4. Test with curl:
   curl -s \
     --form-string "token=YOUR_API_TOKEN" \
     --form-string "user=YOUR_USER_KEY" \
     --form-string "message=test" \
     https://api.pushover.net/1/messages.json
```

### FCM Not Working
```
Problem: Device not receiving notifications
Solution:
1. Verify server key is correct
2. Check device token is valid
3. Ensure FCM is enabled in Firebase Console
4. Check device internet connection
5. Verify app has notification permissions
```

### Email Not Sending
```
Problem: SMTP authentication failed
Solution:
1. Use app-specific password (not account password)
2. Enable "Less secure app access" (Gmail)
3. Check SMTP server and port
4. Verify firewall allows SMTP traffic
```

---

## 📊 Monitoring & Analytics

### Track Notification Delivery
```python
# utils/notification_analytics.py

import sqlite3
from datetime import datetime

class NotificationAnalytics:
    def __init__(self):
        self.db_path = "data/notification_analytics.db"
        self._init_db()
    
    def log_notification(self, user_id, channel, success, notification_type):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO notification_log 
            (user_id, channel, success, notification_type, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, channel, success, notification_type, datetime.now()))
        
        conn.commit()
        conn.close()
    
    def get_delivery_rate(self, channel, days=7):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful
            FROM notification_log
            WHERE channel = ?
            AND timestamp > datetime('now', '-' || ? || ' days')
        """, (channel, days))
        
        result = cursor.fetchone()
        conn.close()
        
        if result[0] > 0:
            return (result[1] / result[0]) * 100
        return 0
```

---

## 🎉 You're All Set!

Your VaultMind instance now supports push notifications! Start with Pushover for the easiest setup, then add more channels as needed.

**Need help?** Check the troubleshooting section or contact support.

