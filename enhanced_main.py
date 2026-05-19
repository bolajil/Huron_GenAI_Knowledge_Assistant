"""
VaultMIND Knowledge Assistant - Enhanced Main Application

This module provides the main application with enhanced document ingestion and querying capabilities.
"""

import logging
import time
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
from datetime import datetime
import os
import sys
import json
import uvicorn
from fastapi import FastAPI, HTTPException, Request, Body
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import schemas
from schemas import IngestRequest, QueryRequest

# Import the enhanced document processor and query processor
try:
    from utils.enhanced_document_processor import get_document_processor
    document_processor = get_document_processor()
    DOCUMENT_PROCESSOR_AVAILABLE = True
except ImportError:
    logger.warning("Enhanced document processor not available. Falling back to legacy processor.")
    DOCUMENT_PROCESSOR_AVAILABLE = False
    document_processor = None

try:
    from utils.enhanced_query_processor import get_query_processor
    query_processor = get_query_processor()
    QUERY_PROCESSOR_AVAILABLE = True
except ImportError:
    logger.warning("Enhanced query processor not available. Falling back to legacy processor.")
    QUERY_PROCESSOR_AVAILABLE = False
    query_processor = None

# Import legacy components for fallback
try:
    from utils.ingest_helpers import ingest_text as legacy_ingest_text
    from utils.query_helpers import query_index as legacy_query_index
    from utils.query_llm import synthesize_answer as legacy_synthesize_answer
    from agents.controller_agent import ControllerAgent
    LEGACY_COMPONENTS_AVAILABLE = True
except ImportError:
    logger.warning("Legacy components not available.")
    LEGACY_COMPONENTS_AVAILABLE = False

# Create FastAPI app
app = FastAPI(
    title="VaultMIND Knowledge Assistant",
    description="Enhanced document ingestion and querying system",
    version="2.0.0"
)

# Extended Pydantic models for the enhanced API
class EnhancedIngestRequest(BaseModel):
    content: str
    index_name: Optional[str] = None
    chunk_size: int = 500
    chunk_overlap: int = 50
    tags: List[str] = []
    title: Optional[str] = None

class EnhancedQueryRequest(BaseModel):
    query: str
    index_name: Optional[str] = None
    top_k: int = 5
    relevance_threshold: float = 0.6
    filters: Optional[Dict[str, Any]] = None
    provider: str = "openai"
    deduplicate: bool = True

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "VaultMIND Knowledge Assistant",
        "version": "2.0.0",
        "enhanced_document_processor": DOCUMENT_PROCESSOR_AVAILABLE,
        "enhanced_query_processor": QUERY_PROCESSOR_AVAILABLE
    }

@app.get("/status")
async def status():
    """Get the status of the application components"""
    components = {
        "document_processor": {
            "available": DOCUMENT_PROCESSOR_AVAILABLE,
            "status": "ready" if DOCUMENT_PROCESSOR_AVAILABLE else "unavailable"
        },
        "query_processor": {
            "available": QUERY_PROCESSOR_AVAILABLE,
            "status": "ready" if QUERY_PROCESSOR_AVAILABLE else "unavailable"
        },
        "legacy_components": {
            "available": LEGACY_COMPONENTS_AVAILABLE,
            "status": "ready" if LEGACY_COMPONENTS_AVAILABLE else "unavailable"
        }
    }
    
    # Get vector database status if available
    try:
        from utils.vector_db_init import get_any_vector_db_provider
        vector_db_provider = get_any_vector_db_provider()
        
        if vector_db_provider:
            status, message = vector_db_provider.get_vector_db_status()
            components["vector_database"] = {
                "available": True,
                "status": status,
                "message": message
            }
        else:
            components["vector_database"] = {
                "available": False,
                "status": "unavailable",
                "message": "Vector database provider not initialized"
            }
    except Exception as e:
        components["vector_database"] = {
            "available": False,
            "status": "error",
            "message": str(e)
        }
    
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "components": components
    }

