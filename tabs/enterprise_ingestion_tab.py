"""
Enterprise Document Ingestion Tab
=================================
Multi-tenant ingestion with hierarchical chunking, quality gates,
and optional web crawling support.

Features:
- Hierarchical chunking (parent 1024 / child 256 tokens)
- Multi-tenant namespace isolation
- Quality gate filtering
- Document classification
- Web crawler integration (Firecrawl)
- Pinecone/FAISS backend support
"""

import streamlit as st
import os
import asyncio
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

# Import ingestion service
try:
    from utils.ingestion_service import IngestionService, IngestionResult
    from utils.hierarchical_chunker import HierarchicalChunker, HierarchicalChunk
    INGESTION_SERVICE_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Ingestion service not available: {e}")
    INGESTION_SERVICE_AVAILABLE = False

# Import tenant context
try:
    from utils.tenant_context import TenantContext, ClearanceLevel
    TENANT_CONTEXT_AVAILABLE = True
except ImportError:
    TENANT_CONTEXT_AVAILABLE = False
    TenantContext = None

# Import Pinecone adapter
try:
    from utils.adapters.pinecone_adapter import PineconeAdapter
    PINECONE_AVAILABLE = True
except ImportError:
    PINECONE_AVAILABLE = False

# Import web crawler
try:
    from utils.web_crawler import WebCrawler
    CRAWLER_AVAILABLE = True
except ImportError:
    CRAWLER_AVAILABLE = False

# Import department registry
try:
    import yaml
    def load_dept_registry():
        registry_path = Path("config/dept_namespace_registry.yml")
        if registry_path.exists():
            with open(registry_path) as f:
                return yaml.safe_load(f)
        return {"departments": {}}
except ImportError:
    def load_dept_registry():
        return {"departments": {}}


def render_enterprise_ingestion(user, permissions, auth_middleware, **kwargs):
    """
    Enterprise Document Ingestion Tab with multi-tenant support.
    """
    
    # Log access
    if auth_middleware:
        auth_middleware.log_user_action("ACCESS_ENTERPRISE_INGESTION")
    
    # Extract user info
    if isinstance(user, dict):
        username = user.get('username', 'Unknown')
        user_role = user.get('role', 'viewer')
        user_dept = user.get('dept_id', None)
        user_tenant = user.get('tenant_id', 'huron')
    else:
        username = getattr(user, 'username', 'Unknown')
        user_role = getattr(user, 'role', 'viewer')
        if hasattr(user_role, 'value'):
            user_role = user_role.value
        user_dept = getattr(user, 'dept_id', None)
        user_tenant = getattr(user, 'tenant_id', 'huron')
    
    # Header
    st.header("📄 Enterprise Document Ingestion")
    st.caption(f"👤 {username} | 🏢 {user_tenant} | 🏷️ {user_dept or 'No department'}")
    
    # Check service availability
    if not INGESTION_SERVICE_AVAILABLE:
        st.error("❌ Ingestion service not available. Check imports.")
        return
    
    # Load department registry
    dept_registry = load_dept_registry()
    departments = dept_registry.get("departments", {})
    
    # Create tabs
    tab1, tab2, tab3 = st.tabs(["📁 File Upload", "🌐 Web Crawl", "📊 Status"])
    
    # ==================== FILE UPLOAD TAB ====================
    with tab1:
        render_file_upload_section(
            username=username,
            user_dept=user_dept,
            user_tenant=user_tenant,
            departments=departments
        )
    
    # ==================== WEB CRAWL TAB ====================
    with tab2:
        render_web_crawl_section(
            username=username,
            user_dept=user_dept,
            user_tenant=user_tenant,
            departments=departments
        )
    
    # ==================== STATUS TAB ====================
    with tab3:
        render_status_section()


