# Index Cleanup Guide 🧹

## Quick Commands

### Option 1: Use the Cleanup Script (Recommended)
```bash
python cleanup_indexes.py
```

This interactive script will:
- ✅ List all indexes with their status
- ✅ Show which are empty
- ✅ Let you choose what to delete
- ✅ Require confirmation before deleting

---

### Option 2: Manual Deletion

#### Delete All Empty Indexes
```bash
# Windows (PowerShell)
Get-ChildItem -Path "data\indexes" -Directory | Where-Object { (Get-ChildItem $_.FullName -Recurse -File).Count -eq 0 } | Remove-Item -Recurse -Force

# Windows (Git Bash)
find data/indexes -type d -empty -delete

# Linux/Mac
find data/indexes -type d -empty -delete
```

#### Delete Specific Index
```bash
# Replace "Demo1_index" with your index name
rm -rf data/indexes/Demo1_index
```

#### Delete ALL Indexes (⚠️ DANGER!)
```bash
# This deletes EVERYTHING!
rm -rf data/indexes/*
rm -rf data/faiss_index/*
```

---

## 📁 Index Locations

Your indexes are stored in:

1. **Text-based indexes:** `data/indexes/`
   - Bylaws2025_index
   - Bylaws2027_index
   - CNN_index
   - Demo1_index
   - GenAI-document_index
   - HOA_index
   - NBC_index
   - October_index
   - Test-demo_index
   - W3schools_index
   - ... and more

2. **FAISS indexes:** `data/faiss_index/`
   - AWS_index

---

## 🎯 What to Delete

### Safe to Delete (Empty Indexes)
These have **0 files** and take up no space:
- Bylaws2025_index (0 items)
- Bylaws2027_index (0 items)
- Bylaws_index (0 items)
- CNN_index (0 items)
- Demo1_index (0 items)
- ... (all showing "0 items")

**Action:** Delete these to clean up clutter

### Keep (Indexes with Data)
These have files and contain actual indexed data:
- Any index showing file counts > 0
- Any index with size > 0 bytes

**Action:** Keep these unless you want to re-index

---

## 📝 Using the Cleanup Script

### Step 1: Run the Script
```bash
python cleanup_indexes.py
```

### Step 2: Review the List
```
============================================================
Current Indexes
============================================================

[data/indexes]
  - Bylaws2025_index              [EMPTY          ] 0 bytes
  - Demo1_index                   [EMPTY          ] 0 bytes
  - GenAI-document_index          [15 files       ] 1,234,567 bytes
  - HOA_index                     [EMPTY          ] 0 bytes
  ...
```

### Step 3: Choose an Option

**Option 1: Delete Empty Indexes (Safest)**
```
Enter choice (1-4): 1

[DRY RUN] Found 18 empty indexes:
  - Bylaws2025_index (data/indexes)
  - Demo1_index (data/indexes)
  ...

Proceed with deletion? (yes/no): yes

Type 'DELETE' to confirm: DELETE

[DELETED] Bylaws2025_index
[DELETED] Demo1_index
...
[SUCCESS] Deleted 18 empty indexes
```

**Option 2: Delete Specific Index**
```
Enter choice (1-4): 2

Enter index name: Demo1_index

Index: Demo1_index
Path: data/indexes/Demo1_index
Files: 0
Size: 0 bytes

Type 'DELETE' to confirm: DELETE

[SUCCESS] Deleted Demo1_index
```

**Option 3: Delete ALL Indexes (⚠️ DANGER!)**
```
Enter choice (1-4): 3

DANGER: This will delete ALL indexes in:
  - data/indexes
  - data/faiss_index

Type 'DELETE ALL INDEXES' to confirm: DELETE ALL INDEXES

[DELETED] Bylaws2025_index
[DELETED] Demo1_index
...
[SUCCESS] Deleted 20 indexes
```

---

## 🔍 Check Index Status

### Quick Check
```bash
# Count files in each index
for dir in data/indexes/*; do
    echo "$dir: $(find "$dir" -type f | wc -l) files"
done
```

