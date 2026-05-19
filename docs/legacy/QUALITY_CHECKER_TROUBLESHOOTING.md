# Document Quality Checker - Troubleshooting Guide 🔧

## Issue: Radio Buttons Not Showing

If you're not seeing the quality checker radio buttons after uploading a document, follow these steps:

---

## ✅ Step 1: Verify You're on the Right Tab

Make sure you're on the **"📄 Ingest Document"** tab (not Query, Chat, or Agent tabs).

---

## ✅ Step 2: Check Which Backend You Selected

The quality checker works with **both** backends, but you need to select one:

1. Look for "🔧 Storage Backend" dropdown at the top
2. You should see one of these options:
   - **FAISS (Local Index)** ← Quality checker enabled
   - **Weaviate (Cloud Vector DB)** ← Quality checker enabled
   - **Both (Weaviate + Local FAISS)** ← Quality checker enabled

---

## ✅ Step 3: Upload a Document

1. Select source type: **PDF File** or **Text File**
2. Click "Choose PDF File" or "Choose Text File"
3. Select a file from your computer
4. Wait for upload to complete

---

## ✅ Step 4: Look for Quality Check Section

After upload, you should see:

```
───────────────────────────────────────
📊 Document Quality Check
🔍 Analyzing: your-file-name.pdf

📄 Extraction method: pdfplumber

┌──────────────┬──────────────┬──────────────┐
│ Quality Score│ Issues Found │ Total Words  │
│    0.XX      │      X       │    X,XXX     │
└──────────────┴──────────────┴──────────────┘
```

**If you DON'T see this section**, continue to Step 5.

---

## ✅ Step 5: Check for Error Messages

Look for any of these messages:

### "⚠️ Quality check unavailable: [error]"
**Cause:** Import error or missing dependency

**Solution:**
```bash
# Install missing dependencies
pip install sentence-transformers
pip install pdfplumber
pip install pymupdf

# Restart Streamlit
streamlit run genai_dashboard_modular.py
```

### "❌ All extraction methods failed"
**Cause:** PDF is corrupted or encrypted

**Solution:**
- Try a different PDF file
- Check if PDF is password-protected
- Try converting PDF to text first

---

## ✅ Step 6: Check Console for Errors

1. Look at the terminal where Streamlit is running
2. Check for error messages like:
   ```
   ModuleNotFoundError: No module named 'utils.document_quality_checker'
   ImportError: cannot import name 'check_document_quality'
   ```

**Solution:**
```bash
# Verify file exists
ls utils/document_quality_checker.py

# If missing, the file wasn't created properly
# Re-download or recreate the file
```

---

## ✅ Step 7: Restart Streamlit

Sometimes Streamlit caches old code:

```bash
# Stop Streamlit (Ctrl+C in terminal)

# Clear cache
streamlit cache clear

# Restart
streamlit run genai_dashboard_modular.py
```

---

## ✅ Step 8: Verify File Upload Worked

After selecting a file, you should see:
- File name appears under the upload button
- File size shown
- Upload progress (if large file)

**If file doesn't upload:**
- Check file size (< 200MB recommended)
- Check file format (PDF, TXT, MD, CSV only)
- Try a smaller file first

---

## 🔍 Debug Mode

If still not working, let's add debug output:

### Check if Quality Check Section is Reached

After uploading, you should see:
```
📊 Document Quality Check
🔍 Analyzing: your-file.pdf
```

**If you see this but NO radio buttons:**
- Quality score might be > 0.8 (good quality)
- Radio buttons only appear for quality < 0.8
- You'll see: "✅ Document quality is good (0.XX) - ready for ingestion!"

**If you DON'T see "🔍 Analyzing..." at all:**
- The quality check code isn't being reached
- Check if file upload completed
- Check browser console for JavaScript errors

---

## 🎯 Expected Behavior

### For Good Quality Documents (Score ≥ 0.8):
```
📊 Document Quality Check
🔍 Analyzing: document.pdf

Quality Score: 0.92    Issues Found: 0    Total Words: 1,234

✅ Document quality is good (0.92) - ready for ingestion!

───────────────────────────────────────
🚀 [Start Ingestion Button]
```
**No radio buttons** - document is already good!

### For Poor Quality Documents (Score < 0.8):
```
📊 Document Quality Check
🔍 Analyzing: document.pdf

Quality Score: 0.45    Issues Found: 3    Total Words: 1,234

⚠️ View 3 Quality Issues [Click to expand]

⚠️ Low quality detected (0.45). Cleaning recommended.

Choose Version for Ingestion:
  ○ ✨ Clean Document (Recommended)  ← RADIO BUTTONS HERE
  ○ ➡️ Use Original Document

───────────────────────────────────────
🚀 [Start Ingestion Button]
```
**Radio buttons appear** - choose which version to use!

---

## 🧪 Test with Sample Document

Create a test file to verify it works:

