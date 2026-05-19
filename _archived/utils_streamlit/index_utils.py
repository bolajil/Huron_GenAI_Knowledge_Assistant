from pathlib import Path
from langchain_community.vectorstores import FAISS
from app.utils.embeddings import get_embeddings
from langchain_community.embeddings import HuggingFaceEmbeddings
import os
import logging
from typing import List

logger = logging.getLogger(__name__)

# Define the default index root
INDEX_ROOT = Path("data/faiss_index")

def list_indexes(index_root: Path = INDEX_ROOT, force_refresh: bool = False) -> List[str]:
    """
    List available FAISS indexes with caching support.
    Returns both standard FAISS indexes and our custom created indexes.
    Always refreshes after deletion to ensure deleted indexes don't reappear.
    """
    import streamlit as st
    
    # Always force refresh if there was a recent deletion
    if st.session_state.get('index_deleted', False):
        force_refresh = True
        st.session_state['index_deleted'] = False
    
    # Use caching to improve performance, but allow force refresh
    cache_key = "cached_index_list"
    if not force_refresh and cache_key in st.session_state:
        cached_indexes = st.session_state[cache_key]
        if cached_indexes:
            logger.info(f"Using cached index list: {cached_indexes}")
            return cached_indexes
    
    # Check both the old faiss_index location and new indexes location
    index_paths = [
        index_root,
        Path("data/indexes"),  # New location where new indexes are saved
        Path("data/faiss_index")  # Legacy location
    ]
    
    indexes = []
    
    for current_path in index_paths:
        if not current_path.exists():
            continue
            
        logger.info(f"Scanning index path: {current_path}")
        
        # Find all directory-based indexes
        for f in current_path.iterdir():
            if f.is_dir():
                name = f.name
                
                # Handle double _index suffix (like Bylaw_index_index)
                if name.endswith("_index_index"):
                    clean_name = name[:-12]  # Remove _index_index suffix
                elif name.endswith("_index"):
                    clean_name = name[:-6]  # Remove _index suffix
                else:
                    clean_name = name
                
                # Add the index if not already present
                if clean_name not in indexes and clean_name:
                    indexes.append(clean_name)
                    logger.info(f"Found index: {clean_name} (from {name})")
    
    # Add any specifically named indexes we want to prioritize
    specific_indexes = ["AWS", "FIA", "Bylaw", "enterprise_docs", "aws_documentation"]
    for specific in specific_indexes:
        if specific not in indexes:
            # Check if this specific index exists in any of our paths
            for current_path in index_paths:
                possible_dirs = [
                    current_path / specific,
                    current_path / f"{specific}_index", 
                    current_path / f"{specific}_index_index"
                ]
                for dir_path in possible_dirs:
                    if dir_path.exists() and dir_path.is_dir():
                        indexes.append(specific)
                        logger.info(f"Added specific index: {specific}")
                        break
                if specific in indexes:
                    break
    
    # Add the standard FAISS index if it exists
    for current_path in index_paths:
        if (current_path / "index.faiss").exists() or (current_path / "index.pkl").exists():
            if "default_index" not in indexes:
                indexes.append("default_index")
                break
    
    # Add additional fallback indexes for demo if no real indexes exist
    if not indexes:
        logger.warning("No real indexes found, adding demo indexes")
        indexes = ["enterprise_docs", "aws_documentation", "company_policies", "technical_manuals"]
    
    # Cache the results
    st.session_state[cache_key] = indexes
    logger.info(f"Final index list (cached): {indexes}")
    return indexes

def refresh_index_cache():
    """Force refresh of the index cache across all tabs"""
    import streamlit as st
    
    # Clear all possible cache keys
    cache_keys = [
        "cached_index_list",
        "cached_indexes", 
        "available_indexes",
        "index_options"
    ]
    
    for key in cache_keys:
        if key in st.session_state:
            del st.session_state[key]
    
    # Force refresh the index list
    return list_indexes(force_refresh=True)

def load_index(index_name: str, index_root: Path = INDEX_ROOT):
    """
    Load a FAISS index from disk with proper error handling and security settings.
    Supports indexes in both data/faiss_index and data/indexes locations.
    """
    try:
        # Define all possible locations where the index might be stored
        # Include both old and new index locations
        base_paths = [
            index_root,
            Path("data/indexes"),  # New location where Bylaw_index_index is saved
            Path("data/faiss_index"),  # Legacy location
            Path("vectorstores"),
            Path("data")
        ]
        
        possible_paths = []
        for base_path in base_paths:
            possible_paths.extend([
                base_path / index_name,
                base_path / f"{index_name}_index",
                base_path / f"{index_name}_index_index",  # Handle double suffix
                base_path / index_name.replace("_index", ""),
                base_path / index_name.replace("-", "_"),
                base_path / index_name.upper(),
                base_path / f"{index_name.upper()}_index",
                base_path / f"{index_name.upper()}_index_index"
            ])

        # Try to find the first existing path that contains index files
        index_path = None
        custom_dir_path = None
        
        for path in possible_paths:
            if path.exists():
                # Check if it's a directory with any content
                if path.is_dir() and any(path.iterdir()):
                    # First, check if it has standard FAISS index files
                    if (path / "index.faiss").exists() and (path / "index.pkl").exists():
                        index_path = path
                        logger.info(f"✅ Found valid FAISS index at: {path}")
                        break
                    else:
                        # It's a directory with content but not a standard FAISS index
                        # Store as potential custom directory but keep looking for FAISS first
                        if not custom_dir_path:
                            custom_dir_path = path
                            logger.info(f"📁 Found directory with content (not FAISS): {path}")
        
        # If we found a FAISS index, use it; otherwise use custom directory
        if not index_path and custom_dir_path:
            logger.info(f"✅ Using custom directory index: {custom_dir_path}")
            return {
                "type": "custom_dir_index", 
                "path": str(custom_dir_path),
                "name": index_name
            }

        if not index_path:
            # If it's not a real index, but we were asked for a standard demo index,
            # return a simulated response
            if index_name in ["enterprise_docs", "aws_documentation", "company_policies", "technical_manuals"]:
                logger.warning(f"Index '{index_name}' not found, but using as demo index")
                return {
                    "type": "simulated_index",
                    "name": index_name
                }
                
            # Otherwise report the failure
            available = "\n".join([str(p) for p in possible_paths])
            raise FileNotFoundError(
                f"Index '{index_name}' not found. Checked locations:\n{available}"
            )

        logger.info(f"🔍 Loading FAISS index from: {index_path}")

        # Load with security override
        return FAISS.load_local(
            folder_path=str(index_path),
            embeddings=get_embeddings(),
            allow_dangerous_deserialization=True
        )
    except Exception as e:
        logger.error(f"❌ Failed to load index {index_name}: {str(e)}")
        # Instead of raising, return a custom error object
        return {
            "type": "error_index",
            "name": index_name,
            "error": str(e)
        }