# Legacy compatibility endpoints
@app.post("/ingest")
async def ingest(payload: IngestRequest):
    """
    Legacy ingest endpoint for backward compatibility
    """
    if DOCUMENT_PROCESSOR_AVAILABLE:
        # Use the enhanced document processor
        try:
            # Save the content to a temporary file
            upload_dir = Path("data/uploads")
            upload_dir.mkdir(parents=True, exist_ok=True)
            
            file_path = upload_dir / f"{datetime.now().strftime('%Y%m%d%H%M%S')}_legacy_ingest.txt"
            
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(payload.content)
            
            # Process the file
            result = document_processor.process_file(
                file_path=file_path,
                index_name=payload.index_name,
                chunk_size=payload.chunk_size,
                chunk_overlap=payload.chunk_overlap
            )
            
            if result["status"] == "error":
                return {"status": "error", "message": result["message"]}
            
            return {"status": "success", "chunks": result["chunk_count"], "index": payload.index_name}
        
        except Exception as e:
            logger.error(f"Error in enhanced ingest: {e}")
            # Fall back to legacy ingest
            if LEGACY_COMPONENTS_AVAILABLE:
                logger.info("Falling back to legacy ingest")
                chunk_count = legacy_ingest_text(
                    content=payload.content,
                    index_name=payload.index_name,
                    chunk_size=payload.chunk_size,
                    chunk_overlap=payload.chunk_overlap
                )
                return {"status": "success", "chunks": chunk_count, "index": payload.index_name}
            else:
                return {"status": "error", "message": str(e)}
    
    elif LEGACY_COMPONENTS_AVAILABLE:
        # Use the legacy ingest
        chunk_count = legacy_ingest_text(
            content=payload.content,
            index_name=payload.index_name,
            chunk_size=payload.chunk_size,
            chunk_overlap=payload.chunk_overlap
        )
        return {"status": "success", "chunks": chunk_count, "index": payload.index_name}
    
    else:
        return {"status": "error", "message": "No document processor available"}

@app.post("/query")
async def query(payload: QueryRequest):
    """
    Legacy query endpoint for backward compatibility
    """
    if QUERY_PROCESSOR_AVAILABLE:
        # Use the enhanced query processor
        try:
            # Perform the search
            results = query_processor.search(
                query=payload.query,
                index_name=payload.index_name,
                top_k=payload.top_k
            )
            
            # Generate an answer
            answer = query_processor.synthesize_answer(
                query=payload.query,
                results=results,
                provider=payload.provider
            )
            
            return {
                "status": "success",
                "query": payload.query,
                "index": payload.index_name,
                "provider": payload.provider,
                "answer": answer
            }
        
        except Exception as e:
            logger.error(f"Error in enhanced query: {e}")
            # Fall back to legacy query
            if LEGACY_COMPONENTS_AVAILABLE:
                logger.info("Falling back to legacy query")
                controller = ControllerAgent()
                answer = controller.run(
                    query=payload.query,
                    index_name=payload.index_name,
                    top_k=payload.top_k,
                    provider=payload.provider
                )
                
                return {
                    "status": "success",
                    "query": payload.query,
                    "index": payload.index_name,
                    "provider": payload.provider,
                    "answer": answer
                }
            else:
                return {"status": "error", "message": str(e)}
    
    elif LEGACY_COMPONENTS_AVAILABLE:
        # Use the legacy query
        controller = ControllerAgent()
        answer = controller.run(
            query=payload.query,
            index_name=payload.index_name,
            top_k=payload.top_k,
            provider=payload.provider
        )
        
        return {
            "status": "success",
            "query": payload.query,
            "index": payload.index_name,
            "provider": payload.provider,
            "answer": answer
        }
    
    else:
        return {"status": "error", "message": "No query processor available"}

