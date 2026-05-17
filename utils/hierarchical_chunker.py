"""
Hierarchical Document Chunker for Multi-Tenant RAG

Implements parent/child chunking strategy:
- Parent chunks: 1024 tokens (for context assembly)
- Child chunks: 256 tokens (for precise retrieval)

Each child chunk references its parent, enabling:
1. Retrieve child for precision
2. Expand to parent for context
3. Return both for comprehensive answers

Usage:
    from utils.hierarchical_chunker import HierarchicalChunker
    from utils.tenant_context import TenantContext
    
    chunker = HierarchicalChunker()
    ctx = TenantContext(tenant_id="huron", dept_id="legal")
    
    chunks = chunker.chunk_document(
        text=document_text,
        source="contract.pdf",
        tenant_context=ctx
    )
"""

import re
import uuid
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)

# Import tenant context
try:
    from utils.tenant_context import TenantContext, ClearanceLevel
except ImportError:
    TenantContext = None
    ClearanceLevel = None


@dataclass
class HierarchicalChunk:
    """A chunk with parent/child relationship and tenant metadata"""
    
    # Core content
    content: str
    chunk_id: str
    
    # Hierarchy
    chunk_type: str  # "parent" or "child"
    parent_id: Optional[str] = None  # For child chunks
    child_ids: List[str] = field(default_factory=list)  # For parent chunks
    
    # Source info
    source: str = ""
    source_type: str = "document"
    page_number: Optional[int] = None
    section_title: Optional[str] = None
    
    # Position
    start_char: int = 0
    end_char: int = 0
    chunk_index: int = 0
    
    # Multi-tenant metadata
    tenant_id: str = "huron"
    dept_id: Optional[str] = None
    namespace: Optional[str] = None
    sensitivity_level: str = "internal"
    uploaded_by: str = "system"
    
    # Quality metrics
    token_count: int = 0
    quality_score: float = 1.0
    
    # Timestamps
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for vector store upsert"""
        return {
            "id": self.chunk_id,
            "content": self.content,
            "chunk_type": self.chunk_type,
            "parent_id": self.parent_id,
            "child_ids": self.child_ids,
            "source": self.source,
            "source_type": self.source_type,
            "page_number": self.page_number,
            "section_title": self.section_title,
            "start_char": self.start_char,
            "end_char": self.end_char,
            "chunk_index": self.chunk_index,
            "tenant_id": self.tenant_id,
            "dept_id": self.dept_id,
            "namespace": self.namespace,
            "sensitivity_level": self.sensitivity_level,
            "uploaded_by": self.uploaded_by,
            "token_count": self.token_count,
            "quality_score": self.quality_score,
            "created_at": self.created_at,
        }
    
    def to_metadata(self) -> Dict[str, Any]:
        """Convert to metadata dict for Pinecone"""
        return {
            "content": self.content[:40000],  # Pinecone metadata limit
            "chunk_type": self.chunk_type,
            "parent_id": self.parent_id or "",
            "source": self.source,
            "source_type": self.source_type,
            "page_number": self.page_number or 0,
            "section_title": self.section_title or "",
            "tenant_id": self.tenant_id,
            "dept_id": self.dept_id or "",
            "namespace": self.namespace or "",
            "sensitivity_level": self.sensitivity_level,
            "uploaded_by": self.uploaded_by,
            "token_count": self.token_count,
            "quality_score": self.quality_score,
            "created_at": self.created_at,
        }


class HierarchicalChunker:
    """
    Creates hierarchical parent/child chunks for RAG retrieval.
    
    Strategy:
    1. Split document into parent chunks (~1024 tokens)
    2. Split each parent into child chunks (~256 tokens)
    3. Link children to parents via parent_id
    4. Add tenant/dept metadata to all chunks
    """
    
    def __init__(
        self,
        parent_chunk_size: int = 1024,
        child_chunk_size: int = 256,
        parent_overlap: int = 128,
        child_overlap: int = 32,
        min_chunk_size: int = 50,
    ):
        """
        Initialize chunker with size parameters.
        
        Args:
            parent_chunk_size: Target size for parent chunks (tokens)
            child_chunk_size: Target size for child chunks (tokens)
            parent_overlap: Overlap between parent chunks
            child_overlap: Overlap between child chunks
            min_chunk_size: Minimum chunk size to keep
        """
        self.parent_chunk_size = parent_chunk_size
        self.child_chunk_size = child_chunk_size
        self.parent_overlap = parent_overlap
        self.child_overlap = child_overlap
        self.min_chunk_size = min_chunk_size
        
        # Approximate chars per token (for estimation)
        self.chars_per_token = 4
        
        # Separators in order of preference
        self.separators = [
            "\n\n\n",   # Major sections
            "\n\n",     # Paragraphs
            "\n",       # Lines
            ". ",       # Sentences
            "! ",
            "? ",
            "; ",
            ", ",       # Clauses
            " ",        # Words
        ]
    
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count from text length"""
        return len(text) // self.chars_per_token
    
    def chunk_document(
        self,
        text: str,
        source: str,
        tenant_context: Optional[Any] = None,
        document_type: str = "general",
        page_numbers: Optional[Dict[int, int]] = None,
        **metadata
    ) -> Tuple[List[HierarchicalChunk], List[HierarchicalChunk]]:
        """
        Chunk document into hierarchical parent/child chunks.
        
        Args:
            text: Document text to chunk
            source: Source identifier (filename, URL, etc.)
            tenant_context: TenantContext for multi-tenant metadata
            document_type: Type of document (legal, technical, etc.)
            page_numbers: Optional mapping of char positions to page numbers
            **metadata: Additional metadata to include
        
        Returns:
            Tuple of (parent_chunks, child_chunks)
        """
        # Extract tenant metadata
        tenant_id = "huron"
        dept_id = None
        namespace = None
        sensitivity = "internal"
        uploaded_by = "system"
        
        if tenant_context:
            tenant_id = getattr(tenant_context, "tenant_id", "huron")
            dept_id = getattr(tenant_context, "dept_id", None)
            uploaded_by = getattr(tenant_context, "username", "system")
            if hasattr(tenant_context, "get_namespace") and dept_id:
                namespace = tenant_context.get_namespace()
            if hasattr(tenant_context, "clearance_level"):
                cl = tenant_context.clearance_level
                sensitivity = cl.value if hasattr(cl, "value") else str(cl)
        
        # Override with explicit metadata
        tenant_id = metadata.get("tenant_id", tenant_id)
        dept_id = metadata.get("dept_id", dept_id)
        sensitivity = metadata.get("sensitivity_level", sensitivity)
        uploaded_by = metadata.get("uploaded_by", uploaded_by)
        
        # Detect sections for better chunking
        sections = self._detect_sections(text, document_type)
        
        parent_chunks = []
        child_chunks = []
        
        # Process each section
        for section_idx, (section_text, section_title) in enumerate(sections):
            # Create parent chunks for this section
            section_parents = self._create_parent_chunks(
                text=section_text,
                source=source,
                section_title=section_title,
                section_offset=self._get_section_offset(text, section_text),
                base_index=len(parent_chunks),
                tenant_id=tenant_id,
                dept_id=dept_id,
                namespace=namespace,
                sensitivity=sensitivity,
                uploaded_by=uploaded_by,
                page_numbers=page_numbers,
            )
            
            # Create child chunks for each parent
            for parent in section_parents:
                children = self._create_child_chunks(
                    parent=parent,
                    tenant_id=tenant_id,
                    dept_id=dept_id,
                    namespace=namespace,
                    sensitivity=sensitivity,
                    uploaded_by=uploaded_by,
                )
                
                # Link children to parent
                parent.child_ids = [c.chunk_id for c in children]
                
                child_chunks.extend(children)
            
            parent_chunks.extend(section_parents)
        
        logger.info(
            f"Created {len(parent_chunks)} parent chunks and "
            f"{len(child_chunks)} child chunks from {source}"
        )
        
        return parent_chunks, child_chunks
    
    def _detect_sections(
        self, 
        text: str, 
        document_type: str
    ) -> List[Tuple[str, Optional[str]]]:
        """
        Detect document sections based on structure.
        
        Returns list of (section_text, section_title) tuples.
        """
        # Section patterns by document type
        patterns = {
            "legal": [
                r"(ARTICLE [IVX]+\..*?)(?=ARTICLE [IVX]+\.|$)",
                r"(SECTION \d+\..*?)(?=SECTION \d+\.|$)",
                r"(Chapter \d+.*?)(?=Chapter \d+|$)",
            ],
            "technical": [
                r"(#{1,3}\s+.*?)(?=#{1,3}\s+|$)",
                r"(<h[1-3]>.*?</h[1-3]>.*?)(?=<h[1-3]>|$)",
            ],
            "general": [
                r"(\n\n\n.*?)(?=\n\n\n|$)",
            ],
        }
        
        doc_patterns = patterns.get(document_type, patterns["general"])
        
        # Try to find sections
        for pattern in doc_patterns:
            try:
                matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
                if matches and len(matches) > 1:
                    sections = []
                    for match in matches:
                        # Extract title from first line
                        lines = match.strip().split('\n')
                        title = lines[0][:100] if lines else None
                        sections.append((match, title))
                    return sections
            except re.error:
                continue
        
        # Fallback: treat entire document as one section
        return [(text, None)]
    
    def _get_section_offset(self, full_text: str, section_text: str) -> int:
        """Get character offset of section within full text"""
        try:
            return full_text.index(section_text)
        except ValueError:
            return 0
    
    def _create_parent_chunks(
        self,
        text: str,
        source: str,
        section_title: Optional[str],
        section_offset: int,
        base_index: int,
        tenant_id: str,
        dept_id: Optional[str],
        namespace: Optional[str],
        sensitivity: str,
        uploaded_by: str,
        page_numbers: Optional[Dict[int, int]] = None,
    ) -> List[HierarchicalChunk]:
        """Create parent chunks from text"""
        
        target_chars = self.parent_chunk_size * self.chars_per_token
        overlap_chars = self.parent_overlap * self.chars_per_token
        
        chunks = []
        start = 0
        chunk_index = base_index
        
        while start < len(text):
            # Find end position
            end = min(start + target_chars, len(text))
            
            # Try to break at a natural boundary
            if end < len(text):
                for sep in self.separators:
                    # Look for separator near the target end
                    search_start = max(start + target_chars - 200, start)
                    sep_pos = text.rfind(sep, search_start, end + 100)
                    if sep_pos > start:
                        end = sep_pos + len(sep)
                        break
            
            chunk_text = text[start:end].strip()
            
            if len(chunk_text) >= self.min_chunk_size:
                # Determine page number if available
                page_num = None
                if page_numbers:
                    abs_pos = section_offset + start
                    for char_pos, page in sorted(page_numbers.items()):
                        if char_pos <= abs_pos:
                            page_num = page
                        else:
                            break
                
                chunk = HierarchicalChunk(
                    content=chunk_text,
                    chunk_id=str(uuid.uuid4()),
                    chunk_type="parent",
                    parent_id=None,
                    source=source,
                    source_type="document",
                    page_number=page_num,
                    section_title=section_title,
                    start_char=section_offset + start,
                    end_char=section_offset + end,
                    chunk_index=chunk_index,
                    tenant_id=tenant_id,
                    dept_id=dept_id,
                    namespace=namespace,
                    sensitivity_level=sensitivity,
                    uploaded_by=uploaded_by,
                    token_count=self.estimate_tokens(chunk_text),
                )
                chunks.append(chunk)
                chunk_index += 1
            
            # Move to next position with overlap
            start = end - overlap_chars
            if start >= end:
                start = end
        
        return chunks
    
    def _create_child_chunks(
        self,
        parent: HierarchicalChunk,
        tenant_id: str,
        dept_id: Optional[str],
        namespace: Optional[str],
        sensitivity: str,
        uploaded_by: str,
    ) -> List[HierarchicalChunk]:
        """Create child chunks from a parent chunk"""
        
        text = parent.content
        target_chars = self.child_chunk_size * self.chars_per_token
        overlap_chars = self.child_overlap * self.chars_per_token
        
        chunks = []
        start = 0
        child_index = 0
        
        while start < len(text):
            end = min(start + target_chars, len(text))
            
            # Try to break at natural boundary
            if end < len(text):
                for sep in self.separators:
                    sep_pos = text.rfind(sep, start + target_chars - 100, end + 50)
                    if sep_pos > start:
                        end = sep_pos + len(sep)
                        break
            
            chunk_text = text[start:end].strip()
            
            if len(chunk_text) >= self.min_chunk_size:
                chunk = HierarchicalChunk(
                    content=chunk_text,
                    chunk_id=str(uuid.uuid4()),
                    chunk_type="child",
                    parent_id=parent.chunk_id,
                    source=parent.source,
                    source_type=parent.source_type,
                    page_number=parent.page_number,
                    section_title=parent.section_title,
                    start_char=parent.start_char + start,
                    end_char=parent.start_char + end,
                    chunk_index=child_index,
                    tenant_id=tenant_id,
                    dept_id=dept_id,
                    namespace=namespace,
                    sensitivity_level=sensitivity,
                    uploaded_by=uploaded_by,
                    token_count=self.estimate_tokens(chunk_text),
                )
                chunks.append(chunk)
                child_index += 1
            
            start = end - overlap_chars
            if start >= end:
                start = end
        
        return chunks
    
    def get_parent_for_child(
        self, 
        child_chunk_id: str, 
        all_parents: List[HierarchicalChunk]
    ) -> Optional[HierarchicalChunk]:
        """Find parent chunk for a given child"""
        # This would typically query the vector store
        # For now, search in provided list
        for parent in all_parents:
            if child_chunk_id in parent.child_ids:
                return parent
        return None


