"""
PDF Dependency Checker
Diagnoses PDF extraction issues and missing dependencies
"""

import sys

print("="*60)
print("🔍 PDF EXTRACTION DEPENDENCY CHECKER")
print("="*60)
print()

# Track what's installed
installed_count = 0
missing_libraries = []
installed_libraries = []

# Check pdfplumber
print("📦 Checking PDF Extraction Libraries...")
print("-"*60)

try:
    import pdfplumber
    print("✅ pdfplumber: INSTALLED")
    print(f"   Version: {pdfplumber.__version__ if hasattr(pdfplumber, '__version__') else 'Unknown'}")
    installed_count += 1
    installed_libraries.append("pdfplumber")
except ImportError:
    print("❌ pdfplumber: NOT INSTALLED")
    print("   Install: pip install pdfplumber")
    missing_libraries.append("pdfplumber")

# Check PyMuPDF
try:
    import fitz
    print("✅ PyMuPDF (fitz): INSTALLED")
    print(f"   Version: {fitz.__version__ if hasattr(fitz, '__version__') else 'Unknown'}")
    installed_count += 1
    installed_libraries.append("PyMuPDF")
except ImportError:
    print("❌ PyMuPDF (fitz): NOT INSTALLED")
    print("   Install: pip install PyMuPDF")
    missing_libraries.append("PyMuPDF")

# Check PyPDF2
try:
    import PyPDF2
    print("✅ PyPDF2: INSTALLED")
    print(f"   Version: {PyPDF2.__version__ if hasattr(PyPDF2, '__version__') else 'Unknown'}")
    installed_count += 1
    installed_libraries.append("PyPDF2")
except ImportError:
    print("❌ PyPDF2: NOT INSTALLED")
    print("   Install: pip install PyPDF2")
    missing_libraries.append("PyPDF2")

# Check pypdf
try:
    import pypdf
    print("✅ pypdf: INSTALLED")
    print(f"   Version: {pypdf.__version__ if hasattr(pypdf, '__version__') else 'Unknown'}")
    if "PyPDF2" not in installed_libraries:
        installed_count += 1
    installed_libraries.append("pypdf")
except ImportError:
    print("❌ pypdf: NOT INSTALLED")
    print("   Install: pip install pypdf")
    if "PyPDF2" not in missing_libraries:
        missing_libraries.append("pypdf")

print()
print("📦 Checking OCR Support (Optional for Scanned PDFs)...")
print("-"*60)

# Check OCR support
ocr_available = True

try:
    import pytesseract
    print("✅ pytesseract: INSTALLED (OCR support)")
    print(f"   Version: {pytesseract.__version__ if hasattr(pytesseract, '__version__') else 'Unknown'}")
except ImportError:
    print("⚠️  pytesseract: NOT INSTALLED (OCR not available)")
    print("   Install: pip install pytesseract")
    print("   Note: Also requires Tesseract OCR binary")
    ocr_available = False

try:
    import pdf2image
    print("✅ pdf2image: INSTALLED (OCR support)")
    print(f"   Version: {pdf2image.__version__ if hasattr(pdf2image, '__version__') else 'Unknown'}")
except ImportError:
    print("⚠️  pdf2image: NOT INSTALLED (OCR not available)")
    print("   Install: pip install pdf2image")
    ocr_available = False

try:
    from PIL import Image
    print("✅ Pillow (PIL): INSTALLED")
    print(f"   Version: {Image.__version__ if hasattr(Image, '__version__') else 'Unknown'}")
except ImportError:
    print("⚠️  Pillow: NOT INSTALLED")
    print("   Install: pip install pillow")

print()
print("="*60)
print("📊 DIAGNOSIS SUMMARY")
print("="*60)

print(f"\n✅ Installed PDF Libraries: {installed_count}/3")
if installed_libraries:
    for lib in installed_libraries:
        print(f"   • {lib}")

if missing_libraries:
    print(f"\n❌ Missing PDF Libraries: {len(missing_libraries)}")
    for lib in missing_libraries:
        print(f"   • {lib}")

print()
print("="*60)
print("💡 RECOMMENDATIONS")
print("="*60)
print()

if installed_count == 0:
    print("❌ CRITICAL: NO PDF libraries installed!")
    print()
    print("📝 Action Required:")
    print("   Run this command to install all PDF libraries:")
    print()
    print("   pip install pdfplumber PyMuPDF pypdf PyPDF2")
    print()
    print("   Then restart your Streamlit app:")
    print("   streamlit run genai_dashboard_modular.py")
    
elif installed_count < 3:
    print("⚠️  WARNING: Some PDF libraries missing")
    print()
    print("📝 Recommended Action:")
    print("   Install missing libraries for better extraction:")
    print()
    if missing_libraries:
        print(f"   pip install {' '.join(missing_libraries)}")
    print()
    print("   Current status: Basic extraction may work, but some PDFs might fail")
    
else:
    print("✅ EXCELLENT: All PDF extraction libraries installed!")
    print()
    print("📝 Your system is ready for PDF extraction.")
    print()
    print("   If you're still getting errors, the PDF might be:")
    print("   1. 📄 Scanned (image-based) - Needs OCR")
    print("   2. 🔒 Password-protected - Remove protection first")
    print("   3. 💔 Corrupted - Try re-downloading")
    print("   4. 📭 Empty - No text content")

if not ocr_available:
    print()
    print("⚠️  OCR Support: NOT AVAILABLE")
    print()
    print("📝 For scanned PDFs (image-based), install OCR:")
    print()
    print("   1. Install Tesseract OCR:")
    print("      Windows: https://github.com/UB-Mannheim/tesseract/wiki")
    print("      Mac: brew install tesseract")
    print("      Linux: sudo apt-get install tesseract-ocr")
    print()
    print("   2. Install Python libraries:")
    print("      pip install pytesseract pdf2image pillow")
else:
    print()
    print("✅ OCR Support: AVAILABLE")
    print("   Scanned PDFs can be processed!")

print()
print("="*60)
print("🧪 NEXT STEPS")
print("="*60)
print()

if installed_count == 0:
    print("1. Install PDF libraries (see command above)")
    print("2. Restart Streamlit")
    print("3. Try uploading your PDF again")
elif installed_count < 3:
    print("1. (Optional) Install missing libraries for better support")
    print("2. Try uploading your PDF")
    print("3. If it fails, check if PDF is scanned/protected/corrupted")
else:
    print("1. Try uploading your PDF")
    print("2. If extraction fails, check:")
    print("   • Can you select text in the PDF? (If no → scanned)")
    print("   • Is the PDF password-protected?")
    print("   • Is the file corrupted?")
    print("3. Check Streamlit console for detailed error messages")

print()
print("="*60)
print("📚 DOCUMENTATION")
print("="*60)
print()
print("For detailed troubleshooting, see:")
print("   FIX_PDF_EXTRACTION_ERROR.md")
print()
print("="*60)
print()

# Exit with appropriate code
if installed_count == 0:
    sys.exit(1)  # Critical error
elif installed_count < 3:
    sys.exit(0)  # Warning but functional
else:
    sys.exit(0)  # All good
