"""
Unified Document Ingestion Service

Orchestrates the full ingestion pipeline:
1. Document parsing (PDF, DOCX, etc.)
2. Hierarchical chunking (parent/child)
3. Quality gate validation
4. Embedding generation
5. Multi-tenant vector store upsert

Usage:
    from utils.ingestion_service import IngestionService
    from utils.tenant_context import TenantContext
    
    service = IngestionService()
    ctx = TenantContext(tenant_id="huron", dept_id="legal")
    
    result = await service.ingest_document(
        file_path="contract.pdf",
        tenant_context=ctx
    )
"""

import os
import logging
from typing import List, Dict, Any, Optional, Tuple, BinaryIO
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Import chunker
from utils.hierarchical_chunker import (
    HierarchicalChunker, 
    HierarchicalChunk,
    apply_quality_gate
)

# Import tenant context
try:
    from utils.tenant_context import TenantContext
except ImportError:
    TenantContext = None

# Import ML models (optional)
try:
    from utils.ml_models.document_classifier import DocumentClassifier
    CLASSIFIER_AVAILABLE = True
except ImportError:
    CLASSIFIER_AVAILABLE = False
    logger.info("Document classifier not available")

# Import embedding function
try:
    from sentence_transformers import SentenceTransformer
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False
    logger.warning("sentence-transformers not available. Using mock embeddings.")

# Import DLP scanner
try:
    from utils.dlp_scanner import DLPScanner, ScanResult, DLPAction
    DLP_AVAILABLE = True
except ImportError:
    DLP_AVAILABLE = False
    logger.info("DLP scanner not available")

# Import Pinecone adapter for vector store upsert
try:
    from utils.adapters.pinecone_adapter import PineconeAdapter, PINECONE_AVAILABLE
    from utils.multi_vector_storage_interface import VectorStoreConfig, VectorStoreType
except ImportError:
    PINECONE_AVAILABLE = False
    PineconeAdapter = None
    VectorStoreConfig = None
    logger.info("Pinecone adapter not available")


@dataclass
class IngestionResult:
    """Result of document ingestion"""
    success: bool
    document_id: str
    source: str
    
    # Chunk counts
    parent_chunks: int = 0
    child_chunks: int = 0
    rejected_chunks: int = 0
    
    # Metadata
    document_type: str = "general"
    tenant_id: str = "huron"
    dept_id: Optional[str] = None
    namespace: Optional[str] = None
    
    # Timing
    processing_time_ms: int = 0
    
    # Errors
    error: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "document_id": self.document_id,
            "source": self.source,
            "parent_chunks": self.parent_chunks,
            "child_chunks": self.child_chunks,
            "rejected_chunks": self.rejected_chunks,
            "document_type": self.document_type,
            "tenant_id": self.tenant_id,
            "dept_id": self.dept_id,
            "namespace": self.namespace,
            "processing_time_ms": self.processing_time_ms,
            "error": self.error,
            "warnings": self.warnings,
        }


