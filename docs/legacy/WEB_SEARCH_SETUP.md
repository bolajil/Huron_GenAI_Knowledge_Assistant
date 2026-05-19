# Web Search Setup Guide

## Current Status
Your web search is showing "No web results found" because no API keys are configured.

## Setup Options (Choose One)

### Option 1: Bing Web Search API (Recommended)
**Best for**: Production use, reliable results
**Cost**: $7/1000 queries (Free tier: 1000 queries/month)

#### Steps:
1. **Get Bing API Key**:
   - Visit: https://portal.azure.com
   - Sign in with Microsoft account
   - Click "Create a resource"
   - Search for "Bing Search v7"
   - Click "Create"
   - Choose pricing tier (F1 = Free tier)
   - Copy the API key from "Keys and Endpoint"

2. **Add to `.env` file**:
   ```bash
   # Add this line to your .env file
   BING_SEARCH_API_KEY=your_actual_bing_api_key_here
   ```

3. **Restart the app**

### Option 2: DuckDuckGo Search (Free, No API Key)
**Best for**: Development, testing, free usage
**Cost**: Free

#### Steps:
1. **Install the package**:
   ```bash
   pip install duckduckgo-search
   ```

2. **Restart the app** - No configuration needed!

### Option 3: Use Built-in Fallback (Already Active)
**Best for**: Quick testing
**Limitations**: May be less reliable, no snippets

- Already works as fallback
- No setup needed
- Try your search again - it should work with basic results

## Testing Web Search

After setup:
1. Go to **🌐 Web Search** tab
2. Enter query: "latest AWS security threat"
3. Click "🔍 Search Web"
4. You should see results with:
   - Title
   - URL (clickable)
   - Snippet (description)

## Troubleshooting

### "No web results found"
- **Check 1**: Verify `.env` file has `BING_SEARCH_API_KEY` (if using Bing)
- **Check 2**: Restart the Streamlit app after adding keys
- **Check 3**: Try installing `duckduckgo-search` package
- **Check 4**: Check internet connectivity

### API Key Not Working
- Verify the key is correct (no extra spaces)
- Check Azure portal that the Bing Search resource is active
- Ensure you're using the correct key (Key 1 or Key 2)

### Package Installation Issues
```bash
# If duckduckgo-search fails, try:
pip install --upgrade duckduckgo-search

# Or use specific version:
pip install duckduckgo-search==4.1.0
```

## Alternative: Use Knowledge Base Search Instead

If you don't need web search, use the **🔎 Quick Search** or **📚 Index Search** tabs to search your indexed documents (Bylaws, AWS docs, etc.).

## Current Implementation Details

The web search tries methods in this order:
1. **Bing API** (if `BING_SEARCH_API_KEY` is set)
2. **DuckDuckGo package** (if `duckduckgo-search` is installed)
3. **DuckDuckGo Lite scraping** (built-in fallback)

Location: `utils/web_search.py`
