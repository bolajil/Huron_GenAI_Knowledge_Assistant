import streamlit as st
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
import os
from utils.llm_config import get_available_llm_models, get_default_llm_model, validate_llm_setup

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ConversationManager:
    def __init__(self):
        self.messages = []
    
    def add_message(self, role: str, content: str, metadata: Dict[str, Any] = None):
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        self.messages.append(message)
    
    def get_recent_messages(self, count: int = 5) -> List[Dict[str, Any]]:
        return self.messages[-count:] if self.messages else []
    
    def clear_history(self):
        self.messages.clear()

class ModernChatAssistant:
    def __init__(self):
        self.conversation_manager = ConversationManager()
        self.available_indexes = self._detect_indexes()
        self.vector_store = self._initialize_vector_store()
    
    def _create_openai_client(self):
        """Create an OpenAI client while avoiding the unsupported 'project' kwarg in older SDKs."""
        try:
            os.environ.pop("OPENAI_PROJECT", None)
        except Exception:
            pass
        from openai import OpenAI  # local import
        api_key = os.getenv("OPENAI_API_KEY")
        organization = os.getenv("OPENAI_ORG") or os.getenv("OPENAI_ORGANIZATION")
        try:
            if api_key and organization:
                return OpenAI(api_key=api_key, organization=organization)
            elif api_key:
                return OpenAI(api_key=api_key)
            else:
                return OpenAI()
        except TypeError:
            return OpenAI(api_key=api_key) if api_key else OpenAI()
    
    def _detect_indexes(self) -> List[str]:
        try:
            from utils.unified_vector_store import UnifiedVectorStore
            vector_store = UnifiedVectorStore()
            return vector_store.list_collections()
        except Exception as e:
            logger.warning(f"Could not detect indexes: {e}")
            return []
    
    def _initialize_vector_store(self):
        try:
            from utils.unified_vector_store import UnifiedVectorStore
            return UnifiedVectorStore()
        except Exception as e:
            logger.warning(f"Could not initialize vector store: {e}")
            return None
    
    def generate_response(self, query: str, selected_indexes: List[str], model_name: str, use_context: bool = True) -> Dict[str, Any]:
        try:
            from utils.unified_search_engine import UnifiedSearchEngine
            search_engine = UnifiedSearchEngine()
            
            if selected_indexes and self.vector_store:
                # Use RAG approach
                response_data = search_engine.query_with_llm(
                    query=query,
                    index_name=selected_indexes[0] if selected_indexes else None,
                    model_name=model_name,
                    top_k=3
                )
                return {
                    'response': response_data.get('llm_response', 'No response generated'),
                    'search_results': response_data.get('search_results', []),
                    'model_used': model_name,
                    'response_type': 'rag',
                    'sources_used': len(response_data.get('search_results', []))
                }
            else:
                # Direct LLM response
                return self._generate_direct_response(query, model_name)
                
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return {
                'response': f"I encountered an error processing your request: {str(e)}",
                'search_results': [],
                'model_used': model_name,
                'response_type': 'error',
                'sources_used': 0
            }
    
    def _generate_direct_response(self, query: str, model_name: str) -> Dict[str, Any]:
        try:
            from utils.llm_config import get_llm_model_config
            import os
            
            model_config = get_llm_model_config(model_name)
            if not model_config:
                raise Exception(f"Model configuration not found for {model_name}")
            
            provider = model_config.get('provider', 'openai')
            
            if provider == 'openai':
                client = self._create_openai_client()
                
                response = client.chat.completions.create(
                    model=model_config.get('model_id', model_name),
                    messages=[
                        {"role": "system", "content": "You are VaultMind AI Assistant, a helpful enterprise AI assistant."},
                        {"role": "user", "content": query}
                    ],
                    max_tokens=1000,
                    temperature=0.7
                )
                
                return {
                    'response': response.choices[0].message.content,
                    'search_results': [],
                    'model_used': model_name,
                    'response_type': 'direct_llm',
                    'sources_used': 0
                }
            else:
                return {
                    'response': f"Direct chat mode active. You asked: '{query}'\n\nI'm configured to use {provider} but the integration is still being set up. Please configure your API keys for full functionality.",
                    'search_results': [],
                    'model_used': model_name,
                    'response_type': 'fallback',
                    'sources_used': 0
                }
                
        except Exception as e:
            logger.error(f"Direct response failed: {e}")
            return {
                'response': f"I'm having trouble generating a response right now. Error: {str(e)}",
                'search_results': [],
                'model_used': model_name,
                'response_type': 'error',
                'sources_used': 0
            }

