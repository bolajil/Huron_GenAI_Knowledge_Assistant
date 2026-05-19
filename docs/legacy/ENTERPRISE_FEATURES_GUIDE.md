# VaultMind Enterprise Features Guide

## Overview

VaultMind has been enhanced with enterprise-grade features that provide advanced document processing, intelligent retrieval, and structured output capabilities. These features are designed to work seamlessly with your existing system while providing significant improvements in accuracy, performance, and user experience.

## Enterprise Components

### 1. Hybrid Search & Re-Ranking

**Location**: `utils/enterprise_hybrid_search.py`

**Features**:
- **BM25 Keyword Search**: Traditional keyword-based search for exact term matching
- **Vector Similarity Search**: Semantic similarity using embeddings
- **Cross-Encoder Re-Ranking**: Advanced transformer-based re-ranking for precision
- **Configurable Weights**: Adjust vector/keyword balance (default: 60/40)

**Usage**:
```python
from utils.enterprise_hybrid_search import get_enterprise_hybrid_search

# Initialize hybrid search
hybrid_search = get_enterprise_hybrid_search(vector_weight=0.6, keyword_weight=0.4)

# Perform search
results = hybrid_search.search(
    query="What are the bylaws regarding board meetings?",
    index_name="ByLaw_index",
    max_results=10
)
```

**Benefits**:
- Combines semantic understanding with exact keyword matching
- Improved relevance through transformer re-ranking
- Handles both conceptual and specific queries effectively

### 2. Advanced Semantic Chunking

**Location**: `utils/enterprise_semantic_chunking.py`

**Features**:
- **Document Type Detection**: Automatically detects legal, technical, or general documents
- **Structure-Aware Splitting**: Respects document hierarchy (articles, sections, headers)
- **LangChain-Style Processing**: Recursive text splitting with configurable separators
- **Rich Metadata**: Preserves document structure and context information

**Usage**:
```python
from utils.enterprise_semantic_chunking import get_enterprise_semantic_chunker

# Initialize chunker
chunker = get_enterprise_semantic_chunker({
    "chunk_size": 1500,
    "chunk_overlap": 500,
    "respect_section_breaks": True,
    "extract_tables": True,
    "preserve_heading_structure": True
})

# Chunk document
chunks = chunker.chunk_document(text, source, document_type="legal")
```

**Benefits**:
- Maintains document context and structure
- Specialized handling for different document types
- Larger chunk sizes (1500 chars) with substantial overlap (500 chars)
- Preserves legal article/section boundaries

### 3. Structured LLM Output

**Location**: `utils/enterprise_structured_output.py`

**Features**:
- **Pydantic Models**: Validated, structured response formats
- **Multiple Response Types**: Legal, technical, and general response templates
- **Citation Extraction**: Automatic extraction and formatting of source citations
- **Export Capabilities**: JSON export for integration and archival

**Usage**:
```python
from utils.enterprise_structured_output import get_enterprise_output_formatter

# Initialize formatter
formatter = get_enterprise_output_formatter()

# Create structured prompt
prompt = formatter.create_structured_prompt(query, context, "legal")

# Parse LLM response (after sending to LLM)
structured_response = formatter.parse_llm_response(llm_output, "legal")

# Format for display
display_text = formatter.format_for_display(structured_response)
```

**Response Structure (Legal)**:
```json
{
    "direct_answer": "Based on Article II, Section 3...",
    "applicable_articles": ["Article II", "Article V"],
    "key_provisions": ["Board meetings require...", "Quorum consists of..."],
    "citations": ["ByLaw Document, Article II, Section 3, Page 5"],
    "legal_interpretation": "The provisions indicate that...",
    "confidence_score": 0.85
}
```

### 4. Metadata Filtering

**Location**: `utils/enterprise_metadata_filtering.py`

**Features**:
- **Complex Filter Criteria**: Support for multiple operators (eq, gt, contains, regex)
- **Predefined Filters**: Common filter templates for legal documents, articles, etc.
- **Filter Combinations**: AND/OR logic for complex filtering
- **Dynamic Suggestions**: Intelligent filter recommendations based on content

**Usage**:
```python
from utils.enterprise_metadata_filtering import get_enterprise_metadata_filter

# Initialize filter system
filter_system = get_enterprise_metadata_filter()

# Create article filter
article_filter = filter_system.create_article_filter(["II", "III", "V"])

# Apply filters
filtered_docs = filter_system.filter_documents(documents, article_filter)

# Use predefined filters
legal_docs = filter_system.filter_documents(documents, "legal_documents")
```

