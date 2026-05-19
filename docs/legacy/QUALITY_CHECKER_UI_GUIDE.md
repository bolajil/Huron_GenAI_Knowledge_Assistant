# Document Quality Checker - UI Guide 🎨

## ✅ FIXED: Radio Button Selection Now Available!

The quality checker now uses **radio buttons** instead of regular buttons, so your choice persists!

---

## 🎬 What You'll See in the UI

### Step 1: Upload Document
```
📄 Ingest Document Tab
┌─────────────────────────────────────┐
│ Choose Backend: [Weaviate] [FAISS] │
│ Source Type: [PDF File ▼]          │
│ [Choose PDF File]                   │
└─────────────────────────────────────┘
```

### Step 2: Quality Check Appears Automatically
```
───────────────────────────────────────
📊 Document Quality Check

📄 Extraction method: pdfplumber

┌──────────────┬──────────────┬──────────────┐
│ Quality Score│ Issues Found │ Total Words  │
│    0.45      │      3       │    1,234     │
│   (Poor)     │              │              │
└──────────────┴──────────────┴──────────────┘

⚠️ View 3 Quality Issues
  ▼ Click to expand
  
  **Missing spaces between words**
    - Severity: High
    - Count: 47 occurrences
    - Examples: TheQuick, BrownFox, LazyDog
  
  **Very long words detected**
    - Severity: Medium
    - Count: 12 occurrences
    - Examples: Thequickbrownfoxjumps...
  
  **Repeated characters**
    - Severity: Low
    - Count: 8 occurrences
    - Examples: Hellooooo, Testttttt

⚠️ Low quality detected (0.45). Cleaning recommended.
───────────────────────────────────────
```

### Step 3: Choose Version (NEW - Radio Buttons!)
```
Choose Version for Ingestion:

Select which version to use:
  ○ ✨ Clean Document (Recommended)
  ○ ➡️ Use Original Document

ℹ️ Clean version will fix spacing, OCR errors, 
   and repeated characters
```

### Step 4a: If You Select "Clean Document"
```
🧹 Cleaning document...

✅ Document cleaned successfully!

┌──────────────┬──────────────┬──────────────┐
│ Spaces Added │ Repeated Rem │ Special Rem  │
│     47       │      8       │      3       │
└──────────────┴──────────────┴──────────────┘

┌──────────────────────────────┐
│ New Quality Score            │
│      0.88                    │
│     +0.43 ↑                  │
└──────────────────────────────┘

✅ Cleaned version will be used for ingestion
```

### Step 4b: If You Select "Use Original"
```
ℹ️ Original version will be used for ingestion
```

### Step 5: Proceed with Ingestion
```
───────────────────────────────────────

🚀 [Start Weaviate Ingestion]
   or
🚀 [Start FAISS Ingestion]
```

---

## 🎯 Key Features

### ✅ Persistent Selection
- **Radio buttons** maintain your choice
- No need to click multiple times
- Selection stays even if page updates

### ✅ Smart Caching
- Cleaning happens once
- Results are cached
- Re-selecting "Clean" shows cached results instantly

### ✅ Clear Feedback
- See exactly what changed
- Quality improvement shown
- Confirmation messages

---

## 📊 Example Scenarios

### Scenario 1: Good Quality Document

```
📊 Document Quality Check

Quality Score: 0.92    Issues Found: 0    Total Words: 1,234

✅ Document quality is good (0.92) - ready for ingestion!

───────────────────────────────────────
🚀 [Start Ingestion]
```
**Result:** No cleaning options shown, proceed directly!

---

### Scenario 2: Poor Quality - User Chooses Clean

```
📊 Document Quality Check

Quality Score: 0.45    Issues Found: 3    Total Words: 1,234

⚠️ View 3 Quality Issues [Click to expand]

⚠️ Low quality detected (0.45). Cleaning recommended.

Choose Version for Ingestion:
  ● ✨ Clean Document (Recommended)  ← USER SELECTS THIS
  ○ ➡️ Use Original Document

✅ Document cleaned successfully!
Spaces Added: 47    Repeated Removed: 8    Special Removed: 3
New Quality Score: 0.88 (+0.43)

✅ Cleaned version will be used for ingestion

───────────────────────────────────────
🚀 [Start Ingestion]  ← Now uses cleaned version
```

---

### Scenario 3: Poor Quality - User Chooses Original

```
📊 Document Quality Check

Quality Score: 0.45    Issues Found: 3    Total Words: 1,234

⚠️ View 3 Quality Issues [Click to expand]

⚠️ Low quality detected (0.45). Cleaning recommended.

Choose Version for Ingestion:
  ○ ✨ Clean Document (Recommended)
  ● ➡️ Use Original Document  ← USER SELECTS THIS

ℹ️ Original version will be used for ingestion

───────────────────────────────────────
🚀 [Start Ingestion]  ← Uses original version
```