class IngestionService:
    """
    Unified document ingestion service with multi-tenant support.
    """
    
    def __init__(
        self,
        embedding_model: str = "all-MiniLM-L6-v2",
        parent_chunk_size: int = 1024,
        child_chunk_size: int = 256,
        enable_quality_gate: bool = True,
        enable_classification: bool = True,
        enable_dlp_scan: bool = True,
        enable_pinecone: bool = True,
        pinecone_index: str = "huron-enterprise-knowledge",
    ):
        """
        Initialize ingestion service.
        
        Args:
            embedding_model: Sentence transformer model name
            parent_chunk_size: Token size for parent chunks
            child_chunk_size: Token size for child chunks
            enable_quality_gate: Whether to filter low-quality chunks
            enable_classification: Whether to auto-classify documents
            enable_dlp_scan: Whether to scan for sensitive data (DLP)
            enable_pinecone: Whether to upsert to Pinecone
            pinecone_index: Pinecone index name
        """
        self.enable_quality_gate = enable_quality_gate
        self.enable_classification = enable_classification and CLASSIFIER_AVAILABLE
        self.enable_dlp_scan = enable_dlp_scan and DLP_AVAILABLE
        self.enable_pinecone = enable_pinecone and PINECONE_AVAILABLE
        self.pinecone_index = pinecone_index
        
        # Initialize chunker
        self.chunker = HierarchicalChunker(
            parent_chunk_size=parent_chunk_size,
            child_chunk_size=child_chunk_size,
        )
        
        # Initialize embedding model
        self.embedder = None
        if EMBEDDINGS_AVAILABLE:
            try:
                self.embedder = SentenceTransformer(embedding_model)
                logger.info(f"Loaded embedding model: {embedding_model}")
            except Exception as e:
                logger.warning(f"Failed to load embedder: {e}")
        
        # Initialize classifier
        self.classifier = None
        if self.enable_classification:
            try:
                self.classifier = DocumentClassifier()
                logger.info("Document classifier initialized")
            except Exception as e:
                logger.warning(f"Failed to load classifier: {e}")
                self.enable_classification = False
        
        # Initialize DLP scanner
        self.dlp_scanner = None
        if self.enable_dlp_scan:
            try:
                self.dlp_scanner = DLPScanner()
                logger.info("DLP scanner initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize DLP scanner: {e}")
                self.enable_dlp_scan = False
        
        # Initialize Pinecone adapter for vector upsert
        self.pinecone_adapter = None
        if self.enable_pinecone and PineconeAdapter and VectorStoreConfig:
            try:
                config = VectorStoreConfig(
                    store_type=VectorStoreType.PINECONE,
                    connection_params={
                        "api_key": os.getenv("PINECONE_API_KEY"),
                        "vector_dimension": 384 if embedding_model == "all-MiniLM-L6-v2" else 1536,
                        "metric": "cosine",
                        "enforce_namespace": True,
                        "default_tenant": "huron",
                    }
                )
                self.pinecone_adapter = PineconeAdapter(config)
                logger.info(f"Pinecone adapter initialized for index: {pinecone_index}")
            except Exception as e:
                logger.warning(f"Failed to initialize Pinecone adapter: {e}")
                self.enable_pinecone = False
    
    async def ingest_document(
        self,
        file_path: Optional[str] = None,
        file_content: Optional[bytes] = None,
        file_name: Optional[str] = None,
        text_content: Optional[str] = None,
        tenant_context: Optional[Any] = None,
        document_type: Optional[str] = None,
        sensitivity_level: str = "internal",
        **metadata
    ) -> IngestionResult:
        """
        Ingest a document into the vector store.
        
        Args:
            file_path: Path to file on disk
            file_content: Raw file bytes
            file_name: Original filename
            text_content: Pre-extracted text
            tenant_context: TenantContext for multi-tenant isolation
            document_type: Optional document type override
            sensitivity_level: Document sensitivity level
            **metadata: Additional metadata
        
        Returns:
            IngestionResult with status and metrics
        """
        import uuid
        import time
        
        start_time = time.time()
        document_id = str(uuid.uuid4())
        source = file_name or file_path or "unknown"
        warnings = []
        
        # Extract tenant info
        tenant_id = "huron"
        dept_id = None
        namespace = None
        
        if tenant_context:
            tenant_id = getattr(tenant_context, "tenant_id", "huron")
            dept_id = getattr(tenant_context, "dept_id", None)
            if hasattr(tenant_context, "get_namespace") and dept_id:
                try:
                    namespace = tenant_context.get_namespace()
                except:
                    pass
        
        # Validate tenant context
        if not dept_id:
            warnings.append("No dept_id provided - document will not be namespace-isolated")
        
        try:
            # Step 1: Extract text
            if text_content:
                text = text_content
            elif file_content:
                text = self._extract_text_from_bytes(file_content, file_name)
            elif file_path:
                text = self._extract_text_from_file(file_path)
            else:
                raise ValueError("No document content provided")
            
            if not text or len(text.strip()) < 50:
                return IngestionResult(
                    success=False,
                    document_id=document_id,
                    source=source,
                    tenant_id=tenant_id,
                    dept_id=dept_id,
                    error="Document has insufficient text content"
                )
            
            # Step 1.5: DLP scan for sensitive data
            if self.enable_dlp_scan and self.dlp_scanner:
                try:
                    dlp_result = self.dlp_scanner.scan_text(text, dept_id=dept_id)
                    
                    if dlp_result.should_block:
                        return IngestionResult(
                            success=False,
                            document_id=document_id,
                            source=source,
                            tenant_id=tenant_id,
                            dept_id=dept_id,
                            error=f"Document blocked by DLP: {dlp_result.finding_summary}"
                        )
                    
                    if dlp_result.has_sensitive_data:
                        warnings.append(
                            f"DLP findings ({dlp_result.finding_summary}): "
                            f"sensitive data redacted"
                        )
                        # Use redacted text for ingestion
                        if dlp_result.redacted_text:
                            text = dlp_result.redacted_text
                            
                except Exception as e:
                    logger.warning(f"DLP scan failed: {e}")
                    warnings.append("DLP scan failed - proceeding without scan")
            
            # Step 2: Classify document type
            if not document_type and self.enable_classification and self.classifier:
                try:
                    classification = self.classifier.classify(text[:5000])
                    document_type = classification.get("type", "general")
                    logger.info(f"Classified document as: {document_type}")
                except Exception as e:
                    logger.warning(f"Classification failed: {e}")
                    document_type = "general"
            else:
                document_type = document_type or "general"
            
            # Step 3: Chunk document hierarchically
            parent_chunks, child_chunks = self.chunker.chunk_document(
                text=text,
                source=source,
                tenant_context=tenant_context,
                document_type=document_type,
                tenant_id=tenant_id,
                dept_id=dept_id,
                sensitivity_level=sensitivity_level,
                **metadata
            )
            
            # Step 4: Apply quality gate
            rejected_count = 0
            if self.enable_quality_gate:
                parent_chunks, rejected_parents = apply_quality_gate(parent_chunks)
                child_chunks, rejected_children = apply_quality_gate(child_chunks)
                rejected_count = len(rejected_parents) + len(rejected_children)
                
                if rejected_count > 0:
                    warnings.append(f"{rejected_count} low-quality chunks filtered")
            
            # Step 5: Generate embeddings
            all_chunks = parent_chunks + child_chunks
            embeddings = self._generate_embeddings([c.content for c in all_chunks])
            
            # Step 6: Upsert to Pinecone vector store (THE CRITICAL WIRING)
            upsert_success = False
            if self.enable_pinecone and self.pinecone_adapter and namespace:
                try:
                    # Convert chunks to document format for Pinecone
                    documents = []
                    for chunk in all_chunks:
                        doc = {
                            "id": chunk.chunk_id,
                            "content": chunk.content,
                            "source": source,
                            "source_type": "document",
                            "document_type": document_type,
                            "sensitivity_level": sensitivity_level,
                            "uploaded_by": getattr(tenant_context, "username", "system") if tenant_context else "system",
                            # Hierarchical chunking metadata
                            "chunk_type": chunk.chunk_type,  # "parent" or "child"
                            "parent_id": chunk.parent_id,
                            "chunk_index": chunk.chunk_index,
                            # Additional metadata
                            **metadata
                        }
                        documents.append(doc)
                    
                    # Execute upsert to Pinecone with namespace isolation
                    upsert_success = await self.pinecone_adapter.upsert_documents(
                        collection_name=self.pinecone_index,
                        documents=documents,
                        embeddings=embeddings,
                        tenant_id=tenant_id,
                        dept_id=dept_id,
                        namespace=namespace,
                    )
                    
                    if upsert_success:
                        logger.info(
                            f"Pinecone upsert SUCCESS: {len(documents)} vectors "
                            f"to index={self.pinecone_index}, namespace={namespace}"
                        )
                    else:
                        warnings.append("Pinecone upsert returned False")
                        
                except Exception as e:
                    logger.error(f"Pinecone upsert failed: {e}")
                    warnings.append(f"Pinecone upsert error: {str(e)}")
            elif self.enable_pinecone and not namespace:
                warnings.append("Pinecone upsert skipped: no namespace (dept_id required)")
            elif not self.enable_pinecone:
                warnings.append("Pinecone upsert skipped: adapter not enabled")
            
            processing_time = int((time.time() - start_time) * 1000)
            
            result = IngestionResult(
                success=True,
                document_id=document_id,
                source=source,
                parent_chunks=len(parent_chunks),
                child_chunks=len(child_chunks),
                rejected_chunks=rejected_count,
                document_type=document_type,
                tenant_id=tenant_id,
                dept_id=dept_id,
                namespace=namespace,
                processing_time_ms=processing_time,
                warnings=warnings,
            )
            
            # Attach chunks and embeddings for caller to use (or fallback stores)
            result._parent_chunks = parent_chunks
            result._child_chunks = child_chunks
            result._embeddings = embeddings
            result._pinecone_upsert_success = upsert_success
            
            logger.info(
                f"Ingested {source}: {len(parent_chunks)} parents, "
                f"{len(child_chunks)} children, {rejected_count} rejected, "
                f"pinecone={'OK' if upsert_success else 'SKIP'} "
                f"({processing_time}ms)"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Ingestion failed for {source}: {e}")
            return IngestionResult(
                success=False,
                document_id=document_id,
                source=source,
                tenant_id=tenant_id,
                dept_id=dept_id,
                error=str(e),
                processing_time_ms=int((time.time() - start_time) * 1000),
            )
    
    def _extract_text_from_file(self, file_path: str) -> str:
        """Extract text from file on disk"""
        path = Path(file_path)
        ext = path.suffix.lower()
        
        if ext == ".txt":
            return path.read_text(encoding="utf-8", errors="ignore")
        
        elif ext == ".pdf":
            return self._extract_pdf_text(path)
        
        elif ext in [".doc", ".docx"]:
            return self._extract_docx_text(path)
        
        elif ext == ".md":
            return path.read_text(encoding="utf-8", errors="ignore")
        
        else:
            # Try as text
            try:
                return path.read_text(encoding="utf-8", errors="ignore")
            except:
                raise ValueError(f"Unsupported file type: {ext}")
    
    def _extract_text_from_bytes(self, content: bytes, filename: str) -> str:
        """Extract text from file bytes"""
        import tempfile
        
        ext = Path(filename).suffix.lower() if filename else ".txt"
        
        # Write to temp file and extract
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as f:
            f.write(content)
            temp_path = f.name
        
        try:
            return self._extract_text_from_file(temp_path)
        finally:
            os.unlink(temp_path)
    
    def _extract_pdf_text(self, path: Path) -> str:
        """Extract text from PDF"""
        try:
            import PyPDF2
            text = ""
            with open(path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    text += page.extract_text() + "\n\n"
            return text
        except ImportError:
            try:
                import pdfplumber
                text = ""
                with pdfplumber.open(path) as pdf:
                    for page in pdf.pages:
                        text += (page.extract_text() or "") + "\n\n"
                return text
            except ImportError:
                raise ImportError("Install PyPDF2 or pdfplumber for PDF support")
    
    def _extract_docx_text(self, path: Path) -> str:
        """Extract text from DOCX"""
        try:
            import docx
            doc = docx.Document(path)
            return "\n\n".join(p.text for p in doc.paragraphs)
        except ImportError:
            raise ImportError("Install python-docx for DOCX support")
    
    def _generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for texts"""
        if self.embedder:
            embeddings = self.embedder.encode(texts, show_progress_bar=False)
            return embeddings.tolist()
        else:
            # Mock embeddings for testing
            import random
            return [[random.random() for _ in range(384)] for _ in texts]


# Convenience function
async def ingest_document(
    file_path: Optional[str] = None,
    text_content: Optional[str] = None,
    tenant_context: Optional[Any] = None,
    **kwargs
) -> IngestionResult:
    """
    Convenience function for document ingestion.
    
    Usage:
        result = await ingest_document(
            file_path="doc.pdf",
            tenant_context=ctx
        )
    """
    service = IngestionService()
    return await service.ingest_document(
        file_path=file_path,
        text_content=text_content,
        tenant_context=tenant_context,
        **kwargs
    )
