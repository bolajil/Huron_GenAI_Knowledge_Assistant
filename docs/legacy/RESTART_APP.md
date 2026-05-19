# How to Restart the App to See Changes

## Current Status
Your Streamlit app is running but hasn't loaded the new changes yet.

## Method 1: Restart from Terminal (Recommended)

### Step 1: Find the Terminal Running Streamlit
Look for the terminal window that shows:
```
You can now view your Streamlit app in your browser.
Local URL: http://localhost:8501
```

### Step 2: Stop the App
In that terminal:
- Press **`Ctrl + C`**
- Wait for it to stop completely

### Step 3: Start Again
```bash
streamlit run genai_dashboard_modular.py
```

### Step 4: Refresh Browser
- Go to: http://localhost:8501
- Press **`Ctrl + F5`** to hard refresh

## Method 2: Kill All Streamlit Processes (If Terminal is Lost)

### Option A: PowerShell Command
```powershell
# Stop all Streamlit processes
Get-Process streamlit -ErrorAction SilentlyContinue | Stop-Process -Force

# Stop all Python processes (be careful - this stops ALL Python)
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force

# Then restart
streamlit run genai_dashboard_modular.py
```

### Option B: Task Manager
1. Press **`Ctrl + Shift + Esc`**
2. Find "streamlit.exe" and "python.exe" processes
3. Right-click → End Task
4. Restart from terminal

## Method 3: Use Streamlit's Rerun Button

### In the Browser:
1. Go to your app: http://localhost:8501
2. Press **`R`** key (or click "Rerun" in top-right menu)
3. This reloads the app without restarting

**Note**: This may not always pick up code changes - full restart is better.

## Verify Changes Are Loaded

### Test 1: Query Tab Improvements
1. Go to **🔎 Quick Search** tab
2. Enter: "What are the board meeting requirements?"
3. Click "Get Answer"
4. **Check**: AI Answer should have clean sections (no TOC/fragments)

### Test 2: Web Search LLM Integration
1. Go to **🌐 Web Search** tab
2. Enter: "latest AWS security threats"
3. Click "🔍 Search Web"
4. **Check**: Should see "🧠 AI Summary" section (not just raw links)

### Test 3: Chat Assistant Error Fix
1. Go to **💬 Chat Assistant** tab
2. Ask: "What are AWS security threats?"
3. **Check**: Either works OR shows clear error (not "NoneType" error)

## If Changes Still Don't Appear

### Check 1: Verify File Changes
```bash
# Check last modified time of query_assistant.py
ls -l tabs/query_assistant.py
```

### Check 2: Check for Python Cache
```bash
# Clear Python cache
Remove-Item -Recurse -Force tabs/__pycache__
Remove-Item -Recurse -Force utils/__pycache__
```

### Check 3: Verify Streamlit is Using Correct Directory
```bash
# Make sure you're in the right directory
cd c:\Users\bolaf\VoultMIND_lanre\genai-knowledge-assistant
streamlit run genai_dashboard_modular.py
```

## Quick Restart Script

Save this as `restart.ps1`:
```powershell
# Stop all Streamlit processes
Write-Host "Stopping Streamlit..." -ForegroundColor Yellow
Get-Process streamlit -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 2

# Clear cache
Write-Host "Clearing cache..." -ForegroundColor Yellow
Remove-Item -Recurse -Force tabs/__pycache__ -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force utils/__pycache__ -ErrorAction SilentlyContinue

# Restart
Write-Host "Starting Streamlit..." -ForegroundColor Green
streamlit run genai_dashboard_modular.py
```

Run with: `.\restart.ps1`

## Expected Changes After Restart

### ✅ Query Tab:
- Clean AI answers (no TOC lines like "II ASSOCIATION...")
- No truncated fragments (no "must be summarized...")
- Proper page numbers (numeric only, no "Page N/A")
- Complete sentences in all sections

### ✅ Web Search:
- AI Summary section appears
- LLM-generated answer from web results
- Clickable source links below

### ✅ Chat Assistant:
- Better error messages (if LLM fails)
- Clear indication of what's wrong

## Still Having Issues?

If changes don't appear after restart:
1. Check the terminal for error messages
2. Look for import errors or syntax errors
3. Verify the files were actually saved
4. Try clearing browser cache: `Ctrl + Shift + Delete`