### Create test_quality.txt:
```
TheQuickBrownFoxJumpsOverTheLazyDog
Hellooooooo World
Testttttttt Document
```

### Upload this file:
1. Go to Ingest Document tab
2. Select "Text File"
3. Upload test_quality.txt
4. Should see quality score ~0.3-0.5
5. Radio buttons should appear

---

## 🔧 Common Issues & Solutions

### Issue 1: "No module named 'utils.document_quality_checker'"
**Solution:**
```bash
# Check if file exists
ls utils/document_quality_checker.py

# If missing, create it from the documentation
# File should be ~300 lines with DocumentQualityChecker class
```

### Issue 2: "No module named 'utils.robust_pdf_extractor'"
**Solution:**
```bash
# Check if file exists
ls utils/robust_pdf_extractor.py

# Install PDF libraries
pip install pdfplumber pymupdf PyPDF2
```

### Issue 3: Radio buttons disappear after clicking
**Solution:**
- This was the old bug - should be fixed now
- Make sure you have the latest code with radio buttons (not regular buttons)
- Look for `st.radio()` in the code, not `st.button()`

### Issue 4: Quality check is slow
**Solution:**
- Normal for large documents (>100 pages)
- Shows spinner: "🔍 Analyzing document quality..."
- Wait for it to complete
- Consider using smaller documents for testing

### Issue 5: Wrong quality score
**Solution:**
- Quality checker is working correctly
- Score reflects actual document quality
- Try cleaning and see if score improves
- Some documents genuinely have low quality (OCR, scans)

---

## 📊 Verification Checklist

Use this checklist to verify everything is working:

- [ ] Streamlit app is running
- [ ] On "📄 Ingest Document" tab
- [ ] Backend selected (FAISS or Weaviate)
- [ ] Source type selected (PDF or Text)
- [ ] File uploaded successfully
- [ ] See "📊 Document Quality Check" header
- [ ] See "🔍 Analyzing: filename" message
- [ ] See quality metrics (3 boxes)
- [ ] See issues list (if any)
- [ ] See radio buttons (if quality < 0.8) OR success message (if quality ≥ 0.8)
- [ ] Can select radio button option
- [ ] See confirmation message
- [ ] Can click ingestion button

---

## 🆘 Still Not Working?

If you've tried everything above and it's still not working:

### 1. Check File Versions
```bash
# Make sure you have the latest version
git pull origin main

# Or check file modification date
ls -l tabs/document_ingestion_fixed.py
# Should be recently modified
```

### 2. Check Python Version
```bash
python --version
# Should be 3.9 or higher
```

### 3. Reinstall Dependencies
```bash
pip install -r requirements-complete.txt --force-reinstall
```

### 4. Try Minimal Test
```python
# test_quality_import.py
from utils.document_quality_checker import check_document_quality

text = "TheQuickBrownFox"
result = check_document_quality(text)
print(f"Quality Score: {result['quality_score']}")
print(f"Issues: {len(result['issues'])}")
```

Run: `python test_quality_import.py`

Should output:
```
Quality Score: 0.XX
Issues: X
```

---

## 📞 Getting Help

If none of the above works:

1. **Check the logs:**
   - Look at Streamlit terminal output
   - Check for Python errors
   - Note any warning messages

2. **Provide details:**
   - Which backend are you using? (FAISS/Weaviate)
   - What file type? (PDF/Text)
   - File size?
   - Any error messages?
   - Screenshot of what you see?

3. **Try the demo file:**
   - Use the test_quality.txt from above
   - If that works, issue is with your specific file
   - If that doesn't work, issue is with setup

---

## ✅ Success Indicators

You'll know it's working when you see:

1. ✅ Quality check section appears after upload
2. ✅ Quality metrics displayed (3 boxes)
3. ✅ Issues list shown (if any)
4. ✅ Radio buttons appear (if quality < 0.8)
5. ✅ Can select an option
6. ✅ Confirmation message shows
7. ✅ Ingestion proceeds with chosen version

---

## 🎉 Quick Test Script

Save this as `test_quality_ui.py`:

```python
import streamlit as st
from utils.document_quality_checker import check_document_quality, clean_document

st.title("Quality Checker Test")

text = st.text_area("Enter text to test:", "TheQuickBrownFoxJumps")

if st.button("Check Quality"):
    result = check_document_quality(text)
    st.metric("Quality Score", f"{result['quality_score']:.2f}")
    st.write(f"Issues: {len(result['issues'])}")
    
    if result['quality_score'] < 0.8:
        choice = st.radio(
            "Choose:",
            ["Clean", "Original"]
        )
        if choice == "Clean":
            cleaned, changes = clean_document(text)
            st.success(f"Cleaned! Spaces added: {changes['spaces_added']}")
            st.code(cleaned)
```

Run: `streamlit run test_quality_ui.py`

This will test if the quality checker works in isolation.

---

<p align="center">Still having issues? The debug output "🔍 Analyzing: filename" will help identify where the problem is!</p>
