# Vector Database Clear Button Guide 🗑️

## ✅ NEW FEATURE: Clear Vector Databases from UI!

You now have **"Manage" buttons** in the Document Ingestion tab that let you delete vector databases directly from the UI!

---

## 🎯 How to Use

### For FAISS Indexes

**Step 1: Go to Document Ingestion Tab**
```
📄 Ingest Document → Select "FAISS (Local Index)"
```

**Step 2: Click "Manage Indexes" Button**
```
📁 Index Configuration
┌─────────────────────────────────────┐
│ Index Name: [document_index    ]   │
│                    [🗑️ Manage Indexes] │
└─────────────────────────────────────┘
```

**Step 3: Select Index to Delete**
```
🗑️ Index Management
📊 Found 20 indexes

Select index to delete:
[Demo1_index (Text) - Empty        ▼]

⚠️ You are about to delete: Demo1_index
- Type: Text
- Status: Empty
- Path: `data/indexes/Demo1_index`

[🗑️ Delete Index]  [❌ Cancel]
```

**Step 4: Confirm Deletion**
- Click "🗑️ Delete Index"
- Index is permanently deleted
- Refresh page to see updated list

---

### For Weaviate Collections

**Step 1: Go to Document Ingestion Tab**
```
📄 Ingest Document → Select "Weaviate (Cloud Vector DB)"
```

**Step 2: Click "Manage Collections" Button**
```
📚 Collection Configuration
┌─────────────────────────────────────┐
│ Collection Name: [my_docs      ]   │
│                [🗑️ Manage Collections] │
└─────────────────────────────────────┘
```

**Step 3: Select Collection to Delete**
```
🗑️ Collection Management
📊 Found 5 collections

Select collection to delete:
[company_docs - 150 objects    ▼]

⚠️ You are about to delete: company_docs
- Type: Weaviate Collection
- Status: 150 objects
- Objects: 150

[🗑️ Delete Collection]  [❌ Cancel]
```

**Step 4: Confirm Deletion**
- Click "🗑️ Delete Collection"
- Collection is permanently deleted from Weaviate
- Refresh page to see updated list

---

## 📊 What You'll See

### FAISS Index Manager
```
🗑️ Index Management
📊 Found 20 indexes

Available indexes:
- AWS_index (FAISS) - 5 files
- Bylaws2025_index (Text) - Empty
- CNN_index (Text) - Empty
- Demo1_index (Text) - Empty
- GenAI-document_index (Text) - 15 files
- HOA_index (Text) - Empty
...

Select index to delete: [-- Select an index -- ▼]
```

### Weaviate Collection Manager
```
🗑️ Collection Management
📊 Found 5 collections

Available collections:
- company_docs - 150 objects
- bylaws_2024 - 45 objects
- test_collection - Empty
- demo_data - 10 objects
- archived_docs - 200 objects

Select collection to delete: [-- Select a collection -- ▼]
```

---

## 🎨 UI Features

### Smart Status Display
- **Empty** - No files/objects (safe to delete)
- **X files** - FAISS index with X files
- **X objects** - Weaviate collection with X objects
- **Unknown** - Status could not be determined

### Safety Features
1. **Dropdown Selection** - Must explicitly select what to delete
2. **Warning Message** - Shows what you're about to delete
3. **Detailed Info** - Type, status, and path/object count
4. **Confirmation Required** - Must click "Delete" button
5. **Cancel Option** - Can back out at any time

### Visual Feedback
```
⚠️ You are about to delete: Demo1_index
- Type: Text
- Status: Empty
- Path: `data/indexes/Demo1_index`

[🗑️ Delete Index]  [❌ Cancel]
     ↓ Click
✅ Deleted Demo1_index
🔄 Refresh the page to see updated list
```

---

## 🔍 Common Scenarios

### Scenario 1: Delete Empty Test Indexes
**Problem:** Created many test indexes during development

**Solution:**
1. Click "🗑️ Manage Indexes"
2. Select empty indexes one by one
3. Delete each one
4. Refresh page

**Result:** Clean workspace!

### Scenario 2: Delete Failed Ingestion
**Problem:** Ingestion failed, left partial data

