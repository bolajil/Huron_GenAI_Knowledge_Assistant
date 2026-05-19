# 🔄 How to Restart Streamlit Properly

## The Issue
Streamlit is caching the old health checker code. You need to do a **complete restart** to load the new code.

## Quick Fix (Choose One)

### Option 1: Use Restart Script (Easiest)
```bash
restart_streamlit.bat
```
This will:
- Stop all Streamlit processes
- Clear Python cache
- Start fresh

### Option 2: Manual Restart
1. **Stop Streamlit completely**:
   - Press `Ctrl+C` in the terminal
   - Wait for it to fully stop
   - Close the terminal window

2. **Clear Python cache**:
   ```bash
   # Delete cache folders
   rmdir /s /q __pycache__
   rmdir /s /q utils\__pycache__
   rmdir /s /q tabs\__pycache__
   ```

3. **Start fresh**:
   ```bash
   # Open NEW terminal
   streamlit run genai_dashboard_modular.py
   ```

### Option 3: Use Clear Cache Button
1. Go to System Monitoring tab
2. Click **🔄 Clear Cache** button (top right)
3. Page will reload with fresh code

## What Changed

The system now uses:
- ✅ `simple_health_checks.py` - No Prometheus dependency
- ✅ Auto-reload on import
- ✅ Clear cache button in UI

## Verify It's Working

After restart, you should see:
- ✅ No error messages in "Component Health Checks"
- ✅ Health status for each component
- ✅ Green/Yellow/Red status indicators
- ✅ Expandable details for each component

## If Still Not Working

1. **Check the file exists**:
   ```bash
   dir utils\monitoring\simple_health_checks.py
   ```
   Should show the file

2. **Force Python to reload**:
   ```bash
   # Delete ALL cache
   del /s /q *.pyc
   rmdir /s /q __pycache__
   ```

3. **Restart from scratch**:
   ```bash
   # Kill all Python processes
   taskkill /F /IM python.exe
   
   # Wait 5 seconds
   timeout /t 5
   
   # Start fresh
   streamlit run genai_dashboard_modular.py
   ```

## Expected Result

After proper restart:

### Component Health Checks Tab Should Show:
```
✅ WEAVIATE
Status: HEALTHY or UNHEALTHY
Message: Connection status
Details: URL, collections

⚠️ FAISS  
Status: HEALTHY or DEGRADED
Message: Index count
Details: Available indexes

⚠️ REDIS
Status: DEGRADED (optional)
Message: Redis not available
Details: Note about optional service

⚠️ CELERY
Status: DEGRADED (optional)
Message: No workers
Details: Start command

✅ DISK_SPACE
Status: HEALTHY
Message: XX% free
Details: Total, used, free GB

⚠️ MEMORY
Status: DEGRADED or HEALTHY
Message: XX% available
Details: Total, available GB
```

## Still Getting Errors?

If you still see the Prometheus error after restart:

1. **Check which file is being imported**:
   - The error means it's still using `health_checks.py` instead of `simple_health_checks.py`

2. **Verify the import in system_monitoring.py**:
   ```python
   # Should be:
   from utils.monitoring.simple_health_checks import simple_health_checker
   
   # NOT:
   from utils.monitoring.health_checks import health_checker
   ```

3. **Contact for help** if issue persists

---

**TL;DR**: Run `restart_streamlit.bat` or do a complete Streamlit restart to load the new code!
