"""
Enhanced Chat Assistant Tab with Real LLM Integration
=====================================================
Properly integrated chat assistant with:
- Real LLM connections (OpenAI, Anthropic, Google, etc.)
- RAG (Retrieval Augmented Generation) with vector stores
- Conversation history and context management
- Multiple response styles
"""

import streamlit as st
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
import os
import time
import json
import asyncio
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

# Initialize embedding model globally
@st.cache_resource
def get_embedding_model(model_name="all-MiniLM-L6-v2"):
    """Get or initialize embedding model"""
    try:
        return SentenceTransformer(model_name)
    except Exception as e:
        logger.error(f"Failed to load embedding model: {e}")
        return None

class LLMManager:
    """Manages LLM connections and responses"""
    
    def __init__(self):
        self.openai_client = None
        self.anthropic_client = None
        self.google_client = None
        self._initialize_clients()
    
    def _initialize_clients(self):
        """Initialize LLM clients based on available API keys"""
        # OpenAI
        if os.getenv("OPENAI_API_KEY"):
            try:
                import openai
                openai.api_key = os.getenv("OPENAI_API_KEY")
                self.openai_client = openai
                logger.info("OpenAI client initialized")
            except ImportError:
                logger.warning("OpenAI library not installed")
        
        # Anthropic Claude
        if os.getenv("ANTHROPIC_API_KEY"):
            try:
                from anthropic import Anthropic
                self.anthropic_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
                logger.info("Anthropic client initialized")
            except ImportError:
                logger.warning("Anthropic library not installed")
        
        # Google Gemini
        if os.getenv("GOOGLE_API_KEY"):
            try:
                import google.generativeai as genai
                genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
                self.google_client = genai
                logger.info("Google Gemini client initialized")
            except ImportError:
                logger.warning("Google GenerativeAI library not installed")
    
    def get_available_models(self) -> List[str]:
        """Get list of available LLM models"""
        models = []
        
        if self.openai_client:
            models.extend([
                "gpt-4-turbo-preview",
                "gpt-4",
                "gpt-3.5-turbo",
                "gpt-3.5-turbo-16k"
            ])
        
        if self.anthropic_client:
            models.extend([
                "claude-3-opus-20240229",
                "claude-3-sonnet-20240229",
                "claude-3-haiku-20240307",
                "claude-2.1"
            ])
        
        if self.google_client:
            models.extend([
                "gemini-pro",
                "gemini-pro-vision"
            ])
        
        # Add fallback model
        if not models:
            models.append("No LLM Available - Configure API Keys")
        
        return models
    
    def generate_response(
        self,
        query: str,
        context: Optional[str] = None,
        model_name: str = "gpt-3.5-turbo",
        temperature: float = 0.7,
        max_tokens: int = 1000,
        conversation_history: List[Dict] = None
    ) -> str:
        """Generate response using selected LLM"""
        
        # Build the prompt
        system_prompt = """You are VaultMind AI Assistant, a knowledgeable and helpful AI that assists with questions 
        about documents, technical topics, and general inquiries. When provided with context from documents, 
        use that information to provide accurate, relevant answers. Always cite your sources when using document context."""
        
        if context:
            user_prompt = f"""Based on the following context from the knowledge base, please answer the question.
            
Context:
{context}

Question: {query}

Please provide a comprehensive answer based on the context provided. If the context doesn't contain relevant information, indicate that and provide what general knowledge you have on the topic."""
        else:
            user_prompt = query
        
        # Route to appropriate LLM
        if "gpt" in model_name.lower() and self.openai_client:
            return self._generate_openai_response(
                system_prompt, user_prompt, model_name, 
                temperature, max_tokens, conversation_history
            )
        elif "claude" in model_name.lower() and self.anthropic_client:
            return self._generate_anthropic_response(
                system_prompt, user_prompt, model_name,
                temperature, max_tokens, conversation_history
            )
        elif "gemini" in model_name.lower() and self.google_client:
            return self._generate_gemini_response(
                system_prompt, user_prompt, model_name,
                temperature, max_tokens, conversation_history
            )
        else:
            # Fallback response when no LLM is available
            return self._generate_fallback_response(query, context)
    
    def _generate_openai_response(
        self, system_prompt: str, user_prompt: str, 
        model: str, temperature: float, max_tokens: int,
        conversation_history: List[Dict]
    ) -> str:
        """Generate response using OpenAI"""
        try:
            messages = [{"role": "system", "content": system_prompt}]
            
            # Add conversation history
            if conversation_history:
                for msg in conversation_history[-5:]:  # Last 5 messages
                    messages.append({
                        "role": msg.get("role", "user"),
                        "content": msg.get("content", "")
                    })
            
            messages.append({"role": "user", "content": user_prompt})
            
            response = self.openai_client.ChatCompletion.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"OpenAI generation failed: {e}")
            return f"Error generating response with {model}: {str(e)}"
    
    def _generate_anthropic_response(
        self, system_prompt: str, user_prompt: str,
        model: str, temperature: float, max_tokens: int,
        conversation_history: List[Dict]
    ) -> str:
        """Generate response using Anthropic Claude"""
        try:
            # Build conversation for Claude
            full_prompt = f"{system_prompt}\n\n"
            
            if conversation_history:
                for msg in conversation_history[-5:]:
                    role = "Human" if msg.get("role") == "user" else "Assistant"
                    full_prompt += f"{role}: {msg.get('content', '')}\n\n"
            
            full_prompt += f"Human: {user_prompt}\n\nAssistant:"
            
            response = self.anthropic_client.completions.create(
                model=model,
                prompt=full_prompt,
                max_tokens_to_sample=max_tokens,
                temperature=temperature
            )
            
            return response.completion
            
        except Exception as e:
            logger.error(f"Anthropic generation failed: {e}")
            return f"Error generating response with {model}: {str(e)}"
    
    def _generate_gemini_response(
        self, system_prompt: str, user_prompt: str,
        model: str, temperature: float, max_tokens: int,
        conversation_history: List[Dict]
    ) -> str:
        """Generate response using Google Gemini"""
        try:
            model = self.google_client.GenerativeModel(model)
            
            # Build prompt with context
            full_prompt = f"{system_prompt}\n\n{user_prompt}"
            
            response = model.generate_content(
                full_prompt,
                generation_config={
                    "temperature": temperature,
                    "max_output_tokens": max_tokens,
                }
            )
            
            return response.text
            
        except Exception as e:
            logger.error(f"Gemini generation failed: {e}")
            return f"Error generating response with {model}: {str(e)}"
    
    def _generate_fallback_response(self, query: str, context: Optional[str]) -> str:
        """Generate fallback response when no LLM is available"""
        if context:
            return f"""📚 **Document Context Found**

Based on your search for "{query}", here is relevant information from your knowledge base:

{context[:1500]}...

**Note:** To get more intelligent responses, please configure LLM API keys in your environment variables:
- OpenAI: OPENAI_API_KEY
- Anthropic: ANTHROPIC_API_KEY  
- Google: GOOGLE_API_KEY
"""
        else:
            return f"""⚠️ **No LLM Configured**

I found your question: "{query}"

However, no LLM API is currently configured. To enable intelligent responses:

1. **Set up API keys** in your environment:
   - OpenAI: `OPENAI_API_KEY`
   - Anthropic: `ANTHROPIC_API_KEY`
   - Google: `GOOGLE_API_KEY`

2. **Install required libraries**:
   ```bash
   pip install openai anthropic google-generativeai
   ```

3. **Restart the application** after configuration.

Once configured, I'll be able to provide detailed, contextual answers to your questions.
"""


