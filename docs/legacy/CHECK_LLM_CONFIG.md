# LLM Configuration Error Fix

## Error Message
```
'NoneType' object has no attribute 'chat'. Please check your LLM configuration and try again.
```

## Root Cause
Your LLM API key is not configured or not being loaded properly.

## Solution Steps

### Step 1: Check if `.env` file exists
1. Look for `.env` file in your project root: `c:/Users/bolaf/VoultMIND_lanre/genai-knowledge-assistant/`
2. If it doesn't exist, create it by copying `.env.example`:
   ```bash
   copy .env.example .env
   ```

### Step 2: Add Your OpenAI API Key
Open `.env` file and add:
```bash
OPENAI_API_KEY=sk-your-actual-openai-api-key-here
```

**Get OpenAI API Key:**
- Go to: https://platform.openai.com/api-keys
- Sign in
- Click "Create new secret key"
- Copy the key (starts with `sk-`)
- Paste it in `.env` file

### Step 3: Alternative LLM Providers (If You Don't Have OpenAI)

**Option A: Use Anthropic Claude**
```bash
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

**Option B: Use Local Ollama (Free, No API Key)**
```bash
OLLAMA_BASE_URL=http://localhost:11434
```
Then install Ollama: https://ollama.ai

**Option C: Use Groq (Free Tier Available)**
```bash
GROQ_API_KEY=your_groq_api_key_here
```

### Step 4: Restart the App
After adding the API key:
1. Stop the Streamlit app (Ctrl+C)
2. Restart it:
   ```bash
   streamlit run genai_dashboard_modular.py
   ```

## Verification

After restart, check:
1. Go to Chat Assistant tab
2. Try asking: "What are the new AWS security threats"
3. You should get an AI response

## Still Not Working?

### Check 1: Verify API Key is Valid
```python
# Run this in Python to test:
import os
from dotenv import load_dotenv
load_dotenv()
print(f"OpenAI Key present: {bool(os.getenv('OPENAI_API_KEY'))}")
print(f"Key starts with: {os.getenv('OPENAI_API_KEY', '')[:7]}...")
```

### Check 2: Check for Typos
- Ensure no extra spaces in `.env`
- Ensure the key starts with `sk-` for OpenAI
- Ensure no quotes around the key (just: `OPENAI_API_KEY=sk-xxx`)

### Check 3: File Location
The `.env` file must be in the project root:
```
genai-knowledge-assistant/
├── .env          ← HERE
├── .env.example
├── genai_dashboard_modular.py
└── ...
```

## Quick Test Command
```bash
# Test if .env is loaded
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('OpenAI Key:', 'FOUND' if os.getenv('OPENAI_API_KEY') else 'MISSING')"
```
