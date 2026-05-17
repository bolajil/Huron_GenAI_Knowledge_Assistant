"""
Enterprise Chat Assistant Tab
==============================
Professional single-prompt Q&A interface with results displayed above input.
Enterprise-grade features with clean, executive-ready UI.
"""

import streamlit as st
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
import os
import time
import json
import asyncio
from dataclasses import dataclass
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

# Custom CSS for enterprise styling
ENTERPRISE_CSS = """
<style>
    /* Enterprise color scheme */
    .result-container {
        background: linear-gradient(135deg, #f5f7fa 0%, #f8f9fb 100%);
        border: 1px solid #e1e4e8;
        border-radius: 12px;
        padding: 2rem;
        margin: 1rem 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    }
    
    .source-card {
        background: white;
        border: 1px solid #e1e4e8;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
        transition: all 0.3s ease;
    }
    
    .source-card:hover {
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        transform: translateY(-2px);
    }
    
    .confidence-high { color: #22863a; font-weight: 600; }
    .confidence-medium { color: #f9826c; font-weight: 500; }
    .confidence-low { color: #cb2431; font-weight: 500; }
    
    .metric-card {
        background: white;
        border-radius: 8px;
        padding: 1rem;
        text-align: center;
        border: 1px solid #e1e4e8;
    }
    
    .metric-value {
        font-size: 2rem;
        font-weight: bold;
        color: #0366d6;
    }
    
    .metric-label {
        color: #586069;
        font-size: 0.875rem;
        margin-top: 0.5rem;
    }
    
    .status-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.875rem;
        font-weight: 500;
        margin: 0.25rem;
    }
    
    .status-success {
        background: #dcffe4;
        color: #22863a;
    }
    
    .status-warning {
        background: #fff5b1;
        color: #735c0f;
    }
    
    .status-error {
        background: #ffdce0;
        color: #cb2431;
    }
</style>
"""

@dataclass
class QueryResult:
    """Enterprise query result structure"""
    query: str
    answer: str
    confidence: float
    sources: List[Dict[str, Any]]
    processing_time: float
    model_used: str
    tokens_used: int = 0
    timestamp: str = ""


