# Document Quality Checker - User Guide

## 🎯 What It Does

The Document Quality Checker automatically detects and fixes common issues in documents before ingestion:

### Issues Detected:
- ❌ **Missing spaces** between words (e.g., "TheQuickBrown" → "The Quick Brown")
- ❌ **Concatenated words** (very long words without spaces)
- ❌ **Repeated characters** (e.g., "Hellooooo" → "Helloo")
- ❌ **Excessive special characters** (OCR artifacts)
- ❌ **OCR errors** (common misrecognitions like "rn" → "m")

### Quality Score:
- **0.8 - 1.0** ✅ Good - Ready for ingestion
- **0.5 - 0.8** ⚠️ Fair - Consider cleaning
- **0.0 - 0.5** ❌ Poor - Cleaning strongly recommended

---

## 🚀 How to Use

### In the UI (Streamlit)

#### Option 1: During Document Ingestion

1. **Upload your document** in the "📄 Ingest Document" tab
2. **Quality check runs automatically** after upload
3. **Review the analysis:**
   - Quality score
   - Issues found
   - Recommendations
4. **Choose action:**
   - Click "✨ Clean Document" to auto-fix issues
   - Click "👁️ Preview Cleaning" to see before/after
   - Click "➡️ Use Original" to skip cleaning
5. **Continue with ingestion** using cleaned or original text

#### Option 2: Standalone Quality Check

```python
# In Python/Jupyter
from utils.document_quality_checker import check_document_quality

text = "YourDocumentTextHere"
result = check_document_quality(text)

print(f"Quality Score: {result['quality_score']:.2f}")
print(f"Issues: {len(result['issues'])}")
for issue in result['issues']:
    print(f"  - {issue.description}")
```

---

## 🧹 Cleaning Modes

### Standard Mode (Default)
- Adds spaces between concatenated words
- Removes excessive repeated characters
- Fixes common OCR errors
- **Safe:** Minimal changes to text

### Aggressive Mode
- All standard fixes PLUS:
- Splits very long words (>20 chars)
- Removes more special characters
- More aggressive OCR correction
- **Use with caution:** May alter more text

---

## 📊 Understanding the Analysis

### Quality Report Includes:

**1. Quality Score (0-1)**
- Overall document quality metric
- Based on detected issues and their severity

**2. Issues List**
- Type of issue
- Severity (high/medium/low)
- Count of occurrences
- Examples from your document

**3. Statistics**
- Total characters
- Total words
- Average word length
- Special character ratio

**4. Recommendations**
- Actionable steps to improve quality
- Whether cleaning is recommended

---

## 🎨 Example Scenarios

### Scenario 1: Good Quality Document
```
Input: "This is a well-formatted document with proper spacing."

Result:
✅ Quality Score: 0.95
✅ Status: Good - Ready for ingestion
✅ Action: No cleaning needed
```

### Scenario 2: OCR Document with Issues
```
Input: "TheQuickBrownFoxJumpsOverTheLazyDog"

Result:
⚠️ Quality Score: 0.45
⚠️ Issues: Missing spaces (15 occurrences)
⚠️ Action: Cleaning recommended

After Cleaning: "The Quick Brown Fox Jumps Over The Lazy Dog"
✅ New Score: 0.92
```

### Scenario 3: Scanned PDF with OCR Errors
```
Input: "Hellooooo World!!!! This is a testtttt document."

Result:
⚠️ Quality Score: 0.60
⚠️ Issues: 
  - Repeated characters (3 occurrences)
  - Excessive punctuation
⚠️ Action: Cleaning recommended

After Cleaning: "Helloo World! This is a testt document."
✅ New Score: 0.88
```

---

## 🔧 Integration Examples

### Example 1: Check Before Ingestion

```python
from utils.document_quality_checker import check_document_quality, clean_document

# Read document
with open('document.txt', 'r') as f:
    text = f.read()

# Check quality
result = check_document_quality(text)

if result['quality_score'] < 0.8:
    print("⚠️ Low quality detected - cleaning...")
    cleaned_text, changes = clean_document(text)
    print(f"✅ Cleaned! Changes: {changes}")
    text = cleaned_text

# Continue with ingestion
ingest_document(text)
```

