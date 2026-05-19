# Weaviate Integration Setup Guide

## Overview

This guide walks you through setting up Weaviate as the main vector database for VaultMind GenAI Knowledge Assistant, replacing the current FAISS implementation with a more scalable and feature-rich solution.

## Architecture

The Weaviate integration provides:
- **Unified Vector Store Interface**: Seamless switching between FAISS and Weaviate
- **Automatic Backend Detection**: Smart fallback to available vector store
- **Migration Tools**: Easy migration from existing FAISS indexes
- **Enhanced Search**: Hybrid search combining vector and keyword matching
- **Multi-tenancy**: Better isolation and security for enterprise use

## Installation

### 1. Install Dependencies

```bash
pip install -r requirements-weaviate.txt
```

### 2. Weaviate Server Setup

#### Option A: Local Docker Instance
```bash
# Start Weaviate with OpenAI vectorizer
docker run -d \
  --name weaviate \
  -p 8080:8080 \
  -e QUERY_DEFAULTS_LIMIT=25 \
  -e AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED=true \
  -e PERSISTENCE_DATA_PATH='/var/lib/weaviate' \
  -e DEFAULT_VECTORIZER_MODULE='text2vec-openai' \
  -e ENABLE_MODULES='text2vec-openai' \
  -e OPENAI_APIKEY='your-openai-key' \
  semitechnologies/weaviate:latest
```