class VectorSearchManager:
    """Manages vector search across different storage backends"""
    
    def __init__(self):
        self.embedding_model = get_embedding_model()
    
    async def search_knowledge_base(
        self,
        query: str,
        collection_name: str,
        backend: str = "auto",
        top_k: int = 5
    ) -> Tuple[List[str], List[Dict]]:
        """Search knowledge base and return relevant documents"""
        try:
            # Generate embedding for query
            if self.embedding_model:
                query_embedding = self.embedding_model.encode(query).tolist()
            else:
                query_embedding = None
            
            results = []
            sources = []
            
            # Try Weaviate first
            if backend in ["auto", "weaviate"]:
                try:
                    from utils.weaviate_manager import get_weaviate_manager
                    wm = get_weaviate_manager()
                    
                    if wm and wm.client:
                        weaviate_results = wm.search_documents(
                            collection_name=collection_name,
                            query=query,
                            query_embedding=query_embedding,
                            limit=top_k
                        )
                        
                        for r in weaviate_results:
                            results.append(r.get('content', ''))
                            sources.append({
                                'source': r.get('source', 'Unknown'),
                                'score': r.get('score', 0.0)
                            })
                        
                        if results:
                            logger.info(f"Found {len(results)} results in Weaviate")
                            return results, sources
                            
                except Exception as e:
                    logger.error(f"Weaviate search failed: {e}")
            
            # Try Pinecone
            if backend in ["auto", "pinecone"] and not results:
                try:
                    from utils.simple_vector_manager import search_index
                    
                    pinecone_results = search_index(
                        index_name=collection_name,
                        query=query,
                        top_k=top_k
                    )
                    
                    for r in pinecone_results:
                        results.append(r.get('content', ''))
                        sources.append({
                            'source': r.get('metadata', {}).get('source', 'Unknown'),
                            'score': r.get('score', 0.0)
                        })
                    
                    if results:
                        logger.info(f"Found {len(results)} results in Pinecone")
                        return results, sources
                        
                except Exception as e:
                    logger.error(f"Pinecone search failed: {e}")
            
            # Try FAISS
            if backend in ["auto", "faiss"] and not results:
                try:
                    from utils.index_manager import get_index_manager
                    im = get_index_manager()
                    
                    if im.index_exists(collection_name):
                        faiss_results = im.search(
                            index_name=collection_name,
                            query=query,
                            top_k=top_k
                        )
                        
                        for r in faiss_results:
                            results.append(r.get('content', ''))
                            sources.append({
                                'source': r.get('metadata', {}).get('source', 'Unknown'),
                                'score': r.get('score', 0.0)
                            })
                        
                        if results:
                            logger.info(f"Found {len(results)} results in FAISS")
                            return results, sources
                            
                except Exception as e:
                    logger.error(f"FAISS search failed: {e}")
            
            return results, sources
            
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return [], []


