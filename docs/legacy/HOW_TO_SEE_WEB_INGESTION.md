# How to See Web Ingestion Option

## ✅ Web Ingestion IS Already There!

The Website URL option exists, but you need to select the right storage backend first.

## 📍 Step-by-Step Guide

### Step 1: Go to Input Document Tab
Click on **📄 Document Ingestion** tab in the main dashboard

### Step 2: Select Storage Backend
You'll see this dropdown:
```
Storage Backend:
○ FAISS (Local Index)
○ Weaviate (Cloud Vector DB)      ← Select this
○ Both (Weaviate + Local FAISS)   ← Or this
```

**Important**: Website URL option only appears when you select:
- **Weaviate (Cloud Vector DB)**, OR
- **Both (Weaviate + Local FAISS)**

### Step 3: Enter Collection Name
```
Collection Name: web_content_index
```

### Step 4: Select Source Type
Now you'll see:
```
Select Source Type:
○ PDF File
○ Text File
● Website URL  ← This will now be visible!
```

### Step 5: Enter Website URL
```
Enter Website URL: https://example.com/article
☐ Render JavaScript
Crawl Depth: [1] ─── [3]
```

### Step 6: Configure Chunking
```
Chunking Method: Semantic Chunking (Recommended)
Chunk Size: 800
Chunk Overlap: 100
```

### Step 7: Click "🚀 Start Weaviate Ingestion"

## 🔍 Why You Might Not See It

### Issue 1: Wrong Storage Backend Selected
**Problem**: You selected "FAISS (Local Index)"
**Solution**: Select "Weaviate" or "Both"

### Issue 2: Weaviate Connection Failed
**Problem**: Weaviate server not running
**Solution**: 
- Check Weaviate connection in .env
- Or use "Both" option to also save to local FAISS

### Issue 3: App Not Restarted
**Problem**: Old version of code running
**Solution**: Restart the app

## 📊 Visual Flow

```
📄 Document Ingestion Tab
    ↓
🔧 Storage Backend
    ├─ FAISS (Local Index) → Only shows PDF/Text
    ├─ Weaviate (Cloud) → Shows PDF/Text/Website ✅
    └─ Both → Shows PDF/Text/Website ✅
    ↓
📚 Collection Name
    ↓
📥 Document Source
    ├─ PDF File
    ├─ Text File
    └─ Website URL ✅ (Only if Weaviate selected)
    ↓
🚀 Start Ingestion
```

## 🎯 Quick Test

1. **Restart app**: `streamlit run genai_dashboard_modular.py`
2. **Go to**: 📄 Document Ingestion
3. **Select**: "Weaviate (Cloud Vector DB)"
4. **Look for**: "Select Source Type" dropdown
5. **Check**: Should see "Website URL" option

## ⚠️ If Still Not Visible

### Check 1: Verify File Being Used
The system uses `tabs/document_ingestion_fixed.py`

Check line 148-152:
```python
source_type = st.selectbox(
    "Select Source Type:",
    ["PDF File", "Text File", "Website URL"],  ← Should be here
    key="weaviate_ingest_source_type"
)
```

### Check 2: Check Weaviate Availability
If Weaviate is not available, the system falls back to FAISS-only mode, which doesn't show Website URL.

**Solution**: 
- Configure Weaviate in .env
- Or use the "Both" option

### Check 3: Browser Cache
Clear browser cache: `Ctrl + Shift + Delete`

## 📝 Summary

**The Website URL option EXISTS** in your code at:
- **File**: `tabs/document_ingestion_fixed.py`
- **Line**: 148-152 (source type selection)
- **Line**: 238-241 (URL input fields)

**To see it**:
1. Select "Weaviate" or "Both" storage backend
2. The "Website URL" option will appear in source type dropdown

**Why it's hidden**:
- Website ingestion requires Weaviate backend
- FAISS-only mode doesn't support web scraping
- This is by design for proper vector storage

---

**Status**: ✅ Feature exists, just need to select right backend
**Location**: Document Ingestion → Weaviate backend → Website URL
**Next**: Restart app and select Weaviate backend to see it!