**Filter Examples**:
```python
# Filter by article numbers
{"article_number": {"operator": "in", "value": ["II", "III", "V"]}}

# Filter by content quality
{"char_count": {"operator": "gte", "value": 500}}

# Filter by document type
{"document_type": {"operator": "eq", "value": "legal"}}
```

### 5. Redis Caching System

**Location**: `utils/enterprise_caching_system.py`

**Features**:
- **Intelligent Caching**: TTL-based caching with access tracking
- **Memory Fallback**: Automatic fallback when Redis unavailable
- **Cache Warming**: Pre-populate cache with common queries
- **Performance Monitoring**: Detailed cache statistics and hit rates

**Usage**:
```python
from utils.enterprise_caching_system import get_global_cache_manager, cached_llm_response

# Get cache manager
cache_manager = get_global_cache_manager()

# Manual caching
cache_manager.cache_response(query, context, response, ttl=3600)
cached = cache_manager.get_cached_response(query, context)

# Decorator for automatic caching
@cached_llm_response(cache_manager, ttl=3600)
def my_llm_function(query, context):
    # Your LLM call here
    return response
```

**Cache Statistics**:
```python
stats = cache_manager.get_cache_stats()
# Returns: hit_rate_percent, total_hits, cache_size, redis_available, etc.
```

### 6. Enterprise Integration Layer

**Location**: `utils/enterprise_integration_layer.py`

**Features**:
- **Unified Interface**: Single entry point for all enterprise features
- **Backward Compatibility**: Seamless integration with existing code
- **Fallback Mechanisms**: Graceful degradation when components unavailable
- **Configuration Management**: Centralized enterprise feature configuration

**Usage**:
```python
from utils.enterprise_integration_layer import enterprise_enhanced_query

# Complete enterprise-enhanced query
result = enterprise_enhanced_query(
    query="What are the board meeting requirements?",
    index_name="ByLaw_index",
    max_results=10,
    response_type="legal",
    filters={"article_number": ["II", "III"]},
    use_cache=True
)
```

## Installation & Setup

### 1. Install Dependencies

```bash
# Install enterprise requirements
pip install -r requirements-enterprise.txt

# Optional: Install Redis for caching
# Windows: Download from https://github.com/microsoftarchive/redis/releases
# Linux: sudo apt-get install redis-server
# macOS: brew install redis
```

### 2. Configuration

Create or update your `.env` file:

```env
# Enterprise Features
ENABLE_ENTERPRISE_FEATURES=true
ENABLE_HYBRID_SEARCH=true
ENABLE_SEMANTIC_CHUNKING=true
ENABLE_STRUCTURED_OUTPUT=true
ENABLE_METADATA_FILTERING=true
ENABLE_CACHING=true

# Redis Configuration (Optional)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# Chunking Configuration
CHUNK_SIZE=1500
CHUNK_OVERLAP=500
RESPECT_SECTION_BREAKS=true
EXTRACT_TABLES=true
PRESERVE_HEADING_STRUCTURE=true

# Search Configuration
VECTOR_WEIGHT=0.6
KEYWORD_WEIGHT=0.4
ENABLE_RERANKING=true
```

### 3. System Integration

The enterprise features are automatically integrated into:

- **Real-Time Retrieval** (`utils/real_time_retrieval.py`)
- **Controller Agent** (`app/agents/controller_agent.py`)
- **Query Assistant** (`tabs/query_assistant.py`)

No additional configuration required - features activate automatically when dependencies are available.

## Performance Optimization

### 1. Chunking Parameters

**Current Settings**:
- Chunk Size: 1500 characters
- Chunk Overlap: 500 characters (33% overlap)
- Effective Context: ~1000 characters per chunk

**Tuning Guidelines**:
- **Larger chunks**: Better context, slower processing
- **Smaller chunks**: Faster processing, less context
- **Higher overlap**: Better continuity, more storage
- **Lower overlap**: Less storage, potential context loss

### 2. Caching Strategy

**Default TTL**: 1 hour (3600 seconds)
**Cache Size**: 1000 entries maximum
**Cleanup**: Automatic LRU-based cleanup