---

### Scenario 4: User Changes Mind

```
📊 Document Quality Check

Quality Score: 0.45    Issues Found: 3

Choose Version for Ingestion:
  ● ✨ Clean Document (Recommended)  ← First choice

✅ Document cleaned successfully!
New Quality Score: 0.88 (+0.43)

✅ Cleaned version will be used for ingestion

[User changes radio button]

Choose Version for Ingestion:
  ○ ✨ Clean Document (Recommended)
  ● ➡️ Use Original Document  ← Changed mind

ℹ️ Original version will be used for ingestion
```
**Result:** User can switch back and forth freely!

---

## 🔧 Technical Details

### Session State Storage

**Weaviate:**
```python
st.session_state.document_quality = {
    'filename.pdf': {
        'original_text': '...',
        'quality_score': 0.45,
        'should_clean': True,  # Based on radio selection
        'cleaned_text': '...',  # Cached after first clean
        'new_score': 0.88
    }
}
```

**FAISS:**
```python
st.session_state.document_quality_faiss = {
    # Same structure as above
}
```

### Radio Button Behavior

```python
choice = st.radio(
    "Select which version to use:",
    ["✨ Clean Document (Recommended)", "➡️ Use Original Document"],
    key=f"quality_choice_{uploaded_file.name}"
)

if choice == "✨ Clean Document (Recommended)":
    # Clean if not already cleaned
    # Show results
    # Set should_clean = True
else:
    # Set should_clean = False
```

### Caching Logic

```python
# First time cleaning
if cleaned_text is None:
    cleaned_text, changes = clean_document(text)
    # Store in session state
    
# Subsequent times
else:
    # Use cached cleaned_text
    # Show cached results
```

---

## 🎨 UI Components Used

### Metrics Display
```python
st.metric("Quality Score", "0.45", delta="Poor")
st.metric("New Quality Score", "0.88", delta="+0.43")
```

### Radio Buttons
```python
st.radio(
    "Select which version to use:",
    ["✨ Clean Document (Recommended)", "➡️ Use Original Document"],
    key="unique_key"
)
```

### Expandable Issues
```python
with st.expander("⚠️ View 3 Quality Issues"):
    for issue in issues:
        st.write(f"**{issue.description}**")
        st.code(", ".join(issue.examples))
```

### Status Messages
```python
st.success("✅ Document cleaned successfully!")
st.info("✅ Cleaned version will be used")
st.warning("⚠️ Low quality detected")
```

---

## 🧪 Testing Checklist

### Test 1: Upload Good Quality Document
- [ ] Quality score shows 0.8+
- [ ] No cleaning options appear
- [ ] Success message shown
- [ ] Can proceed to ingestion

### Test 2: Upload Poor Quality Document
- [ ] Quality score shows < 0.8
- [ ] Radio buttons appear
- [ ] Default selection is "Clean Document"
- [ ] Can select either option

### Test 3: Select "Clean Document"
- [ ] Cleaning spinner appears
- [ ] Changes metrics shown
- [ ] New quality score displayed
- [ ] Confirmation message appears
- [ ] Selection persists on page update

### Test 4: Select "Use Original"
- [ ] No cleaning happens
- [ ] Confirmation message appears
- [ ] Selection persists on page update

### Test 5: Switch Between Options
- [ ] Can change from Clean to Original
- [ ] Can change from Original to Clean
- [ ] Cleaned results are cached
- [ ] No re-cleaning on second selection

### Test 6: Proceed to Ingestion
- [ ] Ingestion button works
- [ ] Correct version is used (cleaned or original)
- [ ] No errors during ingestion

---

## 🎉 Summary

### What's Fixed
✅ **Radio buttons** instead of regular buttons  
✅ **Persistent selection** - choice doesn't disappear  
✅ **Smart caching** - cleaning happens once  
✅ **Clear feedback** - always know which version will be used  
✅ **Easy switching** - change your mind anytime  

### What You Get
- **Visible options** - always see both choices
- **Clear selection** - filled circle shows current choice
- **Instant feedback** - immediate confirmation
- **No confusion** - can't accidentally lose your choice

### Ready to Use!
The quality checker is now **fully functional** with **persistent radio button selection**!

---

## 📝 Quick Start

1. **Start app:** `streamlit run genai_dashboard_modular.py`
2. **Go to:** "📄 Ingest Document" tab
3. **Upload:** Any PDF or text file
4. **See:** Quality check appears automatically
5. **Choose:** Radio button for Clean or Original
6. **Confirm:** See your choice confirmed
7. **Ingest:** Click ingestion button

**Your choice will persist and be used during ingestion!** ✅

---

<p align="center">Quality Checker with Radio Buttons - Now Working Perfectly! 🎉</p>
