"""
Agentic RAG Orchestrator

LangGraph-based pipeline for multi-tenant RAG with:
1. Query ingestion + dept_id extraction
2. Intent classification
3. Namespace-locked retrieval
4. Cross-encoder reranking
5. Hierarchical context assembly
6. LLM generation with guardrails
7. Faithfulness validation

Usage:
    from utils.rag_orchestrator import RAGOrchestrator
    from utils.tenant_context import TenantContext
    
    orchestrator = RAGOrchestrator()
    ctx = TenantContext(tenant_id="huron", dept_id="legal")
    
    response = await orchestrator.query(
        query="What are the vacation policies?",
        tenant_context=ctx
    )
"""

import os
import logging
import asyncio
from typing import Dict, Any, Optional, List, Literal, TypedDict, Annotated
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)

# LangGraph imports
try:
    from langgraph.graph import StateGraph, END
    from langgraph.checkpoint.memory import MemorySaver
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    logger.warning("LangGraph not available. Install with: pip install langgraph")

# Import tenant context
try:
    from utils.tenant_context import TenantContext, require_context
except ImportError:
    TenantContext = None
    require_context = None

# Import department manager
try:
    from utils.department_manager import get_department_manager, AttentionProfile
except ImportError:
    get_department_manager = None
    AttentionProfile = None

# Import existing components
try:
    from utils.query_intent_classifier import QueryIntentClassifier
    INTENT_CLASSIFIER_AVAILABLE = True
except ImportError:
    INTENT_CLASSIFIER_AVAILABLE = False

try:
    from utils.advanced_reranker import AdvancedReranker
    RERANKER_AVAILABLE = True
except ImportError:
    RERANKER_AVAILABLE = False

try:
    from utils.adapters.pinecone_adapter import PineconeAdapter
    PINECONE_AVAILABLE = True
except ImportError:
    PINECONE_AVAILABLE = False


class QueryIntent(Enum):
    """Query intent types"""
    FACTUAL = "factual"           # Direct fact lookup
    ANALYTICAL = "analytical"      # Analysis/comparison
    PROCEDURAL = "procedural"      # How-to questions
    EXPLORATORY = "exploratory"    # Open-ended exploration
    CONVERSATIONAL = "conversational"  # Casual chat


class RetrievalStrategy(Enum):
    """Retrieval strategies based on intent"""
    PRECISE = "precise"       # High precision, few results
    BROAD = "broad"           # Lower precision, more results
    HYBRID = "hybrid"         # Vector + keyword
    MULTI_QUERY = "multi_query"  # Multiple query variations


@dataclass
class RAGState:
    """State object passed through the LangGraph pipeline"""
    
    # Input
    query: str
    tenant_context: Optional[Any] = None
    
    # Extracted info
    tenant_id: str = "huron"
    dept_id: Optional[str] = None
    namespace: Optional[str] = None
    
    # Intent classification
    intent: QueryIntent = QueryIntent.FACTUAL
    intent_confidence: float = 0.0
    retrieval_strategy: RetrievalStrategy = RetrievalStrategy.HYBRID
    
    # Retrieval
    retrieved_chunks: List[Dict[str, Any]] = field(default_factory=list)
    parent_chunks: List[Dict[str, Any]] = field(default_factory=list)
    retrieval_score: float = 0.0
    
    # Reranking
    reranked_chunks: List[Dict[str, Any]] = field(default_factory=list)
    rerank_scores: List[float] = field(default_factory=list)
    
    # Context assembly
    context: str = ""
    context_tokens: int = 0
    sources: List[str] = field(default_factory=list)
    
    # Generation
    response: str = ""
    model_used: str = ""
    
    # Validation
    faithfulness_score: float = 0.0
    hallucination_flags: List[str] = field(default_factory=list)
    
    # Metadata
    processing_time_ms: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "tenant_id": self.tenant_id,
            "dept_id": self.dept_id,
            "namespace": self.namespace,
            "intent": self.intent.value,
            "intent_confidence": self.intent_confidence,
            "response": self.response,
            "sources": self.sources,
            "faithfulness_score": self.faithfulness_score,
            "processing_time_ms": self.processing_time_ms,
            "errors": self.errors,
            "warnings": self.warnings,
        }