#### Option B: Weaviate Cloud Services (WCS)
1. Sign up at [Weaviate Cloud Services](https://console.weaviate.cloud/)
2. Create a new cluster
3. Note your cluster URL and API key

### 3. Environment Configuration

Create a `.env` file or set environment variables:

```bash
# Weaviate Configuration
WEAVIATE_URL=http://localhost:8080  # or your WCS cluster URL
WEAVIATE_API_KEY=your-wcs-api-key   # only for cloud instances
OPENAI_API_KEY=your-openai-key      # for vectorization

# Optional Configuration
WEAVIATE_TIMEOUT=30
WEAVIATE_BATCH_SIZE=100
WEAVIATE_VECTORIZER=text2vec-openai
WEAVIATE_HYBRID_SEARCH=true
```

## Weaviate Python SDK v4 Connection and Collection Creation

### 1. Connect (Cloud and Local)

```python
import os
import weaviate
from weaviate.auth import AuthApiKey

url = os.getenv("WEAVIATE_URL")
api_key = os.getenv("WEAVIATE_API_KEY")
openai_key = os.getenv("OPENAI_API_KEY")

# Cloud (WCS)
headers = {"X-OpenAI-Api-Key": openai_key} if openai_key else None
client = weaviate.connect_to_weaviate_cloud(
    cluster_url=url,
    auth_credentials=AuthApiKey(api_key),
    headers=headers,  # SDK variants without 'headers' also work
)

# OR Local
# client = weaviate.connect_to_local(host="localhost", port=8080, grpc_port=50051)
```

Notes:
- If you have a console URL (e.g., `https://console.weaviate.cloud/<...>/cluster-details/<cluster_id>`), the actual endpoint is `https://<cluster_id>.weaviate.network`. The `WeaviateManager` in `utils/weaviate_manager.py` normalizes this automatically.
- Optional environment variables supported by the manager:
  - `WEAVIATE_GRPC_URL`, `WEAVIATE_GRPC_PORT`
  - `WEAVIATE_PATH_PREFIX`, `WEAVIATE_PATH_PREFIXES`

### 2. Create a Collection (SDK-first with NamedVectors)

Use NamedVectors for OpenAI vectorization. Important: pass `vector_config` (Dep024 fix).

```python
from weaviate.classes.config import Configure, Property, DataType

client.collections.create(
    name="Bylaws20",
    description="Bylaws test collection",
    properties=[
        Property(name="content", data_type=DataType.TEXT, description="Main text content"),
        Property(name="source", data_type=DataType.TEXT, description="Source path"),
        Property(name="source_type", data_type=DataType.TEXT, description="Source type"),
        Property(name="created_at", data_type=DataType.DATE, description="Creation timestamp"),
        Property(name="metadata", data_type=DataType.OBJECT, description="Additional metadata"),
    ],
    vector_config=[
        Configure.NamedVectors.text2vec_openai(
            name="content",
            source_properties=["content"],
        )
    ],
)
```

### 3. REST Fallback for Class Creation (WCS-friendly)

Some WCS clusters disallow `POST /v1/schema/classes` (405). Fallback to `PUT /v1/schema/{className}`. If you define an `object` property, include at least one `nestedProperties` entry; otherwise you'll get 422. If 422 persists, coerce unsupported `object` to `text` and retry.

```python
import httpx

BASE = os.getenv("WEAVIATE_URL").rstrip("/")
headers = {"Authorization": f"Bearer {api_key}", "X-API-KEY": api_key}
if openai_key:
    headers["X-OpenAI-Api-Key"] = openai_key

payload = {
    "class": "Bylaws20",
    "description": "Bylaws test collection",
    "vectorizer": "text2vec-openai" if openai_key else "none",
    "properties": [
        {"name": "content", "dataType": ["text"]},
        {"name": "source", "dataType": ["text"]},
        {"name": "source_type", "dataType": ["text"]},
        {
            "name": "metadata",
            "dataType": ["object"],
            "nestedProperties": [
                {"name": "kv", "dataType": ["text"], "description": "Generic key/value holder"}
            ]
        },
    ],
}

r = httpx.post(f"{BASE}/v1/schema/classes", headers=headers, json=payload, timeout=30)
if r.status_code == 405:
    r = httpx.put(f"{BASE}/v1/schema/Bylaws20", headers=headers, json=payload, timeout=30)
if r.status_code == 422:
    # Coerce object -> text and retry
    fixed = dict(payload)
    fixed["properties"] = [
        {**p, "dataType": ["text"]} if p.get("dataType") == ["object"] else p
        for p in payload["properties"]
    ]
    # Retry PUT first for WCS
    r = httpx.put(f"{BASE}/v1/schema/Bylaws20", headers=headers, json=fixed, timeout=30)
    if r.status_code not in (200, 201, 409):
        r = httpx.post(f"{BASE}/v1/schema/classes", headers=headers, json=fixed, timeout=30)

print("Create status:", r.status_code, getattr(r, "text", ""))
```

### 4. Verify Collections

- SDK: `client.collections.list_all()`
- REST v2: `GET {BASE}/v2/collections`
- REST v1: `GET {BASE}/v1/schema` (list class names)

Quick validation:

```bash
python scripts/verify_weaviate_simple.py
```

## Migration from FAISS

### 1. Analyze Current FAISS Indexes

```python
from utils.migration_tools import FAISSToWeaviateMigrator

# Create migrator instance
migrator = FAISSToWeaviateMigrator()

# Generate migration report
report = migrator.generate_migration_report("migration_report.md")
print(report)
```

### 2. Run Migration

```python
# Dry run first (recommended)
dry_run_report = migrator.migrate_all_indexes(dry_run=True)
print(f"Would migrate {dry_run_report['total_indexes']} indexes")

# Actual migration
migration_report = migrator.migrate_all_indexes(dry_run=False)
print(f"Successfully migrated: {migration_report['successful_migrations']}")
print(f"Failed migrations: {migration_report['failed_migrations']}")
```

### 3. Verify Migration

```python
from utils.unified_vector_store import get_vector_store

# Get unified vector store (will auto-detect Weaviate)
vector_store = get_vector_store()

# List available collections
collections = vector_store.list_collections()
print(f"Available collections: {collections}")

# Test search
results = vector_store.search("your test query", top_k=5)
print(f"Found {len(results)} results")
```

## Usage Across Tabs

### 1. Update Existing Code

Replace direct FAISS calls with unified vector store:

```python
# Old FAISS approach
from utils.direct_vector_search import search_vector_store
results = search_vector_store(query, index_name, top_k)

# New unified approach
from utils.unified_vector_store import get_vector_store
vector_store = get_vector_store()
results = vector_store.search(query, collection_name, top_k)
```

### 2. Enhanced Search Features

```python
# Hybrid search (vector + keyword)
results = vector_store.search(
    query="machine learning",
    collection_name="documents",
    top_k=10,
    search_method="hybrid",
    alpha=0.7  # 0=pure vector, 1=pure keyword
)

# Filtered search
results = vector_store.search(
    query="AI research",
    collection_name="documents", 
    top_k=5,
    where_filter={"source_type": "pdf"}
)
```

### 3. Adding New Documents

```python
# Add documents to Weaviate
documents = [
    {
        "content": "Document content here...",
        "source": "document.pdf",
        "source_type": "pdf",
        "metadata": {"author": "John Doe", "date": "2024-01-01"}
    }
]

success = vector_store.add_documents(documents, "documents")
```

## Tab-Specific Integration

### Multi-Content Enhanced Tab
- **Excel Data**: Store processed Excel content for AI analysis
- **Web Search**: Cache web search results for faster retrieval
- **PowerBI**: Index PowerBI report metadata and content

### Chat Assistant Tab
- **Conversation History**: Store chat sessions for context
- **Knowledge Retrieval**: Enhanced search across all knowledge sources

### Agent Assistant Tab
- **Tool Results**: Cache agent tool execution results
- **Context Memory**: Maintain conversation context across sessions

### Query Assistant Tab
- **Query History**: Store successful queries and results
- **Performance Analytics**: Track query performance and relevance

## Configuration Management

### Collection Schemas

Predefined schemas for different data types:

```python
from config.weaviate_config import create_default_collections

# Get available schemas
schemas = create_default_collections()

# Available schemas:
# - documents: General document storage
# - web_content: Web scraped content  
# - chat_history: Chat conversations
# - excel_data: Excel file content
# - powerbi_reports: PowerBI metadata
```

### Custom Collections

```python
# Create custom collection
vector_store.create_collection(
    name="custom_data",
    description="Custom data collection",
    properties={
        "category": {"data_type": "TEXT", "description": "Data category"},
        "priority": {"data_type": "INT", "description": "Priority level"}
    }
)
```

## Performance Optimization

### 1. Batch Operations
- Use batch insertion for large datasets
- Configure appropriate batch sizes (default: 100)

### 2. Search Optimization
- Use hybrid search for better relevance
- Implement result caching for frequent queries
- Filter searches by collection when possible

### 3. Memory Management
- Monitor Weaviate memory usage
- Implement collection cleanup for old data
- Use pagination for large result sets

## Monitoring and Maintenance

### 1. Health Checks

```python
from utils.weaviate_manager import get_weaviate_manager

manager = get_weaviate_manager()

# Check connection
try:
    collections = manager.list_collections()
    print(f"✅ Weaviate healthy - {len(collections)} collections")
except Exception as e:
    print(f"❌ Weaviate error: {e}")
```

### 2. Collection Statistics

```python
# Get collection stats
stats = manager.get_collection_stats("documents")
print(f"Collection: {stats['name']}")
print(f"Objects: {stats['total_objects']:,}")
```

### 3. Backup and Recovery

- Regular backups of Weaviate data
- Export collections to JSON for portability
- Version control for schema changes

## Troubleshooting

### Common Issues

1. **Connection Failed**
   - Check Weaviate server is running
   - Verify URL and credentials
   - Check firewall settings

2. **Migration Errors**
   - Ensure sufficient disk space
   - Check FAISS file permissions
   - Verify document format compatibility

3. **Search Performance**
   - Optimize vectorizer settings
   - Adjust batch sizes
   - Use appropriate search methods

4. **Schema creation returns 405 (Method Not Allowed)**
   - Some WCS clusters block `POST /v1/schema/classes`.
   - Retry with `PUT /v1/schema/{className}`. The manager in `utils/weaviate_manager.py` already implements this fallback.

5. **Schema validation 422 for `object` property**
   - For `object` (and `object[]`) properties, add at least one entry in `nestedProperties`.
   - Minimal example:
     ```json
     {
       "name": "metadata",
       "dataType": ["object"],
       "nestedProperties": [{"name": "kv", "dataType": ["text"], "description": "Generic key/value holder"}]
     }
     ```
   - As a last resort, coerce unsupported `object` properties to `text` and retry.

6. **Deprecation error for `vectorizer_config` (Dep024)**
   - Use `vector_config` with SDK v4 NamedVectors, e.g. `client.collections.create(..., vector_config=[Configure.NamedVectors.text2vec_openai(...)])`.
   - The guide and `utils/weaviate_manager.py` are updated accordingly.

### Debug Mode

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Enable debug logging for Weaviate operations
```

## Next Steps

1. **Install Dependencies**: Run `pip install -r requirements-weaviate.txt`
2. **Setup Weaviate Server**: Choose local Docker or cloud instance
3. **Configure Environment**: Set required environment variables
4. **Run Migration**: Use migration tools to move FAISS data
5. **Update Tabs**: Replace FAISS calls with unified vector store
6. **Test Integration**: Verify search functionality across all tabs

## Quick Smoke Test (WCS/GCP-friendly)

These steps quickly validate connectivity, collection creation, and ingestion against Weaviate Cloud (GCP) or local.

- Ensure your env is set in `config/weaviate.env`:
  - `WEAVIATE_URL`, `WEAVIATE_API_KEY`, optional `OPENAI_API_KEY`
  - Note: If you have a console URL, the manager auto-normalizes to the actual endpoint (e.g., `https://{cluster_id}.weaviate.network`).
  - Active GCP endpoint example: `https://r5dyopgssm6a9xfo2yg7a.c0.us-west3.gcp.weaviate.cloud`.

- Create or verify a collection and list all collections (adds file logger when `--debug` is used):

```bash
python scripts/create_and_list_weaviate_collection.py --name Bylaws20 --debug
```

- Ingest a sample text file into a collection and run a quick query:

```bash
python scripts/ingest_text_to_weaviate.py --file bylaws_basic_sample.txt --collection Bylaws20 --username tester --semantic --debug
```

- Simple SDK connectivity check:

```bash
python scripts/verify_weaviate_simple.py
```

Notes:
- The manager discovers REST path prefixes and tries v2 and GCP-specific endpoints (e.g., `/v2/collections`, `/api/rest/v2/collections`) before falling back to stable v1 schema endpoints.
- Debug logs are written to `weaviate_run.log` in the project root when `--debug` is provided. Increase verbosity with `logging.basicConfig(level=logging.DEBUG)` as needed.

## False "Collection not found" after creation

Some Weaviate deployments exhibit short consistency delays where a newly created collection is visible via REST before the Python SDK, or vice versa. To prevent false negatives:

- The `WeaviateManager.ensure_collection_ready()` method checks multiple endpoints and returns success if any detects the collection:
  - SDK: `client.collections.get(<name>)`
  - REST v2: `GET {BASE}/v2/collections` with automatic REST prefix discovery (including GCP-specific `/api/rest/v2/collections`)
  - REST v1: `GET {BASE}/v1/schema` as a stable fallback
- Authentication headers are built by `WeaviateManager._get_headers()` and include:
  - `Authorization: Bearer <WEAVIATE_API_KEY>` and `X-API-KEY: <WEAVIATE_API_KEY>`
  - `X-OpenAI-Api-Key: <OPENAI_API_KEY>` when present (for OpenAI vectorization compatibility)
- When running with `--debug`, check `weaviate_run.log` for messages like:
  - “REST prefix discovery …”
  - “SDK get failed …”
  - “Collection '<name>' is ready (REST schema)” or “(REST v2)”
  - “accessible via REST (SDK consistency delay)”

Recommended validation sequence:

- Create or verify a collection:
  - `python scripts/create_and_list_weaviate_collection.py --name Bylaws20 --debug`
- Ingest sample data and query:
  - `python scripts/ingest_text_to_weaviate.py --file bylaws_basic_sample.txt --collection Bylaws20 --username tester --semantic --debug`
- Tail the debug log for readiness and prefix selection details:
  - `Get-Content .\\weaviate_run.log -Tail 200`

## Support

For issues or questions:
- Check Weaviate documentation: https://weaviate.io/developers/weaviate
- Review migration logs for specific errors
- Test with sample data before full migration