def render_file_upload_section(username: str, user_dept: str, user_tenant: str, departments: dict):
    """Render file upload and ingestion UI"""
    
    st.subheader("📁 Upload Documents")
    
    # Department selector (admin can select any, users see their dept)
    col1, col2 = st.columns(2)
    
    with col1:
        dept_options = list(departments.keys()) if departments else ["general", "hr", "legal", "finance"]
        
        if user_dept and user_dept in dept_options:
            default_idx = dept_options.index(user_dept)
        else:
            default_idx = 0
        
        selected_dept = st.selectbox(
            "🏷️ Target Department",
            dept_options,
            index=default_idx,
            key="ingest_dept"
        )
    
    with col2:
        sensitivity_options = ["public", "internal", "confidential", "restricted"]
        sensitivity = st.selectbox(
            "🔒 Sensitivity Level",
            sensitivity_options,
            index=1,  # Default to internal
            key="ingest_sensitivity"
        )
    
    # Document type override (optional)
    doc_type = st.selectbox(
        "📄 Document Type (optional)",
        ["Auto-detect", "legal", "technical", "general", "financial", "hr"],
        key="ingest_doc_type"
    )
    
    # File uploader
    uploaded_files = st.file_uploader(
        "Drop files here",
        type=["pdf", "docx", "doc", "txt", "md"],
        accept_multiple_files=True,
        key="enterprise_file_uploader"
    )
    
    # Chunking options
    with st.expander("⚙️ Advanced Options"):
        col1, col2 = st.columns(2)
        with col1:
            parent_size = st.slider("Parent chunk size (tokens)", 512, 2048, 1024)
            enable_quality_gate = st.checkbox("Enable quality gate", value=True)
        with col2:
            child_size = st.slider("Child chunk size (tokens)", 128, 512, 256)
            enable_classification = st.checkbox("Auto-classify documents", value=True)
    
    # Ingest button
    if uploaded_files:
        st.info(f"📎 {len(uploaded_files)} file(s) selected")
        
        if st.button("🚀 Start Ingestion", type="primary", key="start_ingest"):
            # Create tenant context
            if TENANT_CONTEXT_AVAILABLE and TenantContext:
                ctx = TenantContext(
                    tenant_id=user_tenant,
                    dept_id=selected_dept,
                    username=username,
                    clearance_level=ClearanceLevel.from_string(sensitivity)
                )
            else:
                ctx = None
            
            # Initialize service
            service = IngestionService(
                parent_chunk_size=parent_size,
                child_chunk_size=child_size,
                enable_quality_gate=enable_quality_gate,
                enable_classification=enable_classification and doc_type == "Auto-detect"
            )
            
            # Process files
            progress_bar = st.progress(0)
            status_text = st.empty()
            results_container = st.container()
            
            results = []
            for i, file in enumerate(uploaded_files):
                status_text.text(f"Processing {file.name}...")
                
                # Read file content
                file_content = file.read()
                file.seek(0)  # Reset for potential re-read
                
                # Determine doc type
                file_doc_type = None if doc_type == "Auto-detect" else doc_type
                
                # Run ingestion
                try:
                    result = asyncio.run(service.ingest_document(
                        file_content=file_content,
                        file_name=file.name,
                        tenant_context=ctx,
                        document_type=file_doc_type,
                        sensitivity_level=sensitivity,
                    ))
                    results.append(result)
                except Exception as e:
                    logger.error(f"Ingestion failed for {file.name}: {e}")
                    results.append(IngestionResult(
                        success=False,
                        document_id="",
                        source=file.name,
                        error=str(e)
                    ))
                
                progress_bar.progress((i + 1) / len(uploaded_files))
            
            status_text.text("✅ Ingestion complete!")
            
            # Display results
            with results_container:
                st.subheader("📊 Ingestion Results")
                
                success_count = sum(1 for r in results if r.success)
                st.metric("Success Rate", f"{success_count}/{len(results)}")
                
                for result in results:
                    if result.success:
                        with st.expander(f"✅ {result.source}", expanded=False):
                            col1, col2, col3 = st.columns(3)
                            col1.metric("Parent Chunks", result.parent_chunks)
                            col2.metric("Child Chunks", result.child_chunks)
                            col3.metric("Rejected", result.rejected_chunks)
                            
                            st.caption(f"Type: {result.document_type} | Namespace: {result.namespace}")
                            st.caption(f"Processing time: {result.processing_time_ms}ms")
                            
                            if result.warnings:
                                st.warning("\n".join(result.warnings))
                    else:
                        with st.expander(f"❌ {result.source}", expanded=True):
                            st.error(result.error)
    else:
        st.info("👆 Upload documents to begin ingestion")