### Example 2: Batch Processing

```python
from utils.document_quality_ui import render_batch_quality_check

documents = {
    'doc1.txt': text1,
    'doc2.txt': text2,
    'doc3.txt': text3
}

results = render_batch_quality_check(documents)

# Clean all documents below threshold
for name, analysis in results.items():
    if analysis['quality_score'] < 0.8:
        cleaned, _ = clean_document(documents[name])
        documents[name] = cleaned
```

### Example 3: API Integration

```python
from utils.document_quality_checker import DocumentQualityChecker, DocumentCleaner

checker = DocumentQualityChecker()
cleaner = DocumentCleaner()

def process_document(text: str, auto_clean: bool = True):
    # Analyze
    analysis = checker.analyze_text(text)
    
    # Auto-clean if quality is low
    if auto_clean and analysis['quality_score'] < 0.8:
        text, changes = cleaner.clean_text(text)
        return {
            'text': text,
            'was_cleaned': True,
            'original_score': analysis['quality_score'],
            'changes': changes
        }
    
    return {
        'text': text,
        'was_cleaned': False,
        'score': analysis['quality_score']
    }
```

---

## 🎯 Best Practices

### When to Clean:
✅ **Always clean if:**
- Quality score < 0.5
- Document is from OCR/scanning
- Missing spaces detected
- Planning to use for LLM training

✅ **Consider cleaning if:**
- Quality score 0.5 - 0.8
- Document will be user-facing
- Accuracy is critical

❌ **Skip cleaning if:**
- Quality score > 0.8
- Document is code/technical (may have intentional formatting)
- You need exact original text

### Cleaning Tips:
1. **Always preview first** - Check what will change
2. **Start with standard mode** - Use aggressive only if needed
3. **Verify critical content** - Check important sections after cleaning
4. **Keep originals** - Save original before cleaning
5. **Re-check after cleaning** - Verify improved quality score

---

## 🐛 Troubleshooting

### Issue: Quality score still low after cleaning
**Solution:** Try aggressive mode, or manually review the document

### Issue: Cleaning changed important text
**Solution:** Use original document, or manually edit specific sections

### Issue: False positives (good text marked as issues)
**Solution:** Adjust thresholds in `document_quality_checker.py`

### Issue: Cleaning is too slow
**Solution:** Process in smaller chunks, or disable preview mode

---

## 📈 Performance

- **Analysis speed:** ~1000 words/second
- **Cleaning speed:** ~500 words/second
- **Memory usage:** ~2x document size
- **Recommended max size:** 10MB per document

---

## 🔮 Future Enhancements

Planned features:
- [ ] Language-specific cleaning rules
- [ ] Custom cleaning profiles
- [ ] ML-based quality prediction
- [ ] Batch cleaning with parallel processing
- [ ] Export cleaning reports
- [ ] Integration with document versioning

---

## 📞 Support

**Issues with quality checker?**
- Check logs for detailed error messages
- Verify document encoding (UTF-8 recommended)
- Try smaller document chunks
- Report bugs with sample text

**Questions?**
- See `utils/document_quality_checker.py` for implementation
- See `utils/document_quality_ui.py` for UI components
- Check examples in this guide

---

## 🎓 Technical Details

### Quality Score Calculation:
```
score = 1.0 - Σ(issue_penalties)

Where:
- High severity: penalty = min(0.3, count/text_length * 10)
- Medium severity: penalty = min(0.2, count/text_length * 5)
- Low severity: penalty = min(0.1, count/text_length * 2)
```

### Cleaning Algorithm:
1. Fix missing spaces (regex-based)
2. Split concatenated words (pattern matching)
3. Remove repeated characters (keep max 2)
4. Remove excessive special chars
5. Normalize whitespace
6. Fix common OCR errors

### Detection Patterns:
- **Concatenated words:** `[a-z]{15,}` (15+ lowercase chars)
- **Missing spaces:** `[a-z][A-Z]` (lowercase → uppercase)
- **Repeated chars:** `(.)\1{4,}` (same char 5+ times)
- **Special chars:** `[^\w\s\-.,;:!?()\[\]{}\'\"]+`

---

**Ready to improve your document quality!** 🚀

For more details, see the source code in `utils/document_quality_checker.py`
