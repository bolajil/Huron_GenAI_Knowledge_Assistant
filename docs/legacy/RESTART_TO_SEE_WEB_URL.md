# URGENT: Restart Required to See Website URL Option

## 🔴 Problem Identified

Your screenshot shows the **old version** of the code is still running. The Website URL option exists in the code but isn't showing because:

**The Streamlit app is running cached/old code and needs to be restarted.**

## ✅ Solution: Force Restart

### Method 1: Kill All Streamlit Processes (Recommended)

**In PowerShell:**
```powershell
# Stop all Streamlit processes
Get-Process streamlit -ErrorAction SilentlyContinue | Stop-Process -Force

# Stop all Python processes (be careful!)
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force

# Wait a moment
Start-Sleep -Seconds 2

# Restart
cd C:\Users\bolaf\VoultMIND_lanre\genai-knowledge-assistant
streamlit run genai_dashboard_modular.py
```

### Method 2: Task Manager

1. Press `Ctrl + Shift + Esc`
2. Find all **streamlit.exe** processes
3. Right-click → **End Task** on each
4. Find all **python.exe** processes
5. Right-click → **End Task** on each
6. Restart: `streamlit run genai_dashboard_modular.py`

### Method 3: Clear Cache and Restart

```powershell
# Clear Python cache
Remove-Item -Recurse -Force tabs\__pycache__
Remove-Item -Recurse -Force utils\__pycache__

# Clear Streamlit cache
Remove-Item -Recurse -Force .streamlit\cache

# Restart
streamlit run genai_dashboard_modular.py
```

## 🔍 Verify the Code is Correct

The code at line 447-450 in `tabs/document_ingestion_fixed.py` should show:

```python
source_type = st.selectbox(
    "Select Source Type:",
    ["PDF File", "Text File", "Website URL"],  # ← Website URL IS here!
    key="faiss_ingest_source_type"
)
```

**Check this now:**
```bash
cat tabs/document_ingestion_fixed.py | grep -A 3 "Select Source Type"
```

Expected output:
```
    "Select Source Type:",
    ["PDF File", "Text File", "Website URL"],
    key="faiss_ingest_source_type"
```

## 📊 What You Should See After Restart

### Before (Your Screenshot):
```
Document Source
Select Source Type:
[PDF File ▼]  ← Only shows PDF File
```

### After (Correct):
```
Document Source
Select Source Type:
[PDF File ▼]
Options:
- PDF File
- Text File
- Website URL  ← This should appear!
```

## ⚠️ Common Issues

### Issue 1: Multiple Streamlit Instances Running
**Symptom**: Changes don't appear even after restart
**Solution**: Kill ALL python/streamlit processes, not just one

### Issue 2: Browser Cache
**Symptom**: Old UI still showing
**Solution**: Hard refresh with `Ctrl + Shift + R` or `Ctrl + F5`

### Issue 3: Wrong File Being Used
**Symptom**: Changes in code don't reflect in UI
**Solution**: Verify `tabs/__init__.py` imports `document_ingestion_fixed.py`:
```python
from .document_ingestion_fixed import render_document_ingestion
```

### Issue 4: Python Bytecode Cache
**Symptom**: Old code still executing
**Solution**: Delete `__pycache__` folders:
```powershell
Get-ChildItem -Recurse -Filter "__pycache__" | Remove-Item -Recurse -Force
```

## 🚀 Step-by-Step Restart Process

1. **Stop the app**: Press `Ctrl + C` in terminal running Streamlit
2. **Kill processes**: Run PowerShell command above
3. **Clear cache**: Delete `__pycache__` folders
4. **Verify code**: Check line 449 has "Website URL"
5. **Restart**: `streamlit run genai_dashboard_modular.py`
6. **Hard refresh browser**: `Ctrl + Shift + R`
7. **Check**: Go to Document Ingestion → See Website URL option

## 📝 Quick Verification Script

Create `verify_web_url.py`:
```python
# Verify Website URL option exists in code
with open('tabs/document_ingestion_fixed.py', 'r') as f:
    content = f.read()
    if '"Website URL"' in content:
        print("✅ Website URL option EXISTS in code")
        # Count occurrences
        count = content.count('"Website URL"')
        print(f"   Found {count} occurrences")
    else:
        print("❌ Website URL option NOT FOUND in code")
```

Run: `python verify_web_url.py`

Expected output:
```
✅ Website URL option EXISTS in code
   Found 2 occurrences
```

## 🎯 Final Checklist

After restart, verify:
- [ ] Streamlit starts without errors
- [ ] Go to Document Ingestion tab
- [ ] See "Storage Backend" dropdown
- [ ] Select "FAISS (Local Index)"
- [ ] See "Document Source" section
- [ ] Click "Select Source Type" dropdown
- [ ] **See 3 options: PDF File, Text File, Website URL**

If you still don't see it after following ALL steps above, there may be a different issue.

---

**Status**: Code is correct, app needs restart
**Action**: Kill all Streamlit/Python processes and restart
**Expected**: Website URL option will appear in dropdown