**Solution:**
1. Click "🗑️ Manage Indexes" or "🗑️ Manage Collections"
2. Find the failed index/collection
3. Delete it
4. Re-run ingestion

**Result:** Fresh start!

### Scenario 3: Clear Old Data
**Problem:** Want to rebuild index with new documents

**Solution:**
1. Click manage button
2. Select old index/collection
3. Delete it
4. Create new one with same name

**Result:** Updated data!

---

## ⚠️ Important Notes

### Before Deleting
- ✅ **Check status** - Empty vs. has data
- ✅ **Verify name** - Make sure it's the right one
- ✅ **Backup if needed** - No undo!

### After Deleting
- 🔄 **Refresh page** - To see updated list
- 📝 **Re-ingest if needed** - Data is gone
- ✅ **Verify deletion** - Check it's no longer listed

### What Gets Deleted

**FAISS Indexes:**
- All files in `data/indexes/[index_name]/`
- All files in `data/faiss_index/[index_name]/`
- Entire directory is removed

**Weaviate Collections:**
- All objects in the collection
- Collection schema
- Collection metadata
- **Note:** Data is deleted from Weaviate server

---

## 🧪 Testing the Feature

### Safe Test
1. Create a test index: `mkdir data/indexes/TEST_DELETE_ME`
2. Go to UI → Click "🗑️ Manage Indexes"
3. Select "TEST_DELETE_ME"
4. Click "🗑️ Delete Index"
5. Verify it's gone: `ls data/indexes/`

### What If I Accidentally Delete?
**FAISS:** No recovery unless you have backups
**Weaviate:** No recovery unless you have backups

**Prevention:**
- Always double-check the name
- Read the warning message
- Use the Cancel button if unsure

---

## 📋 Quick Reference

| Task | Steps |
|------|-------|
| Delete FAISS index | Ingest Tab → FAISS → Manage Indexes → Select → Delete |
| Delete Weaviate collection | Ingest Tab → Weaviate → Manage Collections → Select → Delete |
| View all indexes | Click Manage button → See list |
| Cancel deletion | Click "❌ Cancel" button |
| Close manager | Click "Close" or navigate away |

---

## 🔧 Troubleshooting

### "No indexes found"
**Cause:** No indexes exist yet

**Solution:** Create an index first by ingesting documents

### "Error deleting index"
**Cause:** File permissions or locked files

**Solution:**
- Stop Streamlit
- Close any processes using the files
- Try again

### "Error accessing Weaviate"
**Cause:** Weaviate server not running

**Solution:**
- Check Weaviate connection
- Verify server is running
- Check credentials

### Manager won't close
**Cause:** UI state issue

**Solution:**
- Click "Close" button
- Or refresh the page (F5)

---

## 💡 Pro Tips

### Bulk Deletion
For deleting many indexes at once, use the cleanup script:
```bash
python cleanup_indexes.py
```

### Check Before Delete
Hover over the dropdown to see full details:
```
Demo1_index (Text) - Empty
GenAI-document_index (Text) - 15 files  ← Has data!
```

### Quick Access
The manage button is always visible next to the index/collection name input!

---

## 🎉 Benefits

**Before (Manual):**
```bash
# Had to use terminal
rm -rf data/indexes/Demo1_index
# Or run cleanup script
python cleanup_indexes.py
```

**After (UI Button):**
```
Click → Select → Delete → Done! ✅
```

**Advantages:**
- ✅ No terminal needed
- ✅ Visual feedback
- ✅ See all indexes at once
- ✅ Safe confirmation
- ✅ Works for both FAISS and Weaviate

---

## 📝 Summary

### What You Get
- **🗑️ Manage Indexes** button for FAISS
- **🗑️ Manage Collections** button for Weaviate
- Interactive UI for deletion
- Safety confirmations
- Status display (empty vs. has data)

### How to Use
1. Go to Document Ingestion tab
2. Select backend (FAISS or Weaviate)
3. Click manage button
4. Select what to delete
5. Confirm deletion
6. Done!

### Safety Features
- Dropdown selection (no accidental clicks)
- Warning messages
- Detailed information
- Cancel option
- Confirmation required

---

<p align="center">Now you can manage your vector databases directly from the UI! 🎉</p>