# Quality gate function
def apply_quality_gate(
    chunks: List[HierarchicalChunk],
    min_length: int = 50,
    max_length: int = 10000,
    min_quality_score: float = 0.5,
) -> Tuple[List[HierarchicalChunk], List[HierarchicalChunk]]:
    """
    Filter chunks based on quality criteria.
    
    Args:
        chunks: List of chunks to filter
        min_length: Minimum content length
        max_length: Maximum content length
        min_quality_score: Minimum quality score
    
    Returns:
        Tuple of (passed_chunks, rejected_chunks)
    """
    passed = []
    rejected = []
    
    for chunk in chunks:
        content_len = len(chunk.content)
        
        # Check length
        if content_len < min_length:
            chunk.quality_score = 0.3
            rejected.append(chunk)
            continue
        
        if content_len > max_length:
            chunk.quality_score = 0.4
            rejected.append(chunk)
            continue
        
        # Check for garbage content
        if _is_garbage_content(chunk.content):
            chunk.quality_score = 0.2
            rejected.append(chunk)
            continue
        
        # Passed all checks
        chunk.quality_score = 1.0
        passed.append(chunk)
    
    logger.info(f"Quality gate: {len(passed)} passed, {len(rejected)} rejected")
    return passed, rejected


def _is_garbage_content(text: str) -> bool:
    """Check if content appears to be garbage/noise"""
    # Check for excessive special characters
    special_ratio = len(re.findall(r'[^a-zA-Z0-9\s.,!?;:\'"()-]', text)) / max(len(text), 1)
    if special_ratio > 0.3:
        return True
    
    # Check for repetitive patterns
    words = text.lower().split()
    if len(words) > 10:
        unique_ratio = len(set(words)) / len(words)
        if unique_ratio < 0.3:
            return True
    
    # Check for very short words (OCR noise)
    if words:
        avg_word_len = sum(len(w) for w in words) / len(words)
        if avg_word_len < 2:
            return True
    
    return False