class EnterpriseAIEngine:
    """Enterprise-grade AI engine with fallback capabilities"""
    
    def __init__(self):
        self.models = self._initialize_models()
        self.active_model = None
    
    def _initialize_models(self) -> Dict[str, Any]:
        """Initialize available AI models"""
        models = {}
        
        # OpenAI
        if os.getenv("OPENAI_API_KEY"):
            try:
                import openai
                openai.api_key = os.getenv("OPENAI_API_KEY")
                models["openai"] = {
                    "client": openai,
                    "models": ["gpt-4-turbo-preview", "gpt-4", "gpt-3.5-turbo"],
                    "status": "active"
                }
                logger.info("OpenAI initialized")
            except ImportError:
                logger.warning("OpenAI not available")
        
        # Anthropic
        if os.getenv("ANTHROPIC_API_KEY"):
            try:
                from anthropic import Anthropic
                models["anthropic"] = {
                    "client": Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY")),
                    "models": ["claude-3-opus-20240229", "claude-3-sonnet-20240229"],
                    "status": "active"
                }
                logger.info("Anthropic initialized")
            except ImportError:
                logger.warning("Anthropic not available")
        
        # Google
        if os.getenv("GOOGLE_API_KEY"):
            try:
                import google.generativeai as genai
                genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
                models["google"] = {
                    "client": genai,
                    "models": ["gemini-pro"],
                    "status": "active"
                }
                logger.info("Google Gemini initialized")
            except ImportError:
                logger.warning("Google not available")
        
        return models
    
    def get_available_models(self) -> List[str]:
        """Get list of available models"""
        available = []
        for provider, config in self.models.items():
            if config["status"] == "active":
                for model in config["models"]:
                    available.append(f"{provider}:{model}")
        
        if not available:
            available.append("No Models Available")
        
        return available
    
    def process_query(
        self,
        query: str,
        context: Optional[str] = None,
        model_preference: str = "auto",
        temperature: float = 0.7,
        max_tokens: int = 1500
    ) -> QueryResult:
        """Process query and return structured result"""
        
        start_time = time.time()
        
        # Build prompt
        if context:
            prompt = f"""You are an enterprise AI assistant. Use the following context to answer the question accurately and professionally.
            
CONTEXT:
{context[:8000]}

QUESTION: {query}

Provide a comprehensive, professional answer. If the context doesn't fully answer the question, indicate what additional information might be needed."""
        else:
            prompt = f"""You are an enterprise AI assistant. Provide a professional, comprehensive answer to the following question.

QUESTION: {query}

Note: No specific document context was found. Provide the best answer based on general knowledge."""
        
        # Select and execute model
        answer = "No response generated"
        confidence = 0.0
        model_used = "none"
        tokens_used = 0
        
        # Try available models in order of preference
        for provider, config in self.models.items():
            if config["status"] == "active":
                try:
                    if provider == "openai":
                        response = config["client"].ChatCompletion.create(
                            model=config["models"][0],
                            messages=[
                                {"role": "system", "content": "You are an enterprise AI assistant. Provide professional, accurate responses."},
                                {"role": "user", "content": prompt}
                            ],
                            temperature=temperature,
                            max_tokens=max_tokens
                        )
                        answer = response.choices[0].message.content
                        tokens_used = response.usage.total_tokens
                        model_used = config["models"][0]
                        confidence = 0.95 if context else 0.85
                        break
                        
                    elif provider == "anthropic":
                        response = config["client"].messages.create(
                            model=config["models"][0],
                            max_tokens=max_tokens,
                            temperature=temperature,
                            messages=[{"role": "user", "content": prompt}]
                        )
                        answer = response.content[0].text
                        model_used = config["models"][0]
                        confidence = 0.95 if context else 0.85
                        break
                        
                    elif provider == "google":
                        model = config["client"].GenerativeModel(config["models"][0])
                        response = model.generate_content(prompt)
                        answer = response.text
                        model_used = config["models"][0]
                        confidence = 0.93 if context else 0.83
                        break
                        
                except Exception as e:
                    logger.error(f"{provider} failed: {e}")
                    continue
        
        # Fallback if no AI available
        if answer == "No response generated":
            if context:
                answer = f"""📊 **Document Analysis Results**
                
Based on your query about "{query}", here is the relevant information from your knowledge base:

{context[:2000]}...

**Note:** This is a direct excerpt from your documents. For AI-powered analysis, please configure LLM API keys."""
                confidence = 0.6
                model_used = "Document Extraction"
            else:
                answer = f"""⚠️ **Configuration Required**

Your question: "{query}"

To enable intelligent responses, please configure at least one AI provider:
• OpenAI: Set OPENAI_API_KEY
• Anthropic: Set ANTHROPIC_API_KEY  
• Google: Set GOOGLE_API_KEY

Once configured, I'll provide comprehensive, intelligent answers to your questions."""
                confidence = 0.0
                model_used = "Not Configured"
        
        processing_time = time.time() - start_time
        
        return QueryResult(
            query=query,
            answer=answer,
            confidence=confidence,
            sources=[],
            processing_time=processing_time,
            model_used=model_used,
            tokens_used=tokens_used,
            timestamp=datetime.now().isoformat()
        )