def render_chat_assistant():
    """Render the enhanced chat assistant interface"""
    
    st.title("💬 VaultMind Chat Assistant")
    st.markdown("""
    **Intelligent conversational AI with knowledge base integration**
    
    Features:
    - 🤖 Multiple LLM providers (OpenAI, Anthropic, Google)
    - 📚 RAG (Retrieval Augmented Generation) 
    - 🔍 Multi-backend vector search
    - 💡 Context-aware responses
    - 🎨 Multiple conversation styles
    """)
    
    # Initialize managers
    llm_manager = LLMManager()
    search_manager = VectorSearchManager()
    
    # Sidebar configuration
    with st.sidebar:
        st.header("⚙️ Chat Configuration")
        
        # LLM Selection
        available_models = llm_manager.get_available_models()
        selected_model = st.selectbox(
            "🤖 AI Model",
            available_models,
            help="Select the LLM model for responses"
        )
        
        # Check if any LLM is available
        llm_available = not ("No LLM Available" in selected_model)
        
        if llm_available:
            st.success(f"✅ Using: {selected_model}")
        else:
            st.error("❌ No LLM configured - See instructions below")
            with st.expander("Setup Instructions"):
                st.markdown("""
                **Configure at least one LLM API key:**
                
                1. **OpenAI GPT**
                   - Get key from: https://platform.openai.com/api-keys
                   - Set: `OPENAI_API_KEY=your_key`
                
                2. **Anthropic Claude**
                   - Get key from: https://console.anthropic.com/
                   - Set: `ANTHROPIC_API_KEY=your_key`
                
                3. **Google Gemini**
                   - Get key from: https://makersuite.google.com/app/apikey
                   - Set: `GOOGLE_API_KEY=your_key`
                
                Add to your `.env` file and restart the app.
                """)
        
        # Knowledge Base Selection
        st.markdown("### 📚 Knowledge Base")
        
        use_knowledge_base = st.checkbox(
            "Use Knowledge Base (RAG)",
            value=True,
            help="Search your documents for context"
        )
        
        if use_knowledge_base:
            # Backend selection
            backend_options = ["Auto Detect", "Weaviate", "Pinecone", "FAISS"]
            selected_backend = st.selectbox(
                "Vector Store Backend",
                backend_options
            )
            
            # Collection/Index selection
            collection_name = st.text_input(
                "Collection/Index Name",
                value="default",
                help="Name of your knowledge base collection"
            )
            
            # Search settings
            top_k = st.slider(
                "Documents to Retrieve",
                min_value=1,
                max_value=10,
                value=5
            )
        
        # Conversation Style
        st.markdown("### 🎨 Response Style")
        
        conversation_styles = {
            "Balanced": "General purpose, well-rounded responses",
            "Concise": "Brief, to-the-point answers",
            "Detailed": "Comprehensive explanations with examples",
            "Technical": "In-depth technical information",
            "Simple": "Easy to understand explanations"
        }
        
        selected_style = st.selectbox(
            "Conversation Style",
            list(conversation_styles.keys()),
            help="Choose how the AI should respond"
        )
        
        st.caption(conversation_styles[selected_style])
        
        # Advanced Settings
        with st.expander("🔧 Advanced Settings"):
            temperature = st.slider(
                "Temperature (Creativity)",
                min_value=0.0,
                max_value=1.0,
                value=0.7,
                step=0.1
            )
            
            max_tokens = st.slider(
                "Max Response Length",
                min_value=100,
                max_value=2000,
                value=1000,
                step=100
            )
        
        # Clear chat button
        if st.button("🗑️ Clear Chat"):
            st.session_state.chat_messages = []
            st.rerun()
    
    # Initialize chat history
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []
        
        # Welcome message
        welcome = {
            "role": "assistant",
            "content": f"""👋 Welcome to VaultMind Chat Assistant!

I'm here to help you with your questions. {'I can search your knowledge base and provide intelligent, contextual answers.' if use_knowledge_base else 'I can provide intelligent answers to your questions.'}

**Current Configuration:**
- Model: {selected_model if llm_available else 'No LLM configured'}
- Knowledge Base: {'Enabled' if use_knowledge_base else 'Disabled'}
- Style: {selected_style}

How can I assist you today?""",
            "timestamp": datetime.now().isoformat()
        }
        st.session_state.chat_messages.append(welcome)
    
    # Display chat history
    for message in st.session_state.chat_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            
            # Show metadata if available
            if message.get("sources"):
                with st.expander("📄 Sources"):
                    for source in message["sources"]:
                        st.caption(f"• {source['source']} (score: {source['score']:.3f})")
    
    # Chat input
    if prompt := st.chat_input("Ask me anything..."):
        # Add user message
        user_msg = {
            "role": "user",
            "content": prompt,
            "timestamp": datetime.now().isoformat()
        }
        st.session_state.chat_messages.append(user_msg)
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Generate response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    # Search knowledge base if enabled
                    context = None
                    sources = []
                    
                    if use_knowledge_base:
                        # Perform async search
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        
                        search_backend = selected_backend.lower().replace(" ", "_")
                        if search_backend == "auto_detect":
                            search_backend = "auto"
                        
                        documents, sources = loop.run_until_complete(
                            search_manager.search_knowledge_base(
                                query=prompt,
                                collection_name=collection_name,
                                backend=search_backend,
                                top_k=top_k
                            )
                        )
                        
                        if documents:
                            context = "\n\n".join(documents)
                            st.info(f"📚 Found {len(documents)} relevant documents")
                    
                    # Generate response
                    if llm_available:
                        response = llm_manager.generate_response(
                            query=prompt,
                            context=context,
                            model_name=selected_model,
                            temperature=temperature,
                            max_tokens=max_tokens,
                            conversation_history=st.session_state.chat_messages[-10:]
                        )
                    else:
                        # Fallback when no LLM
                        response = llm_manager._generate_fallback_response(prompt, context)
                    
                    # Apply conversation style
                    if selected_style == "Concise":
                        # Truncate to key points
                        lines = response.split("\n")
                        response = "\n".join(lines[:5])
                    elif selected_style == "Simple":
                        # Remove technical jargon (basic implementation)
                        response = response.replace("implementation", "setup")
                        response = response.replace("architecture", "structure")
                        response = response.replace("infrastructure", "system")
                    
                    # Display response
                    st.markdown(response)
                    
                    # Add to history
                    assistant_msg = {
                        "role": "assistant",
                        "content": response,
                        "timestamp": datetime.now().isoformat(),
                        "model": selected_model,
                        "sources": sources if sources else None
                    }
                    st.session_state.chat_messages.append(assistant_msg)
                    
                    # Show sources if available
                    if sources:
                        with st.expander("📄 View Sources"):
                            for source in sources:
                                st.caption(f"• {source['source']} (relevance: {source['score']:.3f})")
                    
                except Exception as e:
                    error_msg = f"❌ Error: {str(e)}"
                    st.error(error_msg)
                    
                    # Log error
                    st.session_state.chat_messages.append({
                        "role": "assistant",
                        "content": error_msg,
                        "error": True,
                        "timestamp": datetime.now().isoformat()
                    })


# Main execution
if __name__ == "__main__":
    render_chat_assistant()
