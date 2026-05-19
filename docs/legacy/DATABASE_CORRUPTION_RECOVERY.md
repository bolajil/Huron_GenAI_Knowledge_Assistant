# Database Corruption Recovery Guide for VaultMIND

This guide provides practical steps for diagnosing and recovering from database corruption in the VaultMIND Knowledge Assistant system. It focuses specifically on vector database issues that affect ByLaw content retrieval, but many principles apply to other types of database corruption.

## Signs of Database Corruption

1. **AttributeError: 'str' object has no attribute 'get'** - This specific error indicates that the system expected a dictionary but received a string from the vector database.
2. **"No content available" errors** - The system cannot retrieve content that should exist in the database.
3. **Partial or inconsistent query results** - Some queries work while similar ones fail.
4. **Slow or timing out queries** - Unusually slow response times can indicate index issues.

## Step 1: Diagnose the Problem

Run the provided diagnostic tools to confirm the issue:

```bash
# Test basic ByLaw content retrieval
python minimal_bylaw_test.py

# Check vector database health
python fix_vector_store.py
```

## Step 2: Create Backups

Before attempting any repairs, create backups of:

1. Vector database indices:
   - Default location: `data/faiss_index/`
   - Back up to: `data/backups/faiss_index/`

2. User database:
   - Default location: `data/users.db`
   - Back up to: `data/users.db.bak`

```bash
# Manual backup commands
mkdir -p data/backups/faiss_index
cp -r data/faiss_index/* data/backups/faiss_index/
cp data/users.db data/users.db.bak
```

## Step 3: Fix User Permissions

User permission issues can sometimes masquerade as database corruption. Run:

```bash
python fix_user_permissions.py
```

This will:
- Check if users have access to ByLaw content
- Update permissions for users who need access
- Create a database backup before making changes

## Step 4: Repair Vector Database

For vector database corruption, run:

```bash
python fix_vector_store.py
```

This interactive script will:
- Check if the ByLaw index exists and is healthy
- Create backups before any repair operations
- Offer options to fix or recreate the index

### Recovery Options

The script provides several recovery approaches:

1. **Fix corrupted index** - Attempts to repair the existing index
2. **Recreate empty index** - Creates a new empty index with the correct structure
3. **Create with template data** - Creates a new index with basic template content

## Step 5: Validate the Fix

After applying fixes, verify that the system is working:

```bash
# Run the minimal test again
python minimal_bylaw_test.py

# Try the direct access UI
streamlit run direct_bylaw_access.py
```

## Step 6: Implement Fallback Systems

Even after fixing the immediate issue, implement these fallback systems:

1. **Patch the agent assistant** to handle ByLaw queries directly:
   ```bash
   python patch_agent_assistant.py
   ```

2. **Use the standalone direct access UI** as a fallback:
   ```bash
   streamlit run direct_bylaw_access.py
   ```

## Advanced Recovery Techniques

If the basic recovery steps don't work, try these advanced techniques:

### 1. Manual Database Inspection

For the SQLite user database:

```bash
# Open SQLite shell
sqlite3 data/users.db

# List tables
.tables

# Check user permissions
SELECT username, permissions FROM users;

# Exit
.exit
```

### 2. FAISS Index Inspection

```python
# Python code to inspect a FAISS index
import faiss
import pickle

# Load the index
index = faiss.read_index("data/faiss_index/ByLawS2_index/index.faiss")

# Get basic info
print(f"Index size: {index.ntotal} vectors")
print(f"Vector dimension: {index.d}")

# Load the pickle file
with open("data/faiss_index/ByLawS2_index/index.pkl", "rb") as f:
    data = pickle.load(f)
    
# Examine the structure
print(data.keys())
```

### 3. Complete Reindexing

If repair fails, reindex the content:

```bash
# Assuming your ingestion script is in scripts/ingest_documents.py
python scripts/ingest_documents.py --source=bylaws --target=ByLawS2_index
```

## Prevention Measures

To prevent future database corruption:

1. **Regular Backups**: Schedule automated backups of vector indices and user database
2. **Health Checks**: Run `fix_vector_store.py` in check-only mode weekly
3. **Redundancy**: Implement multiple retrieval methods for critical content
4. **Monitoring**: Add alerting for database access issues

## Support

For persistent issues or assistance with this guide:

- Review the full fix documentation in `BYLAW_FIX_GUIDE.md`
- Check system logs for detailed error messages
- Contact the VaultMIND development team for specialized support