def render_chat_assistant(user, permissions, auth_middleware):
    """Modern Enterprise Chat Interface"""
    
    # Initialize chat assistant
    if "modern_chat_assistant" not in st.session_state:
        st.session_state.modern_chat_assistant = ModernChatAssistant()
    
    chat_assistant = st.session_state.modern_chat_assistant
    
    # Modern Chat CSS
    st.markdown("""
    <style>
    /* Reset Streamlit defaults */
    .main .block-container {
        padding: 0 !important;
        max-width: 100% !important;
    }
    
    /* Modern Chat Layout */
    .chat-container {
        display: flex;
        height: 100vh;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }
    
    /* Sidebar */
    .chat-sidebar {
        width: 300px;
        background: #f8f9fa;
        border-right: 1px solid #e9ecef;
        padding: 20px;
        overflow-y: auto;
    }
    
    /* Main Chat Area */
    .chat-main {
        flex: 1;
        display: flex;
        flex-direction: column;
        background: #ffffff;
    }
    
    /* Chat Header */
    .chat-header {
        padding: 16px 24px;
        border-bottom: 1px solid #e9ecef;
        background: #ffffff;
        display: flex;
        align-items: center;
        gap: 12px;
    }
    
    .chat-header-avatar {
        width: 36px;
        height: 36px;
        background: #0d6efd;
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-weight: 600;
        font-size: 14px;
    }
    
    .chat-header-info h3 {
        margin: 0;
        font-size: 16px;
        font-weight: 600;
        color: #212529;
    }
    
    .chat-header-info p {
        margin: 0;
        font-size: 13px;
        color: #6c757d;
    }
    
    /* Messages Area */
    .chat-messages {
        flex: 1;
        padding: 20px;
        overflow-y: auto;
        background: #ffffff;
    }
    
    /* Message Bubbles */
    .message {
        margin-bottom: 16px;
        display: flex;
        align-items: flex-start;
        gap: 12px;
    }
    
    .message.user {
        flex-direction: row-reverse;
    }
    
    .message-avatar {
        width: 32px;
        height: 32px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 600;
        font-size: 12px;
        flex-shrink: 0;
    }
    
    .message.assistant .message-avatar {
        background: #e3f2fd;
        color: #1976d2;
    }
    
    .message.user .message-avatar {
        background: #f3e5f5;
        color: #7b1fa2;
    }
    
    .message-content {
        max-width: 70%;
        background: #f8f9fa;
        padding: 12px 16px;
        border-radius: 18px;
        border: 1px solid #e9ecef;
    }
    
    .message.user .message-content {
        background: #0d6efd;
        color: white;
        border-color: #0d6efd;
    }
    
    .message-text {
        margin: 0;
        font-size: 14px;
        line-height: 1.4;
    }
    
    .message-meta {
        margin-top: 8px;
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
    }
    
    .message-badge {
        background: rgba(13, 110, 253, 0.1);
        color: #0d6efd;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 11px;
        font-weight: 500;
    }
    
    /* Chat Input */
    .chat-input-container {
        padding: 16px 20px;
        border-top: 1px solid #e9ecef;
        background: #ffffff;
    }
    
    .chat-input {
        width: 100%;
        border: 1px solid #ced4da;
        border-radius: 24px;
        padding: 12px 20px;
        font-size: 14px;
        outline: none;
        resize: none;
        font-family: inherit;
    }
    
    .chat-input:focus {
        border-color: #0d6efd;
        box-shadow: 0 0 0 3px rgba(13, 110, 253, 0.1);
    }
    
    /* Sidebar Sections */
    .sidebar-section {
        margin-bottom: 24px;
    }
    
    .sidebar-section h4 {
        margin: 0 0 12px 0;
        font-size: 14px;
        font-weight: 600;
        color: #495057;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .status-item {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 8px 0;
        font-size: 13px;
    }
    
    .status-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
    }
    
    .status-online { background: #28a745; }
    .status-offline { background: #dc3545; }
    .status-warning { background: #ffc107; }
    
    /* Typing Indicator */
    .typing-indicator {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 12px 16px;
        background: #f8f9fa;
        border-radius: 18px;
        margin-bottom: 16px;
        border: 1px solid #e9ecef;
    }
    
    .typing-dots {
        display: flex;
        gap: 4px;
    }
    
    .typing-dot {
        width: 6px;
        height: 6px;
        background: #6c757d;
        border-radius: 50%;
        animation: typing 1.4s infinite ease-in-out;
    }
    
    .typing-dot:nth-child(1) { animation-delay: -0.32s; }
    .typing-dot:nth-child(2) { animation-delay: -0.16s; }
    
    @keyframes typing {
        0%, 80%, 100% { transform: scale(0.8); opacity: 0.5; }
        40% { transform: scale(1.2); opacity: 1; }
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Get configuration
    available_models = get_available_llm_models()
    default_model = get_default_llm_model()
    available_indexes = chat_assistant.available_indexes
    
    # Main chat layout
    st.markdown("""
    <div class="chat-container">
        <div class="chat-sidebar">
            <div class="sidebar-section">
                <h4>Configuration</h4>
            </div>
        </div>
        <div class="chat-main">
            <div class="chat-header">
                <div class="chat-header-avatar">VM</div>
                <div class="chat-header-info">
                    <h3>VaultMind AI Assistant</h3>
                    <p>Enterprise Document Intelligence</p>
                </div>
            </div>
            <div class="chat-messages" id="chat-messages">
            </div>
            <div class="chat-input-container">
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar configuration
    with st.sidebar:
        st.markdown("### ⚙️ Configuration")
        
        # Model selection
        if available_models and available_models[0] != "No LLM models available - Please check API keys in .env file":
            selected_model = st.selectbox(
                "AI Model:",
                available_models,
                index=available_models.index(default_model) if default_model in available_models else 0
            )
        else:
            st.error("No AI models configured")
            selected_model = "No models available"
        
        # Document sources
        if available_indexes:
            st.success(f"✅ {len(available_indexes)} document collections")
            use_documents = st.checkbox("Enable document search", value=True)
            
            if use_documents:
                selected_indexes = st.multiselect(
                    "Document Collections:",
                    available_indexes,
                    default=available_indexes[:2] if len(available_indexes) >= 2 else available_indexes
                )
            else:
                selected_indexes = []
        else:
            st.warning("No document collections found")
            selected_indexes = []
            use_documents = False
        
        # Settings
        use_context = st.checkbox("Conversation memory", value=True)
        
        # Actions
        if st.button("🗑️ Clear Chat", use_container_width=True):
            if "chat_messages" in st.session_state:
                st.session_state.chat_messages = []
            chat_assistant.conversation_manager.clear_history()
            st.rerun()
    
    # Initialize chat messages
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []
        
        # Welcome message
        welcome_msg = f"""Hello! I'm your VaultMind AI Assistant.

**Current Setup:**
- Model: {selected_model}
- Document Collections: {len(selected_indexes)} active
- Mode: {'Document-enhanced responses' if selected_indexes else 'Direct AI chat'}

How can I help you today?"""
        
        st.session_state.chat_messages.append({
            "role": "assistant",
            "content": welcome_msg,
            "metadata": {"type": "welcome"}
        })
    
    # Display chat messages
    for message in st.session_state.chat_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            
            # Show metadata for assistant messages
            if message["role"] == "assistant" and "metadata" in message:
                metadata = message["metadata"]
                if metadata.get("type") != "welcome":
                    badges = []
                    if "model_used" in metadata:
                        badges.append(f"🤖 {metadata['model_used']}")
                    if "response_type" in metadata:
                        type_map = {
                            "rag": "📚 Enhanced",
                            "direct_llm": "💬 Direct",
                            "fallback": "🔍 Search"
                        }
                        badges.append(type_map.get(metadata["response_type"], metadata["response_type"]))
                    if "sources_used" in metadata and metadata["sources_used"] > 0:
                        badges.append(f"📄 {metadata['sources_used']} sources")
                    
                    if badges:
                        st.caption(" • ".join(badges))
    
    # Chat input
    if prompt := st.chat_input("Type your message..."):
        # Add user message
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Generate assistant response
        with st.chat_message("assistant"):
            if selected_model == "No models available":
                error_msg = "❌ Please configure AI models in the sidebar to start chatting."
                st.error(error_msg)
                st.session_state.chat_messages.append({
                    "role": "assistant",
                    "content": error_msg,
                    "metadata": {"type": "error"}
                })
            else:
                with st.spinner("Thinking..."):
                    try:
                        response_data = chat_assistant.generate_response(
                            prompt,
                            selected_indexes if use_documents else [],
                            selected_model,
                            use_context
                        )
                        
                        st.markdown(response_data["response"])
                        
                        # Add to chat history
                        st.session_state.chat_messages.append({
                            "role": "assistant",
                            "content": response_data["response"],
                            "metadata": {
                                "model_used": response_data["model_used"],
                                "response_type": response_data["response_type"],
                                "sources_used": response_data["sources_used"]
                            }
                        })
                        
                        # Show metadata
                        badges = [f"🤖 {response_data['model_used']}"]
                        type_map = {
                            "rag": "📚 Enhanced",
                            "direct_llm": "💬 Direct", 
                            "fallback": "🔍 Search"
                        }
                        badges.append(type_map.get(response_data["response_type"], response_data["response_type"]))
                        if response_data["sources_used"] > 0:
                            badges.append(f"📄 {response_data['sources_used']} sources")
                        
                        st.caption(" • ".join(badges))
                        
                    except Exception as e:
                        error_msg = f"❌ Error: {str(e)}"
                        st.error(error_msg)
                        st.session_state.chat_messages.append({
                            "role": "assistant",
                            "content": error_msg,
                            "metadata": {"type": "error"}
                        })

if __name__ == "__main__":
    # For testing
    class MockUser:
        def __init__(self):
            self.role = "admin"
    
    class MockAuth:
        def log_user_action(self, action, details=""):
            pass
    
    render_chat_assistant(MockUser(), {}, MockAuth())
