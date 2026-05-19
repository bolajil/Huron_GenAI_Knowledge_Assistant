# 🚀 Quick Start: Push Notifications in 5 Minutes
## Get notifications on your phone RIGHT NOW

---

## ⚡ Fastest Setup: Pushover (Recommended)

### Why Pushover?
- ✅ **5 minutes** to set up
- ✅ **$5 one-time** payment (no subscription)
- ✅ Works on **iOS & Android**
- ✅ **No coding** required
- ✅ **Instant** notifications

---

## 📱 Step-by-Step Setup

### Step 1: Install Pushover App (2 minutes)

**iPhone:**
1. Open App Store
2. Search "Pushover"
3. Install the app ($5 one-time purchase)

**Android:**
1. Open Google Play Store
2. Search "Pushover Notifications"
3. Install the app ($5 one-time purchase)

---

### Step 2: Get Your Credentials (2 minutes)

1. **Create Account:**
   - Go to https://pushover.net
   - Click "Sign Up"
   - Create free account
   - Login

2. **Get User Key:**
   - You'll see your **User Key** on the dashboard
   - Copy it (looks like: `uQiRzpo4DXghDmr9QzzfQu27cmVRsG`)

3. **Create Application:**
   - Go to https://pushover.net/apps/build
   - Click "Create an Application/API Token"
   - Name: `VaultMind`
   - Description: `VaultMind notifications`
   - Click "Create Application"
   - Copy your **API Token** (looks like: `azGDORePK8gMaC0QOYAMyEEuzJnyUi`)

---

### Step 3: Configure VaultMind (1 minute)

1. **Create config file:**
```bash
# Navigate to your VaultMind directory
cd c:\Users\bolaf\VoultMIND_lanre\genai-knowledge-assistant

# Create notifications.env file
notepad config\notifications.env
```

2. **Add your credentials:**
```bash
# Paste this into notifications.env
PUSHOVER_ENABLED=true
PUSHOVER_USER_KEY=uQiRzpo4DXghDmr9QzzfQu27cmVRsG
PUSHOVER_API_TOKEN=azGDORePK8gMaC0QOYAMyEEuzJnyUi
```

3. **Save and close**

---

### Step 4: Test It! (30 seconds)

**Option A: Python Script**
```python
# test_notification.py
from utils.notification_manager import send_push_notification

send_push_notification(
    title="VaultMind Test",
    message="Push notifications are working! 🎉"
)

print("✅ Notification sent! Check your phone.")
```

Run it:
```bash
python test_notification.py
```

**Option B: Quick Test in Python Console**
```python
python
>>> from utils.notification_manager import send_push_notification
>>> send_push_notification("Test", "Hello from VaultMind!")
>>> exit()
```

---

## 🎉 Done! You'll receive a notification on your phone!

---

## 🔧 Add to Your Tabs

### Query Assistant
```python
# In tabs/query_assistant.py

from utils.notification_manager import notification_manager

# After search completes
notification_manager.notify_query_complete(
    user_id=st.session_state.user['username'],
    query=query,
    results_count=len(results)
)
```

### Document Ingestion
```python
# In tabs/document_ingestion.py

from utils.notification_manager import notification_manager

# After document is processed
notification_manager.notify_document_processed(
    user_id=st.session_state.user['username'],
    document_name=uploaded_file.name,
    chunks_count=chunks
)
```

---

## 📊 What You Can Do Now

### 1. Get notified when queries complete
```python
notification_manager.notify_query_complete(
    user_id="john",
    query="What are the governance powers?",
    results_count=15
)
```

### 2. Get notified when documents are processed
```python
notification_manager.notify_document_processed(
    user_id="john",
    document_name="bylaws.pdf",
    chunks_count=186
)
```

### 3. Send custom notifications
```python
from utils.notification_manager import send_push_notification

send_push_notification(
    title="Custom Alert",
    message="Something important happened!"
)
```

### 4. Send urgent alerts
```python
from utils.notification_manager import notification_manager, NotificationPriority

notification_manager.send_notification(
    title="URGENT",
    message="System requires immediate attention!",
    priority=NotificationPriority.URGENT  # Bypasses quiet hours
)
```

