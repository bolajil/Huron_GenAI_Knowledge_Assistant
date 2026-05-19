# 🔧 Install Tesseract OCR - Quick Guide

## ❌ Current Issue

Your OCR is failing because **Tesseract OCR is not installed** on your system.

**Error you're seeing:**
```
OCR Method: error
Confidence: 0.0%
Words: 0
```

---

## ✅ Solution: Install Tesseract

### Option 1: Using Chocolatey (Easiest)

```powershell
# Open PowerShell as Administrator
choco install tesseract

# Verify installation
tesseract --version
```

### Option 2: Manual Download

1. **Download Tesseract:**
   - Go to: https://github.com/UB-Mannheim/tesseract/wiki
   - Download: `tesseract-ocr-w64-setup-5.3.3.20231005.exe` (or latest version)

2. **Install:**
   - Run the installer
   - Default location: `C:\Program Files\Tesseract-OCR`
   - ✅ Check "Add to PATH" during installation

3. **Verify:**
   ```powershell
   tesseract --version
   ```
   
   Should show:
   ```
   tesseract 5.3.3
   ```

### Option 3: Manual PATH Setup (if not added automatically)

If Tesseract is installed but not in PATH:

1. **Find Tesseract location:**
   - Usually: `C:\Program Files\Tesseract-OCR\tesseract.exe`

2. **Add to PATH:**
   - Open System Properties → Environment Variables
   - Edit "Path" variable
   - Add: `C:\Program Files\Tesseract-OCR`
   - Click OK

3. **Restart PowerShell/Terminal**

4. **Verify:**
   ```powershell
   tesseract --version
   ```

---

## 🧪 Test After Installation

### Step 1: Verify Tesseract
```powershell
tesseract --version
```

Expected output:
```
tesseract 5.3.3
 leptonica-1.83.1
  libgif 5.2.1 : libjpeg 8d (libjpeg-turbo 2.1.3) : libpng 1.6.39 : libtiff 4.5.0 : zlib 1.2.13 : libwebp 1.3.0 : libopenjp2 2.5.0
```

### Step 2: Run Diagnostic
```powershell
python check_ocr_setup.py
```

Expected output:
```
✅ PIL/Pillow: INSTALLED
✅ pytesseract: INSTALLED
✅ Tesseract executable: FOUND
✅ OCR SUCCESS! Extracted: 'Hello World 123'
```

### Step 3: Test Demo
```powershell
streamlit run demo_image_ingestion.py
```

Now upload an image and click "Start OCR Extraction"

Expected result:
```
✅ OCR Method: tesseract
✅ Confidence: 95%
✅ Words: 250
✅ Text extracted successfully
```

---

## 🐛 Troubleshooting

### Issue: "tesseract is not recognized"

**Solution:**
1. Tesseract not installed → Install using steps above
2. Not in PATH → Add to PATH manually
3. Restart terminal after installation

### Issue: "TesseractNotFoundError"

**Solution:**
```python
# Set Tesseract path manually in Python
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
```

Or create a file `tesseract_config.py`:
```python
import pytesseract
import os

# Auto-detect Tesseract
possible_paths = [
    r'C:\Program Files\Tesseract-OCR\tesseract.exe',
    r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
]

for path in possible_paths:
    if os.path.exists(path):
        pytesseract.pytesseract.tesseract_cmd = path
        break
```

### Issue: Still getting 0 words after installation

**Possible causes:**
1. Image quality too low
2. Text too small
3. Poor contrast
4. Wrong language (Tesseract expects English by default)

**Solutions:**
- Use higher resolution images
- Ensure good contrast
- Try EasyOCR instead (more accurate but slower)

---

## 📊 Quick Comparison

| Feature | Tesseract | EasyOCR |
|---------|-----------|---------|
| **Installation** | Requires separate exe | Python package only |
| **Speed** | Fast (~1-2s) | Slower (~5-10s CPU) |
| **Accuracy** | Good (95%+) | Better (96%+) |
| **Setup** | More complex | Easier |
| **Best for** | Clean text, speed | Complex layouts, accuracy |

---

## ✅ After Installation Checklist

- [ ] Tesseract installed
- [ ] `tesseract --version` works
- [ ] `python check_ocr_setup.py` passes
- [ ] Demo runs without errors
- [ ] OCR extracts text (confidence > 0%)
- [ ] Can generate embeddings
- [ ] Can query images

---

## 🎯 Expected Working Demo

```
Step 1: Upload Image ✅
  → Amazon Landscape Lights.jpg

Step 2: Extract Text ✅
  → OCR Method: tesseract
  → Confidence: 92.5%
  → Words: 45
  → Time: 1.2s
  
  Extracted Text:
  "Search or ask a question
   Purchased 1 time
   Last purchased May 17, 2024
   Set reminder
   Visit the Jyoiat Store
   Solar Pathway Lights Outdoor..."

Step 3: Generate Embeddings ✅
  → Model loaded: all-MiniLM-L6-v2
  → Created 1 chunks
  → Generated 1 embeddings (384-dim)
  → FAISS index created

Step 4: Query ✅
  → Query: "When was this purchased?"
  → Result: "Last purchased May 17, 2024"
  → Similarity: 0.89
```

---

## 🚀 Quick Start (After Installation)

```powershell
# 1. Verify setup
python check_ocr_setup.py

# 2. Run demo
streamlit run demo_image_ingestion.py

# 3. Upload image with text

# 4. Click "Start OCR Extraction"

# 5. See text extracted!
```

---

**Install Tesseract now and your OCR will work perfectly!** 🎉