### Detailed Check
```bash
# Show size of each index
du -sh data/indexes/*
```

---

## 🛡️ Safety Features

The cleanup script has multiple safety checks:

1. **Dry Run First:** Shows what will be deleted before doing it
2. **Confirmation Required:** Must type exact phrases to confirm
3. **Error Handling:** Won't crash if a directory is locked
4. **Detailed Logging:** Shows exactly what was deleted

---

## 📊 Common Scenarios

### Scenario 1: Clean Up Test Indexes
**Problem:** Created many test indexes during development

**Solution:**
```bash
python cleanup_indexes.py
# Choose Option 1 (Delete empty indexes)
# Or manually delete specific ones with Option 2
```

### Scenario 2: Start Fresh
**Problem:** Want to rebuild all indexes from scratch

**Solution:**
```bash
python cleanup_indexes.py
# Choose Option 3 (Delete ALL indexes)
# Then re-ingest your documents
```

### Scenario 3: Remove Specific Failed Index
**Problem:** One index got corrupted or failed

**Solution:**
```bash
python cleanup_indexes.py
# Choose Option 2
# Enter the index name
```

---

## ⚠️ Important Notes

### Before Deleting
- ✅ **Backup important indexes** if unsure
- ✅ **Stop Streamlit** to avoid conflicts
- ✅ **Check if index has data** (file count > 0)

### After Deleting
- 🔄 **Restart Streamlit** to refresh index list
- 📝 **Re-ingest documents** if you deleted data indexes
- ✅ **Verify** indexes are gone from UI

---

## 🔄 Re-creating Indexes

After cleanup, to rebuild indexes:

### Method 1: Via UI
1. Go to "📄 Ingest Document" tab
2. Select backend (FAISS or Weaviate)
3. Upload documents
4. Choose index name
5. Click "Start Ingestion"

### Method 2: Via Script
```bash
# If you have a bulk ingestion script
python bulk_ingest.py --index-name "MyNewIndex" --docs-folder "./documents"
```

---

## 🧪 Test the Cleanup

### Safe Test (No Deletion)
```bash
# Just list indexes
python cleanup_indexes.py
# Choose Option 4 (Exit)
```

### Delete One Test Index
```bash
# Create a test index first
mkdir -p data/indexes/TEST_DELETE_ME

# Run cleanup
python cleanup_indexes.py
# Choose Option 2
# Enter: TEST_DELETE_ME
# Confirm deletion

# Verify it's gone
ls data/indexes/
```

---

## 📞 Troubleshooting

### "Permission denied"
**Cause:** Streamlit or another process is using the index

**Solution:**
```bash
# Stop Streamlit
# Close any Python processes
# Try again
```

### "Directory not empty"
**Cause:** Hidden files or system files

**Solution:**
```bash
# Force delete (Windows)
rmdir /s /q data\indexes\IndexName

# Force delete (Linux/Mac)
rm -rf data/indexes/IndexName
```

### "Index still shows in UI"
**Cause:** Streamlit cache

**Solution:**
```bash
streamlit cache clear
streamlit run genai_dashboard_modular.py
```

---

## 📋 Quick Reference

| Task | Command |
|------|---------|
| List all indexes | `python cleanup_indexes.py` (Option 4) |
| Delete empty indexes | `python cleanup_indexes.py` (Option 1) |
| Delete specific index | `python cleanup_indexes.py` (Option 2) |
| Delete ALL indexes | `python cleanup_indexes.py` (Option 3) |
| Manual delete | `rm -rf data/indexes/IndexName` |
| Check index size | `du -sh data/indexes/*` |
| Count files | `find data/indexes/IndexName -type f \| wc -l` |

---

## ✅ Summary

**Safest Method:**
```bash
python cleanup_indexes.py
# Choose Option 1 (Delete empty indexes only)
```

**This will:**
- ✅ Only delete empty directories
- ✅ Keep all indexes with data
- ✅ Require confirmation
- ✅ Show what was deleted

**Result:** Clean workspace with no data loss! 🎉

---

<p align="center">Use the cleanup script for safe, interactive index management!</p>