---

## 🎨 Notification Types

Pushover supports different sounds and priorities:

```python
from utils.notification_manager import NotificationPriority

# Low priority (no sound)
priority=NotificationPriority.LOW

# Normal (default sound)
priority=NotificationPriority.NORMAL

# High priority (loud sound)
priority=NotificationPriority.HIGH

# Urgent (repeats until acknowledged)
priority=NotificationPriority.URGENT
```

---

## 🔔 Advanced: Add User Settings

Let users control their notifications:

```python
# In tabs/user_settings.py
import streamlit as st

st.title("📱 Notification Settings")

enable_notifications = st.checkbox("Enable push notifications", value=True)

if enable_notifications:
    notify_query = st.checkbox("Notify on query complete", value=True)
    notify_document = st.checkbox("Notify on document processed", value=True)
    
    if st.button("🧪 Test Notification"):
        from utils.notification_manager import send_push_notification
        send_push_notification("Test", "Notifications working!")
        st.success("Check your phone!")
```

---

## 🐛 Troubleshooting

### Not receiving notifications?

**1. Check Pushover app is installed**
- Open Pushover app on your phone
- You should see it in your app list

**2. Verify credentials**
```python
# Check if configured correctly
from utils.notification_manager import notification_manager

config = notification_manager.config['pushover']
print(f"Enabled: {config['enabled']}")
print(f"User Key: {config['user_key'][:10]}...")
print(f"API Token: {config['api_token'][:10]}...")
```

**3. Test with curl**
```bash
curl -s \
  --form-string "token=YOUR_API_TOKEN" \
  --form-string "user=YOUR_USER_KEY" \
  --form-string "message=test from curl" \
  https://api.pushover.net/1/messages.json
```

**4. Check phone settings**
- Settings > Notifications > Pushover
- Ensure notifications are enabled
- Check "Do Not Disturb" is off

**5. Check internet connection**
- Both your server and phone need internet
- Pushover works over WiFi and cellular

---

## 💡 Pro Tips

### 1. Different sounds for different events
```python
# In notification_manager.py, modify _send_pushover:
payload['sound'] = 'cosmic'  # See pushover.net/api#sounds
```

### 2. Add images to notifications
```python
# Pushover supports images
payload['attachment'] = image_url
```

### 3. Action buttons
```python
# Add URL to open when tapped
payload['url'] = 'https://your-vaultmind-instance.com/results'
payload['url_title'] = 'View Results'
```

### 4. Group notifications
```python
# Prevent notification spam
payload['tag'] = 'query_results'  # Replaces previous with same tag
```

---

## 🎯 Next Steps

### Want more notification options?

1. **Email** (Free, built-in)
   - See: PUSH_NOTIFICATION_SETUP.md > Email section
   - Setup time: 5 minutes

2. **SMS** (Twilio, pay per message)
   - See: PUSH_NOTIFICATION_SETUP.md > SMS section
   - Setup time: 10 minutes

3. **Telegram** (Free)
   - See: PUSH_NOTIFICATION_SETUP.md > Telegram section
   - Setup time: 5 minutes

4. **Slack/Teams** (Free for workspace)
   - See: PUSH_NOTIFICATION_SETUP.md > Slack/Teams section
   - Setup time: 5 minutes

---

## 📚 Full Documentation

For complete setup of all notification channels:
- **PUSH_NOTIFICATION_SETUP.md** - Complete guide
- **utils/notification_manager.py** - Full implementation
- **utils/notification_integration_example.py** - Code examples

---

## ✅ Checklist

- [ ] Pushover app installed on phone
- [ ] Pushover account created
- [ ] User Key copied
- [ ] API Token created and copied
- [ ] config/notifications.env file created
- [ ] Credentials added to config file
- [ ] Test notification sent
- [ ] Notification received on phone
- [ ] Integrated into Query Assistant
- [ ] Integrated into Document Ingestion

---

## 🎉 You're Done!

You now have push notifications working on your phone! 

Every time a query completes or a document is processed, you'll get a notification instantly.

**Questions?** Check PUSH_NOTIFICATION_SETUP.md for detailed troubleshooting.

