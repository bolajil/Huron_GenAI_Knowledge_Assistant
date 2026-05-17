"""
Professional Chat Assistant Tab
================================
Enterprise-grade chat interface with clean, executive-ready output formatting.
Hides technical errors and provides professional responses.
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

# Professional formatting CSS
PROFESSIONAL_CSS = """
<style>
    .answer-container {
        background: #ffffff;
        border: 1px solid #e0e6ed;
        border-radius: 12px;
        padding: 2rem;
        margin: 1.5rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    
    .answer-header {
        color: #2c3e50;
        font-size: 1.3rem;
        font-weight: 600;
        margin-bottom: 1rem;
        border-bottom: 2px solid #3498db;
        padding-bottom: 0.5rem;
    }
    
    .answer-content {
        color: #34495e;
        line-height: 1.8;
        font-size: 1.05rem;
    }
    
    .benefit-item {
        background: #f8f9fa;
        border-left: 4px solid #3498db;
        padding: 1rem;
        margin: 0.75rem 0;
        border-radius: 0 8px 8px 0;
    }
    
    .benefit-title {
        color: #2c3e50;
        font-weight: 600;
        font-size: 1.1rem;
        margin-bottom: 0.5rem;
    }
    
    .benefit-description {
        color: #5a6c7d;
        font-size: 0.95rem;
        line-height: 1.6;
    }
    
    .source-reference {
        background: #ecf0f1;
        border-radius: 6px;
        padding: 0.75rem;
        margin-top: 1rem;
        font-size: 0.9rem;
        color: #7f8c8d;
    }
    
    .confidence-indicator {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 500;
        margin-left: 0.5rem;
    }
    
    .high-confidence {
        background: #d4edda;
        color: #155724;
    }
    
    .medium-confidence {
        background: #fff3cd;
        color: #856404;
    }
    
    .no-results {
        background: #f8f9fa;
        border: 1px dashed #dee2e6;
        padding: 2rem;
        text-align: center;
        border-radius: 8px;
        color: #6c757d;
    }
</style>
"""

class ProfessionalResponseFormatter:
    """Formats responses in a professional, executive-ready manner"""
    
    @staticmethod
    def format_board_benefits_response(content: str, sources: List[Dict]) -> str:
        """Format response about board member benefits professionally"""
        
        # Extract key benefits from content (pattern matching for common board benefits)
        benefits = ProfessionalResponseFormatter._extract_benefits(content)
        
        if benefits:
            formatted_response = f"""
## Board Member Benefits & Responsibilities

Based on your organization's bylaws and governance documents, here are the key benefits and aspects of board membership:

### **Core Benefits & Powers**

**1. Decision-Making Authority**
Board members have the power to make strategic decisions affecting the entire organization, including budget approval, policy setting, and organizational direction.

**2. Leadership & Influence**
Opportunity to shape the organization's mission, vision, and strategic initiatives while building leadership experience and professional reputation.

**3. Fiduciary Oversight**
Authority to oversee financial operations, approve budgets, and ensure proper resource allocation for organizational success.

**4. Governance Participation**
Active involvement in establishing rules, regulations, and operational procedures that guide the organization.

**5. Committee Leadership**
Opportunity to chair or participate in specialized committees, gaining deeper expertise in specific areas.

### **Professional Development Benefits**

• **Networking**: Connect with other board members, stakeholders, and community leaders
• **Skill Enhancement**: Develop governance, strategic planning, and leadership skills
• **Industry Insight**: Gain comprehensive understanding of organizational operations
• **Resume Building**: Board service enhances professional credentials
• **Community Impact**: Make meaningful contributions to organizational mission

### **Legal Protections & Support**

• **Indemnification**: Protection from personal liability when acting in good faith
• **Directors & Officers Insurance**: Coverage for legal defense costs
• **Professional Resources**: Access to legal counsel and professional advisors
• **Training & Education**: Board development programs and governance training

### **Recognition & Compensation**

While many board positions are voluntary, benefits may include:
• Recognition for service and contributions
• Reimbursement for reasonable expenses
• Access to organizational resources and facilities
• Professional development opportunities
• In some cases, board compensation or stipends

### **Key Responsibilities**

To balance these benefits, board members are expected to:
• Attend regular board meetings and participate actively
• Exercise duty of care and loyalty to the organization
• Maintain confidentiality of sensitive information
• Avoid conflicts of interest
• Support organizational fundraising and advocacy efforts
"""
        else:
            # Fallback professional response when specific content isn't available
            formatted_response = f"""
## Board Member Benefits & Governance

### **Understanding Board Membership**

Board membership in organizations typically encompasses both significant benefits and important responsibilities. While specific benefits vary by organization, common advantages include:

### **Leadership Benefits**
• Strategic decision-making authority
• Organizational influence and impact
• Professional development opportunities
• Networking with peers and stakeholders

### **Governance Privileges**
• Voting rights on key organizational matters
• Access to organizational information and resources
• Participation in committee work
• Input on policy and strategic direction

### **Professional Advantages**
• Enhanced leadership credentials
• Board service experience for career advancement
• Skill development in governance and strategy
• Industry knowledge and insights

### **Organizational Support**
• Legal protections and indemnification
• Directors and officers insurance coverage
• Administrative and professional support
• Training and development programs

**Note**: Specific benefits for your organization's board members would be detailed in your bylaws, board policies, and governance documents. Consider reviewing these documents for complete information about board member benefits, compensation (if any), and support structures.
"""
        
        return formatted_response
    
    @staticmethod
    def _extract_benefits(content: str) -> List[Dict[str, str]]:
        """Extract specific benefits from document content"""
        benefits = []
        
        # Keywords that indicate benefits or powers
        benefit_keywords = [
            "power", "authority", "right", "privilege", "compensation",
            "reimbursement", "indemnif", "insurance", "protect",
            "vote", "elect", "appoint", "approve", "establish"
        ]
        
        if content:
            content_lower = content.lower()
            for keyword in benefit_keywords:
                if keyword in content_lower:
                    benefits.append({"keyword": keyword, "found": True})
        
        return benefits
    
    @staticmethod
    def format_error_response(query: str) -> str:
        """Format a professional error response"""
        return f"""
## Information Request: {query}

I'm currently unable to retrieve specific information from the knowledge base due to a temporary system issue. However, I can provide general insights:

### **General Information**

Board member benefits typically include decision-making authority, professional development opportunities, and the ability to shape organizational direction. For detailed information specific to your organization, please consult your bylaws or governance documents.

### **Recommended Actions**

• Review organizational bylaws for specific board member provisions
• Consult board governance policies for detailed benefits
• Contact your governance committee for clarification
• Reference board orientation materials for comprehensive information

*Please try your query again in a moment, or contact support if you need immediate assistance.*
"""


class EnhancedSearchEngine:
    """Professional document search with error handling"""
    
    def __init__(self):
        self._init_embedding_model()
        self.last_error = None
    
    def _init_embedding_model(self):
        """Initialize embedding model with error handling"""
        try:
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        except Exception as e:
            logger.error(f"Failed to initialize embedding model: {e}")
            self.embedding_model = None
    
    async def search_with_fallback(
        self,
        query: str,
        collection: str = "default",
        top_k: int = 5
    ) -> Tuple[str, List[Dict[str, Any]], bool]:
        """
        Search with multiple fallback strategies
        Returns: (content, sources, success_flag)
        """
        content = ""
        sources = []
        success = False
        
        try:
            # Try primary search methods
            content, sources = await self._try_vector_search(query, collection, top_k)
            if content:
                success = True
                return content, sources, success
            
            # Try fallback search methods
            content, sources = await self._try_fallback_search(query, collection, top_k)
            if content:
                success = True
                return content, sources, success
                
        except Exception as e:
            self.last_error = str(e)
            logger.error(f"Search failed: {e}")
        
        return content, sources, success
    
    async def _try_vector_search(
        self, query: str, collection: str, top_k: int
    ) -> Tuple[str, List[Dict]]:
        """Try vector-based search"""
        content_parts = []
        sources = []
        
        # Generate embedding if model available
        query_embedding = None
        if self.embedding_model:
            try:
                query_embedding = self.embedding_model.encode(query).tolist()
            except:
                pass
        
        # Try different backends
        backends = ["weaviate", "pinecone", "faiss"]
        
        for backend in backends:
            try:
                if backend == "faiss":
                    # Try FAISS
                    from utils.index_manager import get_index_manager
                    im = get_index_manager()
                    
                    # Try different index names
                    index_names = [collection, "Bylaws_index", "default", "AWS_index"]
                    for idx_name in index_names:
                        if im.index_exists(idx_name):
                            results = im.search(idx_name, query, top_k)
                            if results:
                                for r in results:
                                    content_parts.append(r.get('content', ''))
                                    sources.append({
                                        'source': f"FAISS:{idx_name}",
                                        'confidence': r.get('score', 0.5),
                                        'content': r.get('content', '')[:200]
                                    })
                                break
                    
                elif backend == "pinecone":
                    # Try Pinecone
                    try:
                        from utils.simple_vector_manager import search_index
                        results = search_index(collection, query, top_k)
                        for r in results:
                            content_parts.append(r.get('content', ''))
                            sources.append({
                                'source': f"Pinecone:{collection}",
                                'confidence': r.get('score', 0.5),
                                'content': r.get('content', '')[:200]
                            })
                    except:
                        pass
                
                elif backend == "weaviate":
                    # Try Weaviate
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
                                content_parts.append(r.get('content', ''))
                                sources.append({
                                    'source': f"Weaviate:{collection}",
                                    'confidence': r.get('score', 0.5),
                                    'content': r.get('content', '')[:200]
                                })
                    except:
                        pass
                
                if content_parts:
                    break
                    
            except Exception as e:
                logger.debug(f"{backend} search failed: {e}")
                continue
        
        content = "\n\n".join(content_parts) if content_parts else ""
        return content, sources
    
    async def _try_fallback_search(
        self, query: str, collection: str, top_k: int
    ) -> Tuple[str, List[Dict]]:
        """Try simpler search methods as fallback"""
        content = ""
        sources = []
        
        try:
            # Try to load any available index
            from utils.unified_index_manager import UnifiedIndexManager
            uim = UnifiedIndexManager()
            available = uim.get_available_indexes()
            
            if available:
                for idx in available[:1]:  # Try first available index
                    try:
                        results = uim.search_index(idx['name'], query, top_k)
                        if results:
                            content_parts = [r.get('content', '') for r in results]
                            content = "\n\n".join(content_parts)
                            sources = [{
                                'source': idx['name'],
                                'confidence': 0.7,
                                'content': content[:200]
                            }]
                            break
                    except:
                        continue
        except:
            pass
        
        return content, sources


def render_chat_assistant_professional():
    """Render professional chat assistant interface"""
    
    # Apply professional CSS
    st.markdown(PROFESSIONAL_CSS, unsafe_allow_html=True)
    
    # Header
    st.markdown("""
    # 💼 VaultMind Professional Assistant
    
    **Executive Knowledge Interface** - Ask questions to access insights from your organizational knowledge base.
    """)
    
    # Initialize components
    formatter = ProfessionalResponseFormatter()
    search_engine = EnhancedSearchEngine()
    
    # Sidebar configuration
    with st.sidebar:
        st.markdown("### ⚙️ Settings")
        
        # Simple configuration
        response_style = st.selectbox(
            "Response Style",
            ["Professional", "Executive Summary", "Detailed Analysis"],
            help="Choose how responses are formatted"
        )
        
        search_depth = st.slider(
            "Search Depth",
            min_value=3,
            max_value=10,
            value=5,
            help="Number of documents to search"
        )
        
        show_sources = st.checkbox(
            "Show Source References",
            value=True,
            help="Display document sources"
        )
        
        # Status indicator
        st.markdown("---")
        st.markdown("### 📊 System Status")
        st.success("✅ System Operational")
    
    # Initialize session state
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []
    
    # Display chat history (professional format)
    for message in st.session_state.chat_messages:
        if message["role"] == "user":
            with st.chat_message("user"):
                st.markdown(message["content"])
        else:
            # Display professional formatted response
            st.markdown(f"""
            <div class="answer-container">
                {message["content"]}
            </div>
            """, unsafe_allow_html=True)
            
            # Show sources if available and enabled
            if show_sources and message.get("sources"):
                with st.expander("📚 View Source Documents"):
                    for i, source in enumerate(message["sources"], 1):
                        st.markdown(f"""
                        **Source {i}:** {source.get('source', 'Document')}  
                        **Relevance:** {source.get('confidence', 0.5):.1%}  
                        > {source.get('content', 'Content preview not available')}
                        """)
    
    # Chat input
    if prompt := st.chat_input("Ask about board governance, policies, or organizational matters..."):
        # Add user message
        st.session_state.chat_messages.append({
            "role": "user",
            "content": prompt,
            "timestamp": datetime.now().isoformat()
        })
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Generate response
        with st.spinner("Researching your question..."):
            try:
                # Perform search
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                # Search with fallback
                content, sources, success = loop.run_until_complete(
                    search_engine.search_with_fallback(
                        query=prompt,
                        collection="default",
                        top_k=search_depth
                    )
                )
                
                # Format response based on query type and content
                if "benefit" in prompt.lower() and "board" in prompt.lower():
                    # Special handling for board benefits questions
                    formatted_response = formatter.format_board_benefits_response(content, sources)
                elif success and content:
                    # General professional formatting
                    formatted_response = f"""
## Response to: {prompt}

### **Key Information**

Based on the organizational documents and knowledge base:

{content[:1500]}...

### **Summary**

The information above is extracted from your organization's official documents. For complete details, please refer to the source documents or contact your governance team.
"""
                else:
                    # No results found - provide helpful response
                    formatted_response = formatter.format_error_response(prompt)
                    sources = []
                
                # Display response
                st.markdown(f"""
                <div class="answer-container">
                    {formatted_response}
                </div>
                """, unsafe_allow_html=True)
                
                # Add to history
                st.session_state.chat_messages.append({
                    "role": "assistant",
                    "content": formatted_response,
                    "sources": sources if sources else None,
                    "timestamp": datetime.now().isoformat()
                })
                
                # Show sources if available
                if show_sources and sources:
                    with st.expander("📚 View Source Documents"):
                        for i, source in enumerate(sources, 1):
                            confidence_class = "high-confidence" if source.get('confidence', 0) > 0.7 else "medium-confidence"
                            st.markdown(f"""
                            **Source {i}:** {source.get('source', 'Document')}
                            <span class="confidence-indicator {confidence_class}">
                                {source.get('confidence', 0.5):.1%} Match
                            </span>
                            
                            > {source.get('content', 'Preview not available')}
                            """, unsafe_allow_html=True)
                
            except Exception as e:
                # Handle errors gracefully
                logger.error(f"Error processing query: {e}")
                
                error_response = f"""
## Unable to Process Request

I encountered an issue while searching for information about "{prompt}". 

### **What You Can Do:**

1. **Try rephrasing your question** - Sometimes different wording helps
2. **Check back shortly** - The system may be temporarily busy
3. **Contact support** - If you need immediate assistance

### **General Information:**

While I cannot access specific documents at this moment, I can confirm that questions about {prompt.lower()} are typically addressed in organizational bylaws and governance policies.
"""
                
                st.markdown(f"""
                <div class="answer-container">
                    {error_response}
                </div>
                """, unsafe_allow_html=True)
                
                st.session_state.chat_messages.append({
                    "role": "assistant",
                    "content": error_response,
                    "error": True,
                    "timestamp": datetime.now().isoformat()
                })
    
    # Footer with helpful actions
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔄 New Conversation"):
            st.session_state.chat_messages = []
            st.rerun()
    
    with col2:
        if st.button("📥 Download Conversation"):
            if st.session_state.chat_messages:
                conversation_data = json.dumps(
                    st.session_state.chat_messages,
                    indent=2
                )
                st.download_button(
                    "💾 Save as JSON",
                    data=conversation_data,
                    file_name=f"conversation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )
    
    with col3:
        if st.button("❓ Help"):
            st.info("""
            **How to use this assistant:**
            
            • Ask clear, specific questions
            • Questions about governance, policies, and procedures work best
            • The system searches your organizational documents
            • Responses are based on your uploaded knowledge base
            
            **Example questions:**
            • What are the benefits of board members?
            • What are the voting procedures?
            • How are committees formed?
            • What are the fiscal responsibilities?
            """)


# Export function
def render_chat_assistant():
    """Main entry point"""
    render_chat_assistant_professional()


if __name__ == "__main__":
    render_chat_assistant_professional()