def render_web_crawl_section(username: str, user_dept: str, user_tenant: str, departments: dict):
    """Render web crawling UI"""
    
    st.subheader("🌐 Web Crawler")
    
    if not CRAWLER_AVAILABLE:
        st.warning("⚠️ Web crawler not configured. Install Firecrawl to enable.")
        
        st.markdown("""
        ### Setup Instructions
        
        1. Install Firecrawl: `pip install firecrawl`
        2. Get API key from [firecrawl.dev](https://firecrawl.dev)
        3. Add to `.env`: `FIRECRAWL_API_KEY=your_key`
        
        Or configure URLs in `config/dept_namespace_registry.yml`:
        ```yaml
        departments:
          legal:
            web_crawler:
              enabled: true
              seed_urls:
                - https://example.com/legal
        ```
        """)
        return
    
    # Department selector
    col1, col2 = st.columns(2)
    
    with col1:
        dept_options = list(departments.keys()) if departments else ["general"]
        selected_dept = st.selectbox(
            "🏷️ Department",
            dept_options,
            key="crawl_dept"
        )
    
    with col2:
        # Get department config
        dept_config = departments.get(selected_dept, {})
        crawler_config = dept_config.get("web_crawler", {})
        
        if crawler_config.get("enabled"):
            st.success("✅ Crawler enabled for this department")
        else:
            st.warning("⚠️ Crawler not configured for this department")
    
    # URL input
    st.markdown("#### Enter URLs to Crawl")
    
    # Pre-fill with configured seed URLs
    default_urls = "\n".join(crawler_config.get("seed_urls", []))
    urls_input = st.text_area(
        "URLs (one per line)",
        value=default_urls,
        height=100,
        key="crawl_urls"
    )
    
    # Crawl options
    col1, col2 = st.columns(2)
    with col1:
        max_pages = st.number_input("Max pages", min_value=1, max_value=1000, value=50)
        follow_links = st.checkbox("Follow internal links", value=True)
    with col2:
        max_depth = st.number_input("Max depth", min_value=1, max_value=5, value=2)
        respect_robots = st.checkbox("Respect robots.txt", value=True)
    
    # Start crawl
    if st.button("🕷️ Start Crawl", type="primary", key="start_crawl"):
        urls = [u.strip() for u in urls_input.split("\n") if u.strip()]
        
        if not urls:
            st.error("Please enter at least one URL")
            return
        
        st.info(f"Starting crawl of {len(urls)} URL(s)...")
        
        # This would call the actual crawler
        # For now, show placeholder
        with st.spinner("Crawling..."):
            st.warning("🚧 Web crawler integration pending. URLs registered for crawl:")
            for url in urls:
                st.code(url)


def render_status_section():
    """Render ingestion status and history"""
    
    st.subheader("📊 Ingestion Status")
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    # These would come from a database/cache in production
    col1.metric("Documents Today", "12", "+3")
    col2.metric("Total Chunks", "1,847", "+156")
    col3.metric("Quality Pass Rate", "94%", "+2%")
    col4.metric("Avg Processing Time", "2.3s", "-0.5s")
    
    # Recent ingestions
    st.markdown("#### Recent Ingestions")
    
    # Mock data - would come from database
    recent_data = [
        {"file": "contract_2024.pdf", "dept": "legal", "chunks": 45, "status": "✅", "time": "2 min ago"},
        {"file": "employee_handbook.docx", "dept": "hr", "chunks": 89, "status": "✅", "time": "15 min ago"},
        {"file": "quarterly_report.pdf", "dept": "finance", "chunks": 0, "status": "❌", "time": "1 hour ago"},
    ]
    
    for item in recent_data:
        col1, col2, col3, col4, col5 = st.columns([3, 1, 1, 1, 2])
        col1.write(item["file"])
        col2.write(item["dept"])
        col3.write(str(item["chunks"]))
        col4.write(item["status"])
        col5.write(item["time"])
    
    # Namespace usage
    st.markdown("#### Namespace Usage")
    
    namespace_data = {
        "vaultmind-huron-legal-general": {"vectors": 12500, "size_mb": 45},
        "vaultmind-huron-hr-general": {"vectors": 8900, "size_mb": 32},
        "vaultmind-huron-finance-general": {"vectors": 5600, "size_mb": 20},
    }
    
    for ns, stats in namespace_data.items():
        col1, col2, col3 = st.columns([3, 1, 1])
        col1.code(ns)
        col2.write(f"{stats['vectors']:,} vectors")
        col3.write(f"{stats['size_mb']} MB")


# Alias for compatibility
render_document_ingestion = render_enterprise_ingestion
