# Vertex AI Setup Troubleshooting Guide

## Current Issue: "Connection failed during initialization"

This error appears because the **google-cloud-aiplatform** package is not installed in your Python environment.

---

## Quick Fix (3 Steps)

### Step 1: Install Required Packages

Open PowerShell or Command Prompt in the project directory and run:

```bash
py -m pip install google-cloud-aiplatform google-auth
```

**OR** run the batch file I created:
```bash
install_vertex_deps.bat
```

### Step 2: Verify Installation

```bash
py -c "import google.cloud.aiplatform; print('✅ Installed:', google.cloud.aiplatform.__version__)"
```

You should see: `✅ Installed: 1.x.x`

### Step 3: Restart Streamlit

1. Stop your Streamlit app (Ctrl+C)
2. Start it again:
   ```bash
   streamlit run genai_dashboard_modular.py
   ```
3. Go to Multi-Vector Ingestion tab
4. Click **"Reload Manager"** button
5. Check Vector Store Status - Vertex_AI_Matching should now show **green/connected**

---

## Detailed Diagnostics

### Check What's Installed

```bash
py -m pip list | findstr google
```

You should see:
- `google-auth`
- `google-cloud-aiplatform`
- `google-api-core`
- Other google packages

### Run Full Diagnostic

```bash
py trace_vertex_error.py
```

This will show you exactly where the connection is failing.

---

## Common Installation Issues

### Issue 1: "No module named 'google'"

**Cause**: Package not installed  
**Solution**: Run `py -m pip install google-cloud-aiplatform google-auth`

### Issue 2: "Permission denied" during pip install

**Cause**: Need admin rights or virtual environment  
**Solution**: 
- Run PowerShell as Administrator, OR
- Use a virtual environment:
  ```bash
  py -m venv venv
  .\venv\Scripts\activate
  pip install google-cloud-aiplatform google-auth
  ```

### Issue 3: "Could not find a version that satisfies the requirement"

**Cause**: Python version too old/new (you have 3.14 beta)  
**Solution**: 
- Try installing specific version:
  ```bash
  py -m pip install google-cloud-aiplatform==1.38.0 google-auth==2.23.4
  ```
- If still fails, consider using Python 3.11 or 3.12 (stable versions)

### Issue 4: Package installs but still shows error in UI

**Cause**: Streamlit caching old state  
**Solution**:
1. Stop Streamlit
2. Clear Streamlit cache:
   ```bash
   streamlit cache clear
   ```
3. Restart Streamlit
4. Click "Reload Manager" button

---

## Verify Your Configuration

After installing packages, verify your `config/storage.env`:

```env
GCP_PROJECT_ID=vaultmind-genai-assistant
GCP_LOCATION=us-central1
VERTEX_AI_INDEX_ENDPOINT=
GOOGLE_APPLICATION_CREDENTIALS=C:\Users\bolaf\Downloads\vaultmind-genai-assistant-a7d24d0c55d7.json
```

**Important**: No quotes around the file path!

---

## Test Connection Manually

Create a test file `test_vertex_manual.py`:

```python
import os
from google.cloud import aiplatform
from google.oauth2 import service_account

# Set credentials
creds_path = r"C:\Users\bolaf\Downloads\vaultmind-genai-assistant-a7d24d0c55d7.json"
credentials = service_account.Credentials.from_service_account_file(creds_path)

# Initialize
aiplatform.init(
    project='vaultmind-genai-assistant',
    location='us-central1',
    credentials=credentials
)

# Test
from google.cloud.aiplatform import MatchingEngineIndex
indexes = MatchingEngineIndex.list()
print(f"✅ Success! Found {len(indexes)} indexes")
```

Run: `py test_vertex_manual.py`

---

## Still Not Working?

### Check GCP Setup

1. **Verify APIs are enabled**:
   - Go to: https://console.cloud.google.com/apis/library
   - Search "Vertex AI API" → Should show "Enabled"
   - Search "Cloud Storage API" → Should show "Enabled"

2. **Verify Service Account Permissions**:
   - Go to: https://console.cloud.google.com/iam-admin/iam
   - Find your service account: `vaultmind-vertex-sa@...`
   - Should have roles:
     - Vertex AI User
     - Vertex AI Admin
     - Storage Admin

3. **Verify Service Account Key**:
   - File should exist at: `C:\Users\bolaf\Downloads\vaultmind-genai-assistant-a7d24d0c55d7.json`
   - File should be valid JSON
   - Should contain: `type`, `project_id`, `private_key`, `client_email`

### Check Logs

Look for detailed error messages in:
- Terminal where Streamlit is running
- Look for lines starting with `ERROR` or `Failed to initialize`

---

## Alternative: Use Different Vector Store

If Vertex AI continues to have issues, you can use other vector stores:

### Option 1: Use Pinecone (Already configured)
- Your Pinecone is already showing as "Primary Store" and connected
- No additional setup needed

### Option 2: Use Weaviate (Already configured)
- Your Weaviate is showing as "Fallback Store" and connected
- No additional setup needed

### Option 3: Use FAISS (Local, no cloud needed)
- Already installed and working
- No API keys or cloud setup required

To switch primary store, edit `config/multi_vector_config.yml`:
```yaml
primary_store:
  type: "pinecone"  # or "weaviate" or "faiss"
```

---

## Summary Checklist

- [ ] Install packages: `py -m pip install google-cloud-aiplatform google-auth`
- [ ] Verify installation: `py -c "import google.cloud.aiplatform; print('OK')"`
- [ ] Check config/storage.env has correct paths (no quotes)
- [ ] Verify service account JSON file exists
- [ ] Enable Vertex AI API in GCP Console
- [ ] Add roles to service account (Vertex AI Admin, Storage Admin)
- [ ] Restart Streamlit app
- [ ] Click "Reload Manager" button
- [ ] Check Vector Store Status shows green

---

## Need Help?

Run these diagnostic commands and share the output:

```bash
# 1. Python version
py --version

# 2. Installed packages
py -m pip list | findstr google

# 3. Full diagnostic
py trace_vertex_error.py

# 4. Check config
type config\storage.env
```