class EnterpriseSearchEngine:
    """Enterprise document search engine"""
    
    def __init__(self):
        self._init_embedding_model()
    
    def _init_embedding_model(self):
        """Initialize embedding model"""
        try:
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        except:
            self.embedding_model = None
    
    async def search(
        self,
        query: str,
        collection: str,
        backend: str = "auto",
        top_k: int = 5
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """Search documents and return context + sources"""
        
        context_parts = []
        sources = []
        
        try:
            # Generate embedding
            query_embedding = None
            if self.embedding_model:
                query_embedding = self.embedding_model.encode(query).tolist()
            
            # Try Weaviate
            if backend in ["auto", "weaviate"]:
                try:
                    from utils.weaviate_manager import get_weaviate_manager
                    wm = get_weaviate_manager()
                    if wm and wm.client:
                        results = wm.search_documents(
                            collection_name=collection,
                            query=query,
                            query_embedding=query_embedding,
                            limit=top_k
                        )
                        for r in results:
                            context_parts.append(r.get('content', ''))
                            sources.append({
                                'source': r.get('source', 'Unknown'),
                                'confidence': r.get('score', 0.0),
                                'excerpt': r.get('content', '')[:200]
                            })
                except Exception as e:
                    logger.error(f"Weaviate search failed: {e}")
            
            # Try Pinecone
            if not sources and backend in ["auto", "pinecone"]:
                try:
                    from utils.simple_vector_manager import search_index
                    results = search_index(collection, query, top_k)
                    for r in results:
                        context_parts.append(r.get('content', ''))
                        sources.append({
                            'source': r.get('metadata', {}).get('source', 'Unknown'),
                            'confidence': r.get('score', 0.0),
                            'excerpt': r.get('content', '')[:200]
                        })
                except Exception as e:
                    logger.error(f"Pinecone search failed: {e}")
            
            # Try FAISS
            if not sources and backend in ["auto", "faiss"]:
                try:
                    from utils.index_manager import get_index_manager
                    im = get_index_manager()
                    if im.index_exists(collection):
                        results = im.search(collection, query, top_k)
                        for r in results:
                            context_parts.append(r.get('content', ''))
                            sources.append({
                                'source': r.get('metadata', {}).get('source', 'Unknown'),
                                'confidence': r.get('score', 0.0),
                                'excerpt': r.get('content', '')[:200]
                            })
                except Exception as e:
                    logger.error(f"FAISS search failed: {e}")
            
        except Exception as e:
            logger.error(f"Search error: {e}")
        
        context = "\n\n---\n\n".join(context_parts) if context_parts else None
        return context, sources


def render_result_card(result: QueryResult):
    """Render enterprise-style result card"""
    
    # Determine confidence level and color
    if result.confidence >= 0.9:
        confidence_class = "confidence-high"
        confidence_label = "High Confidence"
    elif result.confidence >= 0.7:
        confidence_class = "confidence-medium"
        confidence_label = "Medium Confidence"
    else:
        confidence_class = "confidence-low"
        confidence_label = "Low Confidence"
    
    # Result header with metrics
    col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
    
    with col1:
        st.markdown(f"### 💡 Query Result")
        st.caption(f"Question: {result.query}")
    
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="{confidence_class}">{result.confidence:.0%}</div>
            <div class="metric-label">Confidence</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div style="color: #0366d6; font-size: 1.5rem; font-weight: bold;">
                {result.processing_time:.1f}s
            </div>
            <div class="metric-label">Response Time</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <div style="color: #28a745; font-size: 1rem; font-weight: bold;">
                {len(result.sources)}
            </div>
            <div class="metric-label">Sources Found</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Main answer section
    st.markdown("---")
    st.markdown("### 📝 Answer")
    st.markdown(result.answer)
    
    # Sources section
    if result.sources:
        st.markdown("---")
        st.markdown("### 📚 Sources")
        
        for i, source in enumerate(result.sources, 1):
            confidence_percent = source['confidence'] * 100
            with st.expander(f"Source {i}: {source['source']} (Relevance: {confidence_percent:.0f}%)"):
                st.markdown(f"**Excerpt:**")
                st.markdown(f"> {source['excerpt']}...")
    
    # Technical details (collapsed by default)
    with st.expander("🔧 Technical Details"):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Model:** {result.model_used}")
            st.markdown(f"**Timestamp:** {result.timestamp}")
        with col2:
            if result.tokens_used > 0:
                st.markdown(f"**Tokens Used:** {result.tokens_used:,}")
            st.markdown(f"**Confidence Score:** {result.confidence:.3f}")


def render_chat_assistant_enterprise():
    """Render enterprise chat assistant interface"""
    
    # Apply custom CSS
    st.markdown(ENTERPRISE_CSS, unsafe_allow_html=True)
    
    # Header
    st.markdown("""
    # 🏢 VaultMind Enterprise Assistant
    
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                color: white; padding: 1.5rem; border-radius: 10px; margin-bottom: 2rem;">
        <h3 style="color: white; margin: 0;">Executive AI-Powered Knowledge Interface</h3>
        <p style="color: rgba(255,255,255,0.9); margin: 0.5rem 0 0 0;">
            Ask questions to instantly access insights from your enterprise knowledge base
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Initialize engines
    ai_engine = EnterpriseAIEngine()
    search_engine = EnterpriseSearchEngine()
    
    # Configuration sidebar
    with st.sidebar:
        st.markdown("## ⚙️ Configuration")
        
        # Model status
        available_models = ai_engine.get_available_models()
        model_available = not ("No Models Available" in available_models[0])
        
        if model_available:
            st.success(f"✅ AI Models Active")
            with st.expander("Available Models"):
                for model in available_models:
                    st.caption(f"• {model}")
        else:
            st.error("❌ No AI Models Configured")
            with st.expander("Setup Guide"):
                st.markdown("""
                **Quick Setup:**
                1. Get API key from provider
                2. Add to `.env` file
                3. Restart application
                
                **Providers:**
                • [OpenAI](https://platform.openai.com/api-keys)
                • [Anthropic](https://console.anthropic.com/)
                • [Google](https://makersuite.google.com/app/apikey)
                """)
        
        st.markdown("---")
        
        # Search settings
        st.markdown("### 📚 Knowledge Base")
        
        use_knowledge = st.toggle("Search Documents", value=True)
        
        if use_knowledge:
            collection_name = st.text_input(
                "Collection Name",
                value="default",
                help="Your document collection name"
            )
            
            backend = st.selectbox(
                "Backend",
                ["Auto", "Weaviate", "Pinecone", "FAISS"]
            )
            
            top_k = st.slider("Max Sources", 3, 10, 5)
        
        # Advanced settings
        with st.expander("🎛️ Advanced"):
            temperature = st.slider("Temperature", 0.0, 1.0, 0.7)
            max_tokens = st.slider("Max Length", 500, 3000, 1500)
        
        # Statistics
        if "query_history" not in st.session_state:
            st.session_state.query_history = []
        
        st.markdown("---")
        st.markdown("### 📊 Session Stats")
        st.metric("Queries", len(st.session_state.query_history))
        
        if st.session_state.query_history:
            avg_time = sum(q.processing_time for q in st.session_state.query_history) / len(st.session_state.query_history)
            st.metric("Avg Response Time", f"{avg_time:.1f}s")
    
    # Main content area
    main_container = st.container()
    
    # Result display area (above input)
    result_area = st.container()
    
    # Show last result if exists
    if "last_result" in st.session_state and st.session_state.last_result:
        with result_area:
            render_result_card(st.session_state.last_result)
    else:
        with result_area:
            st.info("👆 Enter your question below to get started")
    
    # Separator
    st.markdown("---")
    
    # Query input area (at bottom)
    st.markdown("### 🔍 Ask Your Question")
    
    col1, col2 = st.columns([5, 1])
    
    with col1:
        query = st.text_input(
            "",
            placeholder="e.g., What are the key compliance requirements for data protection?",
            label_visibility="collapsed",
            key="enterprise_query_input"
        )
    
    with col2:
        search_button = st.button(
            "🚀 Search",
            type="primary",
            use_container_width=True,
            disabled=not query
        )
    
    # Process query
    if search_button and query:
        with st.spinner("🔄 Processing your query..."):
            try:
                # Search for context if enabled
                context = None
                sources = []
                
                if use_knowledge:
                    # Status update
                    status = st.empty()
                    status.info("📚 Searching knowledge base...")
                    
                    # Perform search
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    context, sources = loop.run_until_complete(
                        search_engine.search(
                            query=query,
                            collection=collection_name,
                            backend=backend.lower(),
                            top_k=top_k
                        )
                    )
                    
                    if sources:
                        status.success(f"✅ Found {len(sources)} relevant sources")
                    else:
                        status.warning("⚠️ No relevant documents found")
                    
                    time.sleep(0.5)
                    status.empty()
                
                # Generate response
                result = ai_engine.process_query(
                    query=query,
                    context=context,
                    model_preference="auto",
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                
                # Add sources to result
                result.sources = sources
                
                # Store result
                st.session_state.last_result = result
                st.session_state.query_history.append(result)
                
                # Clear and show new result
                result_area.empty()
                with result_area:
                    render_result_card(result)
                
                # Success notification
                st.success("✅ Query processed successfully!")
                
            except Exception as e:
                st.error(f"❌ Error processing query: {str(e)}")
    
    # Quick action buttons
    st.markdown("---")
    st.markdown("### 💡 Quick Actions")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("📋 Clear Results"):
            st.session_state.last_result = None
            st.rerun()
    
    with col2:
        if st.button("🔄 Reset Session"):
            st.session_state.query_history = []
            st.session_state.last_result = None
            st.rerun()
    
    with col3:
        if st.button("📊 Export History"):
            if st.session_state.query_history:
                history_data = [
                    {
                        "query": q.query,
                        "confidence": q.confidence,
                        "processing_time": q.processing_time,
                        "timestamp": q.timestamp,
                        "model": q.model_used
                    }
                    for q in st.session_state.query_history
                ]
                st.download_button(
                    "💾 Download JSON",
                    data=json.dumps(history_data, indent=2),
                    file_name=f"query_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )
    
    with col4:
        if st.button("❓ Help"):
            st.info("""
            **How to use:**
            1. Enter your question in the search box
            2. Click Search or press Enter
            3. View results above the search box
            4. Sources show document references
            
            **Tips:**
            • Be specific in your questions
            • Check confidence scores
            • Review source documents
            """)


# Export the main function
def render_chat_assistant():
    """Main entry point for enterprise chat assistant"""
    render_chat_assistant_enterprise()


if __name__ == "__main__":
    render_chat_assistant_enterprise()