# LangGraph state type
class GraphState(TypedDict):
    """TypedDict for LangGraph state"""
    query: str
    tenant_id: str
    dept_id: str
    namespace: str
    intent: str
    intent_confidence: float
    retrieval_strategy: str
    retrieved_chunks: List[Dict]
    parent_chunks: List[Dict]
    reranked_chunks: List[Dict]
    context: str
    context_tokens: int
    sources: List[str]
    response: str
    model_used: str
    faithfulness_score: float
    hallucination_flags: List[str]
    errors: List[str]
    warnings: List[str]


class RAGOrchestrator:
    """
    Agentic RAG Orchestrator using LangGraph.
    """
    
    def __init__(
        self,
        pinecone_index: str = "huron-enterprise-knowledge",
        embedding_model: str = "all-MiniLM-L6-v2",
        llm_model: str = "gpt-4o-mini",
        max_context_tokens: int = 4096,
        enable_reranking: bool = True,
        enable_validation: bool = True,
    ):
        """
        Initialize RAG orchestrator.
        
        Args:
            pinecone_index: Pinecone index name
            embedding_model: Embedding model for retrieval
            llm_model: LLM model for generation
            max_context_tokens: Maximum context window
            enable_reranking: Enable cross-encoder reranking
            enable_validation: Enable faithfulness validation
        """
        self.pinecone_index = pinecone_index
        self.embedding_model = embedding_model
        self.llm_model = llm_model
        self.max_context_tokens = max_context_tokens
        self.enable_reranking = enable_reranking and RERANKER_AVAILABLE
        self.enable_validation = enable_validation
        
        # Initialize components
        self._init_components()
        
        # Build LangGraph pipeline
        self.graph = self._build_graph() if LANGGRAPH_AVAILABLE else None
    
    def _init_components(self):
        """Initialize pipeline components"""
        
        # Intent classifier
        self.intent_classifier = None
        if INTENT_CLASSIFIER_AVAILABLE:
            try:
                self.intent_classifier = QueryIntentClassifier()
            except Exception as e:
                logger.warning(f"Failed to init intent classifier: {e}")
        
        # Reranker
        self.reranker = None
        if self.enable_reranking:
            try:
                self.reranker = AdvancedReranker()
            except Exception as e:
                logger.warning(f"Failed to init reranker: {e}")
        
        # Pinecone adapter
        self.pinecone = None
        if PINECONE_AVAILABLE:
            try:
                self.pinecone = PineconeAdapter()
            except Exception as e:
                logger.warning(f"Failed to init Pinecone: {e}")
        
        # Department manager
        self.dept_manager = None
        if get_department_manager:
            try:
                self.dept_manager = get_department_manager()
            except Exception as e:
                logger.warning(f"Failed to init department manager: {e}")
        
        # Embedder
        self.embedder = None
        try:
            from sentence_transformers import SentenceTransformer
            self.embedder = SentenceTransformer(self.embedding_model)
        except Exception as e:
            logger.warning(f"Failed to init embedder: {e}")
        
        # LLM client
        self.llm_client = None
        try:
            import openai
            self.llm_client = openai.OpenAI()
        except Exception as e:
            logger.warning(f"Failed to init LLM client: {e}")
    
    def _build_graph(self) -> Optional[StateGraph]:
        """Build LangGraph pipeline"""
        if not LANGGRAPH_AVAILABLE:
            return None
        
        # Create graph
        workflow = StateGraph(GraphState)
        
        # Add nodes
        workflow.add_node("extract_context", self._node_extract_context)
        workflow.add_node("classify_intent", self._node_classify_intent)
        workflow.add_node("retrieve", self._node_retrieve)
        workflow.add_node("rerank", self._node_rerank)
        workflow.add_node("assemble_context", self._node_assemble_context)
        workflow.add_node("generate", self._node_generate)
        workflow.add_node("validate", self._node_validate)
        
        # Add edges
        workflow.set_entry_point("extract_context")
        workflow.add_edge("extract_context", "classify_intent")
        workflow.add_edge("classify_intent", "retrieve")
        workflow.add_edge("retrieve", "rerank")
        workflow.add_edge("rerank", "assemble_context")
        workflow.add_edge("assemble_context", "generate")
        workflow.add_edge("generate", "validate")
        workflow.add_edge("validate", END)
        
        # Compile
        return workflow.compile()
    
    # ==================== PIPELINE NODES ====================
    
    def _node_extract_context(self, state: GraphState) -> GraphState:
        """Node 1: Extract tenant context from state"""
        # Context should already be set, just validate
        if not state.get("dept_id"):
            state["warnings"] = state.get("warnings", []) + [
                "No dept_id provided - using default namespace"
            ]
        
        # Generate namespace
        if state.get("dept_id"):
            import re
            tenant = state.get("tenant_id", "huron")
            dept = state["dept_id"]
            namespace = f"vaultmind-{tenant}-{dept}-general"
            state["namespace"] = re.sub(r"[^a-z0-9-]", "-", namespace.lower())[:45]
        
        return state
    
    def _node_classify_intent(self, state: GraphState) -> GraphState:
        """Node 2: Classify query intent"""
        query = state["query"]
        
        if self.intent_classifier:
            try:
                result = self.intent_classifier.classify(query)
                state["intent"] = result.get("intent", "factual")
                state["intent_confidence"] = result.get("confidence", 0.5)
            except Exception as e:
                logger.warning(f"Intent classification failed: {e}")
                state["intent"] = "factual"
                state["intent_confidence"] = 0.5
        else:
            # Simple heuristic classification
            state["intent"] = self._heuristic_intent(query)
            state["intent_confidence"] = 0.7
        
        # Determine retrieval strategy based on intent
        state["retrieval_strategy"] = self._intent_to_strategy(state["intent"])
        
        return state
    
    def _node_retrieve(self, state: GraphState) -> GraphState:
        """Node 3: Retrieve chunks from vector store"""
        query = state["query"]
        namespace = state.get("namespace")
        
        if not self.pinecone or not self.embedder:
            state["errors"] = state.get("errors", []) + ["Vector store not available"]
            return state
        
        try:
            # Generate query embedding
            query_embedding = self.embedder.encode(query).tolist()
            
            # Determine top_k based on strategy
            strategy = state.get("retrieval_strategy", "hybrid")
            top_k = {
                "precise": 5,
                "broad": 15,
                "hybrid": 10,
                "multi_query": 20,
            }.get(strategy, 10)
            
            # Search with namespace isolation
            results = self.pinecone.search(
                collection_name=self.pinecone_index,
                query_embedding=query_embedding,
                top_k=top_k,
                tenant_id=state.get("tenant_id", "huron"),
                dept_id=state.get("dept_id"),
                namespace=namespace,
            )
            
            # Convert results to chunks
            chunks = []
            for r in results:
                chunks.append({
                    "id": r.id,
                    "content": r.metadata.get("content", ""),
                    "score": r.score,
                    "source": r.metadata.get("source", ""),
                    "chunk_type": r.metadata.get("chunk_type", "unknown"),
                    "parent_id": r.metadata.get("parent_id"),
                    "metadata": r.metadata,
                })
            
            state["retrieved_chunks"] = chunks
            
            # Fetch parent chunks if available
            parent_ids = set(c.get("parent_id") for c in chunks if c.get("parent_id"))
            if parent_ids:
                # Fetch parent chunks for context expansion
                # This would query Pinecone for parent_id matches
                state["parent_chunks"] = []  # Placeholder
            
        except Exception as e:
            logger.error(f"Retrieval failed: {e}")
            state["errors"] = state.get("errors", []) + [f"Retrieval error: {str(e)}"]
        
        return state
    
    def _node_rerank(self, state: GraphState) -> GraphState:
        """Node 4: Cross-encoder reranking"""
        chunks = state.get("retrieved_chunks", [])
        query = state["query"]
        
        if not chunks:
            return state
        
        if self.reranker:
            try:
                # Rerank using cross-encoder
                reranked = self.reranker.rerank(
                    query=query,
                    documents=[c["content"] for c in chunks],
                    top_k=min(len(chunks), 5),
                )
                
                # Apply attention profile boost if available
                dept_id = state.get("dept_id")
                if self.dept_manager and dept_id:
                    profile = self.dept_manager.get_attention_profile(dept_id)
                    if profile:
                        for item in reranked:
                            item["score"] *= profile.rerank_boost
                
                # Reorder chunks by reranked scores
                reranked_chunks = []
                for item in reranked:
                    idx = item.get("index", 0)
                    if idx < len(chunks):
                        chunk = chunks[idx].copy()
                        chunk["rerank_score"] = item.get("score", 0)
                        reranked_chunks.append(chunk)
                
                state["reranked_chunks"] = reranked_chunks
                
            except Exception as e:
                logger.warning(f"Reranking failed: {e}")
                state["reranked_chunks"] = chunks[:5]
        else:
            # Use original scores
            state["reranked_chunks"] = sorted(
                chunks, 
                key=lambda x: x.get("score", 0), 
                reverse=True
            )[:5]
        
        return state
    
    def _node_assemble_context(self, state: GraphState) -> GraphState:
        """Node 5: Assemble context from reranked chunks"""
        chunks = state.get("reranked_chunks", [])
        parent_chunks = state.get("parent_chunks", [])
        
        if not chunks:
            state["context"] = ""
            state["sources"] = []
            return state
        
        # Build context string
        context_parts = []
        sources = set()
        total_tokens = 0
        
        # Get attention profile for context window
        max_tokens = self.max_context_tokens
        dept_id = state.get("dept_id")
        if self.dept_manager and dept_id:
            profile = self.dept_manager.get_attention_profile(dept_id)
            if profile:
                max_tokens = profile.context_window
        
        for chunk in chunks:
            content = chunk.get("content", "")
            source = chunk.get("source", "Unknown")
            
            # Estimate tokens (rough: 4 chars per token)
            chunk_tokens = len(content) // 4
            
            if total_tokens + chunk_tokens > max_tokens:
                break
            
            context_parts.append(f"[Source: {source}]\n{content}")
            sources.add(source)
            total_tokens += chunk_tokens
        
        state["context"] = "\n\n---\n\n".join(context_parts)
        state["context_tokens"] = total_tokens
        state["sources"] = list(sources)
        
        return state
    
    def _node_generate(self, state: GraphState) -> GraphState:
        """Node 6: Generate response with LLM"""
        query = state["query"]
        context = state.get("context", "")
        dept_id = state.get("dept_id", "general")
        
        if not context:
            state["response"] = "I couldn't find relevant information to answer your question."
            state["warnings"] = state.get("warnings", []) + ["No context available"]
            return state
        
        if not self.llm_client:
            state["response"] = "LLM service not available."
            state["errors"] = state.get("errors", []) + ["LLM not configured"]
            return state
        
        try:
            # Build system prompt with department context
            system_prompt = self._get_system_prompt(dept_id)
            
            # Build user prompt
            user_prompt = f"""Based on the following context, answer the user's question.

Context:
{context}

Question: {query}

Instructions:
- Answer based ONLY on the provided context
- If the context doesn't contain the answer, say so
- Cite sources when possible
- Be concise and professional
"""
            
            # Call LLM
            response = self.llm_client.chat.completions.create(
                model=self.llm_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
                max_tokens=1000,
            )
            
            state["response"] = response.choices[0].message.content
            state["model_used"] = self.llm_model
            
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            state["response"] = "I encountered an error generating the response."
            state["errors"] = state.get("errors", []) + [f"Generation error: {str(e)}"]
        
        return state
    
    def _node_validate(self, state: GraphState) -> GraphState:
        """Node 7: Validate response faithfulness"""
        if not self.enable_validation:
            state["faithfulness_score"] = 1.0
            return state
        
        response = state.get("response", "")
        context = state.get("context", "")
        
        if not response or not context:
            state["faithfulness_score"] = 0.0
            return state
        
        try:
            # Simple faithfulness check: verify key claims appear in context
            # In production, use RAGAS or similar
            score = self._simple_faithfulness_check(response, context)
            state["faithfulness_score"] = score
            
            if score < 0.5:
                state["hallucination_flags"] = state.get("hallucination_flags", []) + [
                    "Low faithfulness score - response may contain hallucinations"
                ]
            
        except Exception as e:
            logger.warning(f"Validation failed: {e}")
            state["faithfulness_score"] = 0.5
        
        return state
    
    # ==================== HELPER METHODS ====================
    
    def _heuristic_intent(self, query: str) -> str:
        """Simple heuristic intent classification"""
        query_lower = query.lower()
        
        if any(w in query_lower for w in ["how to", "how do", "steps", "process", "procedure"]):
            return "procedural"
        elif any(w in query_lower for w in ["compare", "difference", "versus", "vs", "analysis"]):
            return "analytical"
        elif any(w in query_lower for w in ["what is", "who is", "when", "where", "define"]):
            return "factual"
        elif any(w in query_lower for w in ["tell me about", "explain", "describe"]):
            return "exploratory"
        else:
            return "factual"
    
    def _intent_to_strategy(self, intent: str) -> str:
        """Map intent to retrieval strategy"""
        return {
            "factual": "precise",
            "analytical": "broad",
            "procedural": "hybrid",
            "exploratory": "broad",
            "conversational": "precise",
        }.get(intent, "hybrid")
    
    def _get_system_prompt(self, dept_id: str) -> str:
        """Get department-specific system prompt"""
        dept_prompts = {
            "legal": "You are a legal assistant for Huron Consulting. Provide accurate legal information based on company policies and documents. Always recommend consulting with legal counsel for specific situations.",
            "hr": "You are an HR assistant for Huron Consulting. Help employees understand HR policies, benefits, and procedures. Maintain confidentiality and direct sensitive matters to HR representatives.",
            "finance": "You are a finance assistant for Huron Consulting. Provide information about financial policies, expense procedures, and budgeting guidelines. Ensure accuracy in all financial information.",
            "clinical": "You are a healthcare consulting assistant. Ensure all responses comply with HIPAA. Never disclose PHI. Focus on operational and policy information.",
            "operations": "You are an operations assistant for Huron Consulting. Help with operational procedures, workflows, and process documentation.",
            "it": "You are an IT support assistant for Huron Consulting. Help with technical questions, IT policies, and system procedures.",
        }
        
        base_prompt = dept_prompts.get(dept_id, 
            "You are a helpful assistant for Huron Consulting. Provide accurate information based on company documents."
        )
        
        return f"{base_prompt}\n\nAlways base your answers on the provided context. If unsure, say so."
    
    def _simple_faithfulness_check(self, response: str, context: str) -> float:
        """Simple faithfulness scoring"""
        # Extract key phrases from response
        response_words = set(response.lower().split())
        context_words = set(context.lower().split())
        
        # Calculate overlap
        overlap = len(response_words & context_words)
        total = len(response_words)
        
        if total == 0:
            return 0.0
        
        return min(1.0, overlap / (total * 0.3))
    
    # ==================== PUBLIC API ====================
    
    async def query(
        self,
        query: str,
        tenant_context: Optional[Any] = None,
        tenant_id: str = "huron",
        dept_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute RAG query through the pipeline.
        
        Args:
            query: User query
            tenant_context: TenantContext object
            tenant_id: Tenant ID (if no context)
            dept_id: Department ID (if no context)
        
        Returns:
            Response dictionary with answer and metadata
        """
        import time
        start_time = time.time()
        
        # Extract from context if provided
        if tenant_context:
            tenant_id = getattr(tenant_context, "tenant_id", tenant_id)
            dept_id = getattr(tenant_context, "dept_id", dept_id)
        
        # Validate dept_id
        if not dept_id:
            return {
                "success": False,
                "error": "dept_id is required for namespace isolation",
                "response": "",
            }
        
        # Initialize state
        state: GraphState = {
            "query": query,
            "tenant_id": tenant_id,
            "dept_id": dept_id,
            "namespace": "",
            "intent": "factual",
            "intent_confidence": 0.0,
            "retrieval_strategy": "hybrid",
            "retrieved_chunks": [],
            "parent_chunks": [],
            "reranked_chunks": [],
            "context": "",
            "context_tokens": 0,
            "sources": [],
            "response": "",
            "model_used": "",
            "faithfulness_score": 0.0,
            "hallucination_flags": [],
            "errors": [],
            "warnings": [],
        }
        
        # Execute pipeline
        if self.graph:
            try:
                final_state = self.graph.invoke(state)
                state = final_state
            except Exception as e:
                logger.error(f"Pipeline error: {e}")
                state["errors"].append(str(e))
        else:
            # Fallback: run nodes sequentially
            state = self._node_extract_context(state)
            state = self._node_classify_intent(state)
            state = self._node_retrieve(state)
            state = self._node_rerank(state)
            state = self._node_assemble_context(state)
            state = self._node_generate(state)
            state = self._node_validate(state)
        
        processing_time = int((time.time() - start_time) * 1000)
        
        return {
            "success": len(state.get("errors", [])) == 0,
            "response": state.get("response", ""),
            "sources": state.get("sources", []),
            "intent": state.get("intent"),
            "faithfulness_score": state.get("faithfulness_score", 0),
            "model_used": state.get("model_used"),
            "processing_time_ms": processing_time,
            "errors": state.get("errors", []),
            "warnings": state.get("warnings", []),
        }
    
    def query_sync(
        self,
        query: str,
        tenant_context: Optional[Any] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Synchronous wrapper for query"""
        return asyncio.run(self.query(query, tenant_context, **kwargs))
