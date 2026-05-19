"""
Pinecone Vector Store Adapter - Enterprise Multi-Tenant Version

Supports:
- Namespace-based department isolation
- Tenant/department metadata tagging
- Cross-namespace query prevention
"""

import json
import logging
import re
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import asyncio
import os

try:
    import pinecone
    from pinecone import Pinecone, ServerlessSpec
    PINECONE_AVAILABLE = True
except Exception:
    PINECONE_AVAILABLE = False
    pinecone = None
    class Pinecone:
        pass
    class ServerlessSpec:
        pass

from ..multi_vector_storage_interface import (
    BaseVectorStore, VectorStoreConfig, VectorSearchResult, VectorStoreType
)

logger = logging.getLogger(__name__)

class PineconeAdapter(BaseVectorStore):
    """Simplified Pinecone adapter that works"""
    
    def __init__(self, config: VectorStoreConfig):
        super().__init__(config)
        
        if not PINECONE_AVAILABLE:
            raise ImportError("pinecone-client package is required for Pinecone adapter")
        
        # Get API key from config or environment
        params = config.connection_params
        self.api_key = params.get('api_key') or os.getenv('PINECONE_API_KEY')
        
        if not self.api_key:
            raise ValueError("PINECONE_API_KEY is required")
        
        # Vector configuration
        self.vector_dimension = params.get('vector_dimension', 384)
        self.metric = params.get('metric', 'cosine')
        
        # Always use serverless for simplicity
        self.use_serverless = True
        self.serverless_cloud = params.get('serverless_cloud', 'aws')
        self.serverless_region = params.get('serverless_region', 'us-east-1')
        
        self._client = None
        self._indexes = {}
        
        # Multi-tenant configuration
        self._enforce_namespace = params.get('enforce_namespace', True)
        self._default_tenant = params.get('default_tenant', 'huron')
        
        # Initialize client immediately
        try:
            self._client = Pinecone(api_key=self.api_key)
            self._connected = True
            logger.info("Pinecone client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Pinecone client: {e}")
            self._connected = False
    
    async def connect(self) -> bool:
        """Establish connection to Pinecone"""
        if self._client and self._connected:
            return True
            
        try:
            self._client = Pinecone(api_key=self.api_key)
            # Test connection
            indexes = self._client.list_indexes()
            logger.info(f"Connected to Pinecone: {len(indexes)} indexes available")
            self._connected = True
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Pinecone: {e}")
            self._connected = False
            return False
    
    async def disconnect(self) -> None:
        """Close connection to Pinecone"""
        self._connected = False
    
    async def create_collection(self, collection_name: str, **kwargs) -> bool:
        """Create a new Pinecone index"""
        try:
            if not self._client:
                if not await self.connect():
                    return False
            
            # Check if index already exists
            indexes = self._client.list_indexes()
            existing_names = []
            for idx in indexes:
                if hasattr(idx, 'name'):
                    existing_names.append(idx.name)
                elif isinstance(idx, dict) and 'name' in idx:
                    existing_names.append(idx['name'])
                elif isinstance(idx, str):
                    existing_names.append(idx)
            
            if collection_name in existing_names:
                logger.info(f"Pinecone index {collection_name} already exists")
                return True
            
            # Create serverless index
            spec = ServerlessSpec(
                cloud=self.serverless_cloud,
                region=self.serverless_region
            )
            
            self._client.create_index(
                name=collection_name,
                dimension=self.vector_dimension,
                metric=self.metric,
                spec=spec
            )
            
            logger.info(f"Created Pinecone index: {collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create Pinecone index {collection_name}: {e}")
            return False
    
    async def delete_collection(self, collection_name: str) -> bool:
        """Delete a Pinecone index"""
        try:
            if not self._client:
                if not await self.connect():
                    return False
            
            self._client.delete_index(collection_name)
            logger.info(f"Deleted Pinecone index: {collection_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete Pinecone index {collection_name}: {e}")
            return False
    
    async def list_collections(self) -> List[str]:
        """List all available Pinecone indexes"""
        try:
            if not self._client:
                if not await self.connect():
                    return []
            
            indexes = self._client.list_indexes()
            names = []
            for idx in indexes:
                if hasattr(idx, 'name'):
                    names.append(idx.name)
                elif isinstance(idx, dict) and 'name' in idx:
                    names.append(idx['name'])
                elif isinstance(idx, str):
                    names.append(idx)
            return names
        except Exception as e:
            logger.error(f"Failed to list Pinecone indexes: {e}")
            return []
    
    def get_namespace(self, tenant_id: str, dept_id: str, doc_type: str = "general") -> str:
        """Generate namespace name for department isolation.
        
        Format: vaultmind-{tenant}-{dept}-{type}
        Example: vaultmind-huron-legal-general
        
        Pinecone namespace requirements:
        - Max 45 characters
        - Lowercase alphanumeric and hyphens only
        """
        name = f"vaultmind-{tenant_id}-{dept_id}-{doc_type}"
        # Sanitize: lowercase, replace invalid chars with hyphen, truncate
        name = re.sub(r"[^a-z0-9-]", "-", name.lower())[:45]
        return name
    
    def validate_tenant_context(self, tenant_id: Optional[str], dept_id: Optional[str]) -> Tuple[bool, str]:
        """Validate that required tenant context is present.
        
        Returns (is_valid, error_message)
        """
        if self._enforce_namespace:
            if not tenant_id:
                return False, "tenant_id is required for namespace isolation"
            if not dept_id:
                return False, "dept_id is required for namespace isolation"
        return True, ""

    async def upsert_documents(self, 
                             collection_name: str,
                             documents: List[Dict[str, Any]],
                             embeddings: Optional[List[List[float]]] = None,
                             tenant_id: Optional[str] = None,
                             dept_id: Optional[str] = None,
                             namespace: Optional[str] = None) -> bool:
        """Insert or update documents with vectors.
        
        Args:
            collection_name: Pinecone index name
            documents: List of documents with content, source, etc.
            embeddings: Optional pre-computed embeddings
            tenant_id: Tenant identifier (e.g., 'huron')
            dept_id: Department identifier (e.g., 'legal', 'hr')
            namespace: Optional explicit namespace (overrides tenant/dept)
        """
        try:
            # Validate tenant context if enforcement is enabled
            if not namespace:
                is_valid, error = self.validate_tenant_context(tenant_id, dept_id)
                if not is_valid:
                    if self._enforce_namespace:
                        raise ValueError(error)
                    else:
                        # Use default namespace if not enforcing
                        namespace = self.get_namespace(
                            tenant_id or self._default_tenant,
                            dept_id or "general"
                        )
                else:
                    namespace = self.get_namespace(tenant_id, dept_id)
            
            # Get or create index
            if collection_name not in self._indexes:
                if not await self.create_collection(collection_name):
                    return False
                self._indexes[collection_name] = self._client.Index(collection_name)
            
            index = self._indexes[collection_name]
            
            # Prepare vectors for upsert
            vectors_to_upsert = []
            
            for i, doc in enumerate(documents):
                doc_id = doc.get('id', f"doc_{i}_{datetime.now().timestamp()}")
                
                # Get vector
                vector = None
                if embeddings and i < len(embeddings):
                    vector = embeddings[i]
                elif 'vector' in doc:
                    vector = doc['vector']
                else:
                    continue
                
                # Prepare metadata with tenant/department tagging
                metadata = {
                    "content": doc.get('content', '')[:40000],
                    "source": doc.get('source', ''),
                    "source_type": doc.get('source_type', 'unknown'),
                    "created_at": doc.get('created_at', datetime.now().isoformat()),
                    # Multi-tenant metadata
                    "tenant_id": tenant_id or self._default_tenant,
                    "dept_id": dept_id or "general",
                    "namespace": namespace,
                    # Additional document metadata
                    "sensitivity_level": doc.get('sensitivity_level', 'internal'),
                    "uploaded_by": doc.get('uploaded_by', 'system'),
                }
                
                vectors_to_upsert.append({
                    "id": str(doc_id),
                    "values": vector,
                    "metadata": metadata
                })
            
            # Upsert in batches WITH NAMESPACE
            batch_size = 100
            for i in range(0, len(vectors_to_upsert), batch_size):
                batch = vectors_to_upsert[i:i + batch_size]
                index.upsert(vectors=batch, namespace=namespace)
            
            logger.info(f"Upserted {len(vectors_to_upsert)} documents to Pinecone index {collection_name} namespace={namespace}")
            return True
            
        except ValueError as ve:
            logger.error(f"Tenant validation failed: {ve}")
            raise
        except Exception as e:
            logger.error(f"Failed to upsert documents to Pinecone index {collection_name}: {e}")
            return False
    
    async def search(self, 
                    collection_name: str,
                    query: Optional[str] = None,
                    query_embedding: Optional[List[float]] = None,
                    filters: Optional[Dict[str, Any]] = None,
                    limit: int = 10,
                    tenant_id: Optional[str] = None,
                    dept_id: Optional[str] = None,
                    namespace: Optional[str] = None,
                    allowed_departments: Optional[List[str]] = None,
                    **kwargs) -> List[VectorSearchResult]:
        """Search using Pinecone vector similarity with namespace isolation.
        
        Args:
            collection_name: Pinecone index name
            query: Optional text query (not used directly, for logging)
            query_embedding: Vector embedding of the query
            filters: Additional Pinecone metadata filters
            limit: Max results to return
            tenant_id: Tenant identifier for namespace resolution
            dept_id: Primary department for namespace search
            namespace: Explicit namespace (overrides tenant/dept)
            allowed_departments: List of departments user can access (for cross-dept search)
        """
        try:
            if not query_embedding:
                return []
            
            # Validate tenant context
            if not namespace:
                is_valid, error = self.validate_tenant_context(tenant_id, dept_id)
                if not is_valid:
                    if self._enforce_namespace:
                        logger.warning(f"Search blocked: {error}")
                        return []  # Return empty rather than raise in search
                    else:
                        namespace = None  # Search all namespaces (not recommended)
                else:
                    namespace = self.get_namespace(tenant_id, dept_id)
            
            if collection_name not in self._indexes:
                self._indexes[collection_name] = self._client.Index(collection_name)
            
            index = self._indexes[collection_name]
            
            # Build metadata filter
            pinecone_filter = {}
            if filters:
                pinecone_filter.update(filters)
            
            # If searching with allowed_departments, add dept filter
            if allowed_departments and len(allowed_departments) > 1:
                pinecone_filter["dept_id"] = {"$in": allowed_departments}
            
            # Perform search WITH NAMESPACE
            search_kwargs = {
                "vector": query_embedding,
                "top_k": limit,
                "include_metadata": True,
                "include_values": False,
            }
            if namespace:
                search_kwargs["namespace"] = namespace
            if pinecone_filter:
                search_kwargs["filter"] = pinecone_filter
            
            search_response = index.query(**search_kwargs)
            
            # Process results
            results = []
            for match in search_response.matches:
                metadata = match.metadata or {}
                result = VectorSearchResult(
                    content=metadata.get('content', ''),
                    metadata=metadata,
                    score=match.score,
                    source=metadata.get('source'),
                    id=match.id
                )
                results.append(result)
            
            logger.debug(f"Search returned {len(results)} results from namespace={namespace}")
            return results
            
        except Exception as e:
            logger.error(f"Search failed in Pinecone index {collection_name}: {e}")
            return []
    

    def search_sync(self, collection_name: str, query_embedding: List[float], 
                    limit: int = 10, tenant_id: str = "huron", 
                    dept_id: str = None, namespace: str = None, **kwargs):
        """Synchronous wrapper for use in LangGraph nodes"""
        import asyncio
        import concurrent.futures
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    future = pool.submit(
                        asyncio.run, 
                        self.search(collection_name, query_embedding=query_embedding,
                                   limit=limit, tenant_id=tenant_id, dept_id=dept_id,
                                   namespace=namespace, **kwargs)
                    )
                    return future.result(timeout=30)
            else:
                return loop.run_until_complete(
                    self.search(collection_name, query_embedding=query_embedding,
                               limit=limit, tenant_id=tenant_id, dept_id=dept_id,
                               namespace=namespace, **kwargs)
                )
        except Exception as e:
            logger.error(f"search_sync failed: {e}")
            return []

    async def delete_documents(self, 
                               collection_name: str, 
                               document_ids: List[str],
                               tenant_id: Optional[str] = None,
                               dept_id: Optional[str] = None,
                               namespace: Optional[str] = None) -> bool:
        """Delete specific documents from Pinecone index with namespace isolation."""
        try:
            # Resolve namespace
            if not namespace and tenant_id and dept_id:
                namespace = self.get_namespace(tenant_id, dept_id)
            
            if collection_name not in self._indexes:
                self._indexes[collection_name] = self._client.Index(collection_name)
            
            index = self._indexes[collection_name]
            
            # Delete with namespace if provided
            if namespace:
                index.delete(ids=document_ids, namespace=namespace)
            else:
                index.delete(ids=document_ids)
            
            logger.info(f"Deleted {len(document_ids)} documents from namespace={namespace}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete documents from Pinecone index {collection_name}: {e}")
            return False
    
    async def get_collection_stats(self, collection_name: str) -> Dict[str, Any]:
        """Get statistics about a Pinecone index"""
        try:
            if not self._client:
                if not await self.connect():
                    return {"error": "Not connected"}
            
            index_info = self._client.describe_index(collection_name)
            return {
                "document_count": getattr(index_info, 'total_vector_count', 0),
                "dimension": getattr(index_info, 'dimension', self.vector_dimension),
                "metric": getattr(index_info, 'metric', self.metric),
                "status": "ready",
                "health": "green"
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def health_check(self) -> Tuple[bool, str]:
        """Check if Pinecone service is healthy"""
        try:
            if not self._client:
                if not await self.connect():
                    return False, "Connection failed"
            
            indexes = self._client.list_indexes()
            return True, f"Pinecone healthy: {len(indexes)} indexes available"
        except Exception as e:
            return False, f"Health check failed: {e}"

# Register the adapter
from ..multi_vector_storage_interface import VectorStoreFactory
if PINECONE_AVAILABLE:
    VectorStoreFactory.register(VectorStoreType.PINECONE, PineconeAdapter)
    logger.info("Registered simplified Pinecone adapter")
