# 🚀 Start VaultMind with Automation

## Quick Start (30 seconds)

### Windows
```bash
start_with_automation.bat
```

### Linux/Mac
```bash
chmod +x start_with_automation.sh
./start_with_automation.sh
```

## What Gets Started

✅ **Automation System** (Background)
- Prometheus metrics server (Port 8000)
- Health monitoring agent
- Backup agent
- Metrics collection agent

✅ **Streamlit Dashboard** (Port 8501)
- All existing tabs
- New "System Monitoring" tab

## Access Points

- **Main Dashboard**: http://localhost:8501
- **Metrics Endpoint**: http://localhost:8000/metrics
- **Logs**: `logs/automation.log`

## First Time Setup

1. Install dependencies:
```bash
pip install -r requirements-automation.txt
```

2. Configure alerts (optional):
```bash
# Edit .env file
ALERT_EMAIL_ENABLED=true
SMTP_HOST=smtp.gmail.com
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-password
```

3. Start the system (see Quick Start above)

## Documentation

- **IMPLEMENTATION_COMPLETE.md** - Full implementation details
- **AUTOMATION_ROADMAP.md** - Complete automation plan
- **QUICK_START_AUTOMATION.md** - Quick setup guide

## Support

Questions? Check the documentation or contact: bolafiz2001@gmail.com