**Optimization**:
```python
# Warm cache with common queries
common_queries = [
    {"query": "board meeting requirements", "context": "bylaw_context"},
    {"query": "voting procedures", "context": "bylaw_context"}
]
cache_manager.warm_cache(common_queries, llm_function)
```

### 3. Search Configuration

**Hybrid Search Weights**:
- Vector: 60% (semantic similarity)
- Keyword: 40% (exact matching)
- Re-ranking: 30% boost for top results

**Tuning for Different Use Cases**:
```python
# Legal documents (exact terms important)
hybrid_search = get_enterprise_hybrid_search(vector_weight=0.4, keyword_weight=0.6)

# Technical docs (semantic understanding important)
hybrid_search = get_enterprise_hybrid_search(vector_weight=0.8, keyword_weight=0.2)
```

## Monitoring & Diagnostics

### 1. System Status

```python
from utils.enterprise_integration_layer import get_enterprise_retrieval_system

enterprise_system = get_enterprise_retrieval_system()
status = enterprise_system.get_system_status()

print(f"Enterprise Features: {status['enterprise_features_enabled']}")
for component, info in status['components'].items():
    print(f"{component}: {info['status']}")
```

### 2. Cache Performance

```python
from utils.enterprise_caching_system import get_global_cache_manager

cache_manager = get_global_cache_manager()
stats = cache_manager.get_cache_stats()

print(f"Cache Hit Rate: {stats['hit_rate_percent']}%")
print(f"Total Entries: {stats['cache_size']}")
print(f"Redis Available: {stats['redis_available']}")
```

### 3. Search Quality Metrics

```python
# Monitor search result quality
results = hybrid_search.search(query, index_name, max_results=10)

for result in results:
    print(f"Final Score: {result.final_score}")
    print(f"Vector Score: {result.vector_score}")
    print(f"Keyword Score: {result.keyword_score}")
    print(f"Rerank Score: {result.rerank_score}")
```

## Troubleshooting

### Common Issues

1. **Enterprise Features Not Loading**
   - Check `requirements-enterprise.txt` installation
   - Verify no import errors in logs
   - Ensure fallback mechanisms are working

2. **Redis Connection Issues**
   - Verify Redis server is running
   - Check connection parameters in `.env`
   - System automatically falls back to memory cache

3. **Chunking Performance**
   - Monitor chunk processing time
   - Adjust chunk size/overlap for performance
   - Consider document type detection accuracy

4. **Search Quality Issues**
   - Experiment with vector/keyword weight ratios
   - Check re-ranking model availability
   - Verify document metadata quality

### Logs and Debugging

Enable detailed logging:
```python
import logging
logging.getLogger('utils.enterprise_hybrid_search').setLevel(logging.DEBUG)
logging.getLogger('utils.enterprise_semantic_chunking').setLevel(logging.DEBUG)
logging.getLogger('utils.enterprise_caching_system').setLevel(logging.DEBUG)
```

## Migration Guide

### From Basic to Enterprise

1. **Install Dependencies**: `pip install -r requirements-enterprise.txt`
2. **Update Configuration**: Add enterprise settings to `.env`
3. **Test Integration**: Verify features load without errors
4. **Monitor Performance**: Check logs for enterprise feature usage
5. **Optimize Settings**: Tune parameters based on your document types

### Rollback Strategy

Enterprise features include comprehensive fallback mechanisms:
- If enterprise components fail, system automatically uses existing methods
- No data loss or system downtime during feature activation/deactivation
- Can disable individual features via configuration

## Best Practices

### 1. Document Preparation
- Ensure documents have clear structure (headers, sections)
- Include metadata where possible
- Use consistent naming conventions

### 2. Query Optimization
- Use specific terms for keyword matching
- Include context for semantic search
- Leverage metadata filters for precision

### 3. Performance Monitoring
- Monitor cache hit rates (target: >60%)
- Track search response times
- Review chunk processing efficiency

### 4. Security Considerations
- Redis security (password, network isolation)
- Cache data sensitivity
- Access control for enterprise features

## Support and Maintenance

### Regular Maintenance
- Monitor cache size and cleanup frequency
- Review search quality metrics
- Update transformer models periodically
- Backup cache configurations

### Performance Tuning
- Adjust chunk parameters based on document types
- Optimize search weights for your use cases
- Configure cache TTL based on content update frequency

For additional support, refer to the component-specific documentation in each enterprise module.
