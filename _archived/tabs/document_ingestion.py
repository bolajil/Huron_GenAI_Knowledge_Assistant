"""
Document Ingestion Tab
=====================
Upload and index various document types for knowledge base creation.
Access Level: User+ and Admin only
"""

import streamlit as st
from pathlib import Path
import logging
import os
import json
import pickle
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from utils.weaviate_ingestion_helper import get_weaviate_ingestion_helper

def render_document_ingestion(user, permissions, auth_middleware, available_indexes, INDEX_ROOT, PROJECT_ROOT):
    """Document Ingestion Tab Implementation"""
    
    # Handle both dict and object user formats for role check
    if isinstance(user, dict):
        username = user.get('username', 'Unknown')
        role = user.get('role', 'viewer')
    else:
        username = user.username
        role = user.role.value
    
    # Allow all authenticated users to upload documents
    if not st.session_state.get('authenticated', False):
        st.error("❌ Please log in to access document ingestion")
    else:
        auth_middleware.log_user_action("ACCESS_INGEST_TAB")
        
        # Document ingestion form
        st.subheader("📁 Upload and Index Content")
        st.write(f"👤 Logged in as: {username} ({role})")
        st.info("🔧 Updated version with default index name support")
        
        # Index Management Section
        with st.expander("🗂️ Index Management", expanded=False):
            st.subheader("Delete Existing Indexes")
            
            if available_indexes:
                col_idx, col_del = st.columns([3, 1])
                with col_idx:
                    index_to_delete = st.selectbox(
                        "Select index to delete:",
                        options=available_indexes,
                        key="delete_index_selector"
                    )
                with col_del:
                    st.write("")  # Spacing
                    st.write("")  # Spacing
                    if st.button("🗑️ Delete", key="delete_index_btn", type="secondary"):
                        if delete_faiss_index(index_to_delete, INDEX_ROOT):
                            st.success(f"✅ Deleted index: {index_to_delete}")
                            st.rerun()
                        else:
                            st.error(f"❌ Failed to delete: {index_to_delete}")
            else:
                st.info("No indexes available to delete")
        
        # Storage backend selection
        storage_backend = st.radio(
            "Select storage backend:",
            ["Weaviate (Cloud Vector DB)", "Local FAISS Index", "Both (Weaviate + Local FAISS)"],
            horizontal=True,
            help="Choose where to store vectors. 'Both' will index to Weaviate and build a local FAISS index."
        )
        
        source_type = st.radio(
            "Select content source:",
            ["PDF File", "Text File", "Website URL"],
            horizontal=True
        )

        if source_type == "PDF File":
            uploaded_file = st.file_uploader("Choose a PDF file", type=["pdf"])
        elif source_type == "Text File":
            uploaded_file = st.file_uploader("Choose a text file", type=["txt"])
        else:
            url_input = st.text_input(
                "Enter website URL:", placeholder="https://example.com/article"
            )
            render_js = st.checkbox("Render JavaScript (for dynamic sites)")
            max_depth = st.slider("Link depth (for multi-page scraping)", 0, 3, 0)

        if storage_backend in ("Weaviate (Cloud Vector DB)", "Both (Weaviate + Local FAISS)"):
            collection_name = st.text_input(
                "📦 Collection name (no spaces)", 
                value="document_collection",  # Provide default value
                placeholder="e.g. web_article_collection",
                help="Weaviate collection name for storing documents"
            )
            # Upfront Weaviate connectivity check so users see connection status early
            try:
                weaviate_helper_preview = get_weaviate_ingestion_helper()
                conn_ok = weaviate_helper_preview.test_connection()
                if conn_ok:
                    try:
                        api_ver = weaviate_helper_preview.weaviate_manager.detect_api_version()
                    except Exception:
                        api_ver = "unknown"
                    st.success(f"🔗 Weaviate connection OK (API {api_ver}) → {weaviate_helper_preview.weaviate_manager.url}")
                    # Advanced Weaviate ingestion options
                    st.caption("Ingest without OpenAI by computing vectors locally and optionally creating the collection if missing.")
                    use_local_embeddings = st.checkbox(
                        "Use local embeddings (no OpenAI)", value=True, help="Compute vectors with SentenceTransformer and send them with objects."
                    )
                    embedding_model = st.selectbox(
                        "Local embedding model",
                        ["all-MiniLM-L6-v2", "all-MiniLM-L12-v2", "paraphrase-MiniLM-L6-v2"],
                        index=0,
                        help="Model used to generate local vectors for Weaviate."
                    )
                    auto_create_collection = st.checkbox(
                        "Create collection if missing", value=True,
                        help="If enabled, the app will attempt to create the Weaviate collection when it does not exist."
                    )
                    force_rest_batch = st.checkbox(
                        "Use REST batch insertion (diagnostics)", value=True,
                        help="Send objects via REST /v1/batch/objects to capture per-object errors and reliable post-counts."
                    )
                    # Set environment flags used by the ingestion/helper
                    if auto_create_collection:
                        os.environ["WEAVIATE_CREATE_COLLECTIONS"] = "true"
                    else:
                        os.environ["WEAVIATE_CREATE_COLLECTIONS"] = "false"
                    # Enable client-side query vectors for better retrieval when using local vectors
                    if use_local_embeddings:
                        os.environ["WEAVIATE_USE_CLIENT_VECTORS"] = "true"
                    # Force REST batch path for per-object diagnostics
                    os.environ["WEAVIATE_FORCE_REST_BATCH"] = "true" if force_rest_batch else "false"
                else:
                    st.error("❌ Weaviate connection failed. Check WEAVIATE_URL / WEAVIATE_API_KEY in config/weaviate.env or environment. You can switch to 'Local FAISS Index' as a fallback.")
            except Exception as ce:
                st.error(f"❌ Weaviate connectivity check errored: {ce}")
        else:
            collection_name = ""
        if storage_backend in ("Local FAISS Index", "Both (Weaviate + Local FAISS)"):
            index_name = st.text_input(
                "📦 Name for this new index (no spaces)", 
                value="document_index",
                placeholder="e.g. web_article_index"
            )
            if not index_name:
                index_name = "document_index"
                st.info("Using default index name: document_index")
        else:
            index_name = ""
        # Advanced chunking settings
        st.subheader("🔧 Chunking Configuration")
        
        chunking_strategy = st.radio(
            "Select chunking strategy:",
            ["Semantic Chunking (Recommended)", "Size-based Chunking"],
            help="Semantic chunking splits by headers and sections for better accuracy"
        )
        
        if chunking_strategy == "Semantic Chunking (Recommended)":
            chunk_size = st.slider(
                "🧩 Chunk Size", min_value=800, max_value=2000, value=1500, step=100,
                help="Optimal chunk size for preserving context (1200-1800 recommended)"
            )
            chunk_overlap = st.slider(
                "🔁 Chunk Overlap", min_value=100, max_value=500, value=300, step=50,
                help="Prevents sentences from being cut off between chunks"
            )
            split_by_headers = st.checkbox(
                "Split by Headers", value=True,
                help="Creates new chunks at section boundaries (HIGHLY RECOMMENDED)"
            )
            use_embeddings = st.checkbox(
                "Generate Embeddings", value=True,
                help="Enables semantic search using text-embedding-ada-002"
            )
        else:
            chunk_size = st.slider(
                "🧩 Chunk Size", min_value=800, max_value=3000, value=1500, step=100,
                help="Larger chunks preserve more context"
            )
            chunk_overlap = st.slider(
                "🔁 Chunk Overlap", min_value=100, max_value=500, value=300, step=50,
                help="Overlap helps maintain context between chunks"
            )
            split_by_headers = False
            use_embeddings = False

        if st.button("🚀 Ingest & Index"):
            # Determine targets
            do_weaviate = storage_backend in ("Weaviate (Cloud Vector DB)", "Both (Weaviate + Local FAISS)")
            do_local = storage_backend in ("Local FAISS Index", "Both (Weaviate + Local FAISS)")
            # Validate input based on chosen backends with auto-defaults
            if do_weaviate and not collection_name.strip():
                collection_name = "default_collection"
                st.info(f"Using default collection name: {collection_name}")
            if do_local and not index_name.strip():
                index_name = "default_index"
                st.info(f"Using default index name: {index_name}")
            target_name = collection_name if do_weaviate and not do_local else (index_name or collection_name)
            
            auth_middleware.log_user_action("DOCUMENT_INGEST", f"Backend: {storage_backend}, Target: {target_name}, Type: {source_type}")
            
            try:
                st.info("Processing document...")
                progress_bar = st.progress(0)
                
                # Initialize Weaviate helper if using Weaviate backend
                if do_weaviate:
                    weaviate_helper = get_weaviate_ingestion_helper()
                    # Enforce connectivity check before any Weaviate ingestion
                    if not weaviate_helper.test_connection():
                        st.error("❌ Weaviate connection failed. Please verify WEAVIATE_URL / WEAVIATE_API_KEY and try again.")
                        st.stop()
                    else:
                        try:
                            api_ver = weaviate_helper.weaviate_manager.detect_api_version()
                        except Exception:
                            api_ver = "unknown"
                        st.success(f"🔗 Connected to Weaviate (API {api_ver})")
                if do_local:
                    # Create index directory if it doesn't exist (FAISS backend)
                    index_dir = INDEX_ROOT / f"{index_name}_index"
                    if not index_dir.exists():
                        index_dir.mkdir(parents=True, exist_ok=True)
                
                # Process according to source type and storage backend
                if do_weaviate:
                    # Weaviate ingestion path
                    use_semantic = chunking_strategy == "Semantic Chunking (Recommended)"
                    
                    if source_type == "PDF File" and uploaded_file:
                        progress_bar.progress(25)
                        result = weaviate_helper.ingest_pdf_document(
                            collection_name=collection_name,
                            file_content=uploaded_file.getbuffer(),
                            file_name=uploaded_file.name,
                            username=username,
                            chunk_size=chunk_size,
                            chunk_overlap=chunk_overlap,
                            use_semantic_chunking=use_semantic,
                            use_local_embeddings=locals().get("use_local_embeddings", False),
                            embedding_model=locals().get("embedding_model", "all-MiniLM-L6-v2")
                        )
                        
                    elif source_type == "Text File" and uploaded_file:
                        progress_bar.progress(25)
                        try:
                            text_content = uploaded_file.getvalue().decode("utf-8")
                        except UnicodeDecodeError:
                            text_content = uploaded_file.getvalue().decode("latin-1")
                        
                        result = weaviate_helper.ingest_text_document(
                            collection_name=collection_name,
                            text_content=text_content,
                            file_name=uploaded_file.name,
                            username=username,
                            chunk_size=chunk_size,
                            chunk_overlap=chunk_overlap,
                            use_semantic_chunking=use_semantic,
                            use_local_embeddings=locals().get("use_local_embeddings", False),
                            embedding_model=locals().get("embedding_model", "all-MiniLM-L6-v2")
                        )
                        
                    elif source_type == "Website URL" and url_input:
                        progress_bar.progress(25)
                        result = weaviate_helper.ingest_url_content(
                            collection_name=collection_name,
                            url=url_input,
                            username=username,
                            chunk_size=chunk_size,
                            chunk_overlap=chunk_overlap,
                            use_semantic_chunking=use_semantic,
                            render_js=render_js,
                            use_local_embeddings=locals().get("use_local_embeddings", False),
                            embedding_model=locals().get("embedding_model", "all-MiniLM-L6-v2")
                        )
                    else:
                        st.error("Please provide the required input for the selected source type.")
                        st.stop()
                    
                    progress_bar.progress(100)
                    
                    if result.get("success"):
                        st.success("✅ **Document successfully ingested into Weaviate!**")
                        
                        # Display results
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("📄 Documents", "1")
                        with col2:
                            st.metric("🧩 Chunks", str(result.get("total_chunks", 0)))
                        with col3:
                            st.metric("🗄️ Collection", result.get("collection_name", collection_name))
                        
                        st.info(f"**Collection**: `{result.get('collection_name', collection_name)}`")
                        st.success("🔄 **Document available in Weaviate Cloud Service!**")
                        st.info("Your document is now searchable across all tabs using Weaviate.")
                    else:
                        st.error(f"❌ **Weaviate ingestion failed**: {result.get('error', 'Unknown error')}")
                
                # Local FAISS ingestion path (for Local or Both)
                if do_local:
                    # Original FAISS ingestion path
                    import datetime
                    creation_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    chunking_method = "semantic" if chunking_strategy == "Semantic Chunking (Recommended)" else "size_based"
                    
                    with open(index_dir / "index.meta", "w", encoding="utf-8") as f:
                        f.write(f"Created by: {username}\nDocument type: {source_type}\nChunk size: {chunk_size}\nChunk overlap: {chunk_overlap}\nChunking method: {chunking_method}\nSplit by headers: {split_by_headers if chunking_strategy == 'Semantic Chunking (Recommended)' else False}\nUse embeddings: {use_embeddings if chunking_strategy == 'Semantic Chunking (Recommended)' else False}\nCreation date: {creation_date}")
                    
                    # Original FAISS processing logic + ensure extracted_text.txt for index build
                    if source_type == "PDF File" and uploaded_file:
                        try:
                            # Save the uploaded PDF
                            with open(index_dir / f"source_document.pdf", "wb") as f:
                                f.write(uploaded_file.getbuffer())
                            progress_bar.progress(50)
                        
                            # Extract text from PDF if possible
                            try:
                                import io
                                from pypdf import PdfReader
                                reader = PdfReader(io.BytesIO(uploaded_file.getvalue()))
                                text_content = ""
                                for i, page in enumerate(reader.pages):
                                    text_content += f"\n\n--- Page {i+1} ---\n\n"
                                    text_content += page.extract_text() or "[No extractable text on this page]"
                            except:
                                text_content = f"[PDF text extraction failed for {uploaded_file.name}. File was saved but text content couldn't be extracted.]"
                        
                            # Save the extracted text
                            with open(index_dir / "extracted_text.txt", "w", encoding="utf-8") as f:
                                f.write(text_content)
                            
                            # Apply semantic chunking if enabled
                            if chunking_strategy == "Semantic Chunking (Recommended)":
                                try:
                                    from utils.semantic_chunking_strategy import create_semantic_chunks
                                    
                                    st.info("🧠 Applying semantic chunking...")
                                    chunks = create_semantic_chunks(
                                        text_content, 
                                        document_name=uploaded_file.name,
                                        chunk_size=chunk_size,
                                        chunk_overlap=chunk_overlap
                                    )
                                    
                                    # Save semantic chunks
                                    chunks_data = []
                                    for i, chunk in enumerate(chunks):
                                        chunk_file = index_dir / f"semantic_chunk_{i+1}.json"
                                        with open(chunk_file, "w", encoding="utf-8") as f:
                                            json.dump(chunk, f, indent=2, ensure_ascii=False)
                                        chunks_data.append(chunk)
                                    
                                    # Save chunk metadata
                                    with open(index_dir / "chunks_metadata.json", "w", encoding="utf-8") as f:
                                        json.dump({
                                            'total_chunks': len(chunks),
                                            'chunking_method': 'semantic',
                                            'chunk_size': chunk_size,
                                            'chunk_overlap': chunk_overlap,
                                            'split_by_headers': split_by_headers,
                                            'use_embeddings': use_embeddings,
                                            'chunks': [{'title': c['title'], 'size': c['chunk_size'], 'has_embedding': c.get('has_embedding', False)} for c in chunks]
                                        }, f, indent=2)
                                    
                                    st.success(f"✅ Created {len(chunks)} semantic chunks")
                                    
                                except Exception as e:
                                    st.warning(f"Semantic chunking failed, using fallback: {e}")
                                    # Fallback to basic chunking - create simple text chunks
                                    chunk_count = max(1, len(text_content) // (chunk_size - chunk_overlap))
                                    for i in range(min(chunk_count, 10)):
                                        start = i * (chunk_size - chunk_overlap)
                                        end = start + chunk_size
                                        if end > len(text_content):
                                            end = len(text_content)
                                        
                                        chunk = text_content[start:end]
                                        with open(index_dir / f"chunk_{i+1}.txt", "w", encoding="utf-8") as f:
                                            f.write(chunk)
                            
                        except Exception as e:
                            st.warning(f"Partial failure during PDF processing: {str(e)}")
                            # Create a fallback file if extraction failed
                            with open(index_dir / "text_content.txt", "w", encoding="utf-8") as f:
                                f.write(f"Document content from {uploaded_file.name}\nChunked into segments of size {chunk_size} with {chunk_overlap} overlap.")

                    elif source_type == "Text File" and uploaded_file:
                        try:
                            # Try to decode the text with utf-8 first
                            try:
                                text_content = uploaded_file.getvalue().decode("utf-8")
                            except UnicodeDecodeError:
                                # Fall back to latin-1 if utf-8 fails
                                text_content = uploaded_file.getvalue().decode("latin-1")
                            
                            # Save the uploaded text file
                            with open(index_dir / f"source_document.txt", "w", encoding="utf-8") as f:
                                f.write(text_content)
                            progress_bar.progress(50)
                            
                            # Ensure extracted_text.txt exists for FAISS build
                            with open(index_dir / "extracted_text.txt", "w", encoding="utf-8") as f:
                                f.write(text_content)
                            
                            # Create chunks for better retrieval
                            chunk_count = max(1, len(text_content) // (chunk_size - chunk_overlap))
                            for i in range(min(chunk_count, 10)):  # Limit to 10 chunks for performance
                                start = i * (chunk_size - chunk_overlap)
                                end = start + chunk_size
                                if end > len(text_content):
                                    end = len(text_content)
                                
                                chunk = text_content[start:end]
                                with open(index_dir / f"chunk_{i+1}.txt", "w", encoding="utf-8") as f:
                                    f.write(chunk)
                                
                        except Exception as e:
                            st.warning(f"Partial failure during text processing: {str(e)}")
                            # Create a fallback file
                            with open(index_dir / "text_content.txt", "w", encoding="utf-8") as f:
                                f.write(f"Document content from {uploaded_file.name}\nChunked into segments of size {chunk_size} with {chunk_overlap} overlap.")
                        
                    elif source_type == "Website URL" and url_input:
                        try:
                            # Save URL info
                            with open(index_dir / "source_url.txt", "w", encoding="utf-8") as f:
                                f.write(f"URL: {url_input}\nRender JS: {render_js}\nDepth: {max_depth}")
                            progress_bar.progress(30)
                            
                            # Try to fetch content from URL
                            try:
                                import requests
                                from bs4 import BeautifulSoup
                                
                                response = requests.get(url_input, timeout=10)
                                soup = BeautifulSoup(response.content, 'html.parser')
                                
                                # Extract text content
                                text = soup.get_text(separator='\n', strip=True)
                                
                                # Save the raw HTML
                                with open(index_dir / "raw_html.html", "w", encoding="utf-8") as f:
                                    f.write(str(soup))
                                    
                                # Save the extracted text
                                with open(index_dir / "extracted_content.txt", "w", encoding="utf-8") as f:
                                    f.write(text)
                                # Also write extracted_text.txt for FAISS build
                                with open(index_dir / "extracted_text.txt", "w", encoding="utf-8") as f:
                                    f.write(text)
                                    
                                progress_bar.progress(75)
                                
                                # Create chunks for better retrieval
                                chunk_count = max(1, len(text) // (chunk_size - chunk_overlap))
                                for i in range(min(chunk_count, 10)):  # Limit to 10 chunks
                                    start = i * (chunk_size - chunk_overlap)
                                    end = start + chunk_size
                                    if end > len(text):
                                        end = len(text)
                                    
                                    chunk = text[start:end]
                                    with open(index_dir / f"chunk_{i+1}.txt", "w", encoding="utf-8") as f:
                                        f.write(chunk)
                                        
                            except Exception as e:
                                st.warning(f"Error fetching URL content: {str(e)}")
                                # Create a fallback content file
                                with open(index_dir / "url_content.txt", "w", encoding="utf-8") as f:
                                    f.write(f"Content scraped from {url_input}\nWith JavaScript rendering: {render_js}\nLink depth: {max_depth}")
                        
                        except Exception as e:
                            st.warning(f"Partial failure during URL processing: {str(e)}")
                            # Create a fallback file
                            with open(index_dir / "url_content.txt", "w", encoding="utf-8") as f:
                                f.write(f"Content scraped from {url_input}\nWith JavaScript rendering: {render_js}\nLink depth: {max_depth}")
                
                progress_bar.progress(100)
                st.success("✅ **Document successfully indexed!**")
                
                # Build FAISS index for Local/Both so it shows up in Query tab
                if do_local:
                    try:
                        text_path_candidates = [
                            index_dir / "extracted_text.txt",
                            index_dir / "source_document.txt",
                            index_dir / "extracted_content.txt",
                            index_dir / "text_content.txt",
                        ]
                        text_path = next((p for p in text_path_candidates if p.exists()), None)
                        if text_path is None:
                            raise FileNotFoundError("No text file found to build FAISS index (looked for extracted_text.txt, source_document.txt, extracted_content.txt, text_content.txt)")
                        with open(text_path, "r", encoding="utf-8", errors="ignore") as f:
                            text_for_faiss = f.read()
                        faiss_target = Path("data") / "faiss_index" / index_name
                        faiss_target.mkdir(parents=True, exist_ok=True)
                        _build_faiss_index_from_text(text_for_faiss, index_name, faiss_target)
                        st.success(f"🧠 Local FAISS index built at {faiss_target} and ready for queries")
                        # Signal other tabs to refresh the index list
                        st.session_state.force_index_refresh = True
                    except Exception as e:
                        st.error(f"Failed to build FAISS index: {e}")
                
                # Display basic info
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("📄 Documents", "1")
                with col2:
                    st.metric("🧩 Chunks", str(int(5000 / chunk_size)))
                with col3:
                    st.metric("💾 Index", f"{index_name}_index")
                
                st.info(f"**Index saved to**: `{index_dir}`")
                
                # Clear cached index list to force refresh across all tabs
                try:
                    from app.utils.index_utils import refresh_index_cache
                    refresh_index_cache()
                except ImportError:
                    # Fallback manual cache clearing
                    cache_keys = ['cached_indexes', 'available_indexes', 'cached_index_list', 'index_options']
                    for key in cache_keys:
                        if key in st.session_state:
                            del st.session_state[key]
                
                st.success("🔄 **Index list refreshed across all tabs!**")
                st.info("Your document is now available in **Query**, **Chat**, **Agent**, and **Multi-Document** tabs.")
                
                # Trigger index refresh across all tabs
                st.session_state.force_index_refresh = True
                
                # Add refresh button for immediate availability
                if st.button("🔄 Refresh Application", key="refresh_after_upload"):
                    st.rerun()

            except Exception as e:
                st.error(f"❌ **Ingestion failed**: {str(e)}")


# === Helpers: simple chunking and FAISS builder ===
def _simple_text_chunks(text: str, chunk_size: int = 800, overlap: int = 100) -> list[str]:
    """Create simple overlapping chunks from text."""
    if not text:
        return []
    text = text.replace("\r\n", "\n")
    chunks = []
    step = max(1, chunk_size - overlap)
    for i in range(0, len(text), step):
        chunk = text[i:i+chunk_size]
        if chunk:
            chunks.append(chunk)
    return chunks


def _build_faiss_index_from_text(text: str, index_name: str, target_dir: Path, model_name: str = "all-MiniLM-L6-v2") -> None:
    """Build a FAISS index from raw text and save index.faiss + documents.pkl into target_dir."""
    chunks = _simple_text_chunks(text, chunk_size=800, overlap=120)
    if not chunks:
        raise ValueError("No text chunks produced for FAISS build")
    # Embed
    model = SentenceTransformer(model_name)
    embeddings = model.encode(chunks, convert_to_numpy=True, show_progress_bar=False, normalize_embeddings=True)
    embeddings = embeddings.astype('float32')
    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)
    # Save index
    faiss.write_index(index, str(target_dir / "index.faiss"))
    # Save documents metadata
    docs = [{
        "chunk_id": i,
        "text": chunks[i],
        "source": f"local_ingestion:{index_name}",
        "created_at": None
    } for i in range(len(chunks))]
    with open(target_dir / "documents.pkl", "wb") as f:
        pickle.dump(docs, f)


def delete_faiss_index(index_name: str, index_root: Path) -> bool:
    """Delete a FAISS index directory and all its contents."""
    import shutil
    
    try:
        index_path = index_root / index_name
        
        if not index_path.exists():
            logging.warning(f"Index path does not exist: {index_path}")
            return False
        
        # Remove the entire directory
        shutil.rmtree(index_path)
        logging.info(f"Successfully deleted FAISS index: {index_name}")
        return True
        
    except Exception as e:
        logging.error(f"Failed to delete FAISS index '{index_name}': {e}")
        return False
