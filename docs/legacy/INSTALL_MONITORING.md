# Install System Monitoring Tab

## Quick Install (2 Steps)

### Step 1: Install Dependencies
```bash
pip install prometheus-client psutil
```

### Step 2: Restart Streamlit
```bash
# Stop current Streamlit (Ctrl+C)
# Then restart:
streamlit run genai_dashboard_modular.py
```

## What You'll See

After restarting, you'll see a new tab: **🔍 System Monitoring**

This tab includes:
- 📊 **Overview** - System health summary
- 💚 **Health Checks** - Component status (Weaviate, FAISS, Redis, Celery)
- 📈 **Metrics** - Performance metrics endpoint
- 🤖 **AI Agents** - Agent status (requires automation system)
- 💾 **Backups** - Backup management

## Optional: Full Automation System

For complete automation (AI agents, scheduled backups, alerts):

```bash
# Install all automation dependencies
pip install -r requirements-automation.txt

# Start automation system
python run_automation_system.py
```

This enables:
- Automated health monitoring
- Scheduled backups
- Performance metrics collection
- Proactive alerting

## Troubleshooting

**Tab not showing?**
1. Make sure you installed: `pip install prometheus-client psutil`
2. Restart Streamlit completely
3. Check you're logged in (tab is available to all authenticated users)

**Errors in the tab?**
- Some features require the automation system running
- Install optional dependencies: `pip install -r requirements-automation.txt`
- Check logs: `logs/automation.log`

## Need Help?

See `IMPLEMENTATION_COMPLETE.md` for full documentation.