# Enhanced API endpoints
@app.post("/enhanced/ingest")
async def enhanced_ingest(payload: EnhancedIngestRequest):
    """
    Enhanced ingest endpoint
    """
    if not DOCUMENT_PROCESSOR_AVAILABLE:
        raise HTTPException(status_code=503, detail="Enhanced document processor not available")
    
    try:
        # Save the content to a temporary file
        upload_dir = Path("data/uploads")
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        title = payload.title or f"Untitled Document {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        file_path = upload_dir / f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{title.replace(' ', '_')}.txt"
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(payload.content)
        
        # Process the file
        result = document_processor.process_file(
            file_path=file_path,
            index_name=payload.index_name,
            chunk_size=payload.chunk_size,
            chunk_overlap=payload.chunk_overlap,
            tags=payload.tags,
            custom_metadata={"title": title}
        )
        
        return result
    
    except Exception as e:
        logger.error(f"Error in enhanced ingest: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/enhanced/query")
async def enhanced_query(payload: EnhancedQueryRequest):
    """
    Enhanced query endpoint
    """
    if not QUERY_PROCESSOR_AVAILABLE:
        raise HTTPException(status_code=503, detail="Enhanced query processor not available")
    
    try:
        # Perform the search
        results = query_processor.search(
            query=payload.query,
            index_name=payload.index_name,
            top_k=payload.top_k,
            relevance_threshold=payload.relevance_threshold,
            filters=payload.filters,
            deduplicate=payload.deduplicate
        )
        
        # Generate an answer
        answer = query_processor.synthesize_answer(
            query=payload.query,
            results=results,
            provider=payload.provider
        )
        
        # Convert results to dictionaries
        result_dicts = [result.to_dict() for result in results]
        
        return {
            "status": "success",
            "query": payload.query,
            "index": payload.index_name,
            "provider": payload.provider,
            "answer": answer,
            "result_count": len(results),
            "results": result_dicts
        }
    
    except Exception as e:
        logger.error(f"Error in enhanced query: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/enhanced/documents")
async def list_documents(tag: Optional[str] = None, file_type: Optional[str] = None):
    """
    List all indexed documents, optionally filtered by tag or file type
    """
    if not DOCUMENT_PROCESSOR_AVAILABLE:
        raise HTTPException(status_code=503, detail="Document processor not available")
    
    try:
        documents = document_processor.list_documents(tag, file_type)
        return {
            "status": "success",
            "count": len(documents),
            "documents": documents
        }
    
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/indexes")
async def list_indexes():
    """
    List all available FAISS indexes.
    Discovers indexes from data/faiss_index directory.
    """
    from pathlib import Path
    import pickle
    
    indexes = []
    faiss_dir = Path("data/faiss_index")
    
    if faiss_dir.exists():
        for item in faiss_dir.iterdir():
            if item.is_dir():
                # Check for index files
                has_faiss = (item / "index.faiss").exists()
                has_pkl = (item / "index.pkl").exists() or (item / "documents.pkl").exists()
                
                if has_faiss or has_pkl:
                    # Calculate size
                    size_bytes = sum(f.stat().st_size for f in item.rglob('*') if f.is_file())
                    size_mb = size_bytes / (1024 * 1024)
                    
                    # Count documents
                    doc_count = 0
                    for pkl_name in ["documents.pkl", "index.pkl"]:
                        pkl_file = item / pkl_name
                        if pkl_file.exists():
                            try:
                                with open(pkl_file, 'rb') as f:
                                    docs = pickle.load(f)
                                    doc_count = len(docs) if isinstance(docs, list) else 0
                                break
                            except:
                                pass
                    
                    indexes.append({
                        "name": item.name,
                        "type": "FAISS",
                        "documents": doc_count,
                        "size_mb": round(size_mb, 2),
                        "status": "active"
                    })
    
    # Sort by name
    indexes.sort(key=lambda x: x["name"])
    
    return {
        "status": "success",
        "count": len(indexes),
        "indexes": indexes
    }

# Run the application if this module is executed directly
if __name__ == "__main__":
    # Get the port from environment variable or use default
    port = int(os.environ.get("PORT", 8000))
    
    # Run the application
    uvicorn.run(app, host="0.0.0.0", port=port)
